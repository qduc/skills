import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import host_profile


class HostProfileTests(unittest.TestCase):
    def test_discovery_does_not_require_external_tools(self):
        with patch("host_profile.shutil.which", return_value=None):
            profile = host_profile.discover()
        self.assertTrue(all(value is None for value in profile["executables"].values()))
        self.assertEqual(profile["adapters"], {})
        self.assertEqual(profile["memory_sidecar"], "disabled")
        self.assertEqual(host_profile.validate(profile), profile)

    def test_explicit_config_path_with_spaces(self):
        with patch.dict(os.environ, {"COORDINATOR_CONFIG_HOME": "/tmp/host config"}):
            self.assertEqual(host_profile.profile_path(), Path("/tmp/host config/host.json"))

    def test_relative_config_is_rejected(self):
        with patch.dict(os.environ, {"COORDINATOR_CONFIG_HOME": "relative"}):
            with self.assertRaises(ValueError):
                host_profile.profile_path()

    def test_non_linux_process_is_unavailable(self):
        with patch("host_profile.platform.system", return_value="Darwin"):
            self.assertFalse(host_profile.discover()["prerequisites"]["linux_process"])

    def test_sidecar_and_relative_catalog_are_rejected(self):
        for field, value in [("memory_sidecar", "enabled"), ("catalogs", ["relative"])]:
            profile = host_profile.discover()
            profile[field] = value
            with self.assertRaises(ValueError):
                host_profile.validate(profile)


# Fake agent CLIs: the worker follows the probe instruction; the judge prints JSON.
GOOD_WORKER = ("import re,sys; m=re.search(r'named (\\S+) .*text: (.+)', sys.argv[1]); "
               "open(m.group(1),'w').write(m.group(2).splitlines()[0])")
IDLE_WORKER = "import sys"
GOOD_JUDGE = "import sys; sys.stdin.read(); print('thinking...'); print('{\"probe\": \"ok\"}')"
ENVELOPE_JUDGE = ("import json,sys; sys.stdin.read(); "
                  "print(json.dumps({'type': 'result', 'result': 'Sure: {\"probe\": \"ok\"}'}))")


class DriverProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict(os.environ, {"COORDINATOR_CONFIG_HOME": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)
        self.workers_file = Path(self.tmp.name) / "workers.json"

    def worker(self, code, model="m"):
        return {"route": {"harness": "fake", "model": model}, "argv": [sys.executable, "-c", code, "{prompt}"]}

    def test_worker_probe_needs_the_file_written(self):
        self.assertTrue(host_profile.probe_worker(self.worker(GOOD_WORKER)["argv"])["ok"])
        failed = host_profile.probe_worker(self.worker(IDLE_WORKER)["argv"])
        self.assertFalse(failed["ok"])
        self.assertIn("probe file", failed["reason"])

    def test_worker_that_waits_for_input_times_out(self):
        result = host_profile.probe_worker([sys.executable, "-c", "import time; time.sleep(30)", "{prompt}"], timeout=1)
        self.assertFalse(result["ok"])
        self.assertIn("timed out", result["reason"])

    def test_worker_argv_needs_a_prompt_slot(self):
        with self.assertRaisesRegex(ValueError, "prompt"):
            host_profile.probe_worker([sys.executable, "-c", GOOD_WORKER])

    def test_judge_probe_reads_stdin_and_unwraps_envelopes(self):
        for code in (GOOD_JUDGE, ENVELOPE_JUDGE):
            self.assertTrue(host_profile.probe_judge([sys.executable, "-c", code])["ok"])
        self.assertFalse(host_profile.probe_judge([sys.executable, "-c", "print('ok')"])["ok"])

    def test_set_driver_saves_only_verified_routes_and_keeps_the_rest(self):
        existing = host_profile.discover()
        existing["adapters"]["herdr"] = {"status": "verified"}
        host_profile.profile_path().write_text(json.dumps(existing))
        self.workers_file.write_text(json.dumps([self.worker(GOOD_WORKER, "works"), self.worker(IDLE_WORKER, "idle")]))
        result = host_profile.set_driver(json.loads(self.workers_file.read_text()),
                                         [sys.executable, "-c", "print('no json')"])
        self.assertTrue(result["saved"])
        saved = json.loads(host_profile.profile_path().read_text())
        self.assertEqual(saved["adapters"]["herdr"], {"status": "verified"})
        driver = saved["adapters"]["driver"]
        self.assertEqual([w["route"]["model"] for w in driver["workers"]], ["works"])
        self.assertNotIn("judge", driver)  # the failing judge was not saved
        self.assertEqual(host_profile.validate(saved), saved)

    def test_set_driver_saves_nothing_when_every_probe_fails(self):
        result = host_profile.set_driver([self.worker(IDLE_WORKER)], None)
        self.assertFalse(result["saved"])
        self.assertFalse(host_profile.profile_path().exists())


if __name__ == "__main__":
    unittest.main()
