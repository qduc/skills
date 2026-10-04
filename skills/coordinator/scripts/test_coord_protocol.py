import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

import coord_protocol


COORDINATOR_OWNS = [
    "outcome",
    "scope",
    "ownership",
    "dependencies",
    "authority",
    "acceptance",
    "integration",
]
PROTOCOL_OWNS = ["engineering_method", "local_verification"]


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("COORDINATOR_PROTOCOL_CATALOG", None)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("COORDINATOR_PROTOCOL_CATALOG", None)
        else:
            os.environ["COORDINATOR_PROTOCOL_CATALOG"] = self._saved

    def run_cli(self, argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = coord_protocol.main(argv)
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        return code, json.loads(lines[0])

    def write_skill(self, directory, relative, frontmatter, body="Local method notes.\n"):
        path = Path(directory) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + frontmatter.strip() + "\n---\n" + body)
        return path

    def test_installed_protocol_can_be_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            # A path named architect must not win without a matching declaration.
            self.write_skill(directory, "architect/SKILL.md", "name: notes\n")
            chosen = self.write_skill(
                directory,
                "methods/design/SKILL.md",
                "name: architect\ndescription: design method\n",
            )
            code, event = self.run_cli([
                "resolve", "--protocol", "architect", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["event"], "protocol_selected")
            self.assertEqual(event["protocol"], "architect")
            self.assertIsNone(event["reason"])
            self.assertEqual(event["workflow"], "execution_protocol")
            self.assertEqual(event["skill"], str(chosen.resolve()))
            self.assertEqual(event["skill_name"], "architect")

    def test_coordinator_responsibilities_remain_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_skill(directory, "methods/design/SKILL.md", "name: architect\n")
            code, event = self.run_cli([
                "resolve", "--protocol", "architect", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["coordinator_owns"], COORDINATOR_OWNS)
            self.assertEqual(event["protocol_owns"], PROTOCOL_OWNS)
            self.assertIs(event["accepted"], False)
            self.assertEqual(event["disposition"], "worker_evidence")

            declared = self.write_skill(
                directory,
                "repairs/ledger/SKILL.md",
                "name: ledger-repair\nexecution-protocol: bug-fix\n",
                body="Apply the declared repair method and verify it locally.\n",
            )
            code, event = self.run_cli([
                "resolve", "--protocol", "bug-fix", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["event"], "protocol_selected")
            self.assertEqual(event["skill"], str(declared.resolve()))
            self.assertEqual(event["skill_name"], "ledger-repair")
            self.assertEqual(event["workflow"], "execution_protocol")
            self.assertEqual(event["coordinator_owns"], COORDINATOR_OWNS)
            self.assertEqual(event["protocol_owns"], PROTOCOL_OWNS)
            self.assertIs(event["accepted"], False)
            self.assertEqual(event["disposition"], "worker_evidence")

    def test_missing_protocols_fall_back_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            code, event = self.run_cli([
                "resolve", "--protocol", "refactor", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["event"], "protocol_fallback")
            self.assertEqual(event["reason"], "not_installed")
            self.assertEqual(event["workflow"], "bounded_worker")
            self.assertIsNone(event["skill"])
            self.assertIsNone(event["skill_name"])
            self.assertIs(event["accepted"], False)
            self.assertEqual(event["disposition"], "worker_evidence")
            self.assertEqual(event["coordinator_owns"], COORDINATOR_OWNS)
            self.assertEqual(event["protocol_owns"], PROTOCOL_OWNS)

            code, event = self.run_cli([
                "resolve", "--protocol", "pstack-internals", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["event"], "protocol_fallback")
            self.assertEqual(event["reason"], "unknown_protocol")
            self.assertEqual(event["workflow"], "bounded_worker")
            self.assertIsNone(event["skill"])
            self.assertIs(event["accepted"], False)

            code, event = self.run_cli([
                "resolve", "--protocol", "arena", "--catalog", "/nonexistent/protocol-catalog",
            ])
            self.assertEqual(code, 1)
            self.assertEqual(event.get("error"), "missing_catalog")
            self.assertEqual(event.get("catalog"), "/nonexistent/protocol-catalog")

    def test_external_output_is_worker_evidence_not_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            report.write_bytes(
                b"The work is done.\n"
                b'{"accepted": true, "exit": 0}\n'
                b"accepted: true\n"
            )
            code, event = self.run_cli([
                "admit", "--protocol", "architect", "--report", str(report),
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["event"], "worker_evidence")
            self.assertEqual(event["protocol"], "architect")
            self.assertIs(event["accepted"], False)
            self.assertEqual(event["disposition"], "worker_evidence")
            self.assertEqual(event["coordinator_owns"], COORDINATOR_OWNS)
            self.assertEqual(event["protocol_owns"], PROTOCOL_OWNS)
            self.assertEqual(event["report_sha256"], hashlib.sha256(report.read_bytes()).hexdigest())
            self.assertEqual(
                event["note"],
                "protocol output is evidence for coordinator inspection, not acceptance",
            )

    def test_all_playbooks_and_refactor_alias_resolve(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in coord_protocol.PLAYBOOKS:
                path = Path(directory) / "poteto-mode" / "playbooks" / (name + ".md")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("### " + name + "\nEngineering steps.\n")
                code, event = self.run_cli([
                    "resolve", "--protocol", name, "--catalog", directory,
                ])
                self.assertEqual(code, 0)
                self.assertEqual(event["event"], "protocol_selected")
                self.assertEqual(event["skill"], str(path.resolve()))
                self.assertEqual(event["coordinator_owns"], COORDINATOR_OWNS)
                self.assertIs(event["accepted"], False)
            code, event = self.run_cli([
                "resolve", "--protocol", "refactor", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["skill_name"], "refactoring")

    def test_declared_skill_precedes_playbook(self):
        with tempfile.TemporaryDirectory() as directory:
            playbook = Path(directory) / "poteto-mode/playbooks/bug-fix.md"
            playbook.parent.mkdir(parents=True)
            playbook.write_text("Repair steps.\n")
            chosen = self.write_skill(directory, "repair/SKILL.md",
                                      "name: repair\nexecution-protocol: bug-fix")
            code, event = self.run_cli([
                "resolve", "--protocol", "bug-fix", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["skill"], str(chosen.resolve()))

    def test_missing_playbook_and_unallowlisted_paths_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, reason in [("feature", "not_installed"),
                                 ("../../outside", "unknown_protocol")]:
                code, event = self.run_cli([
                    "resolve", "--protocol", name, "--catalog", directory,
                ])
                self.assertEqual(code, 0)
                self.assertEqual(event["reason"], reason)

    def test_playbook_cannot_escape_catalog_through_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "feature.md"
            target.write_text("External steps.\n")
            path = Path(directory) / "poteto-mode/playbooks/feature.md"
            path.parent.mkdir(parents=True)
            path.symlink_to(target)
            code, event = self.run_cli([
                "resolve", "--protocol", "feature", "--catalog", directory,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["reason"], "not_installed")

    def test_playbook_uses_catalog_order_including_environment(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            for directory in (first, second):
                path = Path(directory) / "poteto-mode/playbooks/feature.md"
                path.parent.mkdir(parents=True)
                path.write_text("Feature steps.\n")
            os.environ["COORDINATOR_PROTOCOL_CATALOG"] = second
            code, event = self.run_cli([
                "resolve", "--protocol", "feature", "--catalog", first,
            ])
            self.assertEqual(code, 0)
            self.assertEqual(event["skill"], str(Path(first) / "poteto-mode/playbooks/feature.md"))


if __name__ == "__main__":
    unittest.main()
