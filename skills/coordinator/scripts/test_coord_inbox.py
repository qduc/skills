import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import coord_inbox as inbox
import coord_lifecycle as lifecycle

SCRIPT = Path(lifecycle.__file__).resolve()


class FileInboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state_path = self.root / 'lifecycle.json'
        self.state = lifecycle.prepare(argparse.Namespace(
            state=str(self.state_path), inbox=None, task_id='T1', verify_command=['true']))
        self.state['workers']['worker'] = {'name': 'worker', 'cwd': str(self.root)}
        self.mailbox = lifecycle.register_mailbox(self.state, 'worker')
        lifecycle.save_state(self.state_path, self.state)

    def cli(self, *arguments):
        result = subprocess.run([sys.executable, str(SCRIPT), *arguments],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['result']

    def receive(self, unread_only=False):
        return lifecycle.receive(argparse.Namespace(state=str(self.state_path), wait=0,
                                                    unread_only=unread_only))

    def report(self):
        return {'run_id': self.state['run_id'], 'task_id': 'T1',
                'assignment_id': self.state['workers']['worker']['assignment_id'],
                'worker': 'worker', 'kind': 'complete', 'artifact': str(self.root / 'artifact'),
                'sha256': hashlib.sha256(b'ok').hexdigest(), 'verify_command': ['true'], 'children': []}

    def test_report_builds_completion_without_executing_verification(self):
        artifact = self.root / 'artifact with spaces.txt'
        artifact.write_bytes(b'ok')
        descriptor = self.mailbox / 'assignment.json'
        contract = json.loads(descriptor.read_text())
        contract['verify_command'] = [sys.executable, '-c', 'raise SystemExit(99)']
        descriptor.write_text(json.dumps(contract))
        self.cli('report', '--assignment-file', str(descriptor), '--kind', 'complete',
                 '--artifact', artifact.name)
        payload = self.receive()[0]['completion']
        self.assertEqual(payload['sha256'], hashlib.sha256(b'ok').hexdigest())
        for key in ('run_id', 'task_id', 'assignment_id', 'worker', 'verify_command'):
            self.assertEqual(payload[key], contract[key])
        self.assertEqual(payload['artifact'], str(artifact))
        self.assertEqual(payload['children'], [])

    def test_report_progress_and_blocker_need_only_summary(self):
        for kind in ('progress', 'blocked'):
            result = self.cli('report', '--assignment-file', str(self.mailbox / 'assignment.json'),
                              '--kind', kind, '--summary', 'waiting for review')
            self.assertEqual(result['kind'], kind)
        self.assertEqual({m['completion']['kind'] for m in self.receive()}, {'progress', 'blocked'})

    def test_report_rejects_outside_artifact_and_invalid_children(self):
        descriptor = str(self.mailbox / 'assignment.json')
        artifact = self.root / 'artifact'
        artifact.write_bytes(b'ok')
        children = self.root / 'children.json'
        children.write_text('[{"name":""}]')
        for extra in (['--artifact', '/etc/hosts'],
                      ['--artifact', str(artifact), '--children-file', str(children)]):
            result = subprocess.run([sys.executable, str(SCRIPT), 'report', '--assignment-file', descriptor,
                                     '--kind', 'complete', *extra], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 1)
        self.assertEqual(self.receive(), [])

    def test_publish_receive_restart_mark_read_ack(self):
        report = self.root / 'report.json'
        report.write_text(json.dumps(self.report()))
        published = self.cli('send', '--inbox', str(self.mailbox), '--message-file', str(report))
        message_id = published['message_id']
        for _ in range(2):
            messages = self.cli('receive', '--state', str(self.state_path))
            self.assertEqual(messages[0]['envelope']['status'], 'unread')
        self.cli('mark-read', '--state', str(self.state_path), '--worker', 'worker', '--message-id', message_id)
        self.assertEqual(self.cli('receive', '--state', str(self.state_path), '--unread-only'), [])
        self.assertEqual(self.cli('receive', '--state', str(self.state_path))[0]['envelope']['status'], 'read')
        for _ in range(2):
            self.cli('ack', '--state', str(self.state_path), '--worker', 'worker',
                     '--message-id', message_id, '--outcome', 'verified and checkpointed')
        self.assertEqual(self.receive(), [])
        self.assertEqual(json.loads((self.mailbox / 'processed' / f'{message_id}.json').read_text()), self.report())
        self.cli('stop', '--state', str(self.state_path))
        self.assertTrue((self.mailbox / 'processed' / f'{message_id}.json').exists())

    def test_concurrent_publishers_do_not_overwrite(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(lambda i: inbox.publish(self.mailbox, {'sequence': i}), range(40)))
        self.assertEqual(len(set(ids)), 40)
        self.assertEqual({r['payload']['sequence'] for r in inbox.read(self.mailbox)}, set(range(40)))

    def test_unfinished_publication_is_invisible_and_failure_preserves_existing_reports(self):
        original = inbox.publish(self.mailbox, {'sequence': 1})
        (self.mailbox / 'unread' / '.publishing-interrupted').write_text('{')
        with patch.object(inbox.os, 'replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                inbox.publish(self.mailbox, {'sequence': 2})
        self.assertEqual([r['message_id'] for r in inbox.read(self.mailbox)], [original])

    def test_malformed_message_does_not_hide_good_message(self):
        (self.mailbox / 'unread' / ('a' * 32 + '.json')).write_text('{')
        good = inbox.publish(self.mailbox, {'ok': True})
        messages = self.receive()
        self.assertEqual(len(messages), 2)
        self.assertEqual(sum('error' in m for m in messages), 1)
        self.assertTrue(any(m['envelope']['message_id'] == good and m['completion'] == {'ok': True} for m in messages))

    def test_message_limits_and_path_validation(self):
        with patch.object(inbox, 'MAX_MESSAGE_BYTES', 4):
            with self.assertRaises(inbox.InboxError):
                inbox.publish(self.mailbox, {'too': 'large'})
        with self.assertRaises(inbox.InboxError):
            inbox.acknowledge(self.mailbox, '../other')
        with self.assertRaises(inbox.InboxError):
            inbox.publish(self.mailbox, [])

    def test_symlink_report_is_not_read(self):
        private = self.root / 'private'
        private.write_text('{"secret":true}')
        (self.mailbox / 'unread' / ('b' * 32 + '.json')).symlink_to(private)
        message = self.receive()[0]
        self.assertIsNone(message['completion'])
        self.assertIn('error', message)

    def test_failed_checkpoint_keeps_message_unprocessed(self):
        message_id = inbox.publish(self.mailbox, {'kind': 'blocked'})
        with patch.object(lifecycle, 'save_state', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                lifecycle.acknowledge(argparse.Namespace(state=str(self.state_path), worker='worker',
                                                        message_id=message_id, outcome='blocked'))
        self.assertEqual(self.receive()[0]['envelope']['status'], 'unread')

    def test_read_messages_survive_resume_and_do_not_wake_again(self):
        message_id = inbox.publish(self.mailbox, {'kind': 'progress'})
        inbox.transition(self.mailbox, message_id, 'read')
        event = self.cli('watch', '--state', str(self.state_path), '--wait', '0')
        self.assertEqual(event['event'], 'timeout')
        self.assertEqual(self.cli('receive', '--state', str(self.state_path))[0]['envelope']['status'], 'read')

    def test_watch_reloads_worker_registration(self):
        # A watcher may be armed before dispatch registers the return channel.
        state = lifecycle.load_state(self.state_path)
        state['workers'] = {}
        lifecycle.save_state(self.state_path, state)
        watcher = subprocess.Popen([sys.executable, str(SCRIPT), 'watch', '--state', str(self.state_path),
                                    '--wait', '5'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: watcher.kill() if watcher.poll() is None else None)
        time.sleep(0.1)
        lifecycle.save_state(self.state_path, self.state)
        message_id = inbox.publish(self.mailbox, {'kind': 'progress'})
        stdout, stderr = watcher.communicate(timeout=8)
        self.assertEqual(watcher.returncode, 0, stderr)
        event = json.loads(stdout)['result']
        self.assertEqual(event['event'], 'inbox_unread')
        self.assertEqual(event['messages'][0]['message_id'], message_id)

    def test_bash_watcher_survives_empty_windows_and_preserves_unread(self):
        watcher = subprocess.Popen(['bash', str(SCRIPT.with_name('watch_inbox.sh')),
                                    str(self.state_path), '0.1'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: watcher.terminate() if watcher.poll() is None else None)
        time.sleep(0.35)
        self.assertIsNone(watcher.poll(), 'empty timeouts must not terminate the Bash watcher')
        message_id = inbox.publish(self.mailbox, {'kind': 'blocked'})
        stdout, stderr = watcher.communicate(timeout=5)
        self.assertEqual(watcher.returncode, 0, stderr)
        # Exactly one JSON document: no timeout noise before the notification.
        self.assertEqual(json.loads(stdout)['result']['messages'][0]['message_id'], message_id)
        self.assertEqual(self.receive()[0]['envelope']['status'], 'unread')

    def test_bash_watcher_errors_instead_of_retrying_invalid_state(self):
        result = subprocess.run(['bash', str(SCRIPT.with_name('watch_inbox.sh')),
                                 str(self.root / 'missing state.json'), '0.1'],
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn('state does not exist', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_quiet_timeout_is_distinguishable_from_errors(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'watch', '--state', str(self.state_path),
                                 '--wait', '0.01', '--quiet-timeout'],
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')

    def test_completion_is_bound_to_assigned_mailbox_and_run(self):
        payload = self.report()
        inbox.publish(self.mailbox, payload)
        item = self.receive()[0]
        def validate():
            return lifecycle.validate_completion(item, state=self.state, worker='worker', task_id='T1',
                                                  verify_command=['true'], min_children=0)
        self.assertIsNotNone(validate())
        for field in ('run_id', 'task_id', 'assignment_id', 'worker', 'kind', 'verify_command'):
            previous = item['completion'][field]
            item['completion'][field] = 'wrong'
            self.assertIsNone(validate(), field)
            item['completion'][field] = previous
        item['envelope']['assignment_id'] = 'wrong'
        self.assertIsNone(validate())

    def test_unregistered_mailbox_is_not_attributed(self):
        unknown = Path(self.state['return_sink']['path']) / 'unknown'
        inbox.create(unknown)
        inbox.publish(unknown, self.report())
        self.assertEqual(self.receive(), [])

    def test_legacy_state_is_rejected_without_modifying_it(self):
        legacy = dict(self.state, return_sink={'name': 'old-sink'})
        lifecycle.save_state(self.state_path, legacy)
        before = self.state_path.read_bytes()
        with self.assertRaisesRegex(lifecycle.LifecycleError, 'legacy transport'):
            self.receive()
        self.assertEqual(self.state_path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
