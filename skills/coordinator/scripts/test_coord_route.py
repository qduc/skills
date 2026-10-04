import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import coord_route


class RouteTests(unittest.TestCase):
    def pick(self, pools, history, *args):
        output = io.StringIO()
        argv = ['pick']
        for pool in pools:
            argv += ['--pool', pool]
        argv += ['--history', str(history), *args]
        with contextlib.redirect_stdout(output):
            code = coord_route.main(argv)
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        return code, events

    def test_rotation_cycles_through_pools_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            picks = []
            for _ in range(2):
                for pool in ('term2+zai', 'codex-luna', 'agy'):
                    code, events = self.pick([pool, 'codex-luna', 'agy'], history)
                    self.assertEqual(code, 0)
                    picks.append(events[-1]['pool'])
            self.assertEqual(picks, ['term2+zai', 'codex-luna', 'agy'] * 2)

    def test_never_picked_pool_goes_first(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            code, events = self.pick(['codex-luna', 'agy'], history)
            self.assertEqual(events[-1]['pool'], 'codex-luna')
            code, events = self.pick(['codex-luna', 'agy'], history)
            self.assertEqual(events[-1]['pool'], 'agy')

    def test_exhausted_pool_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            code, events = self.pick(['term2+zai', 'codex-luna'], history, '--exclude', 'term2+zai')
            self.assertEqual(code, 0)
            self.assertEqual(events[-1]['pool'], 'codex-luna')
            self.assertEqual(events[-1]['excluded'], ['term2+zai'])

    def test_all_pools_excluded_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            code, events = self.pick(['term2+zai'], history, '--exclude', 'term2+zai')
            self.assertEqual(code, 1)
            self.assertEqual(events[-1].get('error'), 'no_available_pool')

    def test_missing_inventory_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            code, events = self.pick(['agy'], history, '--inventory', '/nonexistent/inventory.md')
            self.assertEqual(code, 1)
            self.assertEqual(events[-1].get('error'), 'missing_inventory')

    def test_existing_inventory_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            inventory = Path(directory) / 'inventory.md'
            inventory.write_text('# Host inventory\n')
            code, events = self.pick(['agy'], history, '--inventory', str(inventory))
            self.assertEqual(code, 0)
            self.assertEqual(events[-1]['inventory'], str(inventory))

    def test_history_records_picks(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            self.pick(['a', 'b'], history)
            self.pick(['a', 'b'], history)
            data = json.loads(history.read_text())
            self.assertEqual([p['pool'] for p in data['picks']], ['a', 'b'])
            self.assertTrue(all('at' in p for p in data['picks']))

    def test_dry_run_does_not_record_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'route-history.json'
            code, events = self.pick(['a', 'b'], history, '--dry-run')
            self.assertEqual(code, 0)
            self.assertEqual(events[-1]['event'], 'candidate')
            self.assertFalse(history.exists())


if __name__ == '__main__':
    unittest.main()
