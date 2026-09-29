import argparse
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import herdr_worker as worker
from test_start_term2 import FakeSteerHerdr


class WorkerTests(unittest.TestCase):
    def test_routes_preserve_model_provider_effort(self):
        for kind, flag in [('pi', '--thinking'), ('term2', '--reasoning')]:
            self.assertEqual(worker.route_argv(kind, 'model; $(echo nope)', 'provider', 'high'),
                             ['--provider', 'provider', '--model', 'model; $(echo nope)', flag, 'high'])
        argv = worker.route_argv('codex', 'm', 'p', 'high')
        self.assertIn('model_provider="p"', argv)
        self.assertIn('model_reasoning_effort="high"', argv)
        self.assertEqual(worker.route_argv('claude', 'm', effort='high'), ['--model', 'm', '--effort', 'high'])

    def test_unsupported_routes_fail_before_mutations(self):
        for values in [('unknown', 'm', None), ('pi', 'm', None), ('claude', 'm', 'arbitrary'), ('codex', '', None)]:
            with self.assertRaises(worker.WorkerError):
                worker.route_argv(*values)

    def start_args(self, directory, kind='pi'):
        return argparse.Namespace(kind=kind, model='exact model', provider='p', effort='high',
                                  cwd=directory, workspace='opaque-workspace', name='worker', label=None)

    def test_start_forwards_route_without_focusing(self):
        calls = []
        def run(argv, **kw):
            calls.append(argv)
            data = {'result': {}}
            if argv[1:3] == ['tab', 'create']:
                data['result'] = {'tab': {'tab_id': 'opaque-tab'}, 'root_pane': {'pane_id': 'opaque-pane'}}
            if argv[1:3] == ['agent', 'get']:
                data['result']['agent'] = {'agent': 'pi', 'agent_status': 'idle'}
            return subprocess.CompletedProcess(argv, 0, json.dumps(data), '')
        with tempfile.TemporaryDirectory() as directory, patch.object(worker.shutil, 'which', return_value='/bin/pi'):
            result = worker.Herdr(run=run).start(self.start_args(directory))
        self.assertEqual(result['status'], 'ready')
        self.assertIn('--no-focus', calls[0])
        self.assertEqual(calls[1][calls[1].index('--')+1:], worker.route_argv('pi', 'exact model', 'p', 'high'))

    def test_failed_start_preserves_resource_ids(self):
        client = worker.Herdr()
        with tempfile.TemporaryDirectory() as directory, patch.object(worker.shutil, 'which', return_value='/bin/pi'), patch.object(client, 'call', side_effect=[{'result': {'tab': {'tab_id': 't'}, 'root_pane': {'pane_id': 'p'}}}, worker.WorkerError('account verification')]) as call:
            result = client.start(self.start_args(directory))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['pane_id'], 'p')
        self.assertEqual(call.call_count, 2)

    def test_partial_create_keeps_known_tab(self):
        client = worker.Herdr()
        with tempfile.TemporaryDirectory() as directory, patch.object(worker.shutil, 'which', return_value='/bin/pi'), patch.object(client, 'call', return_value={'result': {'tab': {'tab_id': 't'}}}):
            result = client.start(self.start_args(directory))
        self.assertEqual(result['tab_id'], 't')
        self.assertEqual(result['status'], 'failed')

    def test_wrong_harness_is_not_ready(self):
        client = worker.Herdr()
        with tempfile.TemporaryDirectory() as directory, patch.object(worker.shutil, 'which', return_value='/bin/pi'), patch.object(client, 'call', side_effect=[{'result': {'tab': {'tab_id': 't'}, 'root_pane': {'pane_id': 'p'}}}, {'result': {}}, {'result': {'agent': {'agent': 'claude', 'agent_status': 'idle'}}}]):
            self.assertEqual(client.start(self.start_args(directory))['status'], 'failed')

    def test_submit_term2_uses_verified_input(self):
        fake = FakeSteerHerdr(status="idle")
        client = worker.Herdr(run=fake)
        with patch.object(client, 'wait', return_value={}):
            result = client.submit('p', 'Do this task')
        self.assertEqual(result['status'], 'admitted')
        self.assertFalse(any(c[1:3] == ['agent', 'prompt'] for c in fake.calls))
        self.assertTrue(any(c[1:3] == ['pane', 'send-keys'] for c in fake.calls))

    def test_submit_accepts_stale_working_status_only_when_screen_is_stably_idle(self):
        client = worker.Herdr()
        idle = '  ❯\n Standard\n / commands │ @ paths │ ! shell'
        reads = []
        def call(*parts, raw=False):
            if parts[:2] == ('pane', 'read'):
                reads.append(1)
                return idle
            return {'result': {'type': 'ok'}}
        with patch.object(client, 'inspect', return_value={'result': {'agent': {
                'pane_id': 'p', 'agent': 'term2', 'agent_status': 'working'}}}), \
                patch.object(client, 'call', side_effect=call), \
                patch.object(worker.start_term2, 'steer', return_value={'status': 'delivered'}), \
                patch.object(client, 'wait', return_value={}):
            result = client.submit('p', 'Do this task')
        self.assertEqual(result['status'], 'admitted')
        self.assertGreaterEqual(len(reads), 2)

    def test_submit_keeps_working_term2_refusal_when_screen_shows_activity(self):
        client = worker.Herdr()
        active = '  ❯ Do this\n ⏎ steer │ Alt+⏎ queue\n Generating...'
        with patch.object(client, 'inspect', return_value={'result': {'agent': {
                'pane_id': 'p', 'agent': 'term2', 'agent_status': 'working'}}}), \
                patch.object(client, 'call', return_value=active):
            with self.assertRaisesRegex(worker.WorkerError, 'not ready'):
                client.submit('p', 'Do this task')

    def test_failed_admission_is_not_retried(self):
        client = worker.Herdr()
        with patch.object(client, 'inspect', return_value={'result': {'agent': {'agent': 'pi', 'agent_status': 'idle'}}}), patch.object(client, 'call') as call, patch.object(client, 'wait', side_effect=worker.WorkerError('timeout')):
            result = client.submit('p', 'task')
        self.assertEqual(result['status'], 'admission_unknown')
        call.assert_called_once_with('agent', 'prompt', 'p', 'task')

    def agy_submit(self, screen, wait_effects):
        client = worker.Herdr()
        def call(*parts, raw=False):
            return screen if parts[:2] == ('pane', 'read') else {'result': {'type': 'ok'}}
        with patch.object(client, 'inspect', return_value={'result': {'agent': {'agent': 'agy', 'agent_status': 'idle'}}}), \
                patch.object(client, 'call', side_effect=call) as mock_call, patch.object(client, 'wait', side_effect=wait_effects):
            result = client.submit('p', 'Read the brief\nand execute it.')
        prompts = [c for c in mock_call.call_args_list if c.args[:2] == ('agent', 'prompt')]
        return result, prompts

    def test_agy_dropped_first_prompt_is_resent_once(self):
        # agy intermittently discards its first input: the banner stays at an empty prompt.
        idle_empty = 'Antigravity CLI\n>\n? for shortcuts   accept-edits'
        result, prompts = self.agy_submit(idle_empty, [worker.WorkerError('timeout'), {}])
        self.assertEqual(result['status'], 'admitted')
        self.assertEqual(result['resent'], 1)
        self.assertEqual(len(prompts), 2)

    def test_agy_is_not_resent_when_the_prompt_arrived(self):
        received = '> Read the brief and\n  execute it.\n>\n? for shortcuts'
        result, prompts = self.agy_submit(received, [worker.WorkerError('timeout')])
        self.assertEqual(result['status'], 'admission_unknown')
        self.assertEqual(len(prompts), 1)

    def test_agy_is_not_resent_while_busy(self):
        busy = 'Generating...\n>\nesc to cancel'
        result, prompts = self.agy_submit(busy, [worker.WorkerError('timeout')])
        self.assertEqual(result['status'], 'admission_unknown')
        self.assertEqual(len(prompts), 1)

    def test_agy_resend_is_bounded_to_one(self):
        idle_empty = '>\n? for shortcuts'
        result, prompts = self.agy_submit(idle_empty, [worker.WorkerError('timeout'), worker.WorkerError('timeout')])
        self.assertEqual(result['status'], 'admission_unknown')
        self.assertEqual(len(prompts), 2)

    def test_message_flag_is_inline_text_not_a_file_prefix(self):
        args = worker.parser().parse_args(['submit', 'p', '--message', 'Read /tmp/brief.md'])
        self.assertEqual(args.message, 'Read /tmp/brief.md')
        self.assertIsNone(args.message_file)
        with self.assertRaises(SystemExit), patch('sys.stderr'):
            worker.parser().parse_args(['submit', 'p', '--message-f', 'x'])
        with self.assertRaises(SystemExit), patch('sys.stderr'):
            worker.parser().parse_args(['submit', 'p', '--message', 'a', '--message-file', 'b'])

    def test_alias_cannot_mutate_caller(self):
        client = worker.Herdr()
        with patch.dict('os.environ', {'HERDR_PANE_ID': 'caller'}), patch.object(client, 'inspect', return_value={'result': {'agent': {'pane_id': 'caller', 'agent': 'pi', 'agent_status': 'idle'}}}), patch.object(client, 'call') as call:
            with self.assertRaisesRegex(worker.WorkerError, 'caller'):
                client.submit('alias', 'task')
            call.assert_not_called()

    def test_close_rejects_other_tab_and_extra_panes(self):
        args = worker.parser().parse_args(['close', 'p', '--owned-tab', 't'])
        client = worker.Herdr()
        observed = {'result': {'agent': {'pane_id': 'p', 'agent_status': 'done'}}}
        for tab, panes in [('other', []), ('t', [{'pane_id': 'p', 'tab_id': 't'}, {'pane_id': 'human', 'tab_id': 't'}])]:
            with patch.object(client, 'inspect', return_value=observed), patch.object(client, 'call', side_effect=[{'result': {'pane': {'tab_id': tab, 'workspace_id': 'w'}}}, {'result': {'panes': panes}}]) as call:
                with self.assertRaises(worker.WorkerError):
                    worker.execute(args, client)
                self.assertFalse(any(c.args[:2] == ('tab', 'close') for c in call.call_args_list))

    def test_close_only_settled_owned_single_pane(self):
        args = worker.parser().parse_args(['close', 'p', '--owned-tab', 't'])
        client = worker.Herdr()
        with patch.object(client, 'inspect', return_value={'result': {'agent': {'pane_id': 'p', 'agent_status': 'done'}}}), patch.object(client, 'call', side_effect=[{'result': {'pane': {'tab_id': 't', 'workspace_id': 'w'}}}, {'result': {'panes': [{'pane_id': 'p', 'tab_id': 't'}]}}, {'result': {}}]) as call:
            worker.execute(args, client)
        self.assertEqual(call.call_args.args, ('tab', 'close', 't'))

    def test_close_accepts_stale_working_status_when_screen_is_stably_idle(self):
        args = worker.parser().parse_args(['close', 'p', '--owned-tab', 't'])
        client = worker.Herdr()
        idle = '  ❯\n Standard\n / commands │ @ paths │ ! shell'
        def call(*parts, raw=False):
            if parts[:2] == ('pane', 'read'):
                return idle
            if parts[:2] == ('pane', 'get'):
                return {'result': {'pane': {'tab_id': 't', 'workspace_id': 'w'}}}
            if parts[:2] == ('pane', 'list'):
                return {'result': {'panes': [{'pane_id': 'p', 'tab_id': 't'}]}}
            return {'result': {}}
        with patch.object(client, 'inspect', return_value={'result': {'agent': {
                'pane_id': 'p', 'agent': 'term2', 'agent_status': 'working'}}}), \
                patch.object(client, 'call', side_effect=call) as called:
            worker.execute(args, client)
        self.assertEqual(sum(c.args[:2] == ('pane', 'read') for c in called.call_args_list), 2)
        self.assertEqual(called.call_args.args, ('tab', 'close', 't'))

    def test_close_still_refuses_extra_panes_for_stale_status(self):
        args = worker.parser().parse_args(['close', 'p', '--owned-tab', 't'])
        client = worker.Herdr()
        idle = '  ❯\n Standard\n / commands │ @ paths │ ! shell'
        def call(*parts, raw=False):
            if parts[:2] == ('pane', 'read'):
                return idle
            if parts[:2] == ('pane', 'get'):
                return {'result': {'pane': {'tab_id': 't', 'workspace_id': 'w'}}}
            return {'result': {'panes': [{'pane_id': 'p', 'tab_id': 't'},
                                         {'pane_id': 'human', 'tab_id': 't'}]}}
        with patch.object(client, 'inspect', return_value={'result': {'agent': {
                'pane_id': 'p', 'agent': 'term2', 'agent_status': 'working'}}}), \
                patch.object(client, 'call', side_effect=call) as called:
            with self.assertRaisesRegex(worker.WorkerError, 'other panes'):
                worker.execute(args, client)
        self.assertFalse(any(c.args[:2] == ('tab', 'close') for c in called.call_args_list))

    def test_wait_requires_requested_status(self):
        client = worker.Herdr()
        with patch.object(client, 'call', return_value={'result': {'agent': {'agent_status': 'idle'}}}):
            with self.assertRaisesRegex(worker.WorkerError, 'requested lifecycle state'):
                client.wait('p', ['working'])

    def test_receipt_keeps_ids_when_process_dies_during_launch(self):
        client = worker.Herdr()
        with tempfile.TemporaryDirectory() as directory, patch.object(worker.shutil, 'which', return_value='/bin/pi'):
            args = self.start_args(directory)
            args.receipt_file = str(Path(directory) / 'launch.json')
            args.operation_id = 'op'
            def call(*parts, **kwargs):
                durable = json.loads(Path(args.receipt_file).read_text())
                if parts[:2] == ('tab', 'create'):
                    self.assertEqual(durable['status'], 'create_intended')
                    return {'result': {'tab': {'tab_id': 't'}, 'root_pane': {'pane_id': 'p'}}}
                self.assertEqual(durable['status'], 'launch_intended')
                self.assertEqual(durable['pane_id'], 'p')
                raise SystemExit('process died')
            with patch.object(client, 'call', side_effect=call), self.assertRaises(SystemExit):
                client.start(args)
            saved = json.loads(Path(args.receipt_file).read_text())
            self.assertEqual(saved['operation_id'], 'op')
            self.assertEqual(saved['tab_id'], 't')
            with patch.object(client, 'call') as call, self.assertRaisesRegex(worker.WorkerError, 'already exists'):
                client.start(args)
            call.assert_not_called()

    def test_failed_launch_receipt_is_durable(self):
        client = worker.Herdr()
        with tempfile.TemporaryDirectory() as directory, patch.object(worker.shutil, 'which', return_value='/bin/pi'):
            args = self.start_args(directory)
            args.receipt_file = str(Path(directory) / 'receipt.json')
            with patch.object(client, 'call', side_effect=worker.WorkerError('connection lost')):
                result = client.start(args)
            self.assertEqual(json.loads(Path(args.receipt_file).read_text()), result)
            self.assertEqual(result['status'], 'failed')

    def test_stop_unknown_state_withholds_keys(self):
        args = worker.parser().parse_args(['stop', 'p'])
        client = worker.Herdr()
        with patch.object(client, 'inspect', return_value={'result': {'agent': {'agent_status': 'unknown'}}}), patch.object(client, 'call') as call:
            with self.assertRaises(worker.WorkerError):
                worker.execute(args, client)
            call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
