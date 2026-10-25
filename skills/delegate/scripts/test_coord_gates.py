"""Structural gates: selection, brief input, real-use, and lifecycle settlement."""
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
            with self.assertRaisesRegex(lifecycle.LifecycleError, 'recorded selection'):
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

    # Dispatch validates structural inputs, not the wording of an assignment.
    def assert_dispatch_rejected_without_effects(self, brief, error, *extra):
        with patch.object(lifecycle, 'run', side_effect=AssertionError('adapter must not run')) as run:
            with self.assertRaisesRegex(lifecycle.LifecycleError, error):
                self.call('dispatch', '--worker', 'w', '--brief', str(brief), *extra)
            run.assert_not_called()
        worker = lifecycle.load_state(self.state_path)['workers']['w']
        self.assertNotIn('dispatch_status', worker)
        self.assertNotIn('inbox', worker)

    def test_dispatch_accepts_equivalent_brief_wording(self):
        # No magic completion/return/authority labels or Markdown command spans.
        brief_text = ("Owner: lock-fixer. Work in src/lock.py only.\n"
                      "Done: the lock releases on close and issue #12 cannot recur.\n"
                      "Work alone and autonomously; record questions in your findings.\n"
                      "Check using python3 -m unittest tests.test_lock.\n")
        brief = self.ready_worker(brief_text)
        admitted = subprocess.CompletedProcess([], 0, json.dumps({'status': 'admitted'}), '')
        with patch.object(lifecycle, 'run', return_value=admitted) as run:
            self.assertTrue(self.call('dispatch', '--worker', 'w', '--brief', str(brief),
                                      '--brief-kind', 'review')['admitted'])
            run.assert_called_once()
        worker = lifecycle.load_state(self.state_path)['workers']['w']
        self.assertEqual(worker['dispatch_status'], 'admitted')
        self.assertTrue(Path(worker['brief']).read_text().startswith(brief_text))
        assignment = json.loads((Path(worker['delivery_inbox']) / 'assignment.json').read_text())
        self.assertEqual(assignment['verify_command'], ['true'])
        self.assertEqual(assignment['worker'], 'w')
        prompt = (Path(worker['inbox']) / 'dispatch.txt').read_text()
        self.assertIn('report --assignment-file', prompt)
        self.assertIn('never assign work to it', prompt)

    def test_return_path_is_supplied_by_dispatch_itself(self):
        brief = self.ready_worker(GOOD_BRIEF)  # dispatch appends the channel
        admitted = subprocess.CompletedProcess([], 0, json.dumps({'status': 'admitted'}), '')
        with patch.object(lifecycle, 'run', return_value=admitted):
            self.assertTrue(self.call('dispatch', '--worker', 'w', '--brief', str(brief))['admitted'])

    def test_dispatch_refuses_missing_brief(self):
        brief = self.ready_worker(GOOD_BRIEF)
        brief.unlink()
        self.assert_dispatch_rejected_without_effects(brief, 'brief does not exist')

    def test_dispatch_refuses_directory_as_brief(self):
        self.ready_worker(GOOD_BRIEF)
        self.assert_dispatch_rejected_without_effects(self.root, 'brief does not exist')

    def test_dispatch_refuses_empty_brief(self):
        brief = self.ready_worker(' \n\t')
        self.assert_dispatch_rejected_without_effects(brief, 'empty_brief')

    def test_legacy_flags_cannot_bypass_invalid_brief(self):
        brief = self.ready_worker('')
        self.assert_dispatch_rejected_without_effects(
            brief, 'empty_brief', '--lint-override', 'old caller',
            '--allow-ask-user', '--allow-delegation')

    def test_legacy_flags_remain_accepted_without_wording_gate(self):
        brief = self.ready_worker('bounded work')
        admitted = subprocess.CompletedProcess([], 0, json.dumps({'status': 'admitted'}), '')
        with patch.object(lifecycle, 'run', return_value=admitted):
            result = self.call('dispatch', '--worker', 'w', '--brief', str(brief),
                               '--lint-override', 'old caller', '--allow-ask-user', '--allow-delegation')
        self.assertTrue(result['admitted'])
        self.assertFalse(any(e['event'] == 'brief_lint_overridden'
                             for e in lifecycle.load_state(self.state_path)['events']))

    def test_dispatch_refuses_missing_verification_argv(self):
        brief = self.ready_worker(GOOD_BRIEF)
        state = lifecycle.load_state(self.state_path)
        state['verify_command'] = []
        lifecycle.save_state(self.state_path, state)
        self.assert_dispatch_rejected_without_effects(brief, 'coordinator verification argv')

    def test_dispatch_refuses_uncertain_launch(self):
        brief = self.ready_worker(GOOD_BRIEF)
        state = lifecycle.load_state(self.state_path)
        state['workers']['w']['status'] = 'start_unknown'
        lifecycle.save_state(self.state_path, state)
        self.assert_dispatch_rejected_without_effects(brief, 'recover the launch')

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
