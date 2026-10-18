import json
import tempfile
import unittest
from pathlib import Path

import coord_memory
from coord_memory_filter import CLAUDE_CODE, TERM2, filter_record, filter_records, profile_for

FIXTURE = Path(__file__).parent / 'fixtures' / 'claude-code-transcript.jsonl'


def user_text(text):
    return {'type': 'user', 'uuid': 'u', 'message': {'content': text}}


def blocks(record_type, *items):
    return {'type': record_type, 'uuid': 'r', 'message': {'content': list(items)}}


class FilterRecordTest(unittest.TestCase):
    def test_string_content_is_kept(self):
        text, info = filter_record(user_text('Please implement the parser.'))
        self.assertEqual(text, 'Please implement the parser.')
        self.assertTrue(info['kept'])

    def test_text_blocks_are_kept_and_other_blocks_dropped(self):
        record = blocks('assistant', {'type': 'text', 'text': 'I will read the file first.'},
                        {'type': 'tool_use', 'name': 'Read', 'input': {'path': 'x.py'}})
        text, info = filter_record(record)
        self.assertEqual(text, 'I will read the file first.')
        self.assertEqual(info['dropped_blocks'], ['tool_use'])

    def test_tool_result_only_record_is_dropped(self):
        record = blocks('user', {'type': 'tool_result', 'tool_use_id': 't1', 'content': 'huge output'})
        text, info = filter_record(record)
        self.assertIsNone(text)
        self.assertEqual(info, {'dropped': 'no-text'})

    def test_injection_inside_tool_result_is_not_kept(self):
        sentinel = 'SENTINEL-IGNORE-PREVIOUS-INSTRUCTIONS'
        text, _info = filter_record(blocks('user', {'type': 'tool_result', 'content': sentinel}))
        self.assertIsNone(text)
        mixed = blocks('user', {'type': 'text', 'text': 'ok'}, {'type': 'tool_result', 'content': sentinel})
        text, _info = filter_record(mixed)
        self.assertEqual(text, 'ok')
        self.assertNotIn(sentinel, text)

    def test_thinking_is_dropped_text_kept(self):
        record = blocks('assistant', {'type': 'thinking', 'thinking': 'private reasoning'},
                        {'type': 'text', 'text': 'The retention period is 30 days.'})
        text, info = filter_record(record)
        self.assertEqual(text, 'The retention period is 30 days.')
        self.assertEqual(info['dropped_blocks'], ['thinking'])

    def test_image_and_whitespace_yield_no_text(self):
        record = blocks('user', {'type': 'image', 'source': {'data': 'AAAA'}}, {'type': 'text', 'text': '   '})
        text, info = filter_record(record)
        self.assertIsNone(text)
        self.assertEqual(info, {'dropped': 'no-text'})

    def test_unrecognized_record_type_is_dropped_with_its_type(self):
        text, info = filter_record({'type': 'attachment', 'uuid': 'x', 'content': 'body'})
        self.assertIsNone(text)
        self.assertEqual(info, {'dropped': 'record-type', 'record_type': 'attachment'})

    def test_record_without_type_is_dropped(self):
        text, info = filter_record({'uuid': 'x', 'text': 'bare'})
        self.assertIsNone(text)
        self.assertEqual(info, {'dropped': 'record-type', 'record_type': None})

    def test_profile_swap_needs_no_code_change(self):
        narrow = {'name': 'narrow', 'type_path': ('type',),
                  'records': {'assistant': CLAUDE_CODE['records']['assistant']}}
        text, info = filter_record(user_text('user turn'), narrow)
        self.assertIsNone(text)
        self.assertEqual(info['record_type'], 'user')

    def test_profile_for_selects_by_harness(self):
        self.assertIs(profile_for('claude'), CLAUDE_CODE)
        self.assertIs(profile_for('term2'), TERM2)
        self.assertIs(profile_for('unseen'), CLAUDE_CODE)


class Term2ProfileTest(unittest.TestCase):
    def test_user_message_string_is_kept(self):
        record = {'event': {'type': 'user_message', 'message': {'sender': 'user', 'text': 'Please ship it.'}}}
        text, info = filter_record(record, TERM2)
        self.assertEqual(text, 'Please ship it.')
        self.assertTrue(info['kept'])

    def test_assistant_turn_keeps_text_and_drops_reasoning(self):
        record = {'event': {'type': 'assistant_turn', 'turn': {'items': [
            {'type': 'reasoning', 'text': 'private'},
            {'type': 'assistant_text', 'text': 'We decided the retention period is 30 days.'},
            {'type': 'tool_result', 'output': 'huge'}]}}}
        text, info = filter_record(record, TERM2)
        self.assertEqual(text, 'We decided the retention period is 30 days.')
        self.assertEqual(info['dropped_blocks'], ['reasoning', 'tool_result'])

    def test_non_conversational_record_types_are_dropped(self):
        for record_type in ('session_init', 'tool_started', 'assistant_journal_item', 'command_message'):
            text, info = filter_record({'event': {'type': record_type, 'content': 'x'}}, TERM2)
            self.assertIsNone(text)
            self.assertEqual(info, {'dropped': 'record-type', 'record_type': record_type})


class FixtureTest(unittest.TestCase):
    def test_term2_fixture_keeps_only_conversational_text(self):
        records = [json.loads(line) for line in (Path(__file__).parent / 'fixtures' / 'term2-transcript.jsonl').read_text().splitlines() if line.strip()]
        kept, dropped = filter_records(records, TERM2)
        texts = [text for _record, text in kept]
        self.assertEqual(texts, ['Please ship the watcher.', 'We decided the sidecar stays disabled until the gate passes.'])
        self.assertIn('session_init', dropped)
        self.assertIn('tool_started', dropped)
        self.assertEqual(dropped.get('no-text'), 1)

    def test_fixture_keeps_only_conversational_text(self):
        records = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
        kept, dropped = filter_records(records)
        texts = [text for _record, text in kept]
        self.assertIn('Please implement the parser.', texts)
        self.assertIn('We decided the retention period is 30 days.', texts)
        joined = ' '.join(texts)
        self.assertNotIn('SENTINEL-IGNORE-PREVIOUS-INSTRUCTIONS', joined)
        self.assertNotIn('private reasoning', joined)
        self.assertIn('attachment', dropped)
        self.assertIn('mode', dropped)
        self.assertEqual(dropped.get('no-text'), 2)


class EventsIntegrationTest(unittest.TestCase):
    def test_events_drop_noise_and_redact_kept_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 't.jsonl'
            records = [
                user_text('Please implement the parser.'),
                blocks('user', {'type': 'tool_result', 'content': 'SENTINEL-IGNORE-PREVIOUS-INSTRUCTIONS'}),
                blocks('assistant', {'type': 'text', 'text': 'token: sk-abcdefghijklmnop'}),
                {'type': 'mode', 'uuid': 'x', 'mode': 'plan'},
            ]
            path.write_text(''.join(json.dumps(record) + '\n' for record in records))
            events, _read_end = coord_memory._events({'transcript_path': str(path)}, {'transcript_offset': 0})
        texts = [event['text'] for event in events]
        self.assertEqual(len(events), 2)
        self.assertNotIn('SENTINEL-IGNORE-PREVIOUS-INSTRUCTIONS', ' '.join(texts))
        self.assertNotIn('sk-abcdefghijklmnop', ' '.join(texts))

    def test_injection_never_reaches_the_judge_prompt(self):
        sentinel = 'SENTINEL-IGNORE-PREVIOUS-INSTRUCTIONS'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 't.jsonl'
            records = [
                user_text('Please implement the parser.'),
                blocks('user', {'type': 'tool_result', 'content': sentinel}),
                blocks('assistant', {'type': 'thinking', 'thinking': sentinel}),
                blocks('assistant', {'type': 'tool_use', 'name': 'Bash', 'input': {'cmd': sentinel}}),
                blocks('user', {'type': 'image', 'source': {'data': sentinel}}),
            ]
            path.write_text(''.join(json.dumps(record) + '\n' for record in records))
            events, _read_end = coord_memory._events({'transcript_path': str(path)}, {'transcript_offset': 0})
        prompt = coord_memory.prompt(
            {'id': 't', 'project': '/p', 'revision': 1, 'memory': {}}, events)
        self.assertNotIn(sentinel, prompt)
        self.assertIn('Please implement the parser.', prompt)


if __name__ == '__main__':
    unittest.main()
