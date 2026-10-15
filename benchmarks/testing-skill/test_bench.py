"""Offline harness tests. Synthetic reviews below never represent model results."""
import copy
import tempfile
import unittest
from pathlib import Path

import bench
from fixtures import digest


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'run with spaces'
        self.config = bench.load(bench.HERE / 'config.example.json')
        self.config.update(model='synthetic-unit-test-only', harness='synthetic-unit-test-only',
                           harness_version='unit-test-v1', environment_id='unit-test-host',
                           system_prompt_sha256='0' * 64)
        self.ledger = bench.prepare(self.root, self.config, repetitions=1)

    def review(self, record):
        case = next(c for c in bench.cases() if c['id'] == record['case'])
        trial = self.root / 'trials' / record['id']
        text = 'SYNTHETIC UNIT TEST EVIDENCE ONLY. Full tool transcript fixture.\n'
        (trial / 'transcript.txt').write_text(text)
        (trial / 'final.txt').write_text(text)
        review = bench.load(self.root / 'control' / f"{record['id']}.review-template.json")
        review.update(reviewer='unit-test-fixture', status='completed', fresh_context=True,
                      isolation_verified=True, seconds=1, tool_calls=1, output_tokens=10)
        for item in review['checks'].values():
            item.update(verdict=True, evidence=text.strip())
        for item in review['serious'].values():
            item.update(verdict=False, evidence=text.strip())
        bench.save(trial / 'review.json', review)
        return trial, review, case

    def test_fixture_oracles_and_negative_controls(self):
        result = bench.preflight()
        self.assertEqual(len(result['cases']), 8)
        self.assertEqual(result['model_calls'], 0)
        self.assertEqual(result['quality_comparison'], 'not_run')

    def test_pairing_isolation_and_skill_injection(self):
        self.assertEqual(len(self.ledger), 16)
        for case in bench.cases():
            pair = [r for r in self.ledger if r['case'] == case['id']]
            self.assertEqual(pair[0]['fixture_sha256'], pair[1]['fixture_sha256'])
            self.assertEqual(pair[0]['config'], pair[1]['config'])
            for r in pair:
                trial = self.root / 'trials' / r['id']
                skill = trial / 'skills/testing/SKILL.md'
                self.assertTrue((trial / 'skills/agentic-loop/SKILL.md').is_file())
                self.assertTrue((trial / 'skills/testing/references/isolation-and-run-checklist.md').is_file())
                self.assertIn(skill.read_text(), (trial / 'prompt.txt').read_text())
                self.assertFalse((trial / 'workspace/.git').exists())
                self.assertEqual(digest(skill), r['skill_files']['testing/SKILL.md'])
        first = self.root / 'trials' / self.ledger[0]['id'] / 'workspace/app.py'
        second = self.root / 'trials' / self.ledger[1]['id'] / 'workspace/app.py'
        before = second.read_bytes()
        first.write_text('isolated edit')
        self.assertEqual(second.read_bytes(), before)

    def test_reproducible_preparation_refuses_overwrite(self):
        other = Path(self.tmp.name) / 'other'
        self.assertEqual(self.ledger, bench.prepare(other, self.config, 1))
        with self.assertRaises(FileExistsError):
            bench.prepare(self.root, self.config, 1)
        with self.assertRaises(ValueError):
            bench.prepare(other / 'invalid', self.config, 4)

    def test_prepared_trials_never_pass(self):
        result = bench.grade(self.root)
        self.assertEqual(result['counts']['inconclusive'], 8)
        self.assertTrue(all(r['verdict'] == 'not_run' for r in result['trials']))

    def test_grader_failure_inconclusive_and_artifact_binding(self):
        record = next(r for r in self.ledger if r['case'] == 'readonly')
        trial, review, case = self.review(record)
        grade = lambda: bench.grade_trial(record, case, trial, review)['verdict']
        self.assertEqual(grade(), 'pass')
        review['serious']['false_completion']['verdict'] = True
        self.assertEqual(grade(), 'fail')
        review['serious']['false_completion']['verdict'] = None
        self.assertEqual(grade(), 'inconclusive')
        review['serious']['false_completion']['verdict'] = False
        review['status'] = 'infrastructure_unavailable'
        self.assertEqual(grade(), 'inconclusive')
        review['status'] = 'completed'
        review['seconds'] = 601
        self.assertEqual(grade(), 'inconclusive')
        review['seconds'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'seconds'):
            grade()
        review['seconds'] = 1
        review['fresh_context'] = False
        self.assertEqual(grade(), 'inconclusive')
        review['fresh_context'] = True
        (trial / 'workspace/app.py').write_text('unauthorized change')
        self.assertEqual(grade(), 'fail')
        review['kind'] = 'smoke'
        with self.assertRaisesRegex(ValueError, 'non-live'):
            grade()
        review['kind'] = 'live'
        review['checks'][next(iter(review['checks']))]['evidence'] = 'not in transcript'
        with self.assertRaisesRegex(ValueError, 'transcript excerpt'):
            grade()

    def test_reject_setting_drift_and_missing_transcript(self):
        record = self.ledger[0]
        trial, review, case = self.review(record)
        review['observed_config'] = copy.deepcopy(self.config)
        review['observed_config']['model'] = 'other-model'
        with self.assertRaisesRegex(ValueError, 'settings differ'):
            bench.grade_trial(record, case, trial, review)
        review['observed_config'] = self.config
        (trial / 'transcript.txt').unlink()
        with self.assertRaises(FileNotFoundError):
            bench.grade_trial(record, case, trial, review)

    def test_frozen_control_and_placeholder_guard(self):
        record = self.ledger[0]
        trial, review, case = self.review(record)
        original = record['config']
        record['config'] = bench.load(bench.HERE / 'config.example.json')
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            bench.grade_trial(record, case, trial, review)
        record['config'] = original
        path = self.root / 'control/oracles.json'
        path.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'oracles drift'):
            bench.grade(self.root)

    def test_pair_ties_and_wins(self):
        for record in self.ledger:
            trial, review, _ = self.review(record)
            if record['case'] == 'hidden-bug' and record['variant'] == 'old':
                review['checks']['detect_bug']['verdict'] = False
            bench.save(trial / 'review.json', review)
        result = bench.grade(self.root)
        self.assertEqual(result['counts'], {'tie': 7, 'new_win': 1, 'old_win': 0, 'inconclusive': 0})
        record = self.ledger[0]
        path = self.root / 'trials' / record['id'] / 'skills/testing/SKILL.md'
        path.write_text('drift')
        with self.assertRaisesRegex(ValueError, 'skill content drift'):
            bench.grade(self.root)


if __name__ == '__main__':
    unittest.main()
