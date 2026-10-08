"""Behavioral tests for lab.py, run through its real command line."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

LAB = Path(__file__).with_name("lab.py")


class LabTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run_dir = self.root / "run"
        self.store = self.root / "store" / "knowledge.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def lab(self, *args, ok=(0,)):
        proc = subprocess.run([sys.executable, str(LAB), *map(str, args)], capture_output=True, text=True)
        self.assertIn(proc.returncode, ok, proc.stdout + proc.stderr)
        return proc

    def init(self, *extra, cycles=2, web=2, minutes=30):
        self.lab("init", self.run_dir, "--goal", "Does git worktree share hooks?", "--store", self.store,
                 "--max-cycles", cycles, "--max-web", web, "--max-minutes", minutes, *extra)

    def add(self, kind, record, ok=(0,)):
        return self.lab("add", self.run_dir, kind, json.dumps(record), ok=ok)

    def events(self):
        return [json.loads(l) for l in (self.run_dir / "log.jsonl").read_text().splitlines()]

    def test_web_and_cycle_limits_refuse_with_exit_3(self):
        self.init()
        self.lab("charge", self.run_dir, "web")
        self.lab("charge", self.run_dir, "web")
        refused = self.lab("charge", self.run_dir, "web", ok=(3,))
        self.assertIn("REFUSED web", refused.stderr)
        self.lab("charge", self.run_dir, "cycle", "--n", "2")
        self.lab("charge", self.run_dir, "cycle", ok=(3,))
        self.assertIn("budget_refused", [e["event"] for e in self.events()])
        self.assertIn("AUDIT OK", self.lab("audit", self.run_dir, "--observed-web", 2).stdout)

    def test_wall_clock_refuses_and_stops(self):
        self.init(minutes=0.02)
        time.sleep(1.5)
        self.assertIn("wall clock", self.lab("charge", self.run_dir, "web", ok=(3,)).stderr)
        self.assertIn("time spent", self.lab("check", self.run_dir, ok=(10,)).stderr)

    def test_stop_rule_all_resolved_and_stall(self):
        self.init("--max-stall", 1, cycles=5)
        self.add("claim", {"id": "C1", "text": "hooks are shared", "status": "open"})
        self.lab("check", self.run_dir)
        self.lab("charge", self.run_dir, "cycle")
        self.assertIn("stalled", self.lab("check", self.run_dir, ok=(10,)).stderr)
        self.add("claim", {"id": "C1", "text": "hooks are shared", "status": "supported"})
        self.assertIn("no open claims left", self.lab("check", self.run_dir, ok=(10,)).stderr)

    def test_validate_catches_unknown_source_and_brief_url(self):
        self.init()
        self.add("claim", {"id": "C1", "text": "t", "status": "supported"})
        self.add("source", {"id": "S1", "url": "https://git-scm.com/docs/githooks", "excerpt": "a quoted passage"})
        self.add("finding", {"id": "F1", "claim_ids": ["C1"], "source_ids": ["S9"], "statement": "s",
                             "confidence": "high", "uncertainty": "u"})
        out = self.lab("validate", self.run_dir, ok=(4,)).stdout
        self.assertIn("finding F1 cites unknown source S9", out)
        self.add("finding", {"id": "F1", "claim_ids": ["C1"], "source_ids": ["S1"], "statement": "s",
                             "confidence": "high", "uncertainty": "u"})
        (self.run_dir / "brief.md").write_text("See https://example.com/made-up and https://git-scm.com/docs/githooks.\n")
        self.assertIn("brief.md cites https://example.com/made-up", self.lab("validate", self.run_dir, ok=(4,)).stdout)
        (self.run_dir / "brief.md").write_text("See https://git-scm.com/docs/githooks.\n")
        self.assertIn("VALID", self.lab("validate", self.run_dir).stdout)

    def test_source_without_excerpt_is_rejected(self):
        self.init()
        err = self.add("source", {"id": "S1", "url": "https://x.org"}, ok=(2,)).stderr
        self.assertIn("excerpt", err)

    def test_audit_detects_tampering_and_undercounting(self):
        self.init()
        self.lab("charge", self.run_dir, "web")
        self.assertIn("ledger records 1 but 3 were observed",
                      self.lab("audit", self.run_dir, "--observed-web", 3, ok=(5,)).stdout)
        ledger = self.run_dir / "ledger.jsonl"
        ledger.write_text(ledger.read_text().replace('"n": 1', '"n": 0'))
        self.assertIn("hash chain", self.lab("audit", self.run_dir, ok=(5,)).stdout)

    def test_charge_rejects_nonpositive_n_and_audit_flags_it(self):
        self.init()
        for n in (0, -2):
            self.assertIn("at least 1", self.lab("charge", self.run_dir, "web", "--n", n, ok=(2,)).stderr)
        self.assertEqual(len((self.run_dir / "ledger.jsonl").read_text().splitlines()), 1)
        self.lab("charge", self.run_dir, "web")
        self.inject_charge(-2)
        self.assertIn("AUDIT FAIL charge seq 2 has n=-2", self.lab("audit", self.run_dir, ok=(5,)).stdout)

    def test_audit_rejects_non_integer_n_without_crashing(self):
        self.init()
        self.lab("charge", self.run_dir, "web")
        for bad, shown in (("1", "n='1'"), (True, "n=True"), (None, "n=None"), (1.5, "n=1.5")):
            self.inject_charge(bad)
            self.assertIn(f"AUDIT FAIL charge seq 2 has {shown}", self.lab("audit", self.run_dir, ok=(5,)).stdout)

    def inject_charge(self, n):
        """Replace the ledger tail with a charge of n, re-chained with a matching log head (a deliberate rewrite)."""
        ledger = self.run_dir / "ledger.jsonl"
        entries = [json.loads(l) for l in ledger.read_text().splitlines()][:2]
        entries.append(dict(entries[-1], n=n, seq=2))
        prev, lines = hashlib.sha256((self.run_dir / "budget.json").read_bytes()).hexdigest(), []
        for entry in entries:
            lines.append(json.dumps(dict(entry, prev=prev), ensure_ascii=False, sort_keys=True))
            prev = hashlib.sha256(lines[-1].encode()).hexdigest()
        ledger.write_text("\n".join(lines) + "\n")
        with (self.run_dir / "log.jsonl").open("a") as log:
            log.write(json.dumps({"phase": "act", "event": "budget_charged", "ts": "t",
                                  "data": {"ledger_head": prev}}) + "\n")

    def test_unresolved_is_not_progress(self):
        self.init("--max-stall", 1, cycles=5)
        for cid in ("C1", "C2", "C3"):
            self.add("claim", {"id": cid, "text": "t", "status": "open"})
        self.lab("charge", self.run_dir, "cycle")
        self.add("claim", {"id": "C1", "text": "t", "status": "unresolved"})
        self.assertIn("stalled", self.lab("check", self.run_dir, ok=(10,)).stderr)
        self.add("claim", {"id": "C2", "text": "t", "status": "supported"})
        status = json.loads(self.lab("check", self.run_dir).stdout)
        self.assertEqual(status["claims"], {"open": 1, "resolved": 1, "unresolved": 1})
        self.add("claim", {"id": "C3", "text": "t", "status": "unresolved"})
        self.assertIn("no open claims left (1 resolved, 2 unresolved)",
                      self.lab("check", self.run_dir, ok=(10,)).stderr)

    def test_knowledge_round_trip_between_runs(self):
        self.init()
        self.add("claim", {"id": "C1", "text": "t", "status": "supported"})
        self.add("source", {"id": "S1", "url": "https://git-scm.com/docs/githooks",
                            "excerpt": "hooks live in $GIT_COMMON_DIR/hooks"})
        self.add("finding", {"id": "F1", "claim_ids": ["C1"], "source_ids": ["S1"], "confidence": "high",
                             "statement": "Linked worktrees share the hooks directory", "uncertainty": "u"})
        out = self.add("knowledge", {"kind": "finding", "finding_ids": ["F1"], "confidence": "high",
                                     "statement": "Linked worktrees share the hooks directory",
                                     "tags": ["git", "worktree", "hooks"]}).stdout
        kid = out.split()[2]
        stored = json.loads(self.store.read_text().splitlines()[0])
        self.assertEqual(stored["sources"][0]["url"], "https://git-scm.com/docs/githooks")
        second = self.run_dir
        self.run_dir = self.root / "run2"
        self.lab("init", self.run_dir, "--goal", "Can one worktree use different hooks?", "--store", self.store,
                 "--max-cycles", 1, "--max-web", 1, "--max-minutes", 5)
        self.add("claim", {"id": "C1", "text": "t", "status": "supported"})
        self.add("source", {"id": "S1", "url": stored["sources"][0]["url"], "excerpt": "hooks live in x",
                            "via": kid})
        self.add("finding", {"id": "F1", "claim_ids": ["C1"], "source_ids": ["S1"], "confidence": "high",
                             "statement": "s", "uncertainty": "u"})
        self.assertIn("no recall in this run surfaced it", self.lab("validate", self.run_dir, ok=(4,)).stdout)
        recalled = json.loads(self.lab("recall", self.run_dir).stdout)
        self.assertEqual([e["id"] for e in recalled], [kid])
        self.assertEqual(self.events()[-1]["data"]["surfaced"], [kid])
        self.lab("validate", self.run_dir)
        self.assertNotEqual(second, self.run_dir)

    def test_store_must_be_outside_run(self):
        self.lab("init", self.run_dir, "--goal", "g", "--store", self.run_dir / "k.jsonl", "--max-cycles", 1,
                 "--max-web", 1, "--max-minutes", 1, ok=(2,))


if __name__ == "__main__":
    unittest.main()
