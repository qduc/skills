import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import watch_workers


class WorkerWatchTests(unittest.TestCase):
    def test_progress_fingerprint_changes_when_worktree_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.py'
            source.write_text('before')
            before = watch_workers.progress_fingerprint([root])
            source.write_text('after')
            self.assertNotEqual(before, watch_workers.progress_fingerprint([root]))

    def run_watch(self, status, *, idle_grace=0, stall_minutes=15):
        with tempfile.TemporaryDirectory() as directory:
            state = str(Path(directory) / 'watch.json')
            args = argparse.Namespace(state=state, worker=['pane=/missing/report'],
                                      timeout_minutes=1, idle_grace=idle_grace,
                                      stall_minutes=stall_minutes, interval=1, settle=0, debounce=1,
                                      progress_path=[])
            output = io.StringIO()
            with patch.object(watch_workers, 'status', return_value=status), \
                 patch.object(watch_workers, 'footer', return_value='stable footer'), \
                 patch.object(watch_workers.time, 'sleep'), \
                 contextlib.redirect_stdout(output):
                watch_workers.cmd_watch(args)
            return [json.loads(line) for line in output.getvalue().splitlines()]

    def test_stopped_lifecycle_without_report_wakes_as_stall(self):
        # done/idle without the expected report is a stall, not a completion.
        for status in ('blocked', 'unknown', 'done', 'idle'):
            with self.subTest(status=status):
                events = self.run_watch(status)
                self.assertEqual(events[1]['event'], 'stall')
                self.assertEqual(events[1]['status'], status)

    def test_upstream_error_stall_carries_hint(self):
        error_text = 'service_unavailable_error: servers overloaded\nUse /retry-turn to try again'
        with tempfile.TemporaryDirectory() as directory:
            state = str(Path(directory) / 'watch.json')
            args = argparse.Namespace(state=state, worker=['pane=/missing/report'],
                                      timeout_minutes=1, idle_grace=0,
                                      stall_minutes=15, interval=1, settle=0, debounce=1,
                                      progress_path=[])
            output = io.StringIO()
            with patch.object(watch_workers, 'status', return_value='done'), \
                 patch.object(watch_workers, 'footer', return_value='stable footer'), \
                 patch.object(watch_workers, 'herdr', return_value=error_text), \
                 patch.object(watch_workers.time, 'sleep'), \
                 contextlib.redirect_stdout(output):
                watch_workers.cmd_watch(args)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(events[1]['event'], 'stall')
            self.assertEqual(events[1]['hint'], 'service_unavailable_error')

    def test_clean_stall_has_no_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            state = str(Path(directory) / 'watch.json')
            args = argparse.Namespace(state=state, worker=['pane=/missing/report'],
                                      timeout_minutes=1, idle_grace=0,
                                      stall_minutes=15, interval=1, settle=0, debounce=1,
                                      progress_path=[])
            output = io.StringIO()
            with patch.object(watch_workers, 'status', return_value='done'), \
                 patch.object(watch_workers, 'footer', return_value='stable footer'), \
                 patch.object(watch_workers, 'herdr', return_value='all good'), \
                 patch.object(watch_workers.time, 'sleep'), \
                 contextlib.redirect_stdout(output):
                watch_workers.cmd_watch(args)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(events[1]['event'], 'stall')
            self.assertNotIn('hint', events[1])

    def test_frozen_working_footer_wakes_as_no_progress(self):
        events = self.run_watch('working', stall_minutes=0)
        self.assertEqual(events[1]['event'], 'no_progress')

    def test_progress_is_scoped_to_pane_and_frozen_footer_is_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a_path, b_path = root / 'a', root / 'b'
            a_path.mkdir(); b_path.mkdir()
            state = str(root / 'watch.json')
            args = argparse.Namespace(state=state, worker=['A=/missing/a', 'B=/missing/b'],
                                      timeout_minutes=2, idle_grace=0, stall_minutes=1,
                                      interval=1, settle=0, debounce=1, progress_path=[],
                                      worker_progress=[f'A={a_path}', f'B={b_path}'])
            output = io.StringIO()
            now = [0]
            changing_file = a_path / 'work.txt'
            changing_file.write_text('initial')
            sleep_calls = [0]
            def advance(_seconds):
                sleep_calls[0] += 1
                now[0] += 30
                changing_file.write_text(f'change-{sleep_calls[0]}')
            with patch.object(watch_workers, 'status', return_value='working'), \
                 patch.object(watch_workers, 'footer', return_value='frozen footer'), \
                 patch.object(watch_workers.time, 'time', side_effect=lambda: now[0]), \
                 patch.object(watch_workers.time, 'sleep', side_effect=advance), \
                 contextlib.redirect_stdout(output):
                watch_workers.cmd_watch(args)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            no_progress = [e['pane'] for e in events if e['event'] == 'no_progress']
            self.assertEqual(no_progress, ['B'])

    def test_single_worker_legacy_progress_path_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'work'
            work.mkdir()
            args = argparse.Namespace(state=str(root / 'watch.json'),
                                      worker=['pane=/missing/report'], progress_path=[str(work)],
                                      timeout_minutes=1, idle_grace=0, stall_minutes=0,
                                      interval=1, settle=0, debounce=1)
            output = io.StringIO()
            with patch.object(watch_workers, 'status', return_value='working'), \
                 patch.object(watch_workers, 'footer', return_value='stable footer'), \
                 patch.object(watch_workers.time, 'sleep'), \
                 contextlib.redirect_stdout(output):
                watch_workers.cmd_watch(args)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(events[1]['event'], 'no_progress')
            self.assertEqual(events[1]['progress_paths'], [str(work)])


if __name__ == '__main__':
    unittest.main()
