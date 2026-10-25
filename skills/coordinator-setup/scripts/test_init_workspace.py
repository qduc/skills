from datetime import date
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import init_workspace

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


class InitWorkspaceTests(unittest.TestCase):
    def test_creates_filled_workspace_with_commit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, GIT_ENV):
            target, committed = init_workspace.create(
                Path(tmp) / "ws", "demo", "/src/demo", today=date(2026, 1, 2))
            self.assertTrue(committed)
            for name in ["AGENTS.md", "README.md", "STATUS.md", ".gitignore",
                         "decisions/README.md", "knowledge/README.md",
                         "tasks/README.md", "sessions/README.md"]:
                self.assertTrue((target / name).is_file(), name)
            text = "".join(p.read_text() for p in target.rglob("*.md"))
            self.assertNotIn("{{", text)
            self.assertIn("/src/demo", (target / "AGENTS.md").read_text())
            self.assertIn("2026-01-02", (target / "STATUS.md").read_text())
            status = subprocess.run(["git", "status", "--porcelain"], cwd=target,
                                    capture_output=True, text=True, check=True)
            self.assertEqual(status.stdout, "")

    def test_refuses_non_empty_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "keep.txt").write_text("mine")
            with self.assertRaises(ValueError):
                init_workspace.create(tmp, "demo", "/src/demo", git=False)
            self.assertEqual((Path(tmp) / "keep.txt").read_text(), "mine")

    def test_rejects_relative_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                init_workspace.create(Path(tmp) / "ws", "demo", "src", git=False)
            self.assertFalse((Path(tmp) / "ws").exists())


if __name__ == "__main__":
    unittest.main()
