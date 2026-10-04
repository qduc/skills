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
import shutil
from unittest.mock import patch

import coord_state as state

SCRIPT = Path(state.__file__).resolve()
PROGRESS = Path(__file__).with_name('coord_progress.py')


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

    def test_checkpoint_records_phase_and_progress_exposes_it(self):
        result = self.checkpoint(1, {'details': {'phase': 'phase-2'}})
        self.assertEqual(result['state']['details']['phase'], 'phase-2')
        progress = subprocess.run([sys.executable, str(PROGRESS), '--state', str(self.path / 'state.json')],
                                  capture_output=True, text=True, timeout=10)
        self.assertEqual(progress.returncode, 0, progress.stderr)
        self.assertEqual(json.loads(progress.stdout)['phase'], 'phase-2')

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

    def test_unambiguous_task_id_prefix_resolves_to_full_id(self):
        shown = self.cli('show', '--task', self.task[:8])
        self.assertEqual(shown['state']['id'], self.task)
        self.patch_path.write_text(json.dumps({'status': 'active'}))
        self.cli('checkpoint', '--task', self.task[:8], '--owner', self.owner, '--revision', '1',
                 '--patch-file', str(self.patch_path))

    def test_ambiguous_or_short_task_id_prefix_is_rejected(self):
        (self.root / 'tasks' / (self.task[:8] + 'ffff')).mkdir()
        ambiguous = self.run_cli('show', '--task', self.task[:8])
        self.assertNotEqual(ambiguous.returncode, 0)
        self.assertIn('ambiguous', ambiguous.stdout + ambiguous.stderr)
        short = self.run_cli('show', '--task', self.task[:3])
        self.assertNotEqual(short.returncode, 0)

    def test_default_location_honors_only_absolute_xdg_path(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': '/tmp/state-root'}):
            self.assertEqual(state.root_path(), Path('/tmp/state-root/coordinator'))
        with patch.dict(os.environ, {'XDG_STATE_HOME': 'relative'}):
            self.assertEqual(state.root_path(), Path.home() / '.local/state/coordinator')

    def test_auto_binding_finds_nonce_in_newest_transcript(self):
        projects = self.root / 'projects'; (projects / 'one').mkdir(parents=True); (projects / 'two').mkdir()
        (projects / 'one' / 'old.jsonl').write_text('{"text":"other"}\n')
        target = projects / 'two' / 'live.jsonl'; target.write_text('{"text":"coord-nonce-test"}\n')
        args = argparse.Namespace(task=self.task, owner=self.owner, revision=1, session_id='auto',
                                  nonce='coord-nonce-test', projects_dir=str(projects))
        state.bind_session(args, self.root)
        binding = state._load_bindings(self.root)['bindings']['claude:live']
        self.assertEqual(binding['transcript_path'], str(target))

    def test_auto_binding_rejects_no_match_and_ambiguous_match(self):
        projects = self.root / 'projects'; (projects / 'one').mkdir(parents=True); (projects / 'two').mkdir()
        args = argparse.Namespace(task=self.task, owner=self.owner, revision=1, session_id='auto',
                                  nonce='missing', projects_dir=str(projects))
        with self.assertRaisesRegex(state.StateError, 'no Claude transcript'):
            state.bind_session(args, self.root)
        (projects / 'one' / 'a.jsonl').write_text('coord-nonce-ambiguous')
        (projects / 'two' / 'b.jsonl').write_text('coord-nonce-ambiguous')
        args.nonce = 'coord-nonce-ambiguous'
        with self.assertRaisesRegex(state.StateError, 'multiple Claude transcripts'):
            state.bind_session(args, self.root)

    def test_auto_binding_starts_at_current_size_and_rebind_preserves_offset(self):
        projects = self.root / 'projects'; directory = projects / 'one'; directory.mkdir(parents=True)
        transcript = directory / 'live.jsonl'; transcript.write_text('old transcript\ncoord-nonce-offset\n')
        args = argparse.Namespace(task=self.task, owner=self.owner, revision=1, session_id='auto',
                                  nonce='coord-nonce-offset', projects_dir=str(projects))
        state.bind_session(args, self.root)
        first = state._load_bindings(self.root)['bindings']['claude:live']
        self.assertEqual(first['transcript_offset'], transcript.stat().st_size)
        transcript.write_text(transcript.read_text() + 'new line\n')
        args.revision = 2
        state.bind_session(args, self.root)
        second = state._load_bindings(self.root)['bindings']['claude:live']
        self.assertEqual(second['transcript_offset'], first['transcript_offset'])

    def test_auto_binding_ignores_transcripts_beyond_search_limit(self):
        projects = self.root / 'projects'; directory = projects / 'one'; directory.mkdir(parents=True)
        old = directory / 'old.jsonl'; old.write_text('coord-nonce-too-old')
        for index in range(50):
            path = directory / f'{index:02d}.jsonl'; path.write_text('newer')
            os.utime(path, (index + 2, index + 2))
        os.utime(old, (1, 1))
        args = argparse.Namespace(task=self.task, owner=self.owner, revision=1, session_id='auto',
                                  nonce='coord-nonce-too-old', projects_dir=str(projects))
        with self.assertRaisesRegex(state.StateError, 'no Claude transcript'):
            state.bind_session(args, self.root)

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

    def test_incident_notes_validate_key_and_scope_but_accept_legacy_text(self):
        legacy = {'kind': 'incident', 'text': 'free-form incident from an older session'}
        lesson = {'kind': 'incident', 'key': 'worktree-removed-under-worker', 'what': 'worker stranded',
                  'cost': 'relaunch', 'rule': 'close the tab first', 'scope': 'general', 'at': '2026-09-26'}
        saved = self.checkpoint(1, {'details': {'notes': [legacy, lesson, 'plain string note']}})
        self.assertEqual(saved['state']['details']['notes'][1], lesson)
        before = (self.path / 'state.json').read_bytes()
        for invalid in ({'kind': 'incident', 'key': 'Has Spaces'}, {'kind': 'incident', 'scope': 'team'}):
            self.patch_path.write_text(json.dumps({'details': {'notes': [invalid]}}))
            result = self.run_cli('checkpoint', '--task', self.task, '--owner', self.owner,
                                  '--revision', '2', '--patch-file', str(self.patch_path))
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

    def memory_apply(self, revision, actions):
        action_path = self.root / 'actions.json'
        action_path.write_text(json.dumps({'task_id': self.task, 'actions': actions}))
        return self.cli('memory-apply', '--task', self.task, '--owner', self.owner,
                        '--revision', str(revision), '--actions-file', str(action_path))

    def test_v1_fixture_is_read_unchanged_and_first_memory_write_imports_legacy(self):
        fixture = Path(__file__).parent / 'fixtures' / 'v1-task-state.json'
        fixture_state = json.loads(fixture.read_text())
        fixture_path = self.root / 'tasks' / fixture_state['id']
        fixture_path.mkdir()
        shutil.copyfile(fixture, fixture_path / 'state.json')
        before = state.load(fixture_path)
        self.assertEqual(before['schema_version'], 1)
        self.assertEqual(before, fixture_state)
        self.assertEqual(before['details']['notes'], fixture_state['details']['notes'])
        shown = self.run_cli('show', '--task', fixture_state['id'])
        self.assertEqual(shown.returncode, 0, shown.stderr)
        rendered = self.run_cli('render', '--task', fixture_state['id'])
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.assertIn('Legacy unclassified history', (fixture_path / 'state.md').read_text())
        fixture_actions = self.root / 'fixture-actions.json'
        fixture_actions.write_text(json.dumps({'task_id': fixture_state['id'], 'actions': [
            {'action': 'journal', 'event_id': 'fixture-journal', 'category': 'state', 'text': 'fixture observation'}]}))
        applied = self.run_cli('memory-apply', '--task', fixture_state['id'], '--owner', fixture_state['owner'],
                               '--revision', str(fixture_state['revision']), '--actions-file', str(fixture_actions))
        self.assertEqual(applied.returncode, 0, applied.stderr)
        upgraded = json.loads(applied.stdout)['result']['state']
        self.assertEqual(upgraded['schema_version'], 2)
        self.assertEqual(upgraded['memory']['audit'][0]['after']['notes_count'], len(fixture_state['details']['notes']))

        legacy_notes = [{'kind': 'incident', 'key': 'historical-note', 'text': 'historical note'}]
        self.checkpoint(1, {'details': {'notes': legacy_notes}})
        result = self.memory_apply(2, [{'action': 'journal', 'event_id': 'j1',
            'category': 'state', 'text': 'uncertain observation'},
            {'action': 'cold-add', 'event_id': 'legacy-link', 'category': 'state', 'text': 're-evaluated note',
             'supersedes': ['legacy:historical-note']}])
        saved = result['state']
        self.assertEqual(saved['schema_version'], 2)
        self.assertEqual(saved['details']['notes'], legacy_notes)
        self.assertEqual(saved['memory']['audit'][0]['action'], 'legacy-import')

    def test_memory_batch_is_atomic_and_fenced(self):
        before = (self.path / 'state.json').read_bytes()
        with self.assertRaises(AssertionError):
            self.memory_apply(1, [{'action': 'journal', 'event_id': 'ok', 'category': 'state', 'text': 'kept'},
                                  {'action': 'unknown', 'event_id': 'bad'}])
        self.assertEqual((self.path / 'state.json').read_bytes(), before)
        denied = self.run_cli('memory-apply', '--task', self.task, '--owner', 'other', '--revision', '1',
                              '--actions-file', str(self.root / 'actions.json'))
        self.assertNotEqual(denied.returncode, 0)

    def test_memory_invariants_provenance_scope_budget_and_idempotence(self):
        invalid = [
            {'action': 'cold-add', 'event_id': 'p', 'category': 'decisions', 'text': 'no source'},
            {'action': 'cold-add', 'event_id': 'w', 'category': 'state', 'scope': 'workspace', 'text': 'x'},
            {'action': 'hot-update', 'event_id': 'h', 'focus': 'x' * 5000},
        ]
        for action in invalid:
            path = self.root / 'actions.json'; path.write_text(json.dumps({'actions': [action]}))
            result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner,
                                  '--revision', '1', '--actions-file', str(path))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(state.load(self.path)['schema_version'], 1)
        applied = self.memory_apply(1, [{'action': 'journal', 'event_id': 'same', 'category': 'state', 'text': 'one'}])
        revision = applied['state']['revision']
        again = self.memory_apply(revision, [{'action': 'journal', 'event_id': 'same', 'category': 'state', 'text': 'one'}])
        self.assertEqual(again['state']['revision'], revision)
        self.assertEqual(len(again['state']['memory']['journal']), 1)

    def test_supersession_is_same_scope_and_symmetric(self):
        first = self.memory_apply(1, [{'action': 'cold-add', 'event_id': 'old', 'category': 'discoveries',
            'text': 'old claim', 'provenance': [{'kind': 'test', 'ref': 'case'}]}])
        old_id = first['state']['memory']['cold'][0]['id']
        second = self.memory_apply(2, [{'action': 'supersede', 'event_id': 'new', 'old_id': old_id,
            'replacement': {'category': 'discoveries', 'scope': 'task', 'text': 'new claim',
                             'provenance': [{'kind': 'test', 'ref': 'case2'}]}}])
        old, new = second['state']['memory']['cold']
        self.assertEqual(old['status'], 'superseded')
        self.assertEqual(old['superseded_by'], new['id'])
        self.assertEqual(new['supersedes'], [old['id']])

    def test_stale_memory_revision_writes_nothing(self):
        self.memory_apply(1, [{'action': 'journal', 'event_id': 'first', 'category': 'state', 'text': 'x'}])
        before = (self.path / 'state.json').read_bytes()
        actions = self.root / 'actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'journal', 'event_id': 'stale', 'category': 'state', 'text': 'y'}]}))
        result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '1', '--actions-file', str(actions))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('stale revision', result.stderr)
        self.assertEqual((self.path / 'state.json').read_bytes(), before)

    def test_different_payload_reusing_event_id_fails(self):
        self.memory_apply(1, [{'action': 'journal', 'event_id': 'same', 'category': 'state', 'text': 'one'}])
        actions = self.root / 'actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'journal', 'event_id': 'same', 'category': 'state', 'text': 'two'}]}))
        result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '2', '--actions-file', str(actions))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('different payload', result.stderr)

    def test_superseded_target_and_malformed_cycle_are_rejected(self):
        first = self.memory_apply(1, [{'action': 'cold-add', 'event_id': 'old', 'category': 'discoveries', 'text': 'old', 'provenance': [{'kind': 'test', 'ref': 'old'}]}])
        old_id = first['state']['memory']['cold'][0]['id']
        second = self.memory_apply(2, [{'action': 'supersede', 'event_id': 'new', 'old_id': old_id, 'replacement': {'category': 'discoveries', 'text': 'new', 'provenance': [{'kind': 'test', 'ref': 'new'}]}}])
        new_id = second['state']['memory']['cold'][1]['id']
        actions = self.root / 'actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'supersede', 'event_id': 'again', 'old_id': old_id, 'replacement': {'category': 'discoveries', 'text': 'bad', 'provenance': [{'kind': 'test', 'ref': 'bad'}]}}]}))
        result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '3', '--actions-file', str(actions))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(state.load(self.path)['memory']['cold'][1]['id'], new_id)
        malformed = state.load(self.path)
        malformed['memory']['cold'][0]['supersedes'] = [new_id]
        malformed['memory']['cold'][1]['superseded_by'] = old_id
        with self.assertRaises(state.StateError):
            state.validate_memory(malformed['memory'])

    def test_memory_budgets_and_provenance_report_consolidation(self):
        actions = [{'action': 'journal', 'event_id': f'j{i}', 'category': 'state', 'text': 'x'} for i in range(30)]
        self.memory_apply(1, actions)
        path = self.root / 'actions.json'
        path.write_text(json.dumps({'actions': [{'action': 'journal', 'event_id': 'j30', 'category': 'state', 'text': 'x'}]}))
        result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '2', '--actions-file', str(path))
        self.assertIn('consolidation required', result.stderr)
        cases = [
            {'action': 'journal', 'event_id': 'long-j', 'category': 'state', 'text': 'a' * 700},
            {'action': 'cold-add', 'event_id': 'long-c', 'category': 'state', 'text': 'a' * 1100},
            {'action': 'cold-add', 'event_id': 'refs', 'category': 'decisions', 'text': 'x', 'provenance': [{'kind': 'x', 'ref': str(i)} for i in range(4)]},
            {'action': 'journal', 'event_id': 'unicode', 'category': 'state', 'text': '🙂' * 150},
        ]
        # Fresh records keep each budget failure independent and make the error observable.
        for action in cases:
            created = self.cli('create', '--title', 'budget', '--objective', 'test', '--project', str(self.root), '--conversation', 'budget')
            task, owner = created['state']['id'], created['state']['owner']
            path.write_text(json.dumps({'actions': [action]}))
            result = self.run_cli('memory-apply', '--task', task, '--owner', owner, '--revision', '1', '--actions-file', str(path))
            self.assertIn('consolidation required', result.stderr, action)

    def test_cold_update_cannot_edit_claim_fields_and_checkpoint_isolated(self):
        added = self.memory_apply(1, [{'action': 'cold-add', 'event_id': 'claim', 'category': 'state', 'text': 'immutable'}])
        item_id = added['state']['memory']['cold'][0]['id']
        path = self.root / 'actions.json'
        path.write_text(json.dumps({'actions': [{'action': 'cold-update', 'event_id': 'edit', 'id': item_id, 'disposition': 'current', 'text': 'changed', 'category': 'decisions', 'provenance': [{'kind': 'x', 'ref': 'y'}]}]}))
        result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '2', '--actions-file', str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('immutable claim fields', result.stderr)
        path.write_text(json.dumps({'memory': {}, 'audit': []}))
        result = self.run_cli('checkpoint', '--task', self.task, '--owner', self.owner, '--revision', '2', '--patch-file', str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checkpoint accepts only', result.stderr)

    def test_journal_dispositions_are_audited_and_require_pending_ids(self):
        added = self.memory_apply(1, [{'action': 'journal', 'event_id': 'j', 'category': 'state', 'text': 'pending'}])
        journal_id = added['state']['memory']['journal'][0]['id']
        result = self.memory_apply(2, [{'action': 'journal', 'event_id': 'dispose', 'journal_ids': [journal_id], 'disposition': 'consolidated', 'destination': 'cold:later'}])
        self.assertEqual(result['state']['memory']['journal'][0]['status'], 'consolidated')
        self.assertEqual(result['state']['memory']['audit'][-1]['after']['destination'], 'cold:later')
        path = self.root / 'actions.json'
        path.write_text(json.dumps({'actions': [{'action': 'journal', 'event_id': 'bad', 'journal_ids': [journal_id, 'missing'], 'disposition': 'discarded'}]}))
        failed = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '3', '--actions-file', str(path))
        self.assertNotEqual(failed.returncode, 0)

    def test_host_fields_v2_stability_and_hot_boundary(self):
        result = self.memory_apply(1, [{'action': 'cold-add', 'event_id': 'host', 'category': 'state', 'text': 'x', 'id': 'model-id', 'created_at': '1900', 'updated_at': '1900'}])
        item = result['state']['memory']['cold'][0]
        self.assertNotEqual(item['id'], 'model-id')
        self.assertNotEqual(item['created_at'], '1900')
        stable = self.memory_apply(2, [{'action': 'ignore', 'event_id': 'second', 'reason': 'none'}])
        self.assertEqual(sum(x['action'] == 'legacy-import' for x in stable['state']['memory']['audit']), 1)
        self.assertEqual(stable['state']['schema_version'], 2)
        path = self.root / 'actions.json'
        path.write_text(json.dumps({'actions': [{'action': 'hot-update', 'event_id': 'ops', 'focus': 'x', 'next_action': 'forbidden'}]}))
        failed = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '3', '--actions-file', str(path))
        self.assertNotEqual(failed.returncode, 0)

    def test_authored_limit_survives_disposition_supersession_and_withdrawal(self):
        def limit_text(limit):
            text = ''
            while state._authored_bytes({'text': text + 'a', 'provenance': []}) <= limit:
                text += 'a'
            return text
        journal_text = limit_text(600)
        claim_text = limit_text(1024)
        first = self.memory_apply(1, [{'action': 'journal', 'event_id': 'at-journal', 'category': 'state', 'text': journal_text}])
        journal_id = first['state']['memory']['journal'][0]['id']
        second = self.memory_apply(2, [{'action': 'cold-add', 'event_id': 'at-claim', 'category': 'state', 'text': claim_text}])
        old_id = second['state']['memory']['cold'][0]['id']
        third = self.memory_apply(3, [{'action': 'journal', 'event_id': 'consolidate', 'journal_ids': [journal_id], 'disposition': 'consolidated', 'destination': 'cold'}])
        self.assertEqual(third['state']['memory']['journal'][0]['status'], 'consolidated')
        fourth = self.memory_apply(4, [{'action': 'supersede', 'event_id': 'replace-at-limit', 'old_id': old_id,
            'replacement': {'category': 'state', 'text': claim_text}}])
        replacement_id = fourth['state']['memory']['cold'][1]['id']
        fifth = self.memory_apply(5, [{'action': 'cold-update', 'event_id': 'withdraw-at-limit', 'id': replacement_id,
            'disposition': 'withdrawn', 'reason': 'obsolete'}])
        self.assertEqual(fifth['state']['memory']['cold'][1]['status'], 'withdrawn')
        path = self.root / 'actions.json'
        path.write_text(json.dumps({'actions': [{'action': 'cold-update', 'event_id': 'resurrect', 'id': replacement_id, 'disposition': 'current'}]}))
        failed = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '6', '--actions-file', str(path))
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('withdrawn claims are terminal', failed.stderr)

        current = self.memory_apply(6, [{'action': 'cold-add', 'event_id': 'same-status', 'category': 'state', 'text': 'small'}])
        current_id = current['state']['memory']['cold'][-1]['id']
        noop = self.memory_apply(7, [{'action': 'cold-update', 'event_id': 'same-status-update', 'id': current_id, 'disposition': 'current'}])
        self.assertEqual(noop['state']['revision'], current['state']['revision'])

    def test_malformed_memory_types_are_state_errors_for_load_and_cli_scan(self):
        record = state.load(self.path)
        record['schema_version'] = 2; record['memory'] = state._memory_default()
        record['memory']['cold'] = [{'id': 'c', 'category': ['state'], 'text': 'x', 'status': 'current', 'scope': 'task',
            'task_id': self.task, 'created_at': state.now(), 'updated_at': state.now(), 'provenance': [], 'supersedes': [], 'superseded_by': None}]
        (self.path / 'state.json').write_text(json.dumps(record))
        with self.assertRaises(state.StateError):
            state.load(self.path)
        listed = self.run_cli('list')
        self.assertEqual(listed.returncode, 0)
        self.assertTrue(any('invalid cold category' in warning for warning in json.loads(listed.stdout)['result']['warnings']))
        self.setUp()
        for action in ({'action': 'journal', 'event_id': 'bad', 'category': 'state', 'text': 'x', 'disposition': []},
                       {'action': 'cold-update', 'event_id': 'bad2', 'id': 'x', 'disposition': []}):
            path = self.root / 'actions.json'; path.write_text(json.dumps({'actions': [action]}))
            result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '1', '--actions-file', str(path))
            self.assertNotIn('Traceback', result.stderr)
            self.assertNotEqual(result.returncode, 0)

    def test_one_event_can_apply_hot_and_cold_actions_and_replay_stale(self):
        actions = [{'action': 'hot-update', 'event_id': 'compound', 'focus': 'combined'},
                   {'action': 'cold-add', 'event_id': 'compound', 'category': 'state', 'text': 'combined claim'}]
        first = self.memory_apply(1, actions)
        self.assertEqual(first['state']['memory']['hot']['focus'], 'combined')
        self.assertEqual(len(first['state']['memory']['cold']), 1)
        action_path = self.root / 'actions.json'; action_path.write_text(json.dumps({'task_id': self.task, 'actions': actions}))
        replay = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '1', '--actions-file', str(action_path))
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(json.loads(replay.stdout)['result']['state']['revision'], first['state']['revision'])

    def test_grouped_noop_part_persists_other_part_and_replay_key(self):
        current = self.memory_apply(1, [{'action': 'cold-add', 'event_id': 'seed', 'category': 'state', 'text': 'seed'}])
        current_id = current['state']['memory']['cold'][0]['id']
        actions = [{'action': 'hot-update', 'event_id': 'mixed', 'focus': 'persisted focus'},
                   {'action': 'cold-update', 'event_id': 'mixed', 'id': current_id, 'disposition': 'current'}]
        applied = self.memory_apply(2, actions)
        on_disk = state.load(self.path)
        self.assertEqual(on_disk['memory']['hot']['focus'], 'persisted focus')
        self.assertEqual(sum(event['event_id'] == 'mixed' for event in on_disk['memory']['audit']), 1)
        replay = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '2', '--actions-file', str(self.root / 'actions.json'))
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(json.loads(replay.stdout)['result']['state']['revision'], applied['state']['revision'])

        journal_actions = [{'action': 'cold-update', 'event_id': 'mixed-journal', 'id': current_id, 'disposition': 'current'},
                           {'action': 'journal', 'event_id': 'mixed-journal', 'category': 'state', 'text': 'only once'}]
        next_result = self.memory_apply(3, journal_actions)
        self.assertEqual(len(next_result['state']['memory']['journal']), 1)
        self.assertEqual(sum(event['event_id'] == 'mixed-journal' for event in next_result['state']['memory']['audit']), 1)
        replay_path = self.root / 'actions.json'
        replay_path.write_text(json.dumps({'task_id': self.task, 'actions': journal_actions}))
        replay = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '3', '--actions-file', str(replay_path))
        self.assertEqual(replay.returncode, 0)
        self.assertEqual(json.loads(replay.stdout)['result']['state']['revision'], next_result['state']['revision'])

    def test_legacy_import_payload_cannot_authorize_unrelated_stale_batch(self):
        self.checkpoint(1, {'details': {'notes': [{'kind': 'incident', 'key': 'imported', 'text': 'old'}]}})
        record = state.load(self.path)
        import_id = record['memory']['audit'][0]['event_id']
        actions = self.root / 'actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'hot-update', 'event_id': import_id, 'focus': 'must fail'},
                                                   {'action': 'journal', 'event_id': import_id, 'category': 'state', 'text': 'must fail'}]}))
        result = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', '1', '--actions-file', str(actions))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('stale revision', result.stderr)

    def test_checkpoint_is_first_v1_upgrade_and_legacy_notes_remain_append_only(self):
        self.checkpoint(1, {'details': {'notes': [{'kind': 'incident', 'key': 'old', 'text': 'old'}]}})
        upgraded = state.load(self.path)
        self.assertEqual(upgraded['schema_version'], 2)
        self.assertEqual(upgraded['memory']['audit'][0]['action'], 'legacy-import')
        self.patch_path.write_text(json.dumps({'details': {'notes': [{'kind': 'incident', 'key': 'replacement', 'text': 'replaced'}]}}))
        result = self.run_cli('checkpoint', '--task', self.task, '--owner', self.owner, '--revision', '2', '--patch-file', str(self.patch_path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('append-only', result.stderr)

    def test_caller_part_event_id_is_not_deleted_by_grouped_event(self):
        prior = self.memory_apply(1, [{'action': 'journal', 'event_id': 'turn#part-1', 'category': 'state', 'text': 'prior'}])
        actions = [{'action': 'hot-update', 'event_id': 'turn', 'focus': 'later focus'},
                   {'action': 'journal', 'event_id': 'turn', 'category': 'state', 'text': 'later'}]
        applied = self.memory_apply(2, actions)
        saved = state.load(self.path)
        self.assertEqual(sum(event['event_id'] == 'turn#part-1' for event in saved['memory']['audit']), 1)
        replay_path = self.root / 'actions.json'
        replay_path.write_text(json.dumps({'actions': [{'action': 'journal', 'event_id': 'turn#part-1', 'category': 'state', 'text': 'prior'}]}))
        replay = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', str(applied['state']['revision']), '--actions-file', str(replay_path))
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(len([item for item in json.loads(replay.stdout)['result']['state']['memory']['journal'] if item['text'] == 'prior']), 1)

    def test_part_id_noop_then_journal_keeps_replay_key(self):
        seed = self.memory_apply(1, [{'action': 'cold-add', 'event_id': 'seed-part', 'category': 'state', 'text': 'seed'}])
        cold_id = seed['state']['memory']['cold'][0]['id']
        actions = [{'action': 'cold-update', 'event_id': 'batch#part-1', 'id': cold_id, 'disposition': 'current'},
                   {'action': 'journal', 'event_id': 'batch#part-1', 'category': 'state', 'text': 'hashed'}]
        applied = self.memory_apply(2, actions)
        saved = state.load(self.path)
        self.assertEqual(sum(event['event_id'] == 'batch#part-1' for event in saved['memory']['audit']), 1)
        replay_path = self.root / 'actions.json'; replay_path.write_text(json.dumps({'actions': actions}))
        replay = self.run_cli('memory-apply', '--task', self.task, '--owner', self.owner, '--revision', str(applied['state']['revision']), '--actions-file', str(replay_path))
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(len([item for item in json.loads(replay.stdout)['result']['state']['memory']['journal'] if item['text'] == 'hashed']), 1)

    def test_workspace_promotion_is_canonical_idempotent_and_demotable(self):
        project = self.root / 'project'
        project.mkdir()
        created = self.cli('create', '--title', 'workspace', '--objective', 'workspace', '--project', str(project), '--owner', 'workspace-owner')
        task, owner = created['state']['id'], created['state']['owner']
        link = self.root / 'project-link'
        link.symlink_to(project, target_is_directory=True)
        actions = self.root / 'workspace-actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'promote#1',
            'scope': 'workspace', 'category': 'discoveries', 'text': 'shared claim',
            'provenance': [{'kind': 'test', 'ref': 'workspace-promotion'}]}]}))
        first = self.run_cli('memory-apply', '--task', task, '--owner', owner,
                             '--revision', '1', '--actions-file', str(actions))
        self.assertEqual(first.returncode, 0, first.stderr)
        saved = json.loads(first.stdout)['result']['state']
        self.assertEqual(saved['revision'], 3)  # v1 import + intent, then delivery
        replay = self.run_cli('memory-apply', '--task', task, '--owner', owner,
                              '--revision', '3', '--actions-file', str(actions))
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(json.loads(replay.stdout)['result']['state']['revision'], 3)
        workspace = state.load_workspace(state.workspace_path(self.root, str(project) + '/'))
        item = workspace['items'][0]
        self.assertEqual(state.workspace_current(self.root, str(link) + '/')[0]['id'], item['id'])
        demoted = self.run_cli('memory-demote', '--task', task, '--owner', owner,
            '--task-revision', '3', '--id', item['id'], '--workspace-revision', str(workspace['revision']),
            '--reason', 'promotion was too broad')
        self.assertEqual(demoted.returncode, 0, demoted.stderr)
        self.assertEqual(state.workspace_current(self.root, project), [])
        historical = state.load_workspace(state.workspace_path(self.root, project))
        self.assertEqual(historical['items'][0]['status'], 'withdrawn')
        self.assertTrue(any(event['action'] == 'demote' for event in historical['audit']))

    def test_workspace_isolation_and_stale_demotion_are_fenced(self):
        project_a = self.root / 'a'; project_b = self.root / 'b'
        project_a.mkdir(); project_b.mkdir()
        created_a = self.cli('create', '--title', 'a', '--objective', 'a', '--project', str(project_a), '--owner', 'owner-a')
        task_a, owner_a = created_a['state']['id'], created_a['state']['owner']
        actions = self.root / 'workspace-actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'isolate',
            'scope': 'workspace', 'category': 'state', 'text': 'only project a',
            'provenance': [{'kind': 'test', 'ref': 'isolation'}]}]}))
        created = self.cli('create', '--title', 'other', '--objective', 'other', '--project', str(project_b), '--owner', 'other')
        result = self.run_cli('memory-apply', '--task', task_a, '--owner', owner_a,
                              '--revision', '1', '--actions-file', str(actions))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state.workspace_current(self.root, project_b), [])
        workspace = state.load_workspace(state.workspace_path(self.root, project_a), project_a)
        item = workspace['items'][0]
        stale = self.run_cli('memory-demote', '--task', task_a, '--owner', owner_a,
            '--task-revision', '3', '--id', item['id'], '--workspace-revision', '1', '--reason', 'stale')
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn('stale workspace revision', stale.stderr)
        self.assertEqual(state.workspace_current(self.root, project_a)[0]['id'], item['id'])

    def test_two_process_promotions_preserve_both_workspace_claims(self):
        project = self.root / 'concurrent'; project.mkdir()
        tasks = []
        for number in (1, 2):
            created = self.cli('create', '--title', f'concurrent-{number}', '--objective', 'share',
                               '--project', str(project), '--owner', f'owner-{number}')
            action_path = self.root / f'concurrent-{number}.json'
            action_path.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': f'concurrent-{number}',
                'scope': 'workspace', 'category': 'discoveries', 'text': f'claim-{number}',
                'provenance': [{'kind': 'test', 'ref': f'process-{number}'}]}]}))
            tasks.append((created['state']['id'], created['state']['owner'], action_path))
        def promote(args):
            task, owner, path = args
            return self.run_cli('memory-apply', '--task', task, '--owner', owner,
                                '--revision', '1', '--actions-file', str(path))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(promote, tasks))
        for (task, owner, path), result in zip(tasks, results):
            if result.returncode != 0:
                retry = self.run_cli('memory-apply', '--task', task, '--owner', owner,
                                     '--revision', '2', '--actions-file', str(path))
                self.assertEqual(retry.returncode, 0, retry.stderr)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project)
        self.assertEqual({item['text'] for item in workspace['items']}, {'claim-1', 'claim-2'})

    def test_review_demote_allows_same_project_live_owner_and_v1_upgrade(self):
        project = self.root / 'shared'; project.mkdir()
        owner_task = self.cli('create', '--title', 'owner', '--objective', 'owner', '--project', str(project), '--owner', 'owner')
        source_task = self.cli('create', '--title', 'source', '--objective', 'source', '--project', str(project), '--owner', 'source')
        actions = self.root / 'review-actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'review-promote', 'scope': 'workspace', 'category': 'state', 'text': 'claim', 'provenance': [{'kind': 'test', 'ref': 'review'}]}]}))
        promoted = self.run_cli('memory-apply', '--task', source_task['state']['id'], '--owner', 'source', '--revision', '1', '--actions-file', str(actions))
        self.assertEqual(promoted.returncode, 0, promoted.stderr)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project)
        item = workspace['items'][0]
        owner_path = self.root / 'tasks' / owner_task['state']['id']
        source_record = state.load(owner_path)
        source_record['schema_version'] = 1
        source_record.pop('memory', None)
        (owner_path / 'state.json').write_text(json.dumps(source_record))
        demoted = self.run_cli('memory-demote', '--task', owner_task['state']['id'], '--owner', 'owner', '--task-revision', '1', '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'neighbor correction')
        self.assertEqual(demoted.returncode, 0, demoted.stderr)
        self.assertEqual(state.load_workspace(state.workspace_path(self.root, project), project)['items'][0]['status'], 'withdrawn')
        self.assertEqual(state.load(self.root / 'tasks' / owner_task['state']['id'])['schema_version'], 2)

    def test_review_demote_retries_after_workspace_commit_and_task_revision_change(self):
        project = self.root / 'retry'; project.mkdir()
        source = self.cli('create', '--title', 'source', '--objective', 'source', '--project', str(project), '--owner', 'source')
        caller = self.cli('create', '--title', 'caller', '--objective', 'caller', '--project', str(project), '--owner', 'caller')
        actions = self.root / 'retry-actions.json'
        actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'retry-promote', 'scope': 'workspace', 'category': 'state', 'text': 'claim', 'provenance': [{'kind': 'test', 'ref': 'retry'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', '1', '--actions-file', str(actions)).returncode, 0)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project); item = workspace['items'][0]
        caller_path = self.root / 'tasks' / caller['state']['id']
        def fail_save(path, record):
            raise OSError('injected delivery failure')
        with patch.object(state, 'save', side_effect=fail_save):
            with self.assertRaises(OSError):
                state.demote_memory(self.root, argparse.Namespace(task=caller['state']['id'], owner='caller', task_revision=1, item_id=item['id'], workspace_revision=workspace['revision'], reason='retry'))
        current = state.load(caller_path)
        current['details']['next_action'] = 'changed between locks'; current['revision'] += 1; state.save(caller_path, current)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project)
        retried = self.run_cli('memory-demote', '--task', caller['state']['id'], '--owner', 'caller', '--task-revision', str(current['revision']), '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'retry')
        self.assertEqual(retried.returncode, 0, retried.stderr)
        final = state.load(caller_path)
        self.assertEqual(sum(e['action'] == 'demote-delivered' for e in final['memory']['audit']), 1)

    def test_review_workspace_malformed_fields_and_symlink_directory_are_state_errors(self):
        project = self.root / 'malformed'; project.mkdir()
        workspace_dir = state.workspace_path(self.root, project); workspace_dir.mkdir(parents=True)
        record = state._workspace_default(project)
        for field, value in [('category', ['state']), ('status', ['current']), ('origin', ['bad']), ('supersedes', 'bad')]:
            item = {'id': 'x', 'category': 'state', 'text': 'x', 'status': 'current', 'scope': 'workspace', 'project': str(project.resolve()), 'task_id': 't', 'origin': {'task_id': 't', 'item_id': 'i'}, 'created_at': state.now(), 'updated_at': state.now(), 'provenance': [{'kind': 'test', 'ref': 'x'}], 'supersedes': [], 'superseded_by': None}
            item[field] = value; bad = dict(record, items=[item])
            with self.assertRaises(state.StateError): state.validate_workspace(bad)
        link = self.root / 'target'; link.mkdir()
        workspace_dir.rmdir(); workspace_dir.symlink_to(link, target_is_directory=True)
        actions = self.root / 'symlink-actions.json'; actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'symlink', 'scope': 'workspace', 'category': 'state', 'text': 'x', 'provenance': [{'kind': 'test', 'ref': 'x'}]}]}))
        task = self.cli('create', '--title', 'symlink', '--objective', 'symlink', '--project', str(project), '--owner', 'symlink')
        result = self.run_cli('memory-apply', '--task', task['state']['id'], '--owner', 'symlink', '--revision', '1', '--actions-file', str(actions))
        self.assertNotEqual(result.returncode, 0); self.assertIn('symlink', result.stderr)

    def test_review_promotion_failure_after_intent_then_retry_is_idempotent(self):
        project = self.root / 'intent-failure'; project.mkdir()
        created = self.cli('create', '--title', 'intent', '--objective', 'intent', '--project', str(project), '--owner', 'intent')
        actions = self.root / 'intent-failure.json'
        actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'intent-failure', 'scope': 'workspace', 'category': 'state', 'text': 'claim', 'provenance': [{'kind': 'test', 'ref': 'intent-failure'}]}]}))
        proposal = json.loads(actions.read_text())
        with patch.object(state, '_promote_workspace', side_effect=OSError('after intent')):
            with self.assertRaises(OSError):
                state.promote_memory(self.root, argparse.Namespace(task=created['state']['id'], owner='intent', revision=1), proposal)
        self.assertEqual(state.load(self.root / 'tasks' / created['state']['id'])['revision'], 2)
        retried = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'intent', '--revision', '2', '--actions-file', str(actions))
        self.assertEqual(retried.returncode, 0, retried.stderr)
        task = state.load(self.root / 'tasks' / created['state']['id'])
        self.assertEqual(sum(e['action'] == 'promotion-delivered' for e in task['memory']['audit']), 1)

    def test_review_workspace_lock_busy_after_intent_is_retryable_without_duplicates(self):
        project = self.root / 'busy'; project.mkdir()
        created = self.cli('create', '--title', 'busy', '--objective', 'busy', '--project', str(project), '--owner', 'busy')
        actions = self.root / 'busy.json'
        actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'busy', 'scope': 'workspace', 'category': 'state', 'text': 'busy claim', 'provenance': [{'kind': 'test', 'ref': 'busy'}]}]}))
        workspace_dir = state.workspace_path(self.root, project); workspace_dir.mkdir(parents=True)
        with state.locked(workspace_dir / '.write.lock'):
            blocked = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'busy', '--revision', '1', '--actions-file', str(actions))
        self.assertNotEqual(blocked.returncode, 0); self.assertIn('record is busy', blocked.stderr)
        retried = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'busy', '--revision', '2', '--actions-file', str(actions))
        self.assertEqual(retried.returncode, 0, retried.stderr)
        workspace = state.load_workspace(workspace_dir, project)
        self.assertEqual(len(workspace['items']), 1)

    def test_review_workspace_audit_and_origin_collisions_are_safe_errors(self):
        project = self.root / 'collision'; project.mkdir()
        record = state._workspace_default(project)
        for bad in ({'id': [], 'at': state.now(), 'event_id': 'x'}, {'id': 'x', 'at': [], 'event_id': 'x'}, {'id': 'x', 'at': state.now(), 'event_id': []}):
            with self.assertRaises(state.StateError):
                state.validate_workspace(dict(record, audit=[bad]))
        created = self.cli('create', '--title', 'collision', '--objective', 'collision', '--project', str(project), '--owner', 'collision')
        actions = self.root / 'collision.json'; actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'collision', 'scope': 'workspace', 'category': 'state', 'text': 'one', 'provenance': [{'kind': 'test', 'ref': 'collision'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'collision', '--revision', '1', '--actions-file', str(actions)).returncode, 0)
        task = state.load(self.root / 'tasks' / created['state']['id'])
        workspace_dir = state.workspace_path(self.root, project)
        workspace = state.load_workspace(workspace_dir, project); workspace['items'][0]['text'] = 'tampered'; state.save_workspace(workspace_dir, workspace)
        retry = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'collision', '--revision', str(task['revision']), '--actions-file', str(actions))
        self.assertNotEqual(retry.returncode, 0); self.assertIn('different claim', retry.stderr)

    def test_review_nonexistent_project_path_has_stable_workspace_identity(self):
        missing = self.root / 'does-not-exist' / '..' / 'does-not-exist' / 'project'
        first = state.workspace_path(self.root, str(missing) + '/')
        second = state.workspace_path(self.root, str(missing.resolve()))
        self.assertEqual(first, second)

    def test_review_delivered_promotion_reconciles_missing_workspace_file_or_origin(self):
        for mode in ('file', 'origin'):
            with self.subTest(mode=mode):
                project = self.root / ('reconcile-' + mode); project.mkdir()
                created = self.cli('create', '--title', mode, '--objective', mode, '--project', str(project), '--owner', mode)
                actions = self.root / (mode + '-reconcile.json')
                actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'reconcile-' + mode, 'scope': 'workspace', 'category': 'state', 'text': mode, 'provenance': [{'kind': 'test', 'ref': mode}]}]}))
                first = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', mode, '--revision', '1', '--actions-file', str(actions))
                self.assertEqual(first.returncode, 0, first.stderr)
                workspace_dir = state.workspace_path(self.root, project)
                workspace = state.load_workspace(workspace_dir, project)
                if mode == 'file':
                    (workspace_dir / 'memory.json').unlink()
                else:
                    workspace['items'].clear(); state.save_workspace(workspace_dir, workspace)
                current = state.load(self.root / 'tasks' / created['state']['id'])
                repaired = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', mode, '--revision', str(current['revision']), '--actions-file', str(actions))
                self.assertNotEqual(repaired.returncode, 0, repaired.stderr)
                self.assertIn('workspace memory lost', repaired.stderr)
                self.assertFalse((workspace_dir / 'memory.json').exists()) if mode == 'file' else self.assertEqual(state.load_workspace(workspace_dir, project)['items'], [])
                # A stale replay must refuse rather than claim delivery.
                stale = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', mode, '--revision', '1', '--actions-file', str(actions))
                self.assertNotEqual(stale.returncode, 0)
                self.assertIn('stale revision', stale.stderr)

    def test_review_rejected_v1_demotion_does_not_upgrade_and_corrected_retry_works(self):
        project = self.root / 'v1-demote'; project.mkdir(); other = self.root / 'v1-other'; other.mkdir()
        source = self.cli('create', '--title', 'source', '--objective', 'source', '--project', str(project), '--owner', 'source')
        caller = self.cli('create', '--title', 'caller', '--objective', 'caller', '--project', str(project), '--owner', 'caller')
        outsider = self.cli('create', '--title', 'outsider', '--objective', 'outsider', '--project', str(other), '--owner', 'outsider')
        actions = self.root / 'v1-demote-actions.json'; actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'v1-item', 'scope': 'workspace', 'category': 'state', 'text': 'v1 item', 'provenance': [{'kind': 'test', 'ref': 'v1'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', '1', '--actions-file', str(actions)).returncode, 0)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project); item = workspace['items'][0]
        for task, owner, item_id in ((outsider, 'outsider', item['id']), (caller, 'caller', 'missing-id')):
            path = self.root / 'tasks' / task['state']['id']; record = state.load(path); record['schema_version'] = 1; record.pop('memory', None); state.save(path, record)
            result = self.run_cli('memory-demote', '--task', task['state']['id'], '--owner', owner, '--task-revision', '1', '--id', item_id, '--workspace-revision', str(workspace['revision']), '--reason', 'rejected')
            self.assertNotEqual(result.returncode, 0)
            unchanged = state.load(path)
            self.assertEqual(unchanged['schema_version'], 1); self.assertEqual(unchanged['revision'], 1)
        corrected_path = self.root / 'tasks' / caller['state']['id']; corrected = state.load(corrected_path)
        corrected_result = self.run_cli('memory-demote', '--task', caller['state']['id'], '--owner', 'caller', '--task-revision', '1', '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'corrected')
        self.assertEqual(corrected_result.returncode, 0, corrected_result.stderr)
        self.assertEqual(state.load(corrected_path)['schema_version'], 2)

    def test_review_lost_withdrawn_workspace_is_rejected_at_current_and_stale_revision(self):
        project = self.root / 'rebuild-withdrawn'; project.mkdir()
        created = self.cli('create', '--title', 'rebuild', '--objective', 'rebuild', '--project', str(project), '--owner', 'rebuild')
        actions = self.root / 'rebuild-withdrawn.json'; actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'will-withdraw', 'scope': 'workspace', 'category': 'state', 'text': 'will withdraw', 'provenance': [{'kind': 'test', 'ref': 'withdraw'}]}]}))
        first = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'rebuild', '--revision', '1', '--actions-file', str(actions)); self.assertEqual(first.returncode, 0, first.stderr)
        workspace_dir = state.workspace_path(self.root, project); workspace = state.load_workspace(workspace_dir, project); item = workspace['items'][0]; original_id = item['id']
        demoted = self.run_cli('memory-demote', '--task', created['state']['id'], '--owner', 'rebuild', '--task-revision', '3', '--id', original_id, '--workspace-revision', str(workspace['revision']), '--reason', 'withdraw')
        self.assertEqual(demoted.returncode, 0, demoted.stderr)
        current = state.load(self.root / 'tasks' / created['state']['id']); (workspace_dir / 'memory.json').unlink()
        replay = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'rebuild', '--revision', str(current['revision']), '--actions-file', str(actions))
        self.assertNotEqual(replay.returncode, 0); self.assertIn('workspace memory lost', replay.stderr)
        self.assertFalse((workspace_dir / 'memory.json').exists())
        stale = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'rebuild', '--revision', '1', '--actions-file', str(actions))
        self.assertNotEqual(stale.returncode, 0); self.assertIn('stale revision', stale.stderr)
        self.assertFalse((workspace_dir / 'memory.json').exists())

    def test_review_lost_superseded_workspace_is_rejected_at_current_and_stale_revision(self):
        project = self.root / 'rebuild-superseded'; project.mkdir()
        created = self.cli('create', '--title', 'rebuild', '--objective', 'rebuild', '--project', str(project), '--owner', 'rebuild')
        first_path = self.root / 'rebuild-old.json'; first_path.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'old-claim', 'scope': 'workspace', 'category': 'discoveries', 'text': 'old claim', 'provenance': [{'kind': 'test', 'ref': 'old'}]}]}))
        first = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'rebuild', '--revision', '1', '--actions-file', str(first_path)); self.assertEqual(first.returncode, 0, first.stderr)
        workspace_dir = state.workspace_path(self.root, project); workspace = state.load_workspace(workspace_dir, project); old_id = workspace['items'][0]['id']
        second_path = self.root / 'rebuild-new.json'; second_path.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'new-claim', 'scope': 'workspace', 'category': 'discoveries', 'text': 'new claim', 'provenance': [{'kind': 'test', 'ref': 'new'}], 'supersedes': [old_id]}]}))
        second = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'rebuild', '--revision', '3', '--actions-file', str(second_path)); self.assertEqual(second.returncode, 0, second.stderr)
        workspace = state.load_workspace(workspace_dir, project); successor = next(item for item in workspace['items'] if item['id'] != old_id); original_revision = json.loads(second.stdout)['result']['state']['revision']; (workspace_dir / 'memory.json').unlink()
        replay = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'rebuild', '--revision', str(original_revision), '--actions-file', str(first_path)); self.assertNotEqual(replay.returncode, 0); self.assertIn('workspace memory lost', replay.stderr)
        self.assertFalse((workspace_dir / 'memory.json').exists())
        stale = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'rebuild', '--revision', '1', '--actions-file', str(first_path)); self.assertNotEqual(stale.returncode, 0); self.assertIn('stale revision', stale.stderr)
        self.assertFalse((workspace_dir / 'memory.json').exists())

    def test_review_rebuild_rejects_terminal_evidence_from_another_task(self):
        project = self.root / 'rebuild-other-demoter'; project.mkdir()
        source = self.cli('create', '--title', 'source', '--objective', 'source', '--project', str(project), '--owner', 'source'); neighbor = self.cli('create', '--title', 'neighbor', '--objective', 'neighbor', '--project', str(project), '--owner', 'neighbor')
        actions = self.root / 'rebuild-other.json'; actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'other-demoter', 'scope': 'workspace', 'category': 'state', 'text': 'other demoter', 'provenance': [{'kind': 'test', 'ref': 'other'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', '1', '--actions-file', str(actions)).returncode, 0)
        workspace_dir = state.workspace_path(self.root, project); workspace = state.load_workspace(workspace_dir, project); item = workspace['items'][0]
        demoted = self.run_cli('memory-demote', '--task', neighbor['state']['id'], '--owner', 'neighbor', '--task-revision', '1', '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'neighbor demotion'); self.assertEqual(demoted.returncode, 0, demoted.stderr)
        malformed = self.root / 'tasks' / 'malformed-neighbor'; malformed.mkdir(); (malformed / 'state.json').write_bytes(b'{not-json')
        source_state = state.load(self.root / 'tasks' / source['state']['id']); (workspace_dir / 'memory.json').unlink()
        replay = self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', str(source_state['revision']), '--actions-file', str(actions))
        self.assertNotEqual(replay.returncode, 0); self.assertIn('workspace memory lost', replay.stderr)

    def test_review_lost_origin_with_successor_from_another_task_is_not_rebuilt(self):
        project = self.root / 'cross-successor'; project.mkdir()
        source = self.cli('create', '--title', 'source', '--objective', 'source', '--project', str(project), '--owner', 'source')
        successor = self.cli('create', '--title', 'successor', '--objective', 'successor', '--project', str(project), '--owner', 'successor')
        old_actions = self.root / 'cross-old.json'; old_actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'cross-old', 'scope': 'workspace', 'category': 'discoveries', 'text': 'cross old', 'provenance': [{'kind': 'test', 'ref': 'cross-old'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', '1', '--actions-file', str(old_actions)).returncode, 0)
        workspace_dir = state.workspace_path(self.root, project); workspace = state.load_workspace(workspace_dir, project); old_id = workspace['items'][0]['id']
        new_actions = self.root / 'cross-new.json'; new_actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'cross-new', 'scope': 'workspace', 'category': 'discoveries', 'text': 'cross new', 'provenance': [{'kind': 'test', 'ref': 'cross-new'}], 'supersedes': [old_id]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', successor['state']['id'], '--owner', 'successor', '--revision', '1', '--actions-file', str(new_actions)).returncode, 0)
        source_state = state.load(self.root / 'tasks' / source['state']['id']); (workspace_dir / 'memory.json').unlink()
        replay = self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', str(source_state['revision']), '--actions-file', str(old_actions))
        self.assertNotEqual(replay.returncode, 0); self.assertIn('workspace memory lost', replay.stderr); self.assertFalse((workspace_dir / 'memory.json').exists())

    def test_review_mixed_delivered_replay_does_not_bump_or_rebuild(self):
        project = self.root / 'mixed-loss'; project.mkdir()
        created = self.cli('create', '--title', 'mixed-loss', '--objective', 'mixed-loss', '--project', str(project), '--owner', 'mixed-loss')
        actions = self.root / 'mixed-loss.json'; actions.write_text(json.dumps({'actions': [{'action': 'hot-update', 'event_id': 'mixed-hot', 'focus': 'focus'}, {'action': 'cold-add', 'event_id': 'mixed-cold', 'scope': 'workspace', 'category': 'state', 'text': 'claim', 'provenance': [{'kind': 'test', 'ref': 'mixed'}]}]}))
        first = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'mixed-loss', '--revision', '1', '--actions-file', str(actions)); self.assertEqual(first.returncode, 0, first.stderr)
        current = state.load(self.root / 'tasks' / created['state']['id']); workspace_dir = state.workspace_path(self.root, project); workspace = state.load_workspace(workspace_dir, project); item = workspace['items'][0]
        replay = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'mixed-loss', '--revision', str(current['revision']), '--actions-file', str(actions)); self.assertEqual(replay.returncode, 0, replay.stderr); self.assertEqual(json.loads(replay.stdout)['result']['state']['revision'], current['revision'])
        demote = self.run_cli('memory-demote', '--task', created['state']['id'], '--owner', 'mixed-loss', '--task-revision', str(current['revision']), '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'mixed loss'); self.assertEqual(demote.returncode, 0, demote.stderr)
        after_demote = state.load(self.root / 'tasks' / created['state']['id']); (workspace_dir / 'memory.json').unlink()
        lost = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'mixed-loss', '--revision', str(after_demote['revision']), '--actions-file', str(actions)); self.assertNotEqual(lost.returncode, 0); self.assertIn('workspace memory lost', lost.stderr); self.assertFalse((workspace_dir / 'memory.json').exists())

    def test_review_v1_demote_stale_or_busy_does_not_upgrade(self):
        project = self.root / 'v1-live'; project.mkdir()
        source = self.cli('create', '--title', 'source', '--objective', 'source', '--project', str(project), '--owner', 'source'); caller = self.cli('create', '--title', 'caller', '--objective', 'caller', '--project', str(project), '--owner', 'caller')
        actions = self.root / 'v1-live.json'; actions.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'v1-live', 'scope': 'workspace', 'category': 'state', 'text': 'claim', 'provenance': [{'kind': 'test', 'ref': 'v1-live'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', '1', '--actions-file', str(actions)).returncode, 0)
        workspace_dir = state.workspace_path(self.root, project); workspace = state.load_workspace(workspace_dir, project); item = workspace['items'][0]
        caller_path = self.root / 'tasks' / caller['state']['id']; record = state.load(caller_path); state.save(caller_path, record)
        stale = self.run_cli('memory-demote', '--task', caller['state']['id'], '--owner', 'caller', '--task-revision', '1', '--id', item['id'], '--workspace-revision', '1', '--reason', 'stale')
        self.assertNotEqual(stale.returncode, 0); self.assertIn('stale workspace revision', stale.stderr); unchanged = state.load(caller_path); self.assertEqual(unchanged['schema_version'], 1); self.assertEqual(unchanged['revision'], 1)
        with state.locked(workspace_dir / '.write.lock'):
            busy = self.run_cli('memory-demote', '--task', caller['state']['id'], '--owner', 'caller', '--task-revision', '1', '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'busy')
        self.assertNotEqual(busy.returncode, 0); self.assertIn('record is busy', busy.stderr); unchanged = state.load(caller_path); self.assertEqual(unchanged['schema_version'], 1); self.assertEqual(unchanged['revision'], 1); self.assertEqual(state.workspace_current(self.root, project)[0]['status'], 'current')

    def test_review_workspace_supersede_preflight_rejects_missing_and_oversized_targets(self):
        project = self.root / 'preflight'; project.mkdir(); created = self.cli('create', '--title', 'preflight', '--objective', 'preflight', '--project', str(project), '--owner', 'preflight')
        action_path = self.root / 'preflight.json'; missing = {'actions': [{'action': 'cold-add', 'event_id': 'bad-target', 'scope': 'workspace', 'category': 'state', 'text': 'bad', 'provenance': [{'kind': 'test', 'ref': 'bad'}], 'supersedes': ['missing-id']}]}; action_path.write_text(json.dumps(missing))
        result = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'preflight', '--revision', '1', '--actions-file', str(action_path)); self.assertNotEqual(result.returncode, 0); self.assertIn('supersession target', result.stderr); self.assertEqual(state.load(self.root / 'tasks' / created['state']['id'])['revision'], 1); self.assertFalse((self.root / 'tasks' / created['state']['id'] / 'state.json').read_text().find('promotion-intent') >= 0)
        oversized = {'actions': [{'action': 'cold-add', 'event_id': 'too-many', 'scope': 'workspace', 'category': 'state', 'text': 'bad', 'provenance': [{'kind': 'test', 'ref': 'bad'}], 'supersedes': [str(i) for i in range(9)]}]}; action_path.write_text(json.dumps(oversized)); result = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'preflight', '--revision', '1', '--actions-file', str(action_path)); self.assertNotEqual(result.returncode, 0); self.assertIn('at most 8', result.stderr); self.assertEqual(state.load(self.root / 'tasks' / created['state']['id'])['revision'], 1)

    def test_review_delivered_promotion_stale_replay_and_mixed_grouped_batch(self):
        project = self.root / 'mixed'; project.mkdir()
        created = self.cli('create', '--title', 'mixed', '--objective', 'mixed', '--project', str(project), '--owner', 'mixed')
        actions = self.root / 'mixed.json'
        actions.write_text(json.dumps({'actions': [
            {'action': 'hot-update', 'event_id': 'grouped#event', 'focus': 'mixed focus'},
            {'action': 'cold-add', 'event_id': 'grouped#event', 'scope': 'workspace', 'category': 'state', 'text': 'mixed claim', 'provenance': [{'kind': 'test', 'ref': 'mixed'}]}]}))
        first = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'mixed', '--revision', '1', '--actions-file', str(actions))
        self.assertEqual(first.returncode, 0, first.stderr)
        replay = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'mixed', '--revision', '1', '--actions-file', str(actions))
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(json.loads(replay.stdout)['result']['state']['revision'], 3)

    def test_review_workspace_supersede_withdrawn_and_utf8_limits(self):
        project = self.root / 'supersede'; project.mkdir()
        created = self.cli('create', '--title', 'supersede', '--objective', 'supersede', '--project', str(project), '--owner', 'supersede')
        def apply(action, revision):
            path = self.root / 'supersede-action.json'; path.write_text(json.dumps({'actions': [action]}))
            result = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'supersede', '--revision', str(revision), '--actions-file', str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)['result']['state']
        first = apply({'action': 'cold-add', 'event_id': 'first-workspace', 'scope': 'workspace', 'category': 'discoveries', 'text': 'first', 'provenance': [{'kind': 'test', 'ref': 'first'}]}, 1)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project); old = workspace['items'][0]
        self.assertEqual(old['status'], 'current')
        withdrawn = self.run_cli('memory-demote', '--task', created['state']['id'], '--owner', 'supersede', '--task-revision', str(first['revision']), '--id', old['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'withdraw')
        self.assertEqual(withdrawn.returncode, 0, withdrawn.stderr)
        current = json.loads(withdrawn.stdout)['result']['state']
        new = apply({'action': 'cold-add', 'event_id': 'second-workspace', 'scope': 'workspace', 'category': 'discoveries', 'text': 'second', 'provenance': [{'kind': 'test', 'ref': 'second'}], 'supersedes': [old['id']]}, current['revision'])
        workspace = state.load_workspace(state.workspace_path(self.root, project), project)
        self.assertEqual({item['status'] for item in workspace['items']}, {'withdrawn', 'current'})
        replacement_target = next(item for item in workspace['items'] if item['status'] == 'current')
        third = apply({'action': 'supersede', 'event_id': 'third-workspace', 'old_id': replacement_target['id'],
                        'replacement': {'category': 'discoveries', 'scope': 'workspace', 'text': 'third',
                                        'provenance': [{'kind': 'test', 'ref': 'third'}]}}, new['revision'])
        workspace = state.load_workspace(state.workspace_path(self.root, project), project)
        self.assertEqual(sum(item['status'] == 'superseded' for item in workspace['items']), 1)
        oversized = self.root / 'oversized.json'; oversized.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'oversized', 'scope': 'workspace', 'category': 'state', 'text': '🙂' * 400, 'provenance': [{'kind': 'test', 'ref': 'overflow'}]}]}))
        rejected = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'supersede', '--revision', str(third['revision']), '--actions-file', str(oversized))
        self.assertNotEqual(rejected.returncode, 0); self.assertIn('consolidation required', rejected.stderr)

    def test_review_authority_rejects_other_project_and_allows_archived_origin(self):
        project = self.root / 'authority'; project.mkdir(); other = self.root / 'other-authority'; other.mkdir()
        source = self.cli('create', '--title', 'source', '--objective', 'source', '--project', str(project), '--owner', 'source')
        neighbor = self.cli('create', '--title', 'neighbor', '--objective', 'neighbor', '--project', str(project), '--owner', 'neighbor')
        live_neighbor = self.cli('create', '--title', 'live-neighbor', '--objective', 'live-neighbor', '--project', str(project), '--owner', 'live-neighbor')
        outsider = self.cli('create', '--title', 'outsider', '--objective', 'outsider', '--project', str(other), '--owner', 'outsider')
        action = self.root / 'authority.json'; action.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'authority-claim', 'scope': 'workspace', 'category': 'state', 'text': 'authority claim', 'provenance': [{'kind': 'test', 'ref': 'authority'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', source['state']['id'], '--owner', 'source', '--revision', '1', '--actions-file', str(action)).returncode, 0)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project); item = workspace['items'][0]
        denied = self.run_cli('memory-demote', '--task', outsider['state']['id'], '--owner', 'outsider', '--task-revision', '1', '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'wrong project')
        self.assertNotEqual(denied.returncode, 0)
        release = self.run_cli('release', '--task', neighbor['state']['id'], '--owner', 'neighbor', '--revision', '1')
        self.assertEqual(release.returncode, 0)
        denied = self.run_cli('memory-demote', '--task', neighbor['state']['id'], '--owner', 'neighbor', '--task-revision', '2', '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'released')
        self.assertNotEqual(denied.returncode, 0)
        source_record = state.load(self.root / 'tasks' / source['state']['id']); source_record['status'] = 'completed'; source_record['updated_at'] = state.now(); state.save(self.root / 'tasks' / source['state']['id'], source_record)
        archived = state.load(self.root / 'tasks' / source['state']['id']); archived['archived_at'] = state.now(); archived['owner'] = None; state.save(self.root / 'tasks' / source['state']['id'], archived)
        workspace = state.load_workspace(state.workspace_path(self.root, project), project)
        demoted = self.run_cli('memory-demote', '--task', live_neighbor['state']['id'], '--owner', 'live-neighbor', '--task-revision', '1', '--id', item['id'], '--workspace-revision', str(workspace['revision']), '--reason', 'archive cleanup')
        self.assertEqual(demoted.returncode, 0, demoted.stderr)


    def test_review_supersede_retry_after_workspace_commit_accepts_own_superseded_target(self):
        project = self.root / 'supersede-retry'; project.mkdir()
        created = self.cli('create', '--title', 'supersede-retry', '--objective', 'supersede-retry', '--project', str(project), '--owner', 'supersede-retry')
        seed = self.root / 'supersede-seed.json'; seed.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'seed', 'scope': 'workspace', 'category': 'discoveries', 'text': 'seed', 'provenance': [{'kind': 'test', 'ref': 'seed'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'supersede-retry', '--revision', '1', '--actions-file', str(seed)).returncode, 0)
        workspace_dir = state.workspace_path(self.root, project); old_id = state.load_workspace(workspace_dir, project)['items'][0]['id']
        replacement = self.root / 'supersede-replacement.json'; replacement.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'replacement', 'scope': 'workspace', 'category': 'discoveries', 'text': 'replacement', 'provenance': [{'kind': 'test', 'ref': 'replacement'}], 'supersedes': [old_id]}]}))
        with patch.object(state, '_record_promotion_delivery', side_effect=OSError('delivery failure')):
            with self.assertRaises(OSError):
                state.promote_memory(self.root, argparse.Namespace(task=created['state']['id'], owner='supersede-retry', revision=3), json.loads(replacement.read_text()))
        after_failure = state.load(self.root / 'tasks' / created['state']['id']); retried = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'supersede-retry', '--revision', str(after_failure['revision']), '--actions-file', str(replacement))
        self.assertEqual(retried.returncode, 0, retried.stderr)
        final_workspace = state.load_workspace(workspace_dir, project); self.assertEqual(len(final_workspace['items']), 2)
        old = next(item for item in final_workspace['items'] if item['id'] == old_id); successor = next(item for item in final_workspace['items'] if item['id'] != old_id)
        self.assertEqual(old['status'], 'superseded'); self.assertEqual(old['superseded_by'], successor['id']); self.assertEqual(successor['supersedes'], [old_id])

    def test_review_supersede_preflight_rejects_target_superseded_by_other_origin(self):
        project = self.root / 'foreign-supersede'; project.mkdir(); created = self.cli('create', '--title', 'foreign', '--objective', 'foreign', '--project', str(project), '--owner', 'foreign')
        seed = self.root / 'foreign-seed.json'; seed.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'foreign-seed', 'scope': 'workspace', 'category': 'discoveries', 'text': 'seed', 'provenance': [{'kind': 'test', 'ref': 'seed'}]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'foreign', '--revision', '1', '--actions-file', str(seed)).returncode, 0)
        workspace_dir = state.workspace_path(self.root, project); old_id = state.load_workspace(workspace_dir, project)['items'][0]['id']
        other = self.root / 'foreign-other.json'; other.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'foreign-other', 'scope': 'workspace', 'category': 'discoveries', 'text': 'other', 'provenance': [{'kind': 'test', 'ref': 'other'}], 'supersedes': [old_id]}]}))
        self.assertEqual(self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'foreign', '--revision', '3', '--actions-file', str(other)).returncode, 0)
        bad = self.root / 'foreign-bad.json'; bad.write_text(json.dumps({'actions': [{'action': 'cold-add', 'event_id': 'foreign-bad', 'scope': 'workspace', 'category': 'discoveries', 'text': 'bad', 'provenance': [{'kind': 'test', 'ref': 'bad'}], 'supersedes': [old_id]}]}))
        result = self.run_cli('memory-apply', '--task', created['state']['id'], '--owner', 'foreign', '--revision', '5', '--actions-file', str(bad)); self.assertNotEqual(result.returncode, 0); self.assertIn('supersession target', result.stderr); self.assertEqual(state.load(self.root / 'tasks' / created['state']['id'])['revision'], 5)

if __name__ == '__main__':
    unittest.main()
