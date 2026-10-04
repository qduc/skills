"""Exercise the shipped setup script against isolated, real Git repositories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/setup-protocols.sh"
RESOLVER = ROOT / "skills/coordinator/scripts/coord_protocol.py"


class SetupProtocolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="protocol setup ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "checkout with 'quotes' \"double quotes\" $dollars `ticks` \\slashes"
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy2(SCRIPT, self.root / "scripts/setup-protocols.sh")
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith("GIT_") or key in {
                "COORDINATOR_PROTOCOL_CATALOG", "MATT_SKILLS_URL", "CURSOR_PLUGINS_URL"
            }:
                self.env.pop(key)
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_ALLOW_PROTOCOL="file", GIT_TERMINAL_PROMPT="0",
                        GIT_AUTHOR_NAME="Setup test", GIT_AUTHOR_EMAIL="setup@example.invalid",
                        GIT_COMMITTER_NAME="Setup test", GIT_COMMITTER_EMAIL="setup@example.invalid")
        self.plugins = self.make_remote("plugins", "pstack/skills/bug-fix/SKILL.md")
        self.matt = self.make_remote("matt", "skills/architect/SKILL.md")
        # Redirect the real public defaults in Git itself. This also reproduces
        # defects in older setup versions without permitting any network access.
        self.env.update(GIT_CONFIG_COUNT="2",
                        GIT_CONFIG_KEY_0=f"url.{self.plugins.as_uri()}.insteadOf",
                        GIT_CONFIG_VALUE_0="https://github.com/cursor/plugins.git",
                        GIT_CONFIG_KEY_1=f"url.{self.matt.as_uri()}.insteadOf",
                        GIT_CONFIG_VALUE_1="https://github.com/mattpocock/skills.git")
        self.external = self.root / ".external"
        self.plugins_checkout = self.external / "cursor-plugins"
        self.matt_checkout = self.external / "mattpocock-skills"

    def command(self, *argv, check=True, env=None):
        result = subprocess.run(argv, cwd=self.base, env=env or self.env,
                                text=True, capture_output=True, timeout=30)
        if check and result.returncode:
            self.fail(f"Command {argv!r} failed ({result.returncode}):\n"
                      f"{result.stdout}\n{result.stderr}")
        return result

    def git(self, repo, *args, check=True):
        return self.command("git", "-C", str(repo), *args, check=check)

    def make_remote(self, name, skill):
        repo = self.base / name
        repo.mkdir()
        self.git(repo, "init", "--initial-branch=main")
        path = repo / skill
        path.parent.mkdir(parents=True)
        path.write_text(f"---\nname: {path.parent.name}\n---\nA real test skill.\n")
        (repo / "README.md").write_text("Fixture repository\n")
        (repo / ".gitignore").write_text("scratch/\n")
        (repo / "outside-catalog").mkdir()
        (repo / "outside-catalog/unneeded.txt").write_text("Not a skill\n")
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-m", "Create setup fixture")
        return repo

    def setup(self, check=True):
        return self.command("sh", str(self.root / "scripts/setup-protocols.sh"), check=check)

    def catalog_environment(self):
        result = self.command("sh", "-c", '. "$1"; printf "%s" "$COORDINATOR_PROTOCOL_CATALOG"',
                              "sh", str(self.external / "catalog.env"))
        expected = ":".join(str(p.resolve()) for p in (
            self.plugins_checkout / "pstack/skills", self.matt_checkout / "skills"))
        self.assertEqual(result.stdout, expected)
        return dict(self.env, COORDINATOR_PROTOCOL_CATALOG=result.stdout)

    def advance(self, repo, relative):
        path = repo / relative
        path.write_text(path.read_text() + "Upstream update\n")
        self.git(repo, "add", relative)
        self.git(repo, "commit", "-m", "Advance setup fixture")

    def test_fresh_repeat_and_existing_coordinator_resolution(self):
        self.setup()
        env = self.catalog_environment()
        for protocol in ("bug-fix", "architect"):
            result = self.command(sys.executable, str(RESOLVER), "resolve", "--protocol", protocol, env=env)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["event"], "protocol_selected")
            self.assertTrue(Path(payload["skill"]).is_file())
        self.assertFalse((self.plugins_checkout / "outside-catalog").exists())
        self.advance(self.plugins, "pstack/skills/bug-fix/SKILL.md")
        self.advance(self.matt, "skills/architect/SKILL.md")
        self.setup()
        self.setup()
        self.catalog_environment()
        for repo, checkout in ((self.plugins, self.plugins_checkout), (self.matt, self.matt_checkout)):
            self.assertEqual(self.git(repo, "rev-parse", "HEAD").stdout,
                             self.git(checkout, "rev-parse", "HEAD").stdout)

    def test_unrelated_existing_destination_is_preserved(self):
        self.matt_checkout.mkdir(parents=True)
        note = self.matt_checkout / "personal.txt"
        note.write_text("Keep this\n")
        result = self.setup(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing", result.stderr.lower())
        self.assertEqual(note.read_text(), "Keep this\n")
        self.assertFalse(self.plugins_checkout.exists(), "preflight both before modifying either")

    def test_local_checkout_changes_are_preserved(self):
        for kind in ("tracked", "staged", "untracked", "ignored", "commit"):
            with self.subTest(kind=kind):
                if self.external.exists():
                    shutil.rmtree(self.external)
                self.setup()
                tracked = self.matt_checkout / "skills/architect/SKILL.md"
                if kind in {"tracked", "staged", "commit"}:
                    tracked.write_text(tracked.read_text() + "Local edit\n")
                    note = tracked
                    if kind in {"staged", "commit"}:
                        self.git(self.matt_checkout, "add", ".")
                    if kind == "commit":
                        self.git(self.matt_checkout, "commit", "-m", "Local user work")
                else:
                    note = self.matt_checkout / ("scratch/note.txt" if kind == "ignored" else "note.txt")
                    note.parent.mkdir(exist_ok=True)
                    note.write_text("Local work\n")
                content = note.read_bytes()
                old_head = self.git(self.matt_checkout, "rev-parse", "HEAD").stdout
                old_status = self.git(self.matt_checkout, "status", "--porcelain", "--ignored").stdout
                catalog = (self.external / "catalog.env").read_bytes()
                plugins_head = self.git(self.plugins_checkout, "rev-parse", "HEAD").stdout
                self.advance(self.plugins, "pstack/skills/bug-fix/SKILL.md")
                self.advance(self.matt, "skills/architect/SKILL.md")
                result = self.setup(check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("refusing", result.stderr.lower())
                self.assertEqual(note.read_bytes(), content)
                self.assertEqual(self.git(self.matt_checkout, "rev-parse", "HEAD").stdout, old_head)
                self.assertEqual(self.git(self.matt_checkout, "status", "--porcelain", "--ignored").stdout, old_status)
                self.assertEqual((self.external / "catalog.env").read_bytes(), catalog)
                self.assertEqual(self.git(self.plugins_checkout, "rev-parse", "HEAD").stdout, plugins_head)

    def test_symlink_destinations_and_catalog_are_preserved(self):
        other = self.base / "personal"
        other.mkdir()
        note = other / "note.txt"
        note.write_text("Keep this\n")
        for destination in (self.external, self.plugins_checkout, self.external / "catalog.env"):
            with self.subTest(destination=destination.name):
                if self.external.exists():
                    shutil.rmtree(self.external)
                if destination != self.external:
                    self.external.mkdir()
                destination.symlink_to(other, target_is_directory=True)
                result = self.setup(check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("refusing", result.stderr.lower())
                self.assertTrue(destination.is_symlink())
                self.assertEqual(note.read_text(), "Keep this\n")
                destination.unlink()

    def test_unrelated_or_edited_catalog_is_preserved(self):
        self.external.mkdir()
        catalog = self.external / "catalog.env"
        for content in ("Personal shell configuration\n",
                        '# Generated by scripts/setup-protocols.sh; do not edit.\nexport CUSTOM=value\n'):
            with self.subTest(content=content):
                catalog.write_text(content)
                result = self.setup(check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("catalog", result.stderr.lower())
                self.assertIn("refusing", result.stderr.lower())
                self.assertEqual(catalog.read_text(), content)
                self.assertFalse(self.plugins_checkout.exists())

    def test_legacy_catalog_is_migrated(self):
        self.setup()
        catalog = self.external / "catalog.env"
        value = ":".join(str(p) for p in (self.plugins_checkout / "pstack/skills", self.matt_checkout / "skills"))
        catalog.write_text(f"export COORDINATOR_PROTOCOL_CATALOG={value}\n")
        self.setup()
        self.catalog_environment()
        self.assertTrue(catalog.read_text().startswith("# Generated by"))

    def test_explicit_local_source_overrides(self):
        self.env.update(MATT_SKILLS_URL=self.matt.as_uri(), CURSOR_PLUGINS_URL=self.plugins.as_uri())
        self.setup()
        self.setup()
        self.catalog_environment()
        self.assertEqual(self.git(self.matt_checkout, "config", "--get", "remote.origin.url").stdout.strip(),
                         self.matt.as_uri())

    def test_relative_local_sources_fresh_repeat_and_origin_validation(self):
        for spaced in (False, True):
            with self.subTest(spaced=spaced):
                if self.external.exists():
                    shutil.rmtree(self.external)
                if spaced:
                    self.matt = self.matt.rename(self.base / "matt source with spaces")
                    self.plugins = self.plugins.rename(self.base / "plugins source with spaces")
                matt_source = f"./{self.matt.name}"
                plugins_source = f"./{self.plugins.name}"
                self.env.update(MATT_SKILLS_URL=matt_source, CURSOR_PLUGINS_URL=plugins_source)
                self.setup()
                self.catalog_environment()
                self.advance(self.plugins, "pstack/skills/bug-fix/SKILL.md")
                self.advance(self.matt, "skills/architect/SKILL.md")
                self.setup()
                self.setup()
                for repo, checkout, source in ((self.matt, self.matt_checkout, matt_source),
                                               (self.plugins, self.plugins_checkout, plugins_source)):
                    self.assertEqual(self.git(repo, "rev-parse", "HEAD").stdout,
                                     self.git(checkout, "rev-parse", "HEAD").stdout)
                    self.assertEqual(self.git(checkout, "config", "--get", "remote.origin.url").stdout.strip(),
                                     f"{self.base}/{source}")
                self.git(self.matt_checkout, "remote", "set-url", "origin", str(self.plugins))
                head = self.git(self.matt_checkout, "rev-parse", "HEAD").stdout
                catalog = (self.external / "catalog.env").read_bytes()
                result = self.setup(check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("origin", result.stderr.lower())
                self.assertEqual(self.git(self.matt_checkout, "rev-parse", "HEAD").stdout, head)
                self.assertEqual((self.external / "catalog.env").read_bytes(), catalog)

    def test_detached_checkout_is_preserved(self):
        self.setup()
        self.git(self.matt_checkout, "checkout", "--detach")
        head = self.git(self.matt_checkout, "rev-parse", "HEAD").stdout
        result = self.setup(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("detached", result.stderr.lower())
        self.assertEqual(self.git(self.matt_checkout, "rev-parse", "HEAD").stdout, head)

    def test_bad_catalog_path_is_rejected(self):
        old_root = self.root
        self.root = self.base / "colon:path"
        shutil.copytree(old_root, self.root)
        result = self.setup(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("colon", result.stderr.lower())
        self.assertFalse((self.root / ".external").exists())

    def test_wrong_origin_is_preserved(self):
        self.setup()
        self.git(self.matt_checkout, "remote", "set-url", "origin", str(self.plugins))
        head = self.git(self.matt_checkout, "rev-parse", "HEAD").stdout
        result = self.setup(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origin", result.stderr.lower())
        self.assertEqual(self.git(self.matt_checkout, "rev-parse", "HEAD").stdout, head)

    def test_optional_skills_remain_optional(self):
        result = self.command(sys.executable, str(RESOLVER), "resolve", "--protocol", "bug-fix")
        self.assertEqual(json.loads(result.stdout)["event"], "protocol_fallback")
        self.assertFalse(self.external.exists())


if __name__ == "__main__":
    unittest.main()
