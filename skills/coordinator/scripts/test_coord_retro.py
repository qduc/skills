import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import coord_retro as retro

SCRIPT = Path(retro.__file__).resolve()


class RetroDigestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coordinator retro ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'state'
        self.memory = Path(self.temporary.name) / 'memory'
        self.rules = Path(self.temporary.name) / 'skill'
        for directory in (self.root / 'tasks', self.memory, self.rules):
            directory.mkdir(parents=True)

    def task(self, task_id, notes, updated='2026-09-20T00:00:00+00:00'):
        path = self.root / 'tasks' / task_id
        path.mkdir()
        (path / 'state.json').write_text(json.dumps(
            {'id': task_id, 'title': f'Task {task_id}', 'updated_at': updated, 'details': {'notes': notes}}))
        return path / 'state.json'

    def digest(self, *extra):
        before = sorted((p, p.stat().st_mtime_ns) for p in Path(self.temporary.name).rglob('*'))
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), '--memory-dir', str(self.memory),
                                 '--rules-dir', str(self.rules), '--today', '2026-12-31', *extra],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = sorted((p, p.stat().st_mtime_ns) for p in Path(self.temporary.name).rglob('*'))
        self.assertEqual(before, after, 'harvest must be read-only')
        return result.stdout

    def section(self, text, title):
        return text.split(f'## {title}', 1)[1].split('\n## ', 1)[0]

    def test_keyed_incidents_group_across_tasks_and_cite_sources(self):
        first = self.task('aaaa', [{'kind': 'incident', 'key': 'steer-draft-unsent', 'what': 'Long steer stayed in draft',
                                    'cost': '20 minutes idle', 'scope': 'host', 'at': '2026-09-24'}])
        self.task('bbbb', [{'kind': 'incident', 'key': 'steer-draft-unsent', 'what': 'Unrelated wording entirely',
                            'at': '2026-09-26'}, {'kind': 'intent', 'text': 'Long steer stayed in draft'}])
        recurring = self.section(self.digest(), 'Recurring candidates')
        self.assertIn('steer-draft-unsent: 2 mentions in 2 sources, 2026-09-24..2026-09-26, scope host', recurring)
        self.assertIn(f'`{first}` notes[0]', recurring)
        self.assertIn('cost: 20 minutes idle', recurring)
        self.assertNotIn('intent', recurring)

    def test_legacy_notes_and_other_sources_join_by_overlap(self):
        self.task('cccc', ['plain string note', {'kind': 'tooling', 'text':
                           'Removed a git worktree while its worker was alive; worker shell failed with spawn git ENOENT'}])
        (self.root / 'handoff-2026-09-26-2032.md').write_text(
            '# Handoff\n\n## Hard-won rules from this session\n'
            '- Never remove a live worker git worktree; the worker shell fails with\n  spawn git ENOENT.\n'
            '- Unrelated: brief grok with a medium effort flag.\n\n## Live resources\n- pane wS:pP\n')
        (self.root / 'friction-log.md').write_text(
            '# Log\n\n| # | Area | Status |\n|---|---|---|\n| 1 | a | open |\n| 2 | b | withdrawn |\n\n'
            '## 1. Inbox lost on cleanup\n\n- **What happened:** inbox deleted with its directory.\n'
            '- **Suggestion:** keep inboxes outside.\n\n## 2. Withdrawn item\n\n- **What happened:** ignore me.\n')
        (self.memory / 'rule.md').write_text('---\nname: rule\ndescription: "Keep watchers cheap"\nmetadata:\n'
                                             '  type: feedback\n  modified: 2026-09-12T09:03:47Z\n---\n\nUse file loops.\n')
        (self.memory / 'fact.md').write_text('---\nname: fact\nmetadata:\n  type: reference\n---\n\nNot a lesson.\n')
        text = self.digest()
        recurring = self.section(text, 'Recurring candidates')
        self.assertIn('unkeyed: 2 mentions in 2 sources', recurring)
        self.assertIn('handoff-2026-09-26-2032.md` line 4', recurring)
        single = self.section(text, 'Single mentions')
        self.assertIn('Inbox lost on cleanup: inbox deleted with its directory.; rule: keep inboxes outside.', single)
        self.assertIn('Keep watchers cheap', single)
        self.assertIn('2026-09-12', single)
        self.assertNotIn('ignore me', text)
        self.assertNotIn('Not a lesson', text)
        self.assertNotIn('pane wS:pP', text)

    def test_promoted_rules_report_citations_and_prune_candidates(self):
        (self.rules / 'SKILL.md').write_text('Rule.\n<!-- lesson: recurring-rule promoted 2026-09-01 -->\n'
                                             'Other.\n<!-- lesson: quiet-rule promoted 2026-09-01 -->\n'
                                             '<!-- lesson: fresh-rule promoted 2026-12-01 -->\n')
        self.task('dddd', [{'kind': 'incident', 'key': 'recurring-rule', 'what': 'applied', 'outcome': 'prevented',
                            'at': '2026-10-05'}, {'kind': 'incident', 'key': 'quiet-rule', 'what': 'before promotion',
                                                  'at': '2026-08-01'}])
        promoted = self.section(self.digest(), 'Promoted rules')
        self.assertIn('`recurring-rule` promoted 2026-09-01', promoted)
        self.assertIn('1 citations since, last 2026-10-05', promoted)
        lines = {line.split('`')[1]: line for line in promoted.splitlines() if line.startswith('- ')}
        self.assertIn('prune candidate', lines['quiet-rule'])
        self.assertNotIn('prune candidate', lines['recurring-rule'])
        self.assertNotIn('prune candidate', lines['fresh-rule'])

    def test_unreadable_records_are_reported_not_fatal(self):
        (self.root / 'tasks' / 'broken').mkdir()
        (self.root / 'tasks' / 'broken' / 'state.json').write_text('{not json')
        text = self.digest()
        self.assertIn('## Warnings', text)
        self.assertIn('broken', self.section(text, 'Warnings'))


if __name__ == '__main__':
    unittest.main()
