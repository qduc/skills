import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import coord_state as state

SCRIPT = Path(state.__file__).resolve()


class TaskStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coordinator state ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.created = self.cli('create', '--title', 'Multi-day task', '--objective', 'Implement and verify',
                                '--project', str(self.root), '--conversation', 'conversation-1')
        self.task = self.created['state']['id']
        self.owner = self.created['state']['owner']
        self.path = self.root / 'tasks' / self.task
        self.patch_path = self.root / 'patch.json'
        self.pool_path = self.root / 'pool.json'
        self.pool = [{'harness': 'native', 'model': 'chosen-model', 'role': 'implementation'}]
        self.pool_path.write_text(json.dumps(self.pool))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), *args],
                              capture_output=True, text=True, timeout=10)

    def cli(self, *args):
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['result']

    def checkpoint(self, revision, patch):
        self.patch_path.write_text(json.dumps(patch))
        return self.cli('checkpoint', '--task', self.task, '--owner', self.owner,
                        '--revision', str(revision), '--patch-file', str(self.patch_path))

    def test_create_and_resume_in_new_process(self):
        resumed = self.cli('show', '--task', self.task)
        self.assertEqual(resumed['state'], self.created['state'])
        self.assertTrue((self.path / 'state.md').exists())
        self.assertIn('Generated from state.json', (self.path / 'state.md').read_text())
        self.assertEqual(self.cli('list')['tasks'][0]['id'], self.task)
        self.assertEqual(self.cli('list', '--conversation', 'other')['tasks'], [])

    def test_latest_chains_owned_checkpoints_without_bypassing_takeover(self):
        self.cli('select', '--task', self.task, '--owner', self.owner, '--revision', 'latest',
                 '--pool-file', str(self.pool_path), '--confirmed', '--source', 'user chose')
        result = self.checkpoint('latest', {'details': {'next_action': 'verify'}})
        self.assertEqual(result['state']['revision'], 3)
        denied = self.run_cli('release', '--task', self.task, '--owner', 'other', '--revision', 'latest')
        self.assertNotEqual(denied.returncode, 0)
        denied = self.run_cli('claim', '--task', self.task, '--owner', 'other', '--revision', 'latest',
                              '--takeover', '--reason', 'inspected')
        self.assertNotEqual(denied.returncode, 0)

    def test_default_location_honors_only_absolute_xdg_path(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': '/tmp/state-root'}):
            self.assertEqual(state.root_path(), Path('/tmp/state-root/coordinator'))
        with patch.dict(os.environ, {'XDG_STATE_HOME': 'relative'}):
            self.assertEqual(state.root_path(), Path.home() / '.local/state/coordinator')

    def test_takeover_fences_old_owner_and_stale_revisions(self):
        result = self.run_cli('claim', '--task', self.task, '--owner', 'session-2', '--revision', '1')
        self.assertNotEqual(result.returncode, 0)
        takeover = self.cli('claim', '--task', self.task, '--owner', 'session-2', '--revision', '1',
                            '--takeover', '--reason', 'Old session ended; workers reconciled')
        self.assertEqual(takeover['state']['revision'], 2)
        for revision in ('1', '2'):
            result = self.run_cli('release', '--task', self.task, '--owner', self.owner, '--revision', revision)
            self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.cli('show', '--task', self.task)['state']['owner'], 'session-2')
        released = self.cli('release', '--task', self.task, '--owner', 'session-2', '--revision', '2')
        self.assertIsNone(released['state']['owner'])
        self.cli('claim', '--task', self.task, '--owner', 'session-3', '--revision', '3')

    def test_two_simultaneous_checkpoints_cannot_overwrite(self):
        self.patch_path.write_text(json.dumps({'details': {'next_action': 'inspect artifact'}}))
        args = ('checkpoint', '--task', self.task, '--owner', self.owner,
                '--revision', '1', '--patch-file', str(self.patch_path))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.run_cli(*args), range(2)))
        self.assertEqual(sorted(r.returncode for r in results), [0, 1])
        self.assertEqual(self.cli('show', '--task', self.task)['state']['revision'], 2)

    def test_rejected_patch_preserves_checkpoint(self):
        before = (self.path / 'state.json').read_bytes()
        for invalid in ({'owner': 'intruder'}, {'status': 'invented'}, {'details': {'unknown': True}},
                        {'details': {'work_items': [{'id': 'a', 'status': 'pending', 'needs': ['a']}]}}):
            self.patch_path.write_text(json.dumps(invalid))
            result = self.run_cli('checkpoint', '--task', self.task, '--owner', self.owner,
                                 '--revision', '1', '--patch-file', str(self.patch_path))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((self.path / 'state.json').read_bytes(), before)

    def test_failed_atomic_write_leaves_old_json_readable(self):
        before = (self.path / 'state.json').read_bytes()
        with patch.object(state.os, 'replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                state.atomic_write(self.path / 'state.json', '{"incomplete":true}')
        self.assertEqual((self.path / 'state.json').read_bytes(), before)
        self.assertEqual(list(self.path.glob('.checkpoint-*')), [])

    def test_markdown_failure_keeps_authoritative_state_and_can_regenerate(self):
        record = state.load(self.path)
        original = state.atomic_write
        def fail_markdown(path, text):
            if path.suffix == '.md':
                raise OSError('view unavailable')
            return original(path, text)
        with patch.object(state, 'atomic_write', side_effect=fail_markdown):
            warnings = state.save(self.path, record)
        self.assertIn('JSON checkpoint saved', warnings[0])
        self.cli('render', '--task', self.task)
        self.assertEqual((self.path / 'state.md').read_text(), state.markdown(record))

    def test_select_persists_choice_and_history_deduplicates(self):
        selected = self.cli('select', '--task', self.task, '--owner', self.owner, '--revision', '1',
                            '--pool-file', str(self.pool_path), '--confirmed', '--source', 'user chose this pool')
        self.assertEqual(selected['state']['selection'], self.pool)
        self.assertTrue((self.root / 'choices.jsonl').exists())
        self.assertEqual(len(self.cli('choices')['choices']), 1)
        self.assertEqual(self.cli('choices', '--task', 'another')['choices'], [])
        # A failed/torn export cannot erase the choice already saved in the task.
        (self.root / 'choices.jsonl').write_text('{broken')
        recovered = self.cli('choices')
        self.assertEqual(recovered['choices'][0]['pool'], self.pool)
        self.assertTrue(recovered['warnings'])
        self.assertEqual(self.cli('show', '--task', self.task)['state']['selection'], self.pool)

    def test_selection_requires_confirmation_and_concrete_identifiers(self):
        result = self.run_cli('select', '--task', self.task, '--owner', self.owner, '--revision', '1',
                              '--pool-file', str(self.pool_path), '--source', 'guess')
        self.assertNotEqual(result.returncode, 0)
        self.pool_path.write_text(json.dumps([{'harness': 'native', 'model': 'previous'}]))
        result = self.run_cli('select', '--task', self.task, '--owner', self.owner, '--revision', '1',
                              '--pool-file', str(self.pool_path), '--confirmed', '--source', 'same as before')
        self.assertNotEqual(result.returncode, 0)

    def test_completion_archive_preserve_evidence_and_leave_default_list(self):
        self.checkpoint(1, {'details': {'blockers': ['awaiting result']}})
        self.patch_path.write_text(json.dumps({'status': 'completed'}))
        result = self.run_cli('checkpoint', '--task', self.task, '--owner', self.owner, '--revision', '2',
                              '--patch-file', str(self.patch_path))
        self.assertNotEqual(result.returncode, 0)
        artifact = self.path / 'evidence.txt'
        artifact.write_text('verified')
        self.checkpoint(2, {'status': 'completed', 'details': {'blockers': [],
                           'artifacts': [{'path': str(artifact)}], 'next_action': 'none'}})
        archived = self.cli('archive', '--task', self.task, '--owner', self.owner, '--revision', '3')
        self.assertTrue(archived['state']['archived_at'])
        self.assertIsNone(archived['state']['owner'])
        self.assertTrue(artifact.exists())
        self.assertEqual(self.cli('list')['tasks'], [])
        self.assertEqual(len(self.cli('list', '--all')['tasks']), 1)
        self.assertEqual(self.cli('show', '--task', self.task)['state']['status'], 'completed')

    def test_resume_reports_missing_and_changed_artifacts_without_executing_work(self):
        artifact = self.path / 'artifact'
        artifact.write_bytes(b'changed')
        self.checkpoint(1, {'details': {'artifacts': [
            {'path': str(artifact), 'sha256': hashlib.sha256(b'old').hexdigest()},
            {'path': str(self.path / 'missing')}],
            'work_items': [{'id': 'w1', 'status': 'pending'}]}})
        report = self.cli('check-resume', '--task', self.task)
        self.assertEqual({f['kind'] for f in report['findings']}, {'missing_artifact', 'artifact_changed'})
        self.assertEqual(report['unfinished'][0]['id'], 'w1')

    def test_resume_with_worker_report_published_while_coordinator_offline(self):
        import coord_lifecycle as lifecycle
        lifecycle_script = Path(lifecycle.__file__).resolve()
        def worker_cli(*args):
            run = subprocess.run([sys.executable, str(lifecycle_script), *args],
                                 text=True, capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            return json.loads(run.stdout)['result']
        self.cli('select', '--task', self.task, '--owner', self.owner, '--revision', '1',
                 '--pool-file', str(self.pool_path), '--confirmed', '--source', 'user selected')
        lifecycle_path = self.path / 'lifecycle.json'
        worker_cli('prepare', '--state', str(lifecycle_path), '--task-id', self.task,
                   '--verify-command', '["true"]')
        routing = lifecycle.load_state(lifecycle_path)
        # Fixture registration replaces only the Herdr launcher; file operations and CLIs are real.
        routing['workers']['writer'] = {'name': 'writer', 'cwd': str(self.path)}
        mailbox = lifecycle.register_mailbox(routing, 'writer')
        lifecycle.save_state(lifecycle_path, routing)
        self.checkpoint(2, {'details': {'work_items': [{'id': 'implementation', 'status': 'pending'}],
                                      'notes': [{'lifecycle': str(lifecycle_path)}]}})
        self.cli('release', '--task', self.task, '--owner', self.owner, '--revision', '3')
        artifact = self.path / 'result.txt'
        artifact.write_text('worker result')
        worker_cli('report', '--assignment-file', str(mailbox / 'assignment.json'),
                   '--kind', 'complete', '--artifact', str(artifact))
        resumed = self.cli('claim', '--task', self.task, '--owner', 'resumed-session', '--revision', '4')
        self.assertEqual(resumed['state']['selection'], self.pool)
        messages = worker_cli('receive', '--state', str(lifecycle_path))
        self.assertEqual(messages[0]['envelope']['status'], 'unread')
        message = messages[0]
        worker_cli('verify', '--state', str(lifecycle_path), '--artifact', str(artifact),
                   '--sha256', message['completion']['sha256'], '--root', str(self.path))
        worker_cli('mark-read', '--state', str(lifecycle_path), '--worker', 'writer',
                   '--message-id', message['envelope']['message_id'])
        self.owner = 'resumed-session'
        self.checkpoint(5, {'status': 'completed', 'details': {
            'work_items': [{'id': 'implementation', 'status': 'completed'}],
            'artifacts': [{'path': str(artifact), 'sha256': message['completion']['sha256']}],
            'verification': [{'message_id': message['envelope']['message_id'], 'digest_matched': True}]}})
        worker_cli('ack', '--state', str(lifecycle_path), '--worker', 'writer',
                   '--message-id', message['envelope']['message_id'], '--outcome', 'checkpoint revision 6')
        self.cli('archive', '--task', self.task, '--owner', self.owner, '--revision', '6')
        self.assertEqual(worker_cli('receive', '--state', str(lifecycle_path)), [])
        self.assertTrue(artifact.exists())

    def test_bad_records_are_visible_and_legacy_markdown_is_preserved(self):
        legacy = self.root / 'tasks' / 'legacy'
        legacy.mkdir()
        (legacy / 'state.md').write_text('Previous manual record')
        listing = self.cli('list')
        self.assertTrue(any('legacy Markdown' in warning for warning in listing['warnings']))
        result = self.run_cli('show', '--task', '../outside')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((legacy / 'state.md').read_text(), 'Previous manual record')


if __name__ == '__main__':
    unittest.main()
