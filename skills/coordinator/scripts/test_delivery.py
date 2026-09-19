"""Workspace delivery must survive script changes and preserve durable evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import coord_inbox as inbox
import coord_lifecycle as lifecycle


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.path = self.root / 'durable' / 'lifecycle.json'
        self.state = lifecycle.prepare(argparse.Namespace(state=str(self.path), inbox=None, task_id='T', verify_command=['true']))
        self.state['workers']['w'] = {'cwd': str(self.workspace)}
        self.mailbox = lifecycle.register_mailbox(self.state, 'w')
        brief = self.root / 'brief.md'
        brief.write_text('bounded work')
        lifecycle.prepare_delivery(self.state, 'w', brief)
        lifecycle.save_state(self.path, self.state)
        self.entry = self.state['workers']['w']
        self.bundle = Path(self.entry['delivery_inbox'])

    def receive(self):
        return lifecycle.receive(argparse.Namespace(state=str(self.path), wait=0))

    def test_pinned_reporter_and_cleanup_preserve_unread_artifact(self):
        artifact = self.workspace / 'result.txt'
        artifact.write_text('done')
        result = subprocess.run([sys.executable, str(self.bundle / 'coord_lifecycle.py'), 'report',
                                 '--assignment-file', str(self.bundle / 'assignment.json'),
                                 '--kind', 'complete', '--artifact', str(artifact)],
                                cwd=self.workspace, capture_output=True, text=True, timeout=5,
                                env={'PATH': '/usr/bin:/bin', 'PYTHONPATH': ''})
        self.assertEqual(result.returncode, 0, result.stderr)
        mid = json.loads(result.stdout)['result']['message_id']
        self.assertTrue((self.bundle / 'unread' / f'{mid}.json').exists())
        self.assertEqual(self.receive()[0]['envelope']['status'], 'unread')
        manifest = lifecycle.preserve_files(self.state, 'w')
        lifecycle.save_state(self.path, self.state)
        shutil.rmtree(self.workspace)
        self.assertEqual(self.receive()[0]['envelope']['status'], 'unread')
        self.assertEqual(Path(manifest[mid]['path']).read_text(), 'done')
        self.assertEqual(manifest[mid]['sha256'], hashlib.sha256(b'done').hexdigest())

    def test_parallel_harvest_and_ack_never_resurrects_message(self):
        mid = inbox.publish(self.bundle, {'kind': 'progress'})
        inbox.harvest(self.bundle, self.mailbox)
        def work(i):
            if i % 2:
                inbox.harvest(self.bundle, self.mailbox)
            else:
                inbox.acknowledge(self.mailbox, mid)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(work, range(60)))
        self.assertEqual(inbox.read(self.mailbox), [])
        self.assertTrue((self.mailbox / 'processed' / f'{mid}.json').exists())
        self.assertTrue((self.bundle / 'unread' / f'{mid}.json').exists())

    def test_changed_artifact_blocks_retirement(self):
        artifact = self.workspace / 'result'
        artifact.write_text('changed')
        inbox.publish(self.bundle, {'kind': 'complete', 'artifact': str(artifact), 'sha256': hashlib.sha256(b'original').hexdigest()})
        with self.assertRaisesRegex(lifecycle.LifecycleError, 'changed since report'):
            lifecycle.preserve_files(self.state, 'w')
        self.assertFalse(self.entry.get('delivery_retired'))
        self.assertEqual(len(self.receive()), 1)

    def test_preserve_includes_already_processed_artifact(self):
        artifact = self.workspace / 'result'
        artifact.write_bytes(b'ok')
        mid = inbox.publish(self.bundle, {'kind': 'complete', 'artifact': str(artifact), 'sha256': hashlib.sha256(b'ok').hexdigest()})
        self.receive()
        inbox.acknowledge(self.mailbox, mid)
        manifest = lifecycle.preserve_files(self.state, 'w')
        self.assertEqual(Path(manifest[mid]['path']).read_bytes(), b'ok')
        self.assertEqual(self.receive(), [])

    def test_missing_delivery_is_an_error_until_retired(self):
        shutil.rmtree(self.bundle)
        with self.assertRaises(inbox.InboxError):
            self.receive()

    def test_bash_fallback_completes_without_inbox_message(self):
        result = subprocess.run(['bash', str(Path(lifecycle.__file__).with_name('watch_inbox.sh')),
                                 str(self.path), '0.1', '1'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['result']['event'], 'fallback_check_in')
        self.assertEqual(self.receive(), [])
