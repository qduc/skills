import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('coord_progress.py')


class ProgressSnapshotTests(unittest.TestCase):
    def test_snapshot_contains_phase_worker_map_merges_and_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / 'report.md'
            report.write_text('done')
            state = {
                'id': 'task-1', 'status': 'active', 'details': {
                    'phase': 'phase-2', 'next_action': 'wait for review',
                    'work_items': [{'id': 'core', 'status': 'completed'},
                                   {'id': 'review', 'status': 'active'}],
                    'workers': [{'id': 'wS:p40', 'status': 'blocked', 'pane_id': 'wS:p40',
                                 'worktree': '/repo/.worktrees/core', 'report': str(report),
                                 'last_progress_at': '2026-09-29T12:00:00Z'},
                                {'id': 'wS:p41', 'status': 'working'}],
                    'verification': [{'check': 'merge --no-ff', 'result': 'passed'}],
                },
            }
            path = root / 'state.json'
            path.write_text(json.dumps(state))
            result = subprocess.run([sys.executable, str(SCRIPT), '--state', str(path)],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = json.loads(result.stdout)
            self.assertEqual(snapshot['phase'], 'phase-2')
            self.assertEqual(snapshot['workers'][0]['pane'], 'wS:p40')
            self.assertTrue(snapshot['workers'][0]['blocked'])
            self.assertEqual(snapshot['workers'][0]['last_progress_at'], '2026-09-29T12:00:00Z')
            self.assertEqual(snapshot['merges'], [{'check': 'merge --no-ff', 'result': 'passed'}])
            self.assertEqual(snapshot['done'], 1)
            self.assertEqual(snapshot['total'], 2)

    def test_missing_phase_keeps_phase_null_and_exposes_next_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = {'id': 'task-2', 'status': 'active', 'details': {
                'next_action': 'wait for phase-1 fix report'}}
            path = Path(temporary) / 'state.json'
            path.write_text(json.dumps(state))
            result = subprocess.run([sys.executable, str(SCRIPT), '--state', str(path)],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = json.loads(result.stdout)
            self.assertIsNone(snapshot['phase'])
            self.assertEqual(snapshot['next_action'], 'wait for phase-1 fix report')

    def test_worker_timestamps_yield_dispatch_and_merge_durations(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = {'id': 'task-3', 'status': 'active', 'details': {
                'workers': [
                    {'id': 'w1', 'status': 'merged',
                     'dispatched_at': '2026-09-29T10:00:00Z',
                     'reported_at': '2026-09-29T10:30:00Z',
                     'merged_at': '2026-09-29T11:00:00Z',
                     'merge_commit': '70e9ba3e'},
                    {'id': 'w2', 'status': 'working'},
                ]}}
            path = Path(temporary) / 'state.json'
            path.write_text(json.dumps(state))
            result = subprocess.run([sys.executable, str(SCRIPT), '--state', str(path)],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = json.loads(result.stdout)
            first = snapshot['workers'][0]
            self.assertEqual(first['dispatch_to_report_s'], 1800.0)
            self.assertEqual(first['report_to_merge_s'], 1800.0)
            self.assertEqual(first['merge_commit'], '70e9ba3e')
            self.assertNotIn('dispatch_to_report_s', snapshot['workers'][1])
            self.assertNotIn('report_to_merge_s', snapshot['workers'][1])

    def test_worker_without_reported_at_omits_report_metrics_despite_accepted_at(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = {'id': 'task-4', 'status': 'active', 'details': {
                'workers': [
                    {'id': 'w1', 'status': 'merged',
                     'dispatched_at': '2026-09-29T10:00:00Z',
                     'accepted_at': '2026-09-29T15:00:00Z',
                     'merged_at': '2026-09-29T15:30:00Z'}]}}
            path = Path(temporary) / 'state.json'
            path.write_text(json.dumps(state))
            result = subprocess.run([sys.executable, str(SCRIPT), '--state', str(path)],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = json.loads(result.stdout)
            worker = snapshot['workers'][0]
            self.assertNotIn('dispatch_to_report_s', worker)
            self.assertNotIn('report_to_merge_s', worker)

    def test_invalid_state_fails_with_actionable_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            path.write_text('{')
            result = subprocess.run([sys.executable, str(SCRIPT), '--state', str(path)],
                                    text=True, capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('invalid', result.stderr.lower())


if __name__ == '__main__':
    unittest.main()
