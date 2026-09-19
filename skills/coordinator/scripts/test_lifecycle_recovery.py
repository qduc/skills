"""Cross-process ownership and crash boundaries, using a fake external adapter."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import coord_lifecycle as lifecycle
import coord_state as tasks


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        created = tasks.create(argparse.Namespace(title='test', objective='test', project=str(self.root),
                                                  conversation=None, owner='owner-a'), self.root)
        self.task_dir = Path(created['state_path']).parent
        self.task_id = created['state']['id']
        self.state_path = self.root / 'lifecycle.json'
        self.call('prepare', '--task-id', self.task_id, '--task-dir', str(self.task_dir),
                  '--verify-command', '["true"]')
        self.adapter_env = patch.dict(os.environ, {'COORDINATOR_HERDR_HELPER': '/bin/true'})
        self.adapter_env.start()
        self.addCleanup(self.adapter_env.stop)

    def args(self, *parts, owner='owner-a', revision=1):
        args = lifecycle.parser().parse_args([*parts, '--state', str(self.state_path),
                                               '--owner', owner, '--revision', str(revision)])
        if args.command in {'prepare', 'run-task'}:
            args.verify_command = json.loads(args.verify_command)
        return args

    def call(self, *parts, **kwargs):
        return lifecycle.invoke(self.args(*parts, **kwargs))

    def take_over(self):
        return tasks.mutate(argparse.Namespace(command='claim', task=self.task_id, owner='owner-b',
                                               revision=1, takeover=True, reason='old session stopped'), self.root)

    def start_args(self):
        return self.args('start-worker', '--name', 'w', '--kind', 'pi', '--model', 'm',
                         '--provider', 'p', '--workspace', 'ws', '--cwd', str(self.workspace))

    def register(self):
        state = lifecycle.load_state(self.state_path)
        state['workers']['w'] = dict(name='w', kind='pi', model='m', provider='p', effort=None,
                                    pane_id='pane', tab_id='tab', workspace_id='ws', cwd=str(self.workspace),
                                    owned_tab=True, status='ready')
        lifecycle.save_state(self.state_path, state)
        brief = self.root / 'brief.md'
        brief.write_text('bounded work')
        return brief

    def test_stale_owner_cannot_dispatch_or_close_or_ack(self):
        brief = self.register()
        self.take_over()
        for parts in [('dispatch', '--worker', 'w', '--brief', str(brief)),
                      ('reconcile', '--disposition', 'close-owned'),
                      ('ack', '--worker', 'w', '--message-id', 'x', '--outcome', 'accepted'),
                      ('resolve-dispatch', '--worker', 'w', '--outcome', 'not-delivered', '--evidence', 'checked')]:
            with self.subTest(command=parts[0]), patch.object(lifecycle, 'run') as run:
                with self.assertRaisesRegex(tasks.StateError, 'not owned'):
                    self.call(*parts, revision=2)
                run.assert_not_called()

    def test_latest_revision_still_requires_current_owner(self):
        self.take_over()
        with self.assertRaisesRegex(tasks.StateError, 'not owned'):
            self.call('stop', revision='latest')
        self.call('stop', owner='owner-b', revision='latest')

    def test_missing_credentials_explain_both_required_flags(self):
        args = lifecycle.parser().parse_args(['stop', '--state', str(self.state_path)])
        with self.assertRaisesRegex(lifecycle.LifecycleError, '--owner.*--revision'):
            lifecycle.invoke(args)

    def test_stale_revision_cannot_launch(self):
        self.take_over()
        args = self.start_args()
        args.owner = 'owner-b'
        with patch.object(lifecycle, 'run') as run, self.assertRaisesRegex(tasks.StateError, 'stale revision'):
            lifecycle.invoke(args)
        run.assert_not_called()

    def test_unbound_external_state_is_refused(self):
        state = lifecycle.load_state(self.state_path)
        state.pop('task_dir')
        lifecycle.save_state(self.state_path, state)
        with patch.object(lifecycle, 'run') as run, self.assertRaisesRegex(lifecycle.LifecycleError, 'bound task'):
            lifecycle.invoke(self.start_args())
        run.assert_not_called()
        self.call('bind', '--task-dir', str(self.task_dir))
        self.assertEqual(lifecycle.load_state(self.state_path)['task_dir'], str(self.task_dir))

    def test_adapter_crash_after_creation_recovers_without_second_start(self):
        def crash(command, **kwargs):
            entry = lifecycle.load_state(self.state_path)['workers']['w']
            self.assertEqual(entry['status'], 'start_intended')
            receipt = {k: entry[k] for k in ('name', 'kind', 'model', 'provider', 'effort', 'cwd', 'workspace_id', 'operation_id')}
            receipt.update(pane_id='pane', tab_id='tab', owned_tab=True, status='launch_intended')
            lifecycle.save_state(Path(entry['receipt_file']), receipt)
            raise SystemExit('simulated abrupt exit before parent checkpoint')
        with patch.object(lifecycle, 'run', side_effect=crash), self.assertRaises(SystemExit):
            lifecycle.invoke(self.start_args())
        with patch.object(lifecycle, 'run') as run, self.assertRaisesRegex(lifecycle.LifecycleError, 'already recorded'):
            lifecycle.invoke(self.start_args())
        run.assert_not_called()
        state = lifecycle.load_state(self.state_path)
        state['workers']['w'].update(error='empty response', error_detail={'stdout': ''}, next_action='inspect launch')
        lifecycle.save_state(self.state_path, state)
        self.take_over()
        observed = dict(pane_id='pane', tab_id='tab', workspace_id='ws', agent='pi', agent_status='idle')
        with patch.object(lifecycle, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps({'result': {'agent': observed}}), '')) as run:
            recovered = self.call('recover-worker', '--worker', 'w', owner='owner-b', revision=2)
        self.assertEqual(recovered['status'], 'ready')
        saved = lifecycle.load_state(self.state_path)
        for field in ('error', 'error_detail', 'next_action'):
            self.assertNotIn(field, saved['workers']['w'])
        self.assertTrue(any(e['event'] == 'worker_error_resolved' for e in saved['events']))
        self.assertEqual(run.call_args.args[0][-2:], ['inspect', 'pane'])

    def test_crash_before_creation_response_remains_unresolved(self):
        with patch.object(lifecycle, 'run', side_effect=SystemExit), self.assertRaises(SystemExit):
            lifecycle.invoke(self.start_args())
        with patch.object(lifecycle, 'run') as run, self.assertRaisesRegex(lifecycle.LifecycleError, 'outcome unknown'):
            self.call('recover-worker', '--worker', 'w')
        run.assert_not_called()
        self.assertIn('preserved', lifecycle.cleanup_failed_run(self.state_path, 'w'))

    def test_submitted_prompt_is_not_repeated_after_crash(self):
        brief = self.register()
        with patch.object(lifecycle, 'run', side_effect=SystemExit), self.assertRaises(SystemExit):
            self.call('dispatch', '--worker', 'w', '--brief', str(brief))
        self.assertEqual(lifecycle.load_state(self.state_path)['workers']['w']['dispatch_status'], 'intended')
        with patch.object(lifecycle, 'run') as run:
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'already recorded'):
                self.call('dispatch', '--worker', 'w', '--brief', str(brief))
            self.assertIn('preserved', lifecycle.cleanup_failed_run(self.state_path, 'w'))
            run.assert_not_called()
        self.call('resolve-dispatch', '--worker', 'w', '--outcome', 'delivered', '--evidence', 'worker report in inbox')
        with self.assertRaisesRegex(lifecycle.LifecycleError, 'already recorded'):
            self.call('dispatch', '--worker', 'w', '--brief', str(brief))

    def test_explicit_non_delivery_resolution_allows_retry(self):
        brief = self.register()
        with patch.object(lifecycle, 'run', side_effect=SystemExit), self.assertRaises(SystemExit):
            self.call('dispatch', '--worker', 'w', '--brief', str(brief))
        self.call('resolve-dispatch', '--worker', 'w', '--outcome', 'not-delivered',
                  '--evidence', 'transport rejected before sending any input')
        with patch.object(lifecycle, 'run', return_value=subprocess.CompletedProcess([], 0, '{"status":"admitted"}', '')):
            self.assertTrue(self.call('dispatch', '--worker', 'w', '--brief', str(brief))['admitted'])

    def test_every_cli_command_declares_an_ownership_policy(self):
        parser = lifecycle.parser()
        sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        self.assertEqual(set(sub.choices), lifecycle.READ_COMMANDS | lifecycle.WORKER_COMMANDS | lifecycle.MUTATION_COMMANDS)

    def test_live_adapter_keeps_lock_after_coordinator_is_killed(self):
        adapter = self.root / 'adapter.py'
        marker = self.root / 'adapter-pid'
        release = self.root / 'release'
        adapter.write_text('''import os, pathlib, time
pathlib.Path(os.environ['TEST_MARKER']).write_text(str(os.getpid()))
while not pathlib.Path(os.environ['TEST_RELEASE']).exists(): time.sleep(0.02)
print('{"status":"failed","error":"test adapter stopped"}')
''')
        args = self.start_args()
        command = [sys.executable, lifecycle.__file__, 'start-worker', '--state', str(self.state_path),
                   '--name', 'w', '--kind', 'pi', '--model', 'm', '--provider', 'p',
                   '--workspace', 'ws', '--cwd', str(self.workspace), '--owner', 'owner-a', '--revision', '1']
        env = dict(os.environ, COORDINATOR_HERDR_HELPER=str(adapter), TEST_MARKER=str(marker), TEST_RELEASE=str(release))
        parent = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists(), 'adapter did not start')
            parent.kill()
            parent.wait(timeout=5)
            with self.assertRaisesRegex(tasks.StateError, 'busy'):
                self.take_over()
            release.touch()
            deadline = time.monotonic() + 5
            while True:
                try:
                    takeover = self.take_over()
                    break
                except tasks.StateError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.02)
            self.assertEqual(takeover['state']['owner'], 'owner-b')
            self.assertEqual(lifecycle.load_state(self.state_path)['workers']['w']['status'], 'start_intended')
        finally:
            release.touch()
            if parent.poll() is None:
                parent.kill()
            parent.wait(timeout=5)
