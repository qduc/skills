#!/usr/bin/env python3
"""Break each candidate's evaluator run down to per-test pass/fail.

A binary PASS/FAIL hides the difference between a candidate that solved none of
the reported problems and one that solved all but a corner of one. When a task
bundles two independent failures, that difference is most of the signal.
"""
import argparse
import glob
import json
import os
import re

LINE = re.compile(r"^\s*(?P<mark>[✓×])\s+(?P<path>\S+\.ts)\s*>\s*(?P<name>.+?)(?:\s+\d+ms)?\s*$")


def parse(path):
    results = {}
    with open(path, errors="replace") as f:
        for line in f:
            m = LINE.match(line.rstrip())
            if m:
                results[m.group("name").strip()] = (m.group("mark") == "✓")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark-dir", required=True)
    args = ap.parse_args()
    control = os.path.join(args.benchmark_dir, "control")
    with open(os.path.join(control, "meta.json")) as f:
        meta = json.load(f)

    table, names = {}, []
    for cand in meta["candidates"]:
        p = os.path.join(control, "%s.evaluator.txt" % cand)
        if not os.path.exists(p):
            continue
        r = parse(p)
        table[cand] = r
        for n in r:
            if n not in names:
                names.append(n)

    if not names:
        print("no per-test lines found (verify.sh task, or evaluator not run yet)")
        return

    with open(os.path.join(control, "per-test.json"), "w") as f:
        json.dump({"tests": names, "candidates": table}, f, indent=2)

    width = max(len(c) for c in table) + 1
    for i, n in enumerate(names):
        print("%2d. %s" % (i + 1, n))
    print()
    print("%-*s %s" % (width, "candidate", " ".join("%2d" % (i + 1) for i in range(len(names)))))
    for cand, r in table.items():
        cells = []
        for n in names:
            v = r.get(n)
            cells.append(" ." if v is None else (" +" if v else " -"))
        passed = sum(1 for n in names if r.get(n))
        print("%-*s %s   %d/%d" % (width, cand, " ".join(cells), passed, len(names)))


if __name__ == "__main__":
    main()
