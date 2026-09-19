#!/usr/bin/env python3

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parent
PREPARE = SCRIPTS / "prepare-pooled-judge.py"
AGGREGATE = SCRIPTS / "aggregate-judge.py"
POOLED = SCRIPTS / "pooled-judge.sh"


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class PooledJudgeTest(unittest.TestCase):
    def make_sources(self, root):
        first = root / "run-1"
        second = root / "run-2"
        write(first / "control" / "empty.diff", "")
        write(first / "control" / "empty.evaluator.status", "FAIL\n")
        shared = "--- a/file.ts\n+++ b/file.ts\n@@\n-old\n+new\n"
        write(first / "control" / "alpha.diff", shared)
        write(first / "control" / "alpha.evaluator.status", "PASS\n")
        write(first / "control" / "alpha.run.status", "OK\n")
        write(second / "control" / "beta.diff", shared)
        write(second / "control" / "beta.evaluator.status", "PASS\n")
        write(second / "control" / "beta.run.status", "OK\n")
        return first, second

    def test_preparation_deduplicates_and_aggregation_expands_scores(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = self.make_sources(root)
            pool = root / "pool" / "control"
            prompt = root / "prompt.txt"
            write(prompt, "Fix the bug.\n")

            subprocess.run([
                "python3", str(PREPARE), "collect", "--pool-dir", str(pool),
                str(first), str(second),
            ], check=True, capture_output=True, text=True)
            subprocess.run([
                "python3", str(PREPARE), "sample", "--pool-dir", str(pool),
                "--sample", "1", "--prompt", str(prompt),
            ], check=True, capture_output=True, text=True)

            manifest = json.loads((pool / "pool-manifest.json").read_text())
            self.assertEqual(len(manifest["groups"]), 1)
            self.assertEqual(manifest["groups"][0]["candidates"], ["alpha", "beta"])
            self.assertEqual(set(json.loads((pool / "mechanical-scores.json").read_text())), {"empty"})
            mapping = json.loads((pool / "mapping-1.json").read_text())
            self.assertEqual(mapping, {"candidate-A": ["alpha", "beta"]})
            judge_prompt = (pool / "judge-prompt.txt").read_text()
            self.assertEqual(judge_prompt.count("--- a/file.ts"), 1)
            self.assertNotIn("alpha", judge_prompt)
            self.assertNotIn("beta", judge_prompt)
            self.assertIn('"deterministic_evaluator":"PASS"', judge_prompt)

            write(pool / "judge-1.txt", json.dumps({"scores": {
                "candidate-A": {"correctness": 4, "scope": 2, "compatibility": 2, "tests": 1}
            }}))
            subprocess.run([
                "python3", str(AGGREGATE), "--control-dir", str(pool)
            ], check=True, capture_output=True, text=True)
            summary = json.loads((pool / "judge-summary.json").read_text())
            self.assertEqual(summary["candidates"]["alpha"]["total_mean"], 9.0)
            self.assertEqual(summary["candidates"]["beta"]["total_mean"], 9.0)
            self.assertEqual(summary["candidates"]["empty"]["total_mean"], 0.0)
            self.assertEqual(summary["candidates"]["empty"]["score_source"], "mechanical-empty")

    def test_same_diff_with_different_evidence_is_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = self.make_sources(root)
            write(second / "control" / "beta.evaluator.status", "FAIL\n")
            pool = root / "pool"
            subprocess.run([
                "python3", str(PREPARE), "collect", "--pool-dir", str(pool),
                str(first), str(second),
            ], check=True, capture_output=True, text=True)
            manifest = json.loads((pool / "pool-manifest.json").read_text())
            self.assertEqual(len(manifest["groups"]), 2)

    def test_prompt_budget_fails_before_judge_invocation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = self.make_sources(root)
            pool = root / "pool"
            prompt = root / "prompt.txt"
            write(prompt, "Fix it.\n")
            subprocess.run([
                "python3", str(PREPARE), "collect", "--pool-dir", str(pool),
                str(first), str(second),
            ], check=True, capture_output=True, text=True)
            result = subprocess.run([
                "python3", str(PREPARE), "sample", "--pool-dir", str(pool),
                "--sample", "1", "--prompt", str(prompt), "--max-prompt-bytes", "20",
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("above --max-prompt-bytes", result.stderr)

    def test_manifest_candidate_requires_frozen_evaluator_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "run"
            write(run / "control" / "alpha.diff", "+fix\n")
            write(run / "control" / "meta.json", json.dumps({"candidates": ["alpha"]}))
            result = subprocess.run([
                "python3", str(PREPARE), "collect", "--pool-dir", str(root / "pool"),
                str(run),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("run scripts/run-evaluator.sh first", result.stderr)

    def test_aggregator_rejects_extra_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            pool = Path(temp)
            write(pool / "mapping-1.json", json.dumps({"candidate-A": ["alpha"]}))
            write(pool / "judge-1.txt", json.dumps({"scores": {"candidate-A": {
                "correctness": 4, "scope": 2, "compatibility": 2, "tests": 2, "confidence": "high"
            }}}))
            result = subprocess.run([
                "python3", str(AGGREGATE), "--control-dir", str(pool)
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown keys ['confidence']", result.stdout)
            summary = json.loads((pool / "judge-summary.json").read_text())
            self.assertEqual(summary["samples_used"], 0)

    def test_aggregator_tolerates_judge_supplied_total(self):
        # The plain run-judge.sh prompt asks the judge to report "total" as
        # well; the aggregator recomputes it instead of rejecting the sample.
        with tempfile.TemporaryDirectory() as temp:
            pool = Path(temp)
            write(pool / "mapping-1.json", json.dumps({"candidate-A": ["alpha"]}))
            write(pool / "judge-1.txt", json.dumps({"scores": {"candidate-A": {
                "correctness": 4, "scope": 2, "compatibility": 2, "tests": 1, "total": 9
            }}}))
            subprocess.run([
                "python3", str(AGGREGATE), "--control-dir", str(pool)
            ], check=True, capture_output=True, text=True)
            summary = json.loads((pool / "judge-summary.json").read_text())
            self.assertEqual(summary["samples_used"], 1)
            self.assertEqual(summary["candidates"]["alpha"]["total_mean"], 9.0)

    def test_aggregator_names_missing_dimension(self):
        with tempfile.TemporaryDirectory() as temp:
            pool = Path(temp)
            write(pool / "mapping-1.json", json.dumps({"candidate-A": ["alpha"]}))
            write(pool / "judge-1.txt", json.dumps({"scores": {"candidate-A": {
                "correctness": 4, "scope": 2, "compatibility": 2
            }}}))
            result = subprocess.run([
                "python3", str(AGGREGATE), "--control-dir", str(pool)
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing dimensions ['tests']", result.stdout)

    def test_shell_runner_disables_all_judge_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "run"
            write(run / "control" / "alpha.diff", "+fix\n")
            write(run / "control" / "alpha.evaluator.status", "PASS\n")
            prompt = root / "prompt.txt"
            write(prompt, "Fix it.\n")
            args_file = root / "claude-args.json"
            fake = root / "claude"
            write(fake, """#!/usr/bin/env python3
import json, os, sys
open(os.environ['CLAUDE_ARGS_FILE'], 'w').write(json.dumps(sys.argv[1:]))
sys.stdin.read()
print('{"scores":{"candidate-A":{"correctness":4,"scope":2,"compatibility":2,"tests":2}}}')
""")
            fake.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(root) + os.pathsep + env["PATH"]
            env["CLAUDE_ARGS_FILE"] = str(args_file)
            subprocess.run([
                "bash", str(POOLED), "--pool-dir", str(root / "pool" / "control"),
                "--prompt", str(prompt), "--samples", "1", str(run),
            ], check=True, capture_output=True, text=True, env=env)
            args = json.loads(args_file.read_text())
            self.assertIn("--tools", args)
            self.assertEqual(args[args.index("--tools") + 1], "")
            self.assertIn("--disable-slash-commands", args)
            self.assertNotIn("--dangerously-skip-permissions", args)
            self.assertNotIn("--allowed-tools", args)

    def test_all_empty_pool_skips_claude(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "run"
            write(run / "control" / "empty.diff", "")
            prompt = root / "prompt.txt"
            write(prompt, "Fix it.\n")
            result = subprocess.run([
                "bash", str(POOLED), "--pool-dir", str(root / "pool" / "control"),
                "--prompt", str(prompt), "--samples", "3", str(run),
            ], check=True, capture_output=True, text=True, env={**os.environ, "PATH": "/usr/bin:/bin"})
            self.assertIn("skipped judge calls", result.stdout)
            summary = json.loads((root / "pool" / "control" / "judge-summary.json").read_text())
            self.assertEqual(summary["candidates"]["empty"]["total_mean"], 0.0)


if __name__ == "__main__":
    unittest.main()
