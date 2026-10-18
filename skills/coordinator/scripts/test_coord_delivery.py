"""Public CLI journeys: native host tools, non-Git artifacts, and evidence handoff.

Native tool responses are fixture observations; Git, subprocesses, persisted CLI
sessions, checks, packaging, acceptance and integration use real collaborators.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import coord_drive as drive

CLI = Path(__file__).with_name('coord.py')
ROUTE = {'harness': 'native-fixture', 'model': 'fixture-model'}


def check(cid, code):
    return {'id': cid, 'argv': [sys.executable, '-c', code]}


def file_check(path, text):
    return check('content', f'from pathlib import Path; assert Path({path!r}).read_text() == {text!r}')


def item(oid='report', artifact='report.md', text='Verified finding', needs=()):
    return {'id': oid, 'objective': f'Write {oid}', 'rationale': 'Inform the caller',
            'scope': artifact, 'authority': 'Read sources; write the contracted file only',
            'artifact': artifact, 'needs': list(needs), 'checks': [file_check(artifact, text)]}


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='coord-delivery-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source with spaces'
        self.source.mkdir()
        (self.source / 'notes.txt').write_text('Source evidence')
        self.root = self.base / 'state'
        self.workers = self.base / 'workers.json'
        self.workers.write_text(json.dumps([{'route': ROUTE, 'runtime': 'native'}]))
        self.env = dict(os.environ, COORDINATOR_CONFIG_HOME=str(self.base / 'no-profile'))
        self.env.pop('GIT_DIR', None)
        self.env.pop('GIT_WORK_TREE', None)
        self.serial = 0

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(CLI), '--root', str(self.root), *map(str, args)],
                                capture_output=True, text=True, timeout=20, env=self.env)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            return json.loads(result.stdout)['result']
        self.assertNotEqual(result.returncode, 0)
        return result.stderr

    def data(self, value):
        self.serial += 1
        path = self.base / f'data-{self.serial}.json'
        path.write_text(json.dumps(value))
        return path

    def answer(self, status, value, kind):
        request = next(r for r in status['requests'] if r['kind'] == kind)
        prompt = self.cli('prompt', '--task', self.task, '--request', request['id'])['prompt']
        self.assertIn('## Answer', prompt)
        self.assertIn('## This request', prompt)
        return self.cli('answer', '--task', self.task, '--request', request['id'],
                        '--file', self.data(value))['next']

    def start(self, entries=None, patch=False, workers=None, launch=True):
        if workers:
            self.workers.write_text(json.dumps(workers))
        if patch:
            for argv in (['init', '-q', '-b', 'main'], ['add', '-A'],
                         ['-c', 'user.name=fixture', '-c', 'user.email=fixture@localhost', 'commit', '-qm', 'initial']):
                subprocess.run(['git', '-C', str(self.source), *argv], check=True)
        status = self.cli('start', '--repo' if patch else '--workspace', self.source,
                          '--goal', 'Deliver a verified finding', '--criterion', 'The deliverable contains the finding',
                          '--workers-file', self.workers, '--limits-file', self.data({'checks_first': False}))
        self.task = status['task']
        status = self.answer(status, {'pool': [ROUTE], 'rationale': 'Controlled native fixture'}, 'harness')
        status = self.cli('confirm-selection', '--task', self.task, '--question', status['questions'][0]['id'],
                          '--user-message', 'Use the fixture model for this synthetic test.')
        self.entries = entries or [item()]
        goal_checks = ([file_check('notes.txt', 'Verified finding')] if patch else
                       [dict(file_check(f"artifacts/{e['id']}/{e['artifact']}",
                                        'Second finding' if e['id'] == 'second' else 'Verified finding'),
                             id=e['id'] + '-goal') for e in self.entries])
        status = self.answer(status, {'outcomes': self.entries, 'goal_checks': goal_checks,
                                      'rationale': 'Focused evidence deliverables'}, 'decompose')
        return self.cli('advance', '--task', self.task) if launch else status

    def spawn(self):
        action = self.cli('host-next', '--task', self.task)
        self.assertEqual(action['action'], 'spawn', action)
        self.assertIn('label', action)
        cwd = Path(re.search(r'Working directory: (.*?) \(', action['message']).group(1))
        self.cli('host-result', '--task', self.task, '--action', action['id'],
                 '--file', self.data({'handle': action['label']}))
        return action, cwd

    def finish(self, spawn):
        action = self.cli('host-next', '--task', self.task)
        self.assertEqual(action['action'], 'observe', action)
        return self.cli('host-result', '--task', self.task, '--action', action['id'],
                        '--file', self.data({'handle': spawn['label'], 'status': 'finished'}))

    def accept(self, status):
        return self.answer(status, {'verdict': 'accept', 'reason': 'Inspected the deliverable against the source'}, 'inspect')

    def test_native_report_finishes_without_git_or_internal_commands(self):
        self.env['PATH'] = '/no-git-or-other-executables'
        status = self.start()
        self.assertEqual(status['waiting_on'], 'host')
        spawn, cwd = self.spawn()
        self.assertIn('Source material:', spawn['message'])
        (cwd / 'report.md').write_text('Verified finding')
        status = self.accept(self.finish(spawn))
        self.assertTrue(status['done'])
        self.assertIsNone(status['branch'])
        self.assertEqual(status['delivery'], 'artifact')
        self.assertFalse((self.source / '.git').exists())
        self.assertEqual((self.source / 'notes.txt').read_text(), 'Source evidence')
        delivered = Path(status['evidence']['outcomes'][0]['artifact']['path'])
        self.assertEqual(delivered.read_text(), 'Verified finding')
        self.assertEqual(status['evidence']['goal_checks'][0]['exit_code'], 0)
        self.assertIn('argv', status['evidence']['goal_checks'][0])
        self.assertFalse(status['host_actions'])

    def test_native_patch_keeps_original_checkout_unchanged(self):
        entry = item(artifact='notes.txt')
        entry.pop('artifact')
        self.start([entry], patch=True)
        spawn, cwd = self.spawn()
        (cwd / 'notes.txt').write_text('Verified finding')
        status = self.accept(self.finish(spawn))
        self.assertTrue(status['done'])
        self.assertEqual((self.source / 'notes.txt').read_text(), 'Source evidence')
        self.assertEqual((Path(status['integration']) / 'notes.txt').read_text(), 'Verified finding')
        self.assertTrue(status['branch'].startswith('coord/'))

    def test_repeated_issued_spawn_requires_reconciliation_not_duplicate_launch(self):
        self.start()
        first = self.cli('host-next', '--task', self.task)
        second = self.cli('host-next', '--task', self.task)
        self.assertEqual(second['id'], first['id'])
        self.assertEqual(second['action'], 'reconcile')
        self.cli('host-result', '--task', self.task, '--action', first['id'],
                 '--file', self.data({'status': 'unknown', 'basis': 'Host response was lost; cannot establish delivery'}))
        for _ in range(2):
            self.cli('advance', '--task', self.task)
            self.assertEqual(self.cli('host-next', '--task', self.task)['action'], 'reconcile')

    def test_inspected_non_delivery_allows_one_new_attempt_and_rejects_old_result(self):
        self.start()
        first = self.cli('host-next', '--task', self.task)
        status = self.cli('host-result', '--task', self.task, '--action', first['id'],
                          '--file', self.data({'status': 'not_started', 'basis': 'Host confirms tool invocation never occurred'}))
        self.cli('advance', '--task', self.task)
        second = self.cli('host-next', '--task', self.task)
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(second['action'], 'spawn')
        self.assertIn('no issued host action', self.cli('host-result', '--task', self.task, '--action', first['id'],
                      '--file', self.data({'handle': 'obsolete-worker'}), ok=False))

    def test_wrong_handle_does_not_settle_worker(self):
        self.start()
        spawn, cwd = self.spawn()
        observation = self.cli('host-next', '--task', self.task)
        self.assertIn('match the requested handle', self.cli('host-result', '--task', self.task,
                      '--action', observation['id'], '--file', self.data({'handle': 'other', 'status': 'finished'}), ok=False))
        status = self.cli('status', '--task', self.task)
        self.assertFalse(status['done'])
        self.assertFalse(status['requests'])

    def test_pending_spawn_cannot_be_acknowledged_before_it_is_issued(self):
        status = self.start()
        self.assertIn('no issued host action', self.cli('host-result', '--task', self.task,
                      '--action', status['host_actions'][0]['id'], '--file', self.data({'handle': 'worker'}), ok=False))

    def test_halt_before_dispatch_never_issues_a_spawn(self):
        self.start()
        self.cli('halt', '--task', self.task)
        self.assertIsNone(self.cli('host-next', '--task', self.task)['action'])
        status = self.cli('resume', '--task', self.task)
        self.cli('advance', '--task', self.task)
        self.assertEqual(self.cli('host-next', '--task', self.task)['action'], 'spawn')

    def test_halt_after_launch_intent_before_host_queue_never_spawns(self):
        self.start(launch=False)
        task_dir = self.root / 'tasks' / self.task
        with patch.object(drive, 'enqueue_host', side_effect=RuntimeError('interrupted before host queue')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                drive.advance(task_dir)
        self.cli('halt', '--task', self.task)
        self.assertIsNone(self.cli('host-next', '--task', self.task)['action'])

    def test_halt_bound_worker_waits_for_observed_settlement(self):
        self.start()
        spawn, cwd = self.spawn()
        self.cli('halt', '--task', self.task)
        stop = self.cli('host-next', '--task', self.task)
        self.assertEqual(stop['action'], 'stop')
        status = self.cli('host-result', '--task', self.task, '--action', stop['id'],
                          '--file', self.data({'handle': spawn['label'], 'status': 'working'}))
        self.assertTrue(status['halted'])
        self.assertFalse(status['done'])
        observe = self.cli('host-next', '--task', self.task)
        self.assertEqual(observe['action'], 'observe')
        self.cli('host-result', '--task', self.task, '--action', observe['id'],
                 '--file', self.data({'handle': spawn['label'], 'status': 'stopped'}))
        self.cli('resume', '--task', self.task)
        self.cli('advance', '--task', self.task)
        self.assertEqual(self.cli('host-next', '--task', self.task)['action'], 'spawn')

    def test_rejected_artifact_retries_in_fresh_workspace_and_preserves_old_bytes(self):
        self.start()
        first, first_cwd = self.spawn()
        (first_cwd / 'report.md').write_text('Verified finding')
        status = self.finish(first)
        self.answer(status, {'verdict': 'reject', 'reason': 'Evidence needs a clearer explanation',
                             'feedback': 'Explain the source of the finding'}, 'inspect')
        self.cli('advance', '--task', self.task)
        second, second_cwd = self.spawn()
        self.assertNotEqual(first_cwd, second_cwd)
        self.assertEqual((first_cwd / 'report.md').read_text(), 'Verified finding')
        self.assertIn('Explain the source', second['message'])
        (second_cwd / 'report.md').write_text('Verified finding')
        self.assertTrue(self.accept(self.finish(second))['done'])

    def test_dependency_artifact_is_copied_to_consumer_and_both_are_delivered(self):
        second = item('second', 'nested/result.txt', 'Second finding', needs=['report'])
        self.start([item(), second])
        first, cwd = self.spawn()
        (cwd / 'report.md').write_text('Verified finding')
        self.accept(self.finish(first))
        second_spawn, cwd = self.spawn()
        self.assertEqual((cwd / 'inputs/report/report.md').read_text(), 'Verified finding')
        (cwd / 'nested').mkdir()
        (cwd / 'nested/result.txt').write_text('Second finding')
        status = self.accept(self.finish(second_spawn))
        self.assertTrue(status['done'])
        self.assertEqual(len(status['evidence']['outcomes']), 2)

    def test_binary_artifact_preserves_exact_bytes(self):
        entry = item(artifact='image.bin')
        entry['checks'] = [check('binary', "from pathlib import Path; assert Path('image.bin').read_bytes() == b'\\x00\\xff'")]
        status = self.cli('start', '--workspace', self.source, '--goal', 'Deliver binary bytes', '--criterion', 'Exact bytes',
                          '--workers-file', self.workers)
        self.task = status['task']
        status = self.answer(status, {'pool': [ROUTE], 'rationale': 'Binary fixture'}, 'harness')
        status = self.cli('confirm-selection', '--task', self.task, '--question', status['questions'][0]['id'],
                          '--user-message', 'Use this fixture route.')
        goal = check('binary-goal', "from pathlib import Path; assert Path('artifacts/report/image.bin').read_bytes() == b'\\x00\\xff'")
        self.answer(status, {'outcomes': [entry], 'goal_checks': [goal], 'rationale': 'One binary'}, 'decompose')
        spawn, cwd = self.spawn()
        (cwd / 'image.bin').write_bytes(b'\x00\xff')
        status = self.accept(self.finish(spawn))
        self.assertEqual(Path(status['evidence']['outcomes'][0]['artifact']['path']).read_bytes(), b'\x00\xff')

    def test_artifact_symlink_escape_is_rejected_before_inspection(self):
        self.start()
        spawn, cwd = self.spawn()
        (cwd / 'report.md').symlink_to(self.source / 'notes.txt')
        status = self.finish(spawn)
        self.assertFalse(status['done'])
        self.assertFalse(status['requests'])
        self.cli('advance', '--task', self.task)
        retry = self.cli('host-next', '--task', self.task)
        self.assertIn('outside the assigned working directory', retry['message'])

    def test_artifact_name_rejects_parent_paths_and_internal_directories(self):
        for name in ['../escape.md', '/tmp/escape.md', '.coord/report.md', 'inputs/report.md']:
            with self.subTest(name=name):
                status = self.cli('start', '--workspace', self.source, '--goal', 'Report', '--criterion', 'Finding',
                                  '--workers-file', self.workers)
                self.task = status['task']
                status = self.answer(status, {'pool': [ROUTE], 'rationale': 'Fixture'}, 'harness')
                status = self.cli('confirm-selection', '--task', self.task, '--question', status['questions'][0]['id'],
                                  '--user-message', 'Use this fixture route.')
                rid = status['requests'][0]['id']
                error = self.cli('answer', '--task', self.task, '--request', rid, '--file', self.data(
                    {'outcomes': [item(artifact=name)], 'goal_checks': [check('fail', 'raise SystemExit(1)')],
                     'rationale': 'Invalid path fixture'}), ok=False)
                self.assertIn('relative file path', error)

    def test_process_worker_delivers_artifact_through_same_cli(self):
        code = ("import re,sys; from pathlib import Path; "
                "cwd=Path(re.search(r'Working directory: (.*?) \\(',sys.argv[1]).group(1)); "
                "(cwd/'report.md').write_text('Verified finding')")
        self.start(workers=[{'route': ROUTE, 'argv': [sys.executable, '-c', code, '{prompt}']}])
        deadline = time.monotonic() + 15
        while True:
            status = self.cli('advance', '--task', self.task)
            if status['requests']:
                break
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.05)
        self.assertFalse(status['host_actions'])
        self.assertTrue(self.accept(status)['done'])

    def test_doctor_accepts_native_configuration_without_profile(self):
        status = self.cli('doctor', '--workers-file', self.workers, '--delivery', 'artifact')
        self.assertTrue(status['ready'])
        self.assertEqual(status['workers'], [ROUTE])

    def test_native_artifact_stall_assessment_works_without_git(self):
        original_data = self.data
        self.data = lambda value: original_data(dict(value, stall_seconds=0)
                                                if value == {'checks_first': False} else value)
        self.env['PATH'] = '/no-git-or-other-executables'
        self.start()
        self.spawn()
        status = self.cli('advance', '--task', self.task)
        self.assertEqual(status['requests'][0]['kind'], 'assess')
        prompt = self.cli('prompt', '--task', self.task, '--request', status['requests'][0]['id'])['prompt']
        self.assertIn('no_progress', prompt)


if __name__ == '__main__':
    unittest.main()
