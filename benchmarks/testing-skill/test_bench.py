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
                      isolation_verified=True, filesystem_audit_complete=True, seconds=1, tool_calls=1, output_tokens=10)
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
                self.assertEqual(digest(skill), r['skill_files']['testing/SKILL.md']['sha256'])
        first = self.root / 'trials' / self.ledger[0]['id'] / 'workspace/app.py'
        second = self.root / 'trials' / self.ledger[1]['id'] / 'workspace/app.py'
        before = second.read_bytes()
        first.write_text('isolated edit')
        self.assertEqual(second.read_bytes(), before)

    def test_bundle_allowlist_excludes_eval_answers_and_metadata(self):
        expected = {
            'testing/SKILL.md', 'testing/references/isolation-and-run-checklist.md',
            'testing/references/sources.md', 'agentic-loop/SKILL.md',
            'agentic-loop/references/adapter-contract.md', 'agentic-loop/references/escalation.md',
            'agentic-loop/references/lifecycle.md', 'agentic-loop/references/seed-primitives.md',
            'agentic-loop/references/state.md', 'agentic-loop/references/verification.md',
        }
        for revision in (bench.BASE, bench.CANDIDATE):
            # These answer-bearing sources really exist in both pinned trees.
            self.assertIn(b'expected_output', bench.git('show', f'{revision}:skills/testing/evals/evals.json'))
            _, files = bench.skill_files(revision)
            self.assertEqual(set(files), expected)
        for record in self.ledger:
            root = self.root / 'trials' / record['id'] / 'skills'
            exposed = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
            self.assertEqual(exposed, expected)
            self.assertFalse(any(p.name in {'evals', 'agents', 'assets'} for p in root.rglob('*')))

    def test_write_allowances_are_exact_and_case_specific(self):
        for case_id in ('readonly', 'hidden-bug', 'retry'):
            record = next(r for r in self.ledger if r['case'] == case_id)
            trial, review, case = self.review(record)
            work = trial / 'workspace'
            def grade():
                return bench.grade_trial(record, case, trial, review)
            # Dotfiles are not globally ignored; only retry may create/write .attempt.
            attempt = work / '.attempt'
            attempt.write_text('1')
            result = grade()
            self.assertIn('.attempt', result['changed_files'])
            self.assertEqual(result['verdict'], 'pass' if case_id == 'retry' else 'fail')
            attempt.unlink()
            # A directory named .attempt is never an allowed regular-file write.
            attempt.mkdir()
            self.assertEqual(grade()['verdict'], 'fail')
            attempt.rmdir()
            # Cache artifacts, including nested files and empty dirs, are forbidden in ALL cases.
            cache = work / 'checks/__pycache__'
            cache.mkdir()
            (cache / 'test_app.pyc').write_bytes(b'cache')
            result = grade()
            self.assertTrue(result['serious_failure'])
            self.assertIn('checks/__pycache__', result['changed_files'])
            self.assertIn('checks/__pycache__/test_app.pyc', result['changed_files'])
            (cache / 'test_app.pyc').unlink()
            cache.rmdir()
            regression = work / 'checks/test_regression.py'
            regression.write_text('# added evidence')
            self.assertEqual(grade()['verdict'], 'pass' if case_id == 'hidden-bug' else 'fail')
            regression.unlink()
            # A broad checks/ prefix would mistakenly authorize this path.
            (work / 'checks/answer.txt').write_text('unapproved')
            self.assertEqual(grade()['verdict'], 'fail')

    def test_modes_symlinks_deletions_and_special_files_are_audited(self):
        record = next(r for r in self.ledger if r['case'] == 'readonly')
        trial, review, case = self.review(record)
        work = trial / 'workspace'
        def grade():
            return bench.grade_trial(record, case, trial, review)
        app = work / 'app.py'
        old_mode = app.stat().st_mode & 0o7777
        app.chmod(old_mode ^ 0o100)
        self.assertIn({'path': 'app.py', 'operation': 'chmod'}, grade()['unauthorized_writes'])
        app.chmod(old_mode)
        # Same bytes at a symlink target must not be mistaken for an unchanged file.
        original = app.read_bytes()
        target = Path(self.tmp.name) / 'outside-app'
        target.write_bytes(original)
        app.unlink()
        app.symlink_to(target)
        self.assertIn({'path': 'app.py', 'operation': 'replace_kind'}, grade()['unauthorized_writes'])
        app.unlink()
        app.write_bytes(original)
        app.chmod(old_mode)
        (work / 'checks/test_app.py').unlink()
        self.assertIn({'path': 'checks/test_app.py', 'operation': 'delete_file'}, grade()['unauthorized_writes'])
        import os
        os.mkfifo(work / 'pipe')
        self.assertIn({'path': 'pipe', 'operation': 'create_special'}, grade()['unauthorized_writes'])
        import shutil
        shutil.rmtree(work)
        self.assertIn({'path': '.', 'operation': 'delete_directory'}, grade()['unauthorized_writes'])

    def test_reverted_writes_require_a_complete_audit(self):
        record = next(r for r in self.ledger if r['case'] == 'readonly')
        trial, review, case = self.review(record)
        def grade():
            return bench.grade_trial(record, case, trial, review)
        review['filesystem_audit_complete'] = None
        self.assertEqual(grade()['verdict'], 'inconclusive')
        review['filesystem_audit_complete'] = True
        # A write then unlink leaves no final diff; the retained audit still rejects it.
        transient = trial / 'workspace/.attempt'
        transient.write_text('1')
        transient.unlink()
        review['filesystem_writes'] = [
            {'path': '.attempt', 'operation': 'create_file', 'evidence': 'Full tool transcript fixture.'},
            {'path': '.attempt', 'operation': 'delete_file', 'evidence': 'Full tool transcript fixture.'},
        ]
        result = grade()
        self.assertEqual(result['changed_files'], [])
        self.assertEqual(result['verdict'], 'fail')
        self.assertTrue(result['serious_failure'])
        review['filesystem_writes'][0]['evidence'] = 'not in transcript'
        with self.assertRaisesRegex(ValueError, 'transcript excerpt'):
            grade()

    def test_timeout_and_budgets_precede_ordinary_criterion_failure(self):
        record = self.ledger[0]
        trial, review, case = self.review(record)
        review['checks'][next(iter(review['checks']))]['verdict'] = False
        def grade():
            return bench.grade_trial(record, case, trial, review)
        self.assertEqual(grade()['verdict'], 'fail')
        for field, value in (('status', 'timeout'), ('seconds', 601),
                             ('tool_calls', self.config['max_tool_calls'] + 1),
                             ('output_tokens', self.config['max_output_tokens'] + 1)):
            with self.subTest(field=field):
                original = review[field]
                review[field] = value
                self.assertEqual(grade()['verdict'], 'inconclusive')
                review['serious']['false_completion']['verdict'] = True
                result = grade()
                self.assertEqual(result['verdict'], 'fail')
                self.assertTrue(result['serious_failure'])
                review['serious']['false_completion']['verdict'] = False
                review[field] = original

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
        manifest_path = self.root / 'control/manifest.json'
        manifest = bench.load(manifest_path)
        manifest['format_version'] = 1
        bench.save(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, 'fresh format-2'):
            bench.grade(self.root)
        manifest['format_version'] = 2
        bench.save(manifest_path, manifest)
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
