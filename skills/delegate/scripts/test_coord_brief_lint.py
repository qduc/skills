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
            return self.lint_path(brief, *args)

    def lint_path(self, path, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = coord_brief_lint.main(['lint', '--brief', str(path), *args])
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_complete_brief_passes(self):
        code, output = self.lint(GOOD_BRIEF, '--kind', 'build')
        self.assertEqual(code, 0)
        self.assertTrue(output[0]['ok'])
        self.assertEqual(output[0]['kind'], 'build')

    def test_equivalent_prose_does_not_need_template_tokens(self):
        variants = {
            'done_label': GOOD_BRIEF.replace('Done means:', 'Done:'),
            'prose_acceptance': GOOD_BRIEF.replace('Done means:', 'Finish once'),
            'return_location': GOOD_BRIEF.replace(
                'Write the report to /tmp/wedge-report.md when finished.',
                'Leave your findings alongside the assignment.'),
            'authority': GOOD_BRIEF.replace(
                'Workers never call `ask_user` and never delegate or spawn sub-delegation.',
                'Work alone and autonomously; questions go in the final findings.'),
            'unformatted_command': GOOD_BRIEF.replace('`python3 -m unittest tests.test_lock`',
                                                    'python3 -m unittest tests.test_lock'),
        }
        for name, text in variants.items():
            with self.subTest(name=name):
                code, output = self.lint(text)
                self.assertEqual(code, 0, output)
                self.assertTrue(output[0]['ok'])

    def test_nonempty_prose_is_not_judged_for_adequacy(self):
        # A successful mechanical check is not an endorsement of this assignment.
        for kind in ('build', 'research', 'review'):
            with self.subTest(kind=kind):
                code, output = self.lint('bounded work', '--kind', kind)
                self.assertEqual(code, 0, output)
                self.assertTrue(output[0]['ok'])

    def test_legacy_authorization_flags_remain_accepted(self):
        code, output = self.lint('bounded work', '--allow-ask-user', '--allow-delegation')
        self.assertEqual(code, 0, output)

    def test_empty_brief_is_rejected_even_with_legacy_flags(self):
        for text in ('', ' \n\t'):
            with self.subTest(text=text):
                code, output = self.lint(text, '--allow-ask-user', '--allow-delegation')
                self.assertEqual(code, 1)
                self.assertEqual(output, [{'check': 'empty_brief', 'severity': 'error',
                                           'message': 'brief must contain non-whitespace text'}])

    def test_missing_brief_file_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output = self.lint_path(Path(directory) / 'missing.md')
        self.assertEqual(code, 1)
        self.assertEqual(output[0]['error'], 'missing_brief')

    def test_directory_is_not_a_brief(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output = self.lint_path(directory)
        self.assertEqual(code, 1)
        self.assertEqual(output[0]['error'], 'missing_brief')

    def test_invalid_kind_is_rejected_at_cli_boundary(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            self.lint(GOOD_BRIEF, '--kind', 'unknown')
        self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
