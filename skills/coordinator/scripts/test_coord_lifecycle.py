import argparse
import hashlib
import json
import os
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import coord_lifecycle as lifecycle


def completed(stdout="{}", returncode=0, stderr=""):
    return lifecycle.subprocess.CompletedProcess([], returncode, stdout, stderr)


class CoordinatorLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.adapter_env = patch.dict(os.environ, {
            "COORDINATOR_HERDR_HELPER": "/bin/true",
        })
        self.adapter_env.start()

    def tearDown(self):
        self.adapter_env.stop()

    def test_doctor_is_ready_without_optional_adapters(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(lifecycle.shutil, "which", return_value=None):
            result = lifecycle.doctor(argparse.Namespace())
        self.assertTrue(result["core"]["available"])
        self.assertTrue(result["ready"])
        self.assertFalse(result["optional_adapters"]["herdr"]["available"])
        self.assertEqual(set(result["optional_adapters"]), {"herdr"})

    def test_doctor_rejects_existing_but_incompatible_adapters(self):
        result = lifecycle.doctor(argparse.Namespace())
        self.assertFalse(result["optional_adapters"]["herdr"]["available"])
        self.assertEqual(set(result["optional_adapters"]), {"herdr"})
        self.assertIn("invalid JSON", result["optional_adapters"]["herdr"]["reason"])


    def test_run_normalizes_subprocess_timeout(self):
        with patch.object(lifecycle.subprocess, "run", side_effect=subprocess.TimeoutExpired(["adapter"], 1)):
            with self.assertRaisesRegex(lifecycle.LifecycleError, "timed out"):
                lifecycle.run(["adapter"], timeout_seconds=1)


    def test_prepare_records_file_sink_without_external_command(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(lifecycle, "run") as external:
            state_path = Path(directory) / "state.json"
            state = lifecycle.prepare(argparse.Namespace(state=str(state_path), inbox=None))
            self.assertEqual(state["return_sink"]["role"], "return-only")
            self.assertEqual(state["return_sink"]["transport"], "file")
            self.assertTrue(Path(state["return_sink"]["path"]).is_dir())
            self.assertEqual(lifecycle.load_state(state_path)["run_id"], state["run_id"])
            external.assert_not_called()
            with self.assertRaisesRegex(lifecycle.LifecycleError, "overwrite"):
                lifecycle.prepare(argparse.Namespace(state=str(state_path), inbox=None))

    def test_prepare_cleans_empty_inbox_when_state_cannot_be_persisted(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(lifecycle, "save_state", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(lifecycle.LifecycleError, "persist"):
                lifecycle.prepare(argparse.Namespace(state=str(Path(directory) / "state"), inbox=None))
            self.assertEqual(list((Path(directory) / "inbox").iterdir()), [])


    def test_verify_fails_closed_on_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "state.json"
            artifact = root / "artifact"
            artifact.write_bytes(b"evidence\n")
            lifecycle.save_state(state_path, {"version": 1, "return_sink": {}, "workers": {}, "events": []})
            actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
            result = lifecycle.verify(argparse.Namespace(state=str(state_path), artifact=str(artifact), sha256=actual))
            self.assertTrue(result["matched"])
            with self.assertRaises(lifecycle.LifecycleError):
                lifecycle.verify(argparse.Namespace(state=str(state_path), artifact=str(artifact), sha256="0" * 64))

    def test_verify_restricts_artifact_root_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact"
            artifact.write_bytes(b"ok")
            state_path = root / "state.json"
            lifecycle.save_state(state_path, {"version": 1, "return_sink": {}, "workers": {}, "events": []})
            digest = hashlib.sha256(b"ok").hexdigest()
            with self.assertRaisesRegex(lifecycle.LifecycleError, "approved root"):
                lifecycle.verify(argparse.Namespace(state=str(state_path), artifact=str(artifact), sha256=digest, root=str(root / "other")))
            with patch.object(lifecycle, "MAX_ARTIFACT_BYTES", 1):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "size limit"):
                    lifecycle.verify(argparse.Namespace(state=str(state_path), artifact=str(artifact), sha256=digest, root=str(root)))

    def test_run_task_composes_full_lifecycle_and_requires_attribution(self):
        completion = {
            "assignment_id": "assign-1", "kind": "complete", "run_id": "run-1", "task_id": "T1", "worker": "w", "artifact": "/tmp/a",
            "sha256": "a" * 64, "verify_command": ["sha256sum", "/tmp/a"], "children": [],
        }
        args = argparse.Namespace(
            state="/tmp/state", inbox=None,
            worker="w", kind="pi", model="chosen", provider="openai", effort="high", workspace="w1", cwd="/repo", brief="/tmp/brief",
            label=None, wait=30, admission_timeout_ms=5000, settle_timeout_ms=30000,
            min_children=0,
            task_id="T1", verify_command=["sha256sum", "/tmp/a"], verify_timeout_seconds=30,
        )
        unrelated = {"envelope": {"from": "other-result", "worker": "other", "assignment_id": "assign-1", "message_id": "b" * 32}, "completion": completion}
        with patch.object(lifecycle, "prepare", return_value={"run_id": "run-1"}), patch.object(lifecycle, "save_state"), patch.object(lifecycle, "load_state", return_value={"run_id": "run-1", "workers": {"w": {"assignment_id": "assign-1", "pane_id": "w1:p2"}}}), patch.object(lifecycle, "acknowledge"), patch.object(lifecycle, "start_worker"), patch.object(lifecycle, "dispatch"), patch.object(lifecycle, "receive", side_effect=[[unrelated], [{"envelope": {"from": "w-result", "worker": "w", "assignment_id": "assign-1", "message_id": "a" * 32}, "completion": completion}]]) as received, patch.object(lifecycle, "verify", return_value={"matched": True}), patch.object(lifecycle, "run", return_value=completed('{"result":{"agent":{}}}')), patch.object(lifecycle, "reconcile", return_value={"w": {"status": "closed"}}), patch.object(lifecycle, "stop", return_value={"stopped": "sink"}):
            result = lifecycle.run_task(args)
        self.assertTrue(result["verification"]["matched"])
        self.assertEqual(result["completion"]["worker"], "w")
        self.assertEqual(received.call_count, 2)

    def test_completion_requires_exact_task_and_coordinator_command(self):
        base = {
            "assignment_id": "assign-1", "kind": "complete", "run_id": "run-1", "task_id": "wrong", "worker": "w", "artifact": "/repo/a",
            "sha256": "a" * 64, "verify_command": ["false"], "children": [],
        }
        item = {"envelope": {"from": "w-result", "worker": "w", "assignment_id": "assign-1", "message_id": "a" * 32}, "completion": base}
        self.assertIsNone(lifecycle.validate_completion(item, state={"run_id": "run-1", "workers": {"w": {"assignment_id": "assign-1", "pane_id": "w1:p2"}}}, worker="w", task_id="T1", verify_command=["true"], min_children=0))
        base["task_id"] = "T1"
        self.assertIsNone(lifecycle.validate_completion(item, state={"run_id": "run-1", "workers": {"w": {"assignment_id": "assign-1", "pane_id": "w1:p2"}}}, worker="w", task_id="T1", verify_command=["true"], min_children=0))

    def test_declared_children_must_be_structured_and_settled(self):
        completion = {
            "assignment_id": "assign-1", "kind": "complete", "run_id": "run-1", "task_id": "T1", "worker": "w", "artifact": "/repo/a",
            "sha256": "a" * 64, "verify_command": ["true"], "children": ["fake"],
        }
        item = {"envelope": {"from": "w-result", "worker": "w", "assignment_id": "assign-1", "message_id": "a" * 32}, "completion": completion}
        self.assertIsNone(lifecycle.validate_completion(item, state={"run_id": "run-1", "workers": {"w": {"assignment_id": "assign-1", "pane_id": "w1:p2"}}}, worker="w", task_id="T1", verify_command=["true"], min_children=1))
        with patch.object(lifecycle, "run", return_value=completed('{"result":{"agent":{"agent_status":"working"}}}')):
            with self.assertRaisesRegex(lifecycle.LifecycleError, "not settled"):
                lifecycle.reconcile_children([{"name": "child-1"}])

    def test_run_task_can_require_declared_children(self):
        completion = {
            "assignment_id": "assign-1", "kind": "complete", "run_id": "run-1", "task_id": "T1", "worker": "w", "artifact": "/tmp/a",
            "sha256": "a" * 64, "verify_command": ["sha256sum", "/tmp/a"], "children": [],
        }
        args = argparse.Namespace(
            state="/tmp/state", inbox=None,
            worker="w", kind="pi", model="chosen", provider="openai", effort="high", workspace="w1", cwd="/repo", brief="/tmp/brief",
            label=None, wait=0, admission_timeout_ms=5000, settle_timeout_ms=30000,
            min_children=1,
            task_id="T1", verify_command=["sha256sum", "/tmp/a"], verify_timeout_seconds=30,
        )
        with patch.object(lifecycle, "prepare", return_value={"run_id": "run-1"}), patch.object(lifecycle, "save_state"), patch.object(lifecycle, "load_state", return_value={"run_id": "run-1", "workers": {"w": {"assignment_id": "assign-1", "pane_id": "w1:p2"}}}), patch.object(lifecycle, "acknowledge"), patch.object(lifecycle, "start_worker"), patch.object(lifecycle, "dispatch"), patch.object(lifecycle, "receive", return_value=[{"envelope": {"from": "w-result", "worker": "w", "assignment_id": "assign-1", "message_id": "a" * 32}, "completion": completion}]), patch.object(lifecycle, "cleanup_failed_run", return_value={"sink": {"stopped": "sink"}}) as cleanup:
            with self.assertRaisesRegex(lifecycle.LifecycleError, "at least 1"):
                lifecycle.run_task(args)
        cleanup.assert_called_once()

    def test_run_task_rejects_stale_run_id_from_same_sender(self):
        completion = {
            "run_id": "old-run", "task_id": "T1", "worker": "w", "artifact": "/tmp/a",
            "sha256": "a" * 64, "verify_command": ["sha256sum", "/tmp/a"], "children": [],
        }
        args = argparse.Namespace(
            state="/tmp/state", inbox=None,
            worker="w", kind="pi", model="chosen", provider="openai", effort="high", workspace="w1", cwd="/repo", brief="/tmp/brief",
            label=None, wait=0, admission_timeout_ms=5000, settle_timeout_ms=30000,
            min_children=0,
            task_id="T1", verify_command=["sha256sum", "/tmp/a"], verify_timeout_seconds=30,
        )
        with patch.object(lifecycle, "prepare", return_value={"run_id": "new-run"}), patch.object(lifecycle, "save_state"), patch.object(lifecycle, "load_state", return_value={"run_id": "run-1", "workers": {"w": {"assignment_id": "assign-1", "pane_id": "w1:p2"}}}), patch.object(lifecycle, "acknowledge"), patch.object(lifecycle, "start_worker"), patch.object(lifecycle, "dispatch"), patch.object(lifecycle, "receive", return_value=[{"envelope": {"from": "w-result", "worker": "w", "assignment_id": "assign-1", "message_id": "a" * 32}, "completion": completion}]), patch.object(lifecycle, "cleanup_failed_run", return_value={"sink": {"stopped": "sink"}}) as cleanup:
            with self.assertRaisesRegex(lifecycle.LifecycleError, "no attributable completion"):
                lifecycle.run_task(args)
        cleanup.assert_called_once()

    def test_run_task_cleans_up_unexpected_response_shape(self):
        args = argparse.Namespace(
            state="/tmp/state", inbox=None,
            worker="w", kind="pi", model="chosen", provider="openai", effort="high", workspace="w1", cwd="/repo", brief="/tmp/brief",
            label=None, wait=30, admission_timeout_ms=5000, settle_timeout_ms=30000,
            min_children=0,
            task_id="T1", verify_command=["sha256sum", "/tmp/a"], verify_timeout_seconds=30,
        )
        with patch.object(lifecycle, "prepare", return_value={"run_id": "run-1"}), patch.object(lifecycle, "save_state"), patch.object(lifecycle, "start_worker", side_effect=KeyError("result")), patch.object(lifecycle, "cleanup_failed_run", return_value={"sink": {"stopped": "sink"}}) as cleanup:
            with self.assertRaises(lifecycle.LifecycleError):
                lifecycle.run_task(args)
        cleanup.assert_called_once()

    def test_reconcile_closes_only_owned_settled_tabs(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            lifecycle.save_state(state_path, {
                "version": 1,
                "return_sink": {},
                "workers": {"w": {"pane_id": "w1:p2", "owned_tab": True, "tab_id": "w1:t2"}},
                "events": [],
            })
            replies = [completed('{"result":{"agent":{"agent_status":"done"}}}'), completed('{"result":{}}')]
            with patch.object(lifecycle, "run", side_effect=replies) as mocked:
                result = lifecycle.reconcile(argparse.Namespace(state=str(state_path), disposition="close-owned"))
            self.assertEqual(result["w"]["status"], "closed")
            self.assertEqual(mocked.call_args_list[1].args[0], ["/usr/bin/true", "close", "w1:p2", "--owned-tab", "w1:t2"])

    def test_reconcile_fails_closed_on_transient_agent_error(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            lifecycle.save_state(state_path, {"version": 1, "return_sink": {}, "workers": {"w": {"pane_id": "w1:p2", "owned_tab": True, "tab_id": "w1:t2"}}, "events": []})
            with patch.object(lifecycle, "run", return_value=completed("", returncode=1, stderr="socket unavailable")) as mocked:
                with self.assertRaisesRegex(lifecycle.LifecycleError, "not settled"):
                    lifecycle.reconcile(argparse.Namespace(state=str(state_path), disposition="close-owned"))
            self.assertEqual(mocked.call_count, 1)

    def test_failed_cleanup_uses_harness_cancel_key(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            lifecycle.save_state(state_path, {"version": 1, "return_sink": {"name": "sink"}, "workers": {"w": {"pane_id": "w1:p2", "owned_tab": True}}, "events": []})
            replies = [completed('{"result":{"agent":{"agent_status":"working"}}}'), completed('{}'), completed('{}')]
            with patch.object(lifecycle, "run", side_effect=replies) as mocked, patch.object(lifecycle, "reconcile", return_value={}), patch.object(lifecycle, "stop", return_value={}):
                lifecycle.cleanup_failed_run(state_path, "w")
            self.assertEqual(mocked.call_args_list[0].args[0][-2:], ["stop", "w1:p2"])


if __name__ == "__main__":
    unittest.main()
