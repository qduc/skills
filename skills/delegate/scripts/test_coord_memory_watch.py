import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import coord_memory_watch as watcher
import coord_state

DECISION = {'type': 'user', 'uuid': 'd1',
            'message': {'content': 'We decided the retention period is 30 days.'}}


def prompt_events(prompt):
    return json.loads(prompt.split('\n\n', 1)[1])['events']


def ignore_all(prompt, _env, _timeout):
    return json.dumps({'actions': [{'action': 'ignore', 'event_id': event['event_id'], 'reason': 'n'}
                                   for event in prompt_events(prompt)]})


def cold_add_first(prompt, _env, _timeout):
    event_id = prompt_events(prompt)[0]['event_id']
    return json.dumps({'actions': [{'action': 'cold-add', 'event_id': event_id, 'category': 'decisions',
                                    'scope': 'task', 'text': 'Retention is 30 days.',
                                    'provenance': [{'kind': 'transcript', 'ref': event_id}]}]})


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        created = coord_state.create(mock.Mock(title='t', objective='o', project=str(self.root),
                                               conversation=None, owner='owner'), self.root)
        self.task = created['state']['id']

    def tearDown(self):
        self.directory.cleanup()

    def bind(self, transcript):
        watcher.write_launch_marker(self.root, 'session', self.task, 'owner', transcript)
        return watcher.bind_markers(self.root)

    def offset(self):
        return coord_state._load_bindings(self.root)['bindings']['claude:session']['transcript_offset']

    def test_marker_creates_binding_and_watch_applies_memory(self):
        transcript = self.root / 'session.jsonl'
        transcript.write_text(json.dumps(DECISION) + '\n')
        self.assertEqual(self.bind(transcript), ['session'])
        watcher.watch(self.root, iterations=1, runner=cold_add_first)
        task = coord_state.load(coord_state.task_path(self.root, self.task))
        self.assertIn('Retention is 30 days.', [item['text'] for item in task['memory']['cold']])

    def test_binding_is_idempotent_across_passes(self):
        transcript = self.root / 'session.jsonl'
        transcript.write_text(json.dumps(DECISION) + '\n')
        self.assertEqual(self.bind(transcript), ['session'])
        self.assertEqual(watcher.bind_markers(self.root), [])
        watcher.watch(self.root, iterations=2, runner=ignore_all, sleep=lambda _seconds: None)
        self.assertEqual(self.offset(), transcript.stat().st_size)

    def test_watch_without_markers_is_a_noop(self):
        watcher.watch(self.root, iterations=1, runner=ignore_all)

    def test_all_dropped_tail_advances_offset(self):
        transcript = self.root / 'session.jsonl'
        transcript.write_text(json.dumps(DECISION) + '\n' +
                              json.dumps({'type': 'mode', 'uuid': 'x', 'mode': 'plan'}) + '\n')
        self.bind(transcript)
        watcher.watch(self.root, iterations=1, runner=ignore_all)
        self.assertEqual(self.offset(), transcript.stat().st_size)

    def test_truncated_transcript_resets_and_reapplies(self):
        transcript = self.root / 'session.jsonl'
        transcript.write_text(json.dumps(DECISION) + '\n')
        self.bind(transcript)
        bindings = coord_state._load_bindings(self.root)
        bindings['bindings']['claude:session']['transcript_offset'] = 9999
        coord_state._save_bindings(self.root, bindings)
        seen = []

        def runner(prompt, _env, _timeout):
            seen.append([event['event_id'] for event in prompt_events(prompt)])
            return ignore_all(prompt, _env, _timeout)

        watcher.watch(self.root, iterations=1, runner=runner)
        self.assertEqual(seen, [['e1']])

    def test_two_sessions_same_project_bind_deterministically(self):
        first = self.root / 'project' / 'a.jsonl'; first.parent.mkdir()
        second = self.root / 'project' / 'b.jsonl'
        first.write_text(json.dumps(DECISION) + '\n')
        second.write_text(json.dumps(DECISION) + '\n')
        watcher.write_launch_marker(self.root, 'session-a', self.task, 'owner', first)
        watcher.write_launch_marker(self.root, 'session-b', self.task, 'owner', second)
        self.assertEqual(sorted(watcher.bind_markers(self.root)), ['session-a', 'session-b'])
        bindings = coord_state._load_bindings(self.root)['bindings']
        self.assertEqual(bindings['claude:session-a']['transcript_path'], str(first))
        self.assertEqual(bindings['claude:session-b']['transcript_path'], str(second))

    def test_term2_marker_binds_and_filters_with_the_term2_profile(self):
        transcript = self.root / 'session.jsonl'
        envelope = {'v': 3, 'seq': 1, 'ts': 't',
                    'event': {'type': 'user_message',
                              'message': {'sender': 'user',
                                          'text': 'We decided the retention period is 30 days.'}}}
        transcript.write_text(json.dumps(envelope) + '\n')
        watcher.write_launch_marker(self.root, 'term', self.task, 'owner', transcript, harness='term2')
        self.assertEqual(watcher.bind_markers(self.root), ['term'])
        self.assertIn('term2:term', coord_state._load_bindings(self.root)['bindings'])
        watcher.watch(self.root, iterations=1, runner=cold_add_first)
        task = coord_state.load(coord_state.task_path(self.root, self.task))
        self.assertIn('Retention is 30 days.', [item['text'] for item in task['memory']['cold']])

    def test_unreadable_marker_is_skipped(self):
        (self.root / 'sessions').mkdir()
        (self.root / 'sessions' / 'broken.json').write_text('{not json')
        self.assertEqual(watcher.read_markers(self.root), {})
        self.assertEqual(watcher.bind_markers(self.root), [])

    def test_watch_survives_a_judge_failure(self):
        transcript = self.root / 'session.jsonl'
        transcript.write_text(json.dumps(DECISION) + '\n')
        self.bind(transcript)
        results = []
        with mock.patch.object(watcher.coord_memory, 'judge', side_effect=RuntimeError('boom')):
            watcher.watch(self.root, iterations=1, runner=ignore_all, logger=lambda s, r: results.append(r))
        self.assertEqual(results, [{'status': 'deferred', 'reason': 'RuntimeError'}])


if __name__ == '__main__':
    unittest.main()
