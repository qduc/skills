"""Behavioral tests for lab.py. Run: python3 -m unittest discover -s skills/research-lab/scripts"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).with_name("lab.py")


def lab(*args, stdin: str | None = None):
    return subprocess.run([sys.executable, str(LAB), *map(str, args)], input=stdin,
                          capture_output=True, text=True)


class LabTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.run = self.tmp / "r1"
        self.kb = self.tmp / "kb"
        self.assertEqual(lab("init", self.run, "--goal", "Q?", "--max-searches", 2,
                             "--kb", self.kb).returncode, 0)

    def snap(self, text="Multi-agent beat single-agent by 90.2% on our eval.", typ="primary"):
        out = lab("snapshot", self.run, "--url", "https://x.test/a", "--title", "A",
                  "--type", typ, stdin=text)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.split()[1]

    def test_budget_stops_predictably(self):
        self.assertEqual(lab("charge", self.run, "search").returncode, 0)
        self.assertEqual(lab("charge", self.run, "search").returncode, 0)
        out = lab("charge", self.run, "search")
        self.assertEqual(out.returncode, 3)
        meta = json.loads((self.run / "run.json").read_text())
        self.assertEqual(meta["status"], "STOPPED")
        self.assertEqual(meta["spent"]["search"], 2)  # refused charge not counted
        # no further acting allowed, but verify/report still work
        self.assertEqual(lab("claim-add", self.run, "x").returncode, 3)
        self.assertEqual(lab("report", self.run).returncode, 0)

    def test_open_key_claim_fails_verify(self):
        lab("claim-add", self.run, "Multi-agent wins", "--key")
        out = lab("verify", self.run)
        self.assertEqual(out.returncode, 2)
        self.assertIn("ISSUE coverage: C1 key claim still open", out.stdout)
        self.assertIn("ISSUE challenge: C1 key claim never challenged", out.stdout)

    def test_fabricated_quote_is_caught(self):
        lab("claim-add", self.run, "Multi-agent wins", "--key")
        s = self.snap()
        out = lab("evidence", self.run, "C1", "--snapshot", s, "--stance", "supports",
                  "--quote", "beat single-agent by 95%")
        self.assertIn("ISSUE quote not found", out.stdout)
        lab("claim-set", self.run, "C1", "--status", "supported", "--confidence", "medium")
        lab("challenge", self.run, "C1", "--query", "q", "--found", "no")
        v = lab("verify", self.run)
        self.assertEqual(v.returncode, 2)
        self.assertIn("quote not found in S1", v.stdout)
        self.assertIn("supported without verified evidence", v.stdout)

    def scan(self):
        self.assertEqual(lab("scan", self.run, "--query", "survey", "--lineages", "a; b").returncode, 0)

    def test_full_pass_report_and_learn(self):
        self.scan()
        lab("claim-add", self.run, "Multi-agent wins", "--key")
        self.scan()
        s = self.snap("Header\n**Multi-agent beat**   single-agent by 90.2% on our eval.\n")
        lab("evidence", self.run, "C1", "--snapshot", s, "--stance", "supports",
            "--quote", "multi-agent beat single-agent by 90.2%")
        lab("challenge", self.run, "C1", "--query", "multi-agent worse", "--found", "no")
        lab("claim-set", self.run, "C1", "--status", "supported", "--confidence", "high")
        (self.run / "synthesis.md").write_text(
            "## Answer\nYes.\n\n## Follow-up questions\n- Does it hold at equal tokens?\n")
        (self.run / "lessons.md").write_text("- vendor evals need independent replication\n")
        self.assertEqual(lab("verify", self.run).returncode, 0, lab("verify", self.run).stdout)
        self.assertEqual(lab("report", self.run).returncode, 0)
        report = (self.run / "findings.md").read_text()
        self.assertNotIn("DRAFT", report)
        self.assertIn("Multi-agent wins", report)
        out = lab("learn", self.run)
        self.assertIn("promoted=1 questions=1", out.stdout)
        # idempotent promotion
        self.assertIn("promoted=0", lab("learn", self.run).stdout)
        hit = lab("kb-search", self.kb, "multi-agent", "--lessons")
        self.assertIn("[supported/high] Multi-agent wins", hit.stdout)
        self.assertIn("LESSON", hit.stdout)

    def test_high_confidence_needs_primary_and_contradiction_needs_note(self):
        self.scan()
        lab("claim-add", self.run, "X", "--key")
        self.scan()
        s1 = self.snap("blog says X is true", typ="secondary")
        s2 = self.snap("study finds X is false", typ="primary")
        lab("evidence", self.run, "C1", "--snapshot", s1, "--stance", "supports", "--quote", "X is true")
        lab("evidence", self.run, "C1", "--snapshot", s2, "--stance", "contradicts", "--quote", "X is false")
        lab("challenge", self.run, "C1", "--query", "q", "--found", "yes")
        lab("claim-set", self.run, "C1", "--status", "supported", "--confidence", "high")
        out = lab("verify", self.run).stdout
        self.assertIn("high confidence without primary source", out)
        self.assertIn("supported despite contradicting E2", out)
        lab("claim-set", self.run, "C1", "--status", "contested", "--confidence", "low")
        self.assertEqual(lab("verify", self.run).returncode, 0)

    def test_breadth_requires_scan_before_and_after_decomposition(self):
        lab("claim-add", self.run, "X", "--key")
        out = lab("verify", self.run).stdout
        self.assertIn("written before any breadth scan", out)
        self.assertIn("no final gap-check", out)
        self.scan()
        out = lab("verify", self.run).stdout
        self.assertIn("written before any breadth scan", out)
        self.assertNotIn("no final gap-check", out)

    def test_elided_quote_matches_in_order(self):
        lab("claim-add", self.run, "Y")
        s = self.snap("alpha beta gamma delta epsilon")
        out = lab("evidence", self.run, "C1", "--snapshot", s, "--stance", "context",
                  "--quote", "alpha beta ... epsilon")
        self.assertNotIn("ISSUE", out.stdout)
        out = lab("evidence", self.run, "C1", "--snapshot", s, "--stance", "context",
                  "--quote", "epsilon ... alpha")
        self.assertIn("ISSUE", out.stdout)


if __name__ == "__main__":
    unittest.main()
