import os
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
