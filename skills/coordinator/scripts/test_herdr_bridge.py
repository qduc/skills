import argparse
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import coord_lifecycle as lifecycle


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.state = self.root / 'state.json'
        lifecycle.prepare(argparse.Namespace(state=str(self.state), inbox=None, task_id='T1', verify_command=['true']))
        self.env = patch.dict(os.environ, {'COORDINATOR_HERDR_HELPER': '/bin/true'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_start_saves_route_and_opaque_ids(self):
        receipt = dict(status='ready', pane_id='opaque-pane', tab_id='opaque-tab', model='chosen', provider='p', effort='high', owned_tab=True)
        with patch.object(lifecycle, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(receipt), '')) as run:
            lifecycle.start_worker(argparse.Namespace(state=str(self.state), name='w', kind='pi', model='chosen', provider='p', effort='high', workspace='workspace', cwd=str(self.workspace), label=None))
        self.assertIn('--model', run.call_args.args[0])
        self.assertIn('chosen', run.call_args.args[0])
        self.assertEqual(lifecycle.load_state(self.state)['workers']['w']['pane_id'], 'opaque-pane')

    def test_failed_launch_keeps_recovery_receipt(self):
        receipt = dict(status='failed', tab_id='opaque-tab', error='startup blocked', owned_tab=True)
        with patch.object(lifecycle, 'run', return_value=subprocess.CompletedProcess([], 1, json.dumps(receipt), '')):
            with self.assertRaises(lifecycle.LifecycleError):
                lifecycle.start_worker(argparse.Namespace(state=str(self.state), name='w', kind='pi', model='chosen', provider='p', effort=None, workspace='workspace', cwd=str(self.workspace), label=None))
        with patch.object(lifecycle, 'run') as run:
            result = lifecycle.cleanup_failed_run(self.state, 'w')
            run.assert_not_called()
        self.assertEqual(result['preserved']['tab_id'], 'opaque-tab')

    def test_dispatch_writes_contract_and_uses_recorded_pane(self):
        state = lifecycle.load_state(self.state)
        state['workers']['w'] = dict(pane_id='opaque-pane', cwd=str(self.workspace))
        lifecycle.save_state(self.state, state)
        brief = self.root / 'brief.md'
        brief.write_text('bounded task')
        def run(command, **kwargs):
            self.assertEqual(command[3:5], ['submit', 'opaque-pane'])
            body = Path(command[-1]).read_text()
            self.assertIn('report --assignment-file', body)
            self.assertIn('never assign work to it', body)
            return subprocess.CompletedProcess([], 0, '{"status":"admitted"}', '')
        with patch.object(lifecycle, 'run', side_effect=run):
            result = lifecycle.dispatch(argparse.Namespace(state=str(self.state), worker='w', brief=str(brief), timeout_ms=5000))
        self.assertTrue(result['admitted'])
        self.assertTrue((Path(lifecycle.load_state(self.state)['workers']['w']['inbox']) / 'assignment.json').is_file())

    def test_model_required_at_cli_boundary(self):
        with self.assertRaises(SystemExit), patch('sys.stderr'):
            lifecycle.parser().parse_args(['start-worker', '--state', 's', '--name', 'w', '--kind', 'pi', '--workspace', 'ws', '--cwd', '.'])

    def test_inventory_delegates_without_parsing_cli_help(self):
        data = dict(available=True, kinds=[dict(kind='pi', available=True)], live_agents=[])
        with patch.object(lifecycle, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(data), '')) as run:
            self.assertEqual(lifecycle.inventory(argparse.Namespace()), data)
        self.assertEqual(run.call_args.args[0][-1], 'inventory')
