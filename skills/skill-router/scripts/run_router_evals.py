#!/usr/bin/env python3
"""Run the router evals through a model and report which cases route wrong.

usage: run_router_evals.py [--model M] [--runs N] [--ids 5,12] [--jobs J]

check_router.py proves every exit exists and is tested. It cannot tell whether
a case is reachable, because that depends on reading the rows top to bottom and
taking the first match: a general row placed early silently answers cases meant
for a narrower row below it. This script asks a model to do exactly that
reading for each eval prompt, with the router as its only instructions, and
compares the exit it picks with expected_exit (or an also_ok alternative,
for the few cases on a genuinely fuzzy boundary).

Each call runs `claude -p` with no tools, in an empty temporary directory, so
no skills, repo files, or instruction files influence the answer. Exits 1 when
any case misses in any run. Costs one model call per case per run.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROUTER_DIR = Path(__file__).resolve().parents[1]
ANSWER = re.compile(r"EXIT:\s*(.+)", re.IGNORECASE)
CHAIN = re.compile(r"\s*(?:→|->)\s*")

INSTRUCTIONS = """You are testing a skill router. The router document follows.
Apply its Route section to the user's request exactly as written: top to bottom,
first matching row wins. Do not do the request and do not explain.
Reply with one line only:
EXIT: <exit>
where <exit> is none, one skill slug, or a chain written as a → b.

--- ROUTER ---
"""


def normalize(exit_: str) -> str:
    exit_ = exit_.strip().strip("`*. ").replace("`", "")
    exit_ = re.sub(r"^chain\s+", "", exit_, flags=re.IGNORECASE)
    return " → ".join(p.strip() for p in CHAIN.split(exit_) if p.strip())


def parse(output: str) -> str:
    found = ANSWER.findall(output)
    return normalize(found[-1]) if found else "?"


def claude_runner(model: str | None):
    def run(system: str, prompt: str) -> str:
        cmd = ["claude", "-p", prompt, "--system-prompt", system,
               "--tools", "", "--no-session-persistence"]
        if model:
            cmd += ["--model", model]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        with tempfile.TemporaryDirectory() as empty:
            done = subprocess.run(cmd, capture_output=True, text=True,
                                  cwd=empty, env=env, timeout=300)
        return done.stdout if done.returncode == 0 else f"ERROR: {done.stderr.strip()[:200]}"
    return run


def evaluate(cases, router_text, run, runs=1, jobs=4):
    """Return [(case, [picked exit per run])]."""
    system = INSTRUCTIONS + router_text
    work = [(c, i) for c in cases for i in range(runs)]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        picked = list(pool.map(lambda w: parse(run(system, w[0]["prompt"])), work))
    results = {}
    for (case, _), exit_ in zip(work, picked):
        results.setdefault(case["id"], (case, []))[1].append(exit_)
    return [results[c["id"]] for c in cases]


def report(results) -> int:
    misses = 0
    for case, picked in results:
        want = normalize(case["expected_exit"])
        ok = {want} | {normalize(a) for a in case.get("also_ok", [])}
        hits = sum(p in ok for p in picked)
        if hits < len(picked):
            misses += 1
            wrong = ", ".join(sorted({p for p in picked if p not in ok}))
            print(f"MISS {case['id']:>3} {hits}/{len(picked)}  want {want}  got {wrong}")
            print(f"         {case['prompt']}")
    total = len(results)
    print(f"{total - misses}/{total} cases routed as expected in every run")
    return 1 if misses else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", help="model alias or name passed to claude")
    ap.add_argument("--runs", type=int, default=1, help="runs per case (default 1)")
    ap.add_argument("--ids", help="comma-separated eval ids to run")
    ap.add_argument("--jobs", type=int, default=4, help="parallel calls (default 4)")
    args = ap.parse_args(argv)
    cases = json.loads((ROUTER_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))["evals"]
    if args.ids:
        keep = {int(i) for i in args.ids.split(",")}
        cases = [c for c in cases if c["id"] in keep]
    router_text = (ROUTER_DIR / "SKILL.md").read_text(encoding="utf-8")
    results = evaluate(cases, router_text, claude_runner(args.model), args.runs, args.jobs)
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
