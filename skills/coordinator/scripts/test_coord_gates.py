"""Gates that used to be prose: selection, brief contract, real-use, and lifecycle settlement."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import coord_lifecycle as lifecycle
import coord_state as tasks

GOOD_BRIEF = ("Done when `python3 -m unittest test_feature.py` passes. "
              "Do not ask the user questions. Do not delegate to subagents.")


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        created = tasks.create(argparse.Namespace(title='gates', objective='gates', project=str(self.root),
                                                  conversation=None, owner='owner'), self.root)
        self.task_dir = Path(created['state_path']).parent
        self.task_id = created['state']['id']
        self.state_path = self.root / 'lifecycle.json'
        self.adapter_env = patch.dict(os.environ, {'COORDINATOR_HERDR_HELPER': '/bin/true'})
        self.adapter_env.start()
        self.addCleanup(self.adapter_env.stop)
        self.call('prepare', '--task-id', self.task_id, '--task-dir', str(self.task_dir),
                  '--verify-command', '["true"]')

    def call(self, *parts):
        args = lifecycle.parser().parse_args([*parts, '--state', str(self.state_path),
                                               '--owner', 'owner', '--revision', 'latest'])
        if args.command == 'prepare':
            args.verify_command = json.loads(args.verify_command)
        return lifecycle.invoke(args)

    def select(self, pool):
        task = tasks.load(self.task_dir)
        task['selection'] = pool
        tasks.save(self.task_dir, task)

    def start(self, model='m'):
        return self.call('start-worker', '--name', 'w', '--kind', 'pi', '--model', model, '--provider', 'p',
                         '--workspace', 'ws', '--cwd', str(self.workspace))

    def ready_worker(self, brief_text):
        state = lifecycle.load_state(self.state_path)
        state['workers']['w'] = dict(name='w', kind='pi', model='m', provider='p', effort=None, pane_id='pane',
                                    tab_id='tab', workspace_id='ws', cwd=str(self.workspace), owned_tab=True,
                                    status='ready')
        lifecycle.save_state(self.state_path, state)
        brief = self.root / 'brief.md'
        brief.write_text(brief_text)
        return brief

    def mutate_task(self, command, **fields):
        return tasks.mutate(argparse.Namespace(command=command, task=self.task_id, owner='owner',
                                               revision='latest', **fields), self.root)

    def complete(self):
        patch_file = self.root / 'complete.json'
        patch_file.write_text(json.dumps({'status': 'completed'}))
        return self.mutate_task('checkpoint', patch_file=str(patch_file))

    # Selection: stop rule 1 enforced on the Herdr path.
    def test_worker_without_confirmed_selection_never_launches(self):
        with patch.object(lifecycle, 'run') as run:
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'user-confirmed selection'):
                self.start()
            run.assert_not_called()
        self.assertEqual(lifecycle.load_state(self.state_path)['workers'], {})

    def test_worker_outside_confirmed_pool_never_launches(self):
        self.select([{'harness': 'pi', 'model': 'other-model'}])
        with patch.object(lifecycle, 'run') as run:
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'pi/m is not in'):
                self.start()
            run.assert_not_called()

    def test_confirmed_route_reaches_the_adapter(self):
        self.select([{'harness': 'pi', 'model': 'm'}])  # no provider pinned: any provider matches
        receipt = json.dumps({'status': 'ready', 'pane_id': 'pane'})
        with patch.object(lifecycle, 'run', return_value=subprocess.CompletedProcess([], 0, receipt, '')) as run:
            self.assertEqual(self.start()['status'], 'ready')
            run.assert_called_once()

    def test_route_matching_respects_pinned_fields(self):
        self.assertTrue(lifecycle.route_matches({'harness': 'pi', 'model': 'm', 'provider': 'p'}, 'pi', 'm', 'p', None))
        self.assertFalse(lifecycle.route_matches({'harness': 'pi', 'model': 'm', 'provider': 'p'}, 'pi', 'm', 'q', None))
        self.assertFalse(lifecycle.route_matches({'harness': 'pi', 'model': 'm', 'effort': 'high'}, 'pi', 'm', None, 'low'))

    # Brief contract: lint inside dispatch, not as a separate remembered step.
    def test_dispatch_refuses_brief_missing_contract_clauses(self):
        brief = self.ready_worker('bounded work')
        with patch.object(lifecycle, 'run') as run:
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'communication contract'):
                self.call('dispatch', '--worker', 'w', '--brief', str(brief))
            run.assert_not_called()
        worker = lifecycle.load_state(self.state_path)['workers']['w']
        self.assertNotIn('dispatch_status', worker)
        self.assertNotIn('inbox', worker)  # nothing was registered for a refused dispatch

    def test_return_path_is_supplied_by_dispatch_itself(self):
        brief = self.ready_worker(GOOD_BRIEF)  # names no report path; dispatch appends the channel
        admitted = subprocess.CompletedProcess([], 0, json.dumps({'status': 'admitted'}), '')
        with patch.object(lifecycle, 'run', return_value=admitted):
            self.assertTrue(self.call('dispatch', '--worker', 'w', '--brief', str(brief))['admitted'])

    def test_lint_override_is_recorded(self):
        brief = self.ready_worker('bounded work')
        admitted = subprocess.CompletedProcess([], 0, json.dumps({'status': 'admitted'}), '')
        with patch.object(lifecycle, 'run', return_value=admitted):
            self.call('dispatch', '--worker', 'w', '--brief', str(brief), '--lint-override', 'user approved a quick spike')
        events = [e for e in lifecycle.load_state(self.state_path)['events'] if e['event'] == 'brief_lint_overridden']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['reason'], 'user approved a quick spike')

    # Completion: every path, not only outcome plans.
    def test_unsettled_lifecycle_worker_blocks_completion(self):
        self.ready_worker(GOOD_BRIEF)
        with self.assertRaisesRegex(tasks.StateError, 'reconcile lifecycle workers'):
            self.complete()
        state = lifecycle.load_state(self.state_path)
        state['workers']['w']['status'] = 'closed'
        lifecycle.save_state(self.state_path, state)
        self.assertEqual(self.complete()['state']['status'], 'completed')

    def test_required_real_use_blocks_completion_until_waived(self):
        self.mutate_task('real-use', status='required', source='skill changed', evidence=None)
        with self.assertRaisesRegex(tasks.StateError, 'real-use verification is still required'):
            self.complete()
        self.mutate_task('real-use', status='waived', source='user: "skip the real-use run this time"', evidence=None)
        self.assertEqual(self.complete()['state']['status'], 'completed')

    def test_real_use_pass_records_evidence_hash(self):
        self.mutate_task('real-use', status='required', source='skill changed', evidence=None)
        with self.assertRaisesRegex(tasks.StateError, 'evidence file'):
            self.mutate_task('real-use', status='passed', source='fresh agent run', evidence=None)
        evidence = self.root / 'run.md'
        evidence.write_text('fresh agent used the shipped skill on a real task')
        self.mutate_task('real-use', status='passed', source='fresh agent run', evidence=str(evidence))
        gate = tasks.load(self.task_dir)['gates']['real_use']
        self.assertEqual(gate['status'], 'passed')
        self.assertEqual(len(gate['events'][-1]['evidence']['sha256']), 64)

    def test_generic_checkpoint_cannot_touch_gates(self):
        patch_file = self.root / 'sneaky.json'
        patch_file.write_text(json.dumps({'gates': {'real_use': {'status': 'waived'}}}))
        with self.assertRaisesRegex(tasks.StateError, 'only title, status, and details'):
            self.mutate_task('checkpoint', patch_file=str(patch_file))


if __name__ == '__main__':
    unittest.main()
