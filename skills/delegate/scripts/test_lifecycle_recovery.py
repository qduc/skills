"""Cross-process ownership and crash boundaries, using a fake external adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
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
        task = tasks.load(self.task_dir)
        task['selection'] = [{'harness': 'pi', 'model': 'm', 'provider': 'p'}]
        tasks.save(self.task_dir, task)
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
        brief.write_text('Done when `python3 -m unittest test_feature.py` passes. Do not ask the user questions. Do not delegate to subagents.')
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


    def historical_intent(self):
        state = lifecycle.load_state(self.state_path)
        operation = uuid.uuid4().hex
        entry = dict(name='w', kind='pi', model='m', provider='p', effort=None,
                     cwd=str(self.workspace), workspace_id='ws', operation_id=operation,
                     receipt_file=str(self.root / 'operations' / state['run_id'] / (operation + '.json')),
                     status='start_intended', children=[])
        state['workers']['w'] = entry
        lifecycle.record(state, 'worker_start_intended', worker='w', operation_id=operation)
        lifecycle.save_state(self.state_path, state)
        self.evidence = self.root / 'prelaunch-evidence.md'
        self.evidence.write_text('Owner inspected the original host receipt and source boundary: no external start ran.')
        self.evidence_hash = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
        return entry

    def attestation_args(self, entry):
        return ('recover-worker', '--worker', 'w', '--confirm-prelaunch', entry['operation_id'],
                '--evidence-file', str(self.evidence), '--evidence-sha256', self.evidence_hash)

    def cli(self, *parts, owner='owner-a', revision=1, env=None):
        return subprocess.run([sys.executable, lifecycle.__file__, *parts, '--state', str(self.state_path),
                               '--owner', owner, '--revision', str(revision)],
                              capture_output=True, text=True, timeout=10, env=env)

    def fake_start_adapter(self):
        adapter = self.root / 'fake-start.py'
        adapter.write_text('''import json, os, pathlib, sys
args = sys.argv[1:]
assert args[0] == 'start'
operation = args[args.index('--operation-id') + 1]
receipt_path = pathlib.Path(args[args.index('--receipt-file') + 1])
state = json.loads(pathlib.Path(os.environ['TEST_STATE']).read_text())
entry = state['workers']['w']
assert entry['status'] == 'start_intended' and entry['operation_id'] == operation
assert entry['receipt_file'] == str(receipt_path) and not receipt_path.exists()
with pathlib.Path(os.environ['TEST_STARTS']).open('a') as log: log.write(operation + '\\n')
receipt = {k: entry[k] for k in ('name', 'kind', 'model', 'provider', 'effort', 'cwd', 'workspace_id', 'operation_id')}
receipt.update(status='ready', pane_id='pane', tab_id='tab', owned_tab=True)
receipt_path.parent.mkdir(parents=True, exist_ok=True)
receipt_path.write_text(json.dumps(receipt))
print(json.dumps(receipt))
''')
        return dict(os.environ, COORDINATOR_HERDR_HELPER=str(adapter),
                    TEST_STATE=str(self.state_path), TEST_STARTS=str(self.root / 'starts'))

    def cli_start(self, env):
        return self.cli('start-worker', '--name', 'w', '--kind', 'pi', '--model', 'm',
                        '--provider', 'p', '--workspace', 'ws', '--cwd', str(self.workspace), env=env)

    def test_missing_adapter_has_no_intent_then_corrected_cli_starts_once(self):
        before = self.state_path.read_bytes()
        env = dict(os.environ, COORDINATOR_HERDR_HELPER=str(self.root / 'absent-adapter'))
        result = self.cli_start(env)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('optional adapter unavailable', result.stderr)
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertFalse((self.root / 'operations').exists())
        self.assertFalse((self.root / 'starts').exists())
        env = self.fake_start_adapter()
        result = self.cli_start(env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.cli_start(env).returncode, 1)
        self.assertEqual(len((self.root / 'starts').read_text().splitlines()), 1)

    def test_historic_cli_attestation_and_explicit_retry_preserve_history(self):
        entry = self.historical_intent()
        env = self.fake_start_adapter()
        old_state = lifecycle.load_state(self.state_path)
        result = self.cli(*self.attestation_args(entry), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'starts').exists(), 'recovery must not launch')
        saved = lifecycle.load_state(self.state_path)
        self.assertEqual(saved['workers']['w']['status'], 'start_intended')
        # Attestation is not readiness, even if dispatch's brief is absent.
        with patch.object(lifecycle, 'run') as run, self.assertRaisesRegex(lifecycle.LifecycleError, 'recover the launch'):
            self.call('dispatch', '--worker', 'w', '--brief', str(self.root / 'missing-brief'))
        run.assert_not_called()
        # Changed route cannot spend the one-shot authorization.
        args = self.start_args()
        args.workspace = 'another-workspace'
        with patch.object(lifecycle, 'run') as run, self.assertRaisesRegex(lifecycle.LifecycleError, 'identity'):
            lifecycle.invoke(args)
        run.assert_not_called()
        result = self.cli_start(env)
        self.assertEqual(result.returncode, 0, result.stderr)
        worker = lifecycle.load_state(self.state_path)['workers']['w']
        self.assertNotEqual(worker['operation_id'], entry['operation_id'])
        self.assertNotEqual(worker['receipt_file'], entry['receipt_file'])
        self.assertEqual(worker['prelaunch_retry_of'], entry['operation_id'])
        self.assertEqual(worker['status'], 'ready')
        self.assertTrue(Path(worker['receipt_file']).is_file())
        self.assertFalse(Path(entry['receipt_file']).exists())
        state = lifecycle.load_state(self.state_path)
        self.assertEqual(state['events'][:len(old_state['events'])], old_state['events'])
        retried = next(e for e in state['events'] if e['event'] == 'worker_prelaunch_retried')
        self.assertEqual(retried['previous']['operation_id'], entry['operation_id'])
        self.assertEqual(retried['previous']['prelaunch_attestation']['evidence_sha256'], self.evidence_hash)
        self.assertEqual(retried['previous']['prelaunch_attestation']['owner'], 'owner-a')
        self.assertEqual(retried['previous']['prelaunch_attestation']['revision'], 1)
        self.assertEqual(self.cli_start(env).returncode, 1)
        self.assertEqual(self.cli(*self.attestation_args(entry), env=env).returncode, 1)
        self.assertEqual(len((self.root / 'starts').read_text().splitlines()), 1)

    def test_attestation_requires_exact_operation_and_paired_evidence(self):
        entry = self.historical_intent()
        good = self.attestation_args(entry)
        cases = [good[:3] + ('--confirm-prelaunch', 'other') + good[5:], good[:5],
                 good[:3] + good[5:], good[:-1] + ('0' * 64,)]
        for parts in cases:
            before = self.state_path.read_bytes()
            with self.subTest(parts=parts), patch.object(lifecycle, 'run') as run:
                with self.assertRaises(lifecycle.LifecycleError):
                    self.call(*parts)
                run.assert_not_called()
                self.assertEqual(self.state_path.read_bytes(), before)

    def test_conflicting_or_uncertain_worker_cannot_be_attested(self):
        entry = self.historical_intent()
        original = self.state_path.read_bytes()
        conflicts = [{'status': 'ready'}, {'status': 'start_unknown'}, {'status': 'failed'},
                     {'status': 'dispatched'}, {'pane_id': 'pane'}, {'tab_id': 'tab'},
                     {'owned_tab': True}, {'dispatch_status': 'intended'}, {'dispatch_id': 'sent'},
                     {'children': [{'name': 'child'}]}, {'prelaunch_retry_of': 'old'}]
        for fields in conflicts:
            self.state_path.write_bytes(original)
            state = lifecycle.load_state(self.state_path)
            state['workers']['w'].update(fields)
            lifecycle.save_state(self.state_path, state)
            before = self.state_path.read_bytes()
            with self.subTest(fields=fields), patch.object(lifecycle, 'run') as run:
                with self.assertRaises(lifecycle.LifecycleError):
                    self.call(*self.attestation_args(entry))
                run.assert_not_called()
                self.assertEqual(self.state_path.read_bytes(), before)
        self.state_path.write_bytes(original)
        receipt = Path(entry['receipt_file'])
        receipt.parent.mkdir(parents=True)
        for content in ('{}', 'malformed', json.dumps(dict(entry, operation_id='other'))):
            receipt.write_text(content)
            with self.subTest(receipt=content), self.assertRaises(lifecycle.LifecycleError):
                self.call(*self.attestation_args(entry))
        receipt.unlink()
        receipt.symlink_to(self.root / 'absent-receipt-target')
        with self.assertRaises(lifecycle.LifecycleError):
            self.call(*self.attestation_args(entry))

    def test_retry_rechecks_resources_identity_evidence_and_selection(self):
        entry = self.historical_intent()
        self.call(*self.attestation_args(entry))
        original = self.state_path.read_bytes()
        for fields in ({'pane_id': 'late-pane'}, {'dispatch_status': 'unknown'},
                       {'operation_id': 'other'}, {'model': 'other'}, {'cwd': '/other'}):
            self.state_path.write_bytes(original)
            state = lifecycle.load_state(self.state_path)
            state['workers']['w'].update(fields)
            lifecycle.save_state(self.state_path, state)
            before = self.state_path.read_bytes()
            with self.subTest(fields=fields), patch.object(lifecycle, 'run') as run:
                with self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.invoke(self.start_args())
                run.assert_not_called()
                self.assertEqual(self.state_path.read_bytes(), before)
        self.state_path.write_bytes(original)
        Path(entry['receipt_file']).parent.mkdir(parents=True)
        Path(entry['receipt_file']).write_text('{}')
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.invoke(self.start_args())
        Path(entry['receipt_file']).unlink()
        self.evidence.write_text('changed after attestation')
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.invoke(self.start_args())
        self.evidence.write_text('Owner inspected the original host receipt and source boundary: no external start ran.')
        task = tasks.load(self.task_dir)
        task['selection'] = []
        tasks.save(self.task_dir, task)
        with self.assertRaisesRegex(lifecycle.LifecycleError, 'recorded selection'):
            lifecycle.invoke(self.start_args())

    def test_stale_owner_revision_and_changed_owner_cannot_spend_attestation(self):
        entry = self.historical_intent()
        self.call(*self.attestation_args(entry))
        self.take_over()
        for owner, revision in [('owner-a', 2), ('owner-b', 1)]:
            for parts in [self.attestation_args(entry), ('start-worker', '--name', 'w', '--kind', 'pi',
                           '--model', 'm', '--provider', 'p', '--workspace', 'ws', '--cwd', str(self.workspace))]:
                with self.subTest(owner=owner, parts=parts), patch.object(lifecycle, 'run') as run:
                    with self.assertRaises(tasks.StateError):
                        self.call(*parts, owner=owner, revision=revision)
                    run.assert_not_called()
        args = self.start_args()
        args.owner, args.revision = 'owner-b', 'latest'
        with self.assertRaisesRegex(lifecycle.LifecycleError, 'owner|revision'):
            lifecycle.invoke(args)
        # A fresh positive attestation under the current owner may replace an unspent one.
        self.call(*self.attestation_args(entry), owner='owner-b', revision=2)
        args = self.start_args()
        args.owner, args.revision = 'owner-b', 'latest'
        with patch.object(lifecycle, 'run', side_effect=SystemExit), self.assertRaises(SystemExit):
            lifecycle.invoke(args)
        # Even an abrupt retry death cannot mint a second prelaunch retry.
        retry = lifecycle.load_state(self.state_path)['workers']['w']
        with self.assertRaises(lifecycle.LifecycleError):
            self.call(*self.attestation_args(retry), owner='owner-b', revision=2)

    def test_timeout_and_malformed_launch_cannot_rearm_from_absence(self):
        for failure in [lifecycle.LifecycleError('command timed out after 150s'),
                        subprocess.CompletedProcess([], 0, 'not JSON', '')]:
            state = lifecycle.load_state(self.state_path)
            state['workers'] = {}
            lifecycle.save_state(self.state_path, state)
            with self.subTest(failure=failure):
                kwargs = {'side_effect': failure} if isinstance(failure, Exception) else {'return_value': failure}
                with patch.object(lifecycle, 'run', **kwargs), self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.invoke(self.start_args())
                worker = lifecycle.load_state(self.state_path)['workers']['w']
                self.assertEqual(worker['status'], 'start_unknown')
                with self.assertRaisesRegex(lifecycle.LifecycleError, 'outcome unknown'):
                    self.call('recover-worker', '--worker', 'w')
                with self.assertRaisesRegex(lifecycle.LifecycleError, 'already recorded'):
                    lifecycle.invoke(self.start_args())
                self.evidence = self.root / 'timeout-evidence'
                self.evidence.write_text('No receipt exists')
                self.evidence_hash = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
                with self.assertRaises(lifecycle.LifecycleError):
                    self.call(*self.attestation_args(worker))


    def test_retry_requires_identical_route_and_keeps_authorization_on_preflight_failure(self):
        entry = self.historical_intent()
        self.call(*self.attestation_args(entry))
        original = self.state_path.read_bytes()
        for field, value in [('kind', 'term2'), ('model', 'other'), ('provider', 'other'),
                             ('effort', 'high'), ('cwd', '/other'), ('workspace', 'other'),
                             ('label', 'other')]:
            args = self.start_args()
            setattr(args, field, value)
            with self.subTest(field=field), patch.object(lifecycle, 'run') as run:
                with self.assertRaisesRegex(lifecycle.LifecycleError, 'identity'):
                    lifecycle.invoke(args)
                run.assert_not_called()
                self.assertEqual(self.state_path.read_bytes(), original)
        with patch.dict(os.environ, {'COORDINATOR_HERDR_HELPER': str(self.root / 'missing')}):
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'optional adapter unavailable'):
                lifecycle.invoke(self.start_args())
        self.assertEqual(self.state_path.read_bytes(), original)

    def test_same_owner_new_revision_requires_fresh_attestation(self):
        entry = self.historical_intent()
        self.call(*self.attestation_args(entry))
        task = tasks.load(self.task_dir)
        task['revision'] += 1
        tasks.save(self.task_dir, task)
        args = self.start_args()
        args.revision = 'latest'
        before = self.state_path.read_bytes()
        with patch.object(lifecycle, 'run') as run:
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'owner/revision changed'):
                lifecycle.invoke(args)
            run.assert_not_called()
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_no_external_start_if_intent_cannot_be_persisted(self):
        with patch.object(lifecycle, 'save_state', side_effect=OSError('test disk failure')):
            with patch.object(lifecycle, 'run') as run, self.assertRaises(OSError):
                lifecycle.invoke(self.start_args())
            run.assert_not_called()
        self.assertEqual(lifecycle.load_state(self.state_path)['workers'], {})

    def test_actual_timeout_exception_and_malformed_cli_remain_unknown(self):
        with patch.object(lifecycle.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['fake'], 150)):
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'timed out'):
                lifecycle.invoke(self.start_args())
        state = lifecycle.load_state(self.state_path)
        self.assertEqual(state['workers']['w']['status'], 'start_unknown')
        state['workers'] = {}
        lifecycle.save_state(self.state_path, state)
        adapter = self.root / 'malformed.py'
        adapter.write_text("print('not JSON')")
        result = self.cli_start(dict(os.environ, COORDINATOR_HERDR_HELPER=str(adapter)))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('invalid JSON', result.stderr)
        self.assertEqual(lifecycle.load_state(self.state_path)['workers']['w']['status'], 'start_unknown')
        result = self.cli('recover-worker', '--worker', 'w')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('outcome unknown', result.stderr)
