"""Behavioral probes across durable storage, gates, recovery and CLI boundaries."""
import copy
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from lab import Lab


class LabProbes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'run.sqlite')
        self.lab = Lab(self.path)
        self.lab.init({'question': 'Does autonomous research improve evidence quality?'})

    def tearDown(self):
        self.lab.db.close()
        self.tmp.cleanup()

    def plan(self):
        req = self.lab.request()
        self.lab.submit(req['id'], {'claims': [{'id': 'c1', 'text': 'Research benefits'}], 'strategy': 'Inspect original studies and contrary evidence'})
        return self.lab.request()

    def research(self):
        req = self.plan()
        rid = self.lab.reserve('web', queries=1, pages=1)['reservation']
        self.lab.observe(rid, {'ok': True, 'description': 'Inspected results table', 'opened_urls': ['https://example.org/study']})
        payload = {'sources': [{'id': 's1', 'url': 'https://example.org/study', 'title': 'Controlled experiment', 'kind': 'primary', 'note': 'The study reports better task coverage within its tested population.', 'locator': 'Table 2', 'reservation': rid}], 'claims': [{'id': 'c1', 'text': 'Research benefits on tested tasks', 'status': 'supported', 'sources': ['s1'], 'uncertainty': 'Generalization beyond tested tasks is unknown'}]}
        return req, payload

    def challenge(self, verdict='supports', needs_more=False):
        req, payload = self.research()
        self.lab.submit(req['id'], payload)
        req = self.lab.request()
        self.lab.submit(req['id'], {'reviews': [{'claim': 'c1', 'verdict': verdict, 'reason': 'Table supports restricted scope only', 'sources': ['s1']}], 'contradictions': ['Broad superiority remains untested'], 'followups': ['Repeat with equal compute'], 'needs_more': needs_more})

    def finish(self):
        req = self.lab.request()
        return self.lab.submit(req['id'], {'conclusion': 'Some restricted evidence of benefit', 'judgment': 'Decide whether more trials are worth funding', 'uncertainties': ['Compute-matched replication missing'], 'followups': ['What is the equal-cost effect?'], 'lessons': ['Require comparator budget information']})

    def test_complete_run_persists_reviewed_knowledge_and_report(self):
        self.challenge()
        self.finish()
        self.lab.db.close()
        self.lab = Lab(self.path)
        state = self.lab.export()
        self.assertEqual(state['status'], 'completed')
        self.assertEqual(state['used']['web_calls'], 1)
        self.assertEqual(self.lab.db.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0], 1)
        self.assertIn('https://example.org/study', self.lab.report())
        self.assertTrue({'observe', 'decide', 'act', 'verify', 'learn'} <= {e['phase'] for e in state['events']})

    def test_uncited_supported_claim_cannot_advance_and_retry_keeps_request(self):
        req, payload = self.research()
        bad = copy.deepcopy(payload)
        bad['claims'][0]['sources'] = []
        with self.assertRaisesRegex(ValueError, 'need evidence'):
            self.lab.submit(req['id'], bad)
        self.assertEqual(self.lab.request()['id'], req['id'])
        self.lab.submit(req['id'], payload)

    def test_unknown_source_and_search_snippet_are_rejected(self):
        req, payload = self.research()
        bad = copy.deepcopy(payload)
        bad['claims'][0]['sources'] = ['invented']
        with self.assertRaisesRegex(ValueError, 'unknown claim source'):
            self.lab.submit(req['id'], bad)
        bad = copy.deepcopy(payload)
        bad['sources'][0]['url'] = 'https://example.org/unopened'
        with self.assertRaisesRegex(ValueError, 'snippets'):
            self.lab.submit(req['id'], bad)

    def test_missing_challenge_is_rejected(self):
        req, payload = self.research()
        self.lab.submit(req['id'], payload)
        req = self.lab.request()
        with self.assertRaisesRegex(ValueError, 'every claim'):
            self.lab.submit(req['id'], {'reviews': [], 'contradictions': [], 'followups': [], 'needs_more': False})

    def test_disputed_claim_is_not_promoted_to_knowledge(self):
        self.challenge('disputes')
        self.finish()
        self.assertEqual(self.lab.export()['claims'][0]['status'], 'unsupported')
        self.assertEqual(self.lab.db.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0], 0)

    def test_tool_budget_rejects_before_execution_preserves_partial_report(self):
        self.plan()
        result = self.lab.reserve('web', queries=13)
        self.assertEqual(result['denied'], ['queries'])
        self.assertEqual(self.lab.export()['used']['web_calls'], 0)
        self.assertEqual(self.lab.export()['status'], 'running')

    def test_negative_or_paid_reservation_rejected(self):
        self.plan()
        for kwargs in ({'queries': -1}, {'micro_usd': 1}, {'pages': True}):
            with self.assertRaises(ValueError):
                self.lab.reserve('web', **kwargs)
        self.assertEqual(self.lab.export()['used']['web_calls'], 0)

    def test_pending_request_survives_restart_without_double_charge(self):
        first = self.lab.request()
        self.lab.db.close()
        self.lab = Lab(self.path)
        self.assertEqual(self.lab.request()['id'], first['id'])
        self.assertEqual(self.lab.export()['used']['steps'], 1)

    def test_deadline_is_terminal_across_resume(self):
        s = self.lab.state()
        with patch('lab.time.time', return_value=s['started_epoch'] + 601):
            self.assertEqual(self.lab.request()['stop_reason'], 'deadline')
        self.assertEqual(self.lab.request()['status'], 'stopped')
        self.assertEqual(self.lab.reserve('web')['status'], 'stopped')

    def test_stale_response_and_replayed_observation_rejected(self):
        req, payload = self.research()
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.lab.submit(req['id'] + 1, payload)
        with self.assertRaisesRegex(ValueError, 'already observed'):
            self.lab.observe(payload['sources'][0]['reservation'], {'ok': True, 'description': 'Replay'})

    def test_failed_tools_remain_charged_and_block_source_promotion(self):
        req = self.plan()
        rid = self.lab.reserve('web', pages=1)['reservation']
        self.lab.observe(rid, {'ok': False, 'description': 'Primary source inaccessible'})
        self.assertEqual(self.lab.export()['used']['web_calls'], 1)
        self.assertIn('Primary source inaccessible', self.lab.export()['lessons'])
        with self.assertRaisesRegex(ValueError, 'successful'):
            self.lab.validate_sources([{'id': 's1', 'url': 'https://example.org', 'title': 'A', 'note': 'B', 'locator': 'C', 'kind': 'primary', 'reservation': rid}])

    def test_outstanding_tool_blocks_submission(self):
        req = self.plan()
        self.lab.reserve('web')
        with self.assertRaisesRegex(ValueError, 'outstanding'):
            self.lab.submit(req['id'], {})

    def test_refinement_stops_at_cycle_limit(self):
        self.challenge(needs_more=True)
        self.assertEqual(self.lab.state()['stage'], 'research')
        self.assertEqual(self.lab.state()['cycle'], 2)
        # Existing evidence can be explicitly reinspected/reused in the second cycle.
        req = self.lab.request()
        s = self.lab.state()
        self.lab.submit(req['id'], {'sources': s['sources'], 'claims': s['claims']})
        req = self.lab.request()
        self.lab.submit(req['id'], {'reviews': [{'claim': 'c1', 'verdict': 'supports', 'reason': 'Scope unchanged', 'sources': ['s1']}], 'contradictions': [], 'followups': [], 'needs_more': True})
        self.assertEqual(self.lab.state()['stage'], 'report')
        self.finish()
        self.assertEqual(self.lab.state()['status'], 'completed')

    def test_legacy_observation_recovers_original_timestamp(self):
        req, payload = self.research()
        rid = payload['sources'][0]['reservation']
        result = json.loads(self.lab.db.execute('SELECT result FROM reservations WHERE id=?', (rid,)).fetchone()[0])
        original = result.pop('observed_at')
        with self.lab.transaction():
            self.lab.db.execute('UPDATE reservations SET result=? WHERE id=?', (json.dumps(result), rid))
        self.lab.submit(req['id'], payload)
        recovered = self.lab.state()['sources'][0]['accessed_at']
        self.assertLess(abs((__import__('datetime').datetime.fromisoformat(recovered) - __import__('datetime').datetime.fromisoformat(original)).total_seconds()), .1)

    def test_subsequent_run_retrieves_knowledge_as_hints(self):
        self.challenge()
        self.finish()
        second = Lab(str(Path(self.tmp.name) / 'second.sqlite'))
        try:
            second.init({'question': 'What research benefits persist?'}, knowledge_from=self.path)
            knowledge = second.request()['prior_knowledge']
            self.assertEqual(len(knowledge), 1)
            self.assertEqual(knowledge[0]['evidence'][0]['url'], 'https://example.org/study')
            self.assertEqual(second.state()['claims'], [])
        finally:
            second.db.close()

    def test_cli_reports_errors_and_exports_real_state(self):
        script = Path(__file__).with_name('lab.py')
        bad = subprocess.run([sys.executable, str(script), '--db', self.path, 'submit', '--request', '99', '--file', str(Path(__file__))], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        good = subprocess.run([sys.executable, str(script), '--db', self.path, 'export'], capture_output=True, text=True)
        self.assertEqual(json.loads(good.stdout)['question'], self.lab.state()['question'])


if __name__ == '__main__':
    unittest.main()
