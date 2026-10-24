import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import coord_state

SCRIPT = Path(coord_state.__file__).resolve()


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coord resume ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        result = self.cli('create', '--title', 'Resume', '--objective', 'verify', '--project', str(self.project))
        self.task = result['state']['id']
        self.path = self.root / 'tasks' / self.task

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), *args], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['result']

    def record(self):
        return json.loads((self.path / 'state.json').read_text())

    def save_v2(self, record, cold=None):
        coord_state.upgrade_memory(record)
        record['updated_at'] = '2026-09-26T01:30:04.267257+00:00'
        record['memory']['cold'] = cold or []
        (self.path / 'state.json').write_text(json.dumps(record, indent=2) + '\n')

    def cold(self, number, status='current', text='claim'):
        return {'id': f'claim-{number}', 'category': 'state', 'text': text, 'status': status, 'scope': 'task', 'created_at': '2026-09-25T00:00:00+00:00', 'updated_at': f'2026-09-{25 - number // 24:02d}T{number % 24:02d}:00:00+00:00', 'provenance': [{'kind': 'test', 'ref': f'source-{number}'}], 'supersedes': [], 'superseded_by': None, 'task_id': self.task}

    def test_resume_is_read_only_and_filters_cold_memory(self):
        record = self.record()
        self.save_v2(record, [self.cold(1), self.cold(2, 'superseded')])
        before = (self.path / 'state.json').read_bytes()
        revision = self.record()['revision']
        result = self.cli('resume', '--task', self.task)
        self.assertEqual((self.path / 'state.json').read_bytes(), before)
        self.assertEqual(self.record()['revision'], revision)
        self.assertEqual([item['id'] for item in result['memory']['cold']], ['claim-1'])

    def test_git_snapshot_reports_commits_dirty_missing_and_nonrepo(self):
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)
        subprocess.run(['git', '-C', str(self.project), 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', '-C', str(self.project), 'config', 'user.name', 'Test'], check=True)
        (self.project / 'tracked').write_text('one')
        subprocess.run(['git', '-C', str(self.project), 'add', 'tracked'], check=True)
        env = dict(os.environ, GIT_AUTHOR_DATE='2026-09-27T00:00:00+00:00', GIT_COMMITTER_DATE='2026-09-27T00:00:00+00:00')
        subprocess.run(['git', '-C', str(self.project), 'commit', '-qm', 'after'], check=True, env=env)
        (self.project / 'dirty').write_text('change')
        nonrepo = self.root / 'nonrepo'
        nonrepo.mkdir()
        record = self.record()
        record['details']['work_items'] = [{'id': 'paths', 'status': 'pending', 'cwd': str(nonrepo), 'worktree': str(self.root / 'missing')}]
        self.save_v2(record)
        result = self.cli('resume', '--task', self.task)
        by_path = {item['path']: item for item in result['git']}
        self.assertIn('after', by_path[str(self.project)]['commits_since_update'][0])
        self.assertGreaterEqual(by_path[str(self.project)]['dirty'], 1)
        self.assertIn('error', by_path[str(nonrepo)])
        self.assertIn('error', by_path[str(self.root / 'missing')])

    def test_budget_keeps_protected_fields_and_records_drop_order(self):
        record = self.record()
        record['details']['next_action'] = 'do not drop'
        record['details']['blockers'] = ['keep blocker']
        record['details']['work_items'] = [{'id': 'large', 'status': 'pending', 'notes': 'x' * 5000, 'cwd': str(self.root / 'missing')}]
        self.save_v2(record, [self.cold(i, text='x' * 500) for i in range(12)])
        result = self.cli('resume', '--task', self.task, '--budget-bytes', '1800')
        self.assertEqual(result['task']['next_action'], 'do not drop')
        self.assertEqual(result['task']['blockers'], ['keep blocker'])
        self.assertGreater(result['omitted']['cold_items'], 0)
        self.assertGreater(result['omitted']['work_item_notes'], 0)
        self.assertTrue(any('error' in repo for repo in result['git']))

    def test_v1_and_worker_reminder_behavior(self):
        result = self.cli('resume', '--task', self.task)
        self.assertTrue(result['memory']['legacy'])
        record = self.record()
        record['details']['workers'] = [{'id': 'worker', 'cwd': str(self.root)}]
        self.save_v2(record)
        result = self.cli('resume', '--task', self.task)
        self.assertIn('reminders', result['checks'])
        record['details']['workers'] = []
        self.save_v2(record)
        self.assertNotIn('reminders', self.cli('resume', '--task', self.task)['checks'])


if __name__ == '__main__':
    unittest.main()
