import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import coord_claimcheck as claimcheck

SCRIPT = Path(claimcheck.__file__).resolve()


class ClaimcheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="claimcheck-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.git("config", "commit.gpgsign", "false")
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_export.py").write_text("def test_ok():\n    pass\n")
        self.git("add", "tests/test_export.py")
        self.git("commit", "-q", "-m", "add test")
        self.sha = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True)

    def report(self, text):
        path = Path(self.temporary.name) / "report.md"
        path.write_text(text)
        return path

    def run_check(self, text, cwd=None):
        path = self.report(text)
        before = sorted((item, item.stat().st_mtime_ns) for item in self.repo.rglob("*") if item.is_file())
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(cwd or self.repo), "--report", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        after = sorted((item, item.stat().st_mtime_ns) for item in self.repo.rglob("*") if item.is_file())
        self.assertEqual(before, after, "claimcheck must be read-only")
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        return result

    def test_real_hash_and_test_path_pass(self):
        result = self.run_check(
            f"Introduced in {self.sha[:7]} ({self.sha}). Gate: tests/test_export.py::test_ok\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_unknown_hash_and_missing_test_block(self):
        result = self.run_check(
            "See cafebabe1234 and tests/test_missing.py for the regression.\n"
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("blocker: commit cafebabe1234 does not resolve", result.stdout)
        self.assertIn("blocker: test path tests/test_missing.py is not a file", result.stdout)

    def test_short_token_digest_and_url_are_not_citations(self):
        digest = "a" * 64
        result = self.run_check(
            f"build abcdef now. digest {digest}. See https://example.com/tests/test_export.py.\n"
            "Gate tests/test_export.py passed.\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_prose_digits_are_commit_citations(self):
        result = self.run_check("Retry count 1234567 on tests/test_export.py.\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("commit 1234567 does not resolve", result.stdout)

    def test_uuid_fragments_in_rollout_filename_are_not_commit_citations(self):
        report = (
            "rollout-2026-09-28T00-02-18-01a0e3d1-4737-7893-8dc2-c48dc10f5ca8.jsonl\n"
            "rollout-2026-09-28T00-02-18-01a0e5e7-1234-5678-9abc-7df71c0f54a0.jsonl\n"
        )
        result = self.run_check(report)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_explicit_unknown_commit_citations_still_block(self):
        result = self.run_check("Commit `cafebabe` is missing; commit 1234567 also failed.\n")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("commit cafebabe does not resolve", result.stdout)
        self.assertIn("commit 1234567 does not resolve", result.stdout)

    def test_hex_substrings_in_prose_words_are_not_commit_citations(self):
        result = self.run_check("Commit succeeded; checker exceeded expectations.\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(claimcheck.commits("commit succeeded, cafebabe"), ["cafebabe"])

    def test_hex_task_path_components_are_not_commit_citations(self):
        result = self.run_check(
            "Probe /tmp/tasks/a4a30412c9a74458a805da1244cafce4/probe.ts passed.\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(claimcheck.commits("tasks/cafebabe/report.md; commit deadbeef"), ["deadbeef"])

    def test_hex_owner_id_is_not_a_commit_citation(self):
        result = self.run_check(
            'The report included owner claude-coord-20260928-e09fed0d in pasted JSON.\n'
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_absolute_test_paths_stay_inside_cwd(self):
        inside = (self.repo / "tests" / "test_export.py").resolve()
        outside_dir = Path("/tmp/cc-outside")
        outside_dir.mkdir(exist_ok=True)
        outside = outside_dir / "test_other.py"
        outside.write_text("pass\n")
        self.addCleanup(outside.unlink, missing_ok=True)
        self.assertEqual(claimcheck.test_paths(f"see {inside}"), [str(inside)])
        self.assertTrue(claimcheck.resolves_test(self.repo.resolve(), str(inside)))
        self.assertEqual(claimcheck.test_paths(f"see {outside}"), [str(outside)])
        self.assertFalse(claimcheck.resolves_test(self.repo.resolve(), str(outside)))
        result = self.run_check(f"Ran {outside} and tests/test_export.py.\n")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f"test path {outside} is not a file under", result.stdout)
        self.assertNotIn("test_export.py", result.stdout)

    def test_dotted_unittest_id_resolves_through_module_file(self):
        pkg = self.repo / "pkg"
        pkg.mkdir()
        (pkg / "test_mod.py").write_text("class Cls:\n    def test_name(self):\n        pass\n")
        self.git("add", "pkg/test_mod.py")
        self.git("commit", "-q", "-m", "add pkg test")
        result = self.run_check("See test_mod.Cls.test_name for the regression.\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")
        missing = self.run_check("See test_absent.Cls.test_name for the regression.\n")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("test path test_absent.Cls.test_name is not a file", missing.stdout)

    def test_package_qualified_dotted_ids_resolve_longest_module_suffix(self):
        nested = self.repo / "tests" / "test_mod.py"
        nested.parent.mkdir(exist_ok=True)
        nested.write_text("pass\n")
        self.git("add", "tests/test_mod.py")
        self.git("commit", "-q", "-m", "add nested test")
        existing = self.run_check("See tests.test_mod.Cls.test_name.\n")
        self.assertEqual(existing.returncode, 0, existing.stdout + existing.stderr)

        (self.repo / "tests.py").write_text("pass\n")
        self.git("add", "tests.py")
        self.git("commit", "-q", "-m", "add decoy")
        nested.unlink()
        self.git("rm", "-q", "tests/test_mod.py")
        self.git("commit", "-q", "-m", "remove nested test")
        absent = self.run_check("See tests.test_mod.Cls.test_name.\n")
        self.assertEqual(absent.returncode, 1, absent.stdout)
        self.assertIn("test path tests.test_mod.Cls.test_name is not a file", absent.stdout)

    def test_package_prefix_before_test_module_is_checked(self):
        missing = self.run_check("See pkg.test_mod.Cls.test_name.\n")
        self.assertEqual(missing.returncode, 1, missing.stdout)
        self.assertIn("test path pkg.test_mod.Cls.test_name is not a file", missing.stdout)

    def test_package_qualified_id_does_not_resolve_to_different_package(self):
        other = self.repo / "other" / "test_mod.py"
        other.parent.mkdir()
        other.write_text("pass\n")
        self.git("add", "other/test_mod.py")
        self.git("commit", "-q", "-m", "add other package test")
        result = self.run_check("See tests.test_mod.Cls.test_name.\n")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("test path tests.test_mod.Cls.test_name is not a file", result.stdout)

    def test_bare_basename_resolves_through_git_ls_files(self):
        ok = self.run_check("Focused file `test_export.py`.\n")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        missing = self.run_check("Focused file `test_nowhere.py`.\n")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("blocker: test path test_nowhere.py is not a file", missing.stdout)
        nested = self.run_check("See tests/missing/test_export.py.\n")
        self.assertEqual(nested.returncode, 1)
        self.assertIn("blocker: test path tests/missing/test_export.py is not a file", nested.stdout)
        untracked = self.repo / "tests" / "test_untracked.py"
        untracked.write_text("pass\n")
        self.addCleanup(untracked.unlink, missing_ok=True)
        bare_report = self.report("Also `test_untracked.py`.\n")
        bare = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(self.repo), "--report", str(bare_report)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(bare.returncode, 1, bare.stdout)
        self.assertIn("test path test_untracked.py", bare.stdout)

    def test_bare_basename_walks_outside_a_git_repo(self):
        root = Path(self.temporary.name) / "plain"
        (root / "nested").mkdir(parents=True)
        (root / "nested" / "test_plain.py").write_text("pass\n")
        found = self.report("See test_plain.py.\n")
        ok = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(root), "--report", str(found)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        absent = self.report("See test_absent.py.\n")
        blocked = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(root), "--report", str(absent)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("test path test_absent.py", blocked.stdout)

    def test_usage_errors(self):
        missing = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(self.repo), "--report", str(self.repo / "nope.md")],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(missing.returncode, 2)
        not_dir = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(self.repo / "tests" / "test_export.py"), "--report", str(self.report("x"))],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(not_dir.returncode, 2)


if __name__ == "__main__":
    unittest.main()
