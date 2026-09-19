#!/usr/bin/env python3
"""Fold several single-task benchmark runs into one quality-and-cost grid.

Reads each run's control/ directory and joins three facts per cell: whether the
hidden gate passed, what the blind judge scored it, and what it cost. Quality
is reported gate-first — a candidate that fails the deterministic gate is
wrong, however well it reads, so its judge score is shown but never used to
rank it above a passing one.
"""
import argparse
import json
import os
import statistics


def load_run(bench_dir):
    control = os.path.join(bench_dir, "control")
    with open(os.path.join(control, "meta.json")) as f:
        meta = json.load(f)
    task = meta["task_id"]
    judge = {}
    jpath = os.path.join(control, "judge-summary.json")
    if os.path.exists(jpath):
        with open(jpath) as f:
            judge = json.load(f).get("candidates", {})
    cells = {}
    for cand in list(meta["candidates"]) + ["human"]:
        def read(suffix, default=None):
            p = os.path.join(control, "%s.%s" % (cand, suffix))
            try:
                with open(p) as f:
                    return f.read().strip()
            except OSError:
                return default
        cost = {}
        cpath = os.path.join(control, "%s.cost.json" % cand)
        if os.path.exists(cpath):
            with open(cpath) as f:
                cost = json.load(f)
        j = judge.get(cand, {})
        if cand == "human" and not j:
            continue
        cells[cand] = {
            "gate": read("evaluator.status"),
            "run_status": read("run.status"),
            "seconds": read("seconds"),
            "judge_mean": j.get("total_mean"),
            "judge_stdev": j.get("total_stdev"),
            "usd": cost.get("usd"),
            "total_tokens": cost.get("total_tokens"),
            "model_calls": cost.get("model_calls"),
        }
    return task, cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="benchmark run directories")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    runs = [load_run(r) for r in args.runs]
    tasks = [t for t, _ in runs]
    cands = []
    for _, cells in runs:
        for c in cells:
            if c not in cands:
                cands.append(c)

    lines = []
    def w(s=""):
        lines.append(s)

    w("# Quality and cost grid")
    w()
    w("Tasks: " + ", ".join(tasks))
    w()

    w("## Gate (hidden test + typecheck)")
    w()
    w("| candidate | " + " | ".join(tasks) + " | passed |")
    w("|---|" + "---|" * (len(tasks) + 1))
    for c in cands:
        row, passed = [], 0
        for _, cells in runs:
            g = (cells.get(c) or {}).get("gate")
            row.append({"PASS": "PASS", "FAIL": "fail"}.get(g, "--"))
            passed += 1 if g == "PASS" else 0
        w("| %s | %s | %d/%d |" % (c, " | ".join(row), passed, len(tasks)))
    w()

    w("## Blind judge score (mean of samples, out of 10)")
    w()
    w("| candidate | " + " | ".join(tasks) + " | mean |")
    w("|---|" + "---|" * (len(tasks) + 1))
    for c in cands:
        row, vals = [], []
        for _, cells in runs:
            v = (cells.get(c) or {}).get("judge_mean")
            row.append("--" if v is None else "%.1f" % v)
            if v is not None:
                vals.append(v)
        w("| %s | %s | %s |" % (c, " | ".join(row),
                                "%.1f" % statistics.mean(vals) if vals else "--"))
    w()

    w("## Cost (USD at list prices, proxy for consumption)")
    w()
    w("| candidate | " + " | ".join(tasks) + " | total |")
    w("|---|" + "---|" * (len(tasks) + 1))
    for c in cands:
        if c == "human":
            continue
        row, tot = [], 0.0
        for _, cells in runs:
            v = (cells.get(c) or {}).get("usd")
            row.append("--" if v is None else "%.3f" % v)
            tot += v or 0.0
        w("| %s | %s | %.3f |" % (c, " | ".join(row), tot))
    w()

    w("## Quality per dollar (mean judge score / total USD)")
    w()
    w("| candidate | gate passed | judge mean | total USD | score per $ |")
    w("|---|---|---|---|---|")
    for c in cands:
        if c == "human":
            continue
        vals, tot, passed = [], 0.0, 0
        for _, cells in runs:
            cell = cells.get(c) or {}
            if cell.get("judge_mean") is not None:
                vals.append(cell["judge_mean"])
            tot += cell.get("usd") or 0.0
            passed += 1 if cell.get("gate") == "PASS" else 0
        m = statistics.mean(vals) if vals else None
        w("| %s | %d/%d | %s | %.3f | %s |" % (
            c, passed, len(tasks), "--" if m is None else "%.1f" % m, tot,
            "--" if (m is None or tot == 0) else "%.0f" % (m / tot)))
    w()

    w("## Run outcomes and wall clock")
    w()
    w("| candidate | " + " | ".join("%s status / s" % t for t in tasks) + " |")
    w("|---|" + "---|" * len(tasks))
    for c in cands:
        if c == "human":
            continue
        row = []
        for _, cells in runs:
            cell = cells.get(c) or {}
            row.append("%s / %s" % (cell.get("run_status") or "--", cell.get("seconds") or "--"))
        w("| %s | %s |" % (c, " | ".join(row)))

    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print("wrote " + args.out)
    print(text)


if __name__ == "__main__":
    main()
