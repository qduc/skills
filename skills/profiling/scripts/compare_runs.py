#!/usr/bin/env python3
"""Compare baseline vs after run values for one metric (stdlib only).

usage: compare_runs.py BASELINE_FILE AFTER_FILE [--higher-is-better]
Each file: one numeric observation per line (raw runs, not summaries).
Prints n, median, min-max spread per side, absolute delta, and relative change
using (baseline - after) / baseline * 100% for lower-is-better metrics
(after - baseline for higher-is-better). Exit 2 if either side has < 2 runs:
one run is exploratory evidence, never a percentage-improvement proof.
Exit 3 if the run ranges overlap (change not separated from noise; report as uncertain).
"""
import statistics, sys

def load(p):
    return [float(x) for x in open(p).read().split() if x.strip()]

def main(a):
    hib = "--higher-is-better" in a
    a = [x for x in a if not x.startswith("--")]
    if len(a) != 2: print(__doc__); return 64
    b, c = load(a[0]), load(a[1])
    for name, v in (("baseline", b), ("after", c)):
        print(f"{name}: n={len(v)} median={statistics.median(v) if v else 'NA'} range={min(v) if v else 'NA'}..{max(v) if v else 'NA'}")
    if len(b) < 2 or len(c) < 2:
        print("FAIL: need >=2 runs per side; single run is exploratory only"); return 2
    mb, mc = statistics.median(b), statistics.median(c)
    delta = mc - mb
    if mb == 0: print(f"absolute delta={delta}; relative change undefined (baseline 0)")
    else:
        rel = ((mc - mb) if hib else (mb - mc)) / mb * 100
        print(f"absolute delta={delta:+g}; relative improvement={rel:+.1f}%")
    if max(min(b), min(c)) <= min(max(b), max(c)):
        print("WARN: run ranges overlap; investigate variance before claiming a change"); return 3
    print("OK: ranges separated"); return 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
