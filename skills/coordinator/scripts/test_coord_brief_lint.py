import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import coord_brief_lint


GOOD_BRIEF = """Outcome and single accountable owner: fix the FIFO lock wedge.
Parent goal: unblock the persistence milestone.
Mode: build
Done means: NAMED-TEST passes and src/lock.py releases
the FIFO lock on close; the wedge in issue #12 is not reproducible.
Scope: src/lock.py only; do not touch the gateway.
Workers never call `ask_user` and never delegate or spawn sub-delegation.
Verify with `python3 -m unittest tests.test_lock`.
Write the report to /tmp/wedge-report.md when finished.
"""


class BriefLintTests(unittest.TestCase):
    def lint(self, text, *args):
        with tempfile.TemporaryDirectory() as directory:
            brief = Path(directory) / 'brief.md'
            brief.write_text(text)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = coord_brief_lint.main(['lint', '--brief', str(brief), *args])
            findings = [obj for obj in (json.loads(line) for line in output.getvalue().splitlines())
                        if 'check' in obj]
            return code, findings

    def checks(self, findings):
        return {f['check'] for f in findings}

    def test_complete_brief_passes(self):
        code, findings = self.lint(GOOD_BRIEF, '--kind', 'build')
        self.assertEqual(code, 0)
        self.assertEqual(self.checks(findings), set())

    def test_missing_ask_user_clause_is_rejected(self):
        text = GOOD_BRIEF.replace('never call `ask_user` and ', '')
        code, findings = self.lint(text)
        self.assertEqual(code, 1)
        self.assertIn('ask_user_clause', self.checks(findings))

    def test_missing_delegation_clause_is_rejected(self):
        text = GOOD_BRIEF.replace('never delegate or spawn sub-delegation', 'focus on your own work')
        code, findings = self.lint(text)
        self.assertEqual(code, 1)
        self.assertIn('delegation_clause', self.checks(findings))

    def test_explicit_authorization_suppresses_clause_checks(self):
        text = GOOD_BRIEF.replace('Workers never call `ask_user` and never delegate or spawn sub-delegation.\n', '')
        code, findings = self.lint(text, '--allow-ask-user', '--allow-delegation')
        self.assertEqual(code, 0)

    def test_missing_done_criteria_is_rejected(self):
        text = GOOD_BRIEF.replace('Done means: NAMED-TEST passes', 'Finish the lock work')
        code, findings = self.lint(text)
        self.assertEqual(code, 1)
        self.assertIn('done_criteria', self.checks(findings))

    def test_missing_return_path_is_rejected(self):
        text = GOOD_BRIEF.replace('Write the report to /tmp/wedge-report.md when finished.', 'Report back when finished.')
        code, findings = self.lint(text)
        self.assertEqual(code, 1)
        self.assertIn('return_path', self.checks(findings))

    def test_build_brief_without_verification_command_is_rejected(self):
        text = GOOD_BRIEF.replace('Verify with `python3 -m unittest tests.test_lock`.\n', '')
        code, findings = self.lint(text, '--kind', 'build')
        self.assertEqual(code, 1)
        self.assertIn('verification_command', self.checks(findings))

    def test_research_brief_needs_no_verification_command(self):
        text = GOOD_BRIEF.replace('Mode: build', 'Mode: investigate').replace(
            'Verify with `python3 -m unittest tests.test_lock`.\n', '')
        code, findings = self.lint(text, '--kind', 'research')
        self.assertEqual(code, 0)

    def test_native_brief_with_equivalent_wording_passes(self):
        text = ("Acceptance criteria: tests pass; do not spawn subagents; "
                "return findings in the native result channel.\n")
        code, findings = self.lint(text, '--kind', 'research', '--allow-ask-user')
        self.assertEqual(code, 0)
        self.assertEqual(self.checks(findings), set())

    def test_negation_case_insensitivity(self):
        text = GOOD_BRIEF.replace(
            'Workers never call `ask_user` and never delegate or spawn sub-delegation.',
            'Do not call ask_user. No delegation to other agents.'
        )
        code, findings = self.lint(text, '--kind', 'build')
        self.assertEqual(code, 0)
        self.assertEqual(self.checks(findings), set())

    def test_common_rules_wording_passes(self):
        text = """Outcome: heal brief lint
Mode: build
Gate: `python3 -m unittest discover -s skills/coordinator/scripts`, run from your worktree. It must pass.
Do not spawn subagents or ask the user questions.
Write the report to /tmp/heal-brieflint-report.md when finished.
`python3 -m unittest discover -s skills/coordinator/scripts`
"""
        code, findings = self.lint(text, '--kind', 'build')
        self.assertEqual(code, 1)
        self.assertIn('done_criteria', self.checks(findings))
        self.assertNotIn('ask_user_clause', self.checks(findings))
        self.assertNotIn('delegation_clause', self.checks(findings))

    def test_gate_alone_does_not_satisfy_done_criteria(self):
        text = ("Outcome: fix lock wedge\n"
                "Gate: `python3 -m unittest tests.test_lock` must pass\n"
                "Do not call ask_user. Do not delegate. Return results to /tmp/lock-report.md.\n")
        code, findings = self.lint(text, '--kind', 'build')
        self.assertEqual(code, 1)
        self.assertIn('done_criteria', self.checks(findings))

    def test_missing_brief_file_errors(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = coord_brief_lint.main(['lint', '--brief', '/nonexistent/brief.md'])
        self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()


