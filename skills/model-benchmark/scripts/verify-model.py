#!/usr/bin/env python3
"""Confirm each run actually used the model it was asked for.

pi fuzzy-matches model ids and will silently resolve an unknown one to a
different model on the same provider; a run then looks fine and measures the
wrong thing. This checks the model recorded in the run's own output and fails
loudly on a mismatch.
"""
import argparse
import glob
import json
import os
import re
import sys


def models_in_pi_log(path):
    found = set()
    with open(path, errors="replace") as f:
        for line in f:
            for m in re.findall(r'"model":"([^"]+)"', line):
                found.add(m)
    return found


def models_in_codex_log(path):
    found = set()
    with open(path, errors="replace") as f:
        for line in f:
            for m in re.findall(r'"model":\s*"([^"]+)"', line):
                found.add(m)
    return found


def models_in_term2_traffic(traffic_root, start, end):
    import calendar, time
    found = set()
    if not os.path.isdir(traffic_root):
        return found
    for day in os.listdir(traffic_root):
        day_dir = os.path.join(traffic_root, day)
        if not os.path.isdir(day_dir):
            continue
        for session in os.listdir(day_dir):
            try:
                started = calendar.timegm(
                    time.strptime(day + " " + session.split("_", 1)[0], "%Y-%m-%d %H-%M-%S"))
            except ValueError:
                continue
            if not (start - 2 <= started <= end):
                continue
            for f in glob.glob(os.path.join(day_dir, session, "*.json")):
                try:
                    rec = json.load(open(f))
                except (json.JSONDecodeError, OSError):
                    continue
                m = (rec.get("received") or {}).get("model")
                if m:
                    found.add(m)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark-dir", required=True)
    ap.add_argument("--term2-traffic-root",
                    default=os.path.expanduser("~/.local/state/term2-nodejs/logs/provider-traffic"))
    args = ap.parse_args()
    control = os.path.join(args.benchmark_dir, "control")
    meta = json.load(open(os.path.join(control, "meta.json")))

    bad = []
    for cand in meta["candidates"]:
        spec = meta["candidate_specs"][cand]
        want = spec.get("model_id")
        harness = spec["harness"]
        log = os.path.join(control, "%s.run.log" % cand)
        seen = set()
        if harness == "pi" and os.path.exists(log):
            seen = models_in_pi_log(log)
        elif harness == "codex" and os.path.exists(log):
            seen = models_in_codex_log(log)
        elif harness.startswith("term2"):
            try:
                start = float(open(os.path.join(control, "%s.start_epoch" % cand)).read())
                end = float(open(os.path.join(control, "%s.end_epoch" % cand)).read())
            except OSError:
                start = end = 0
            seen = models_in_term2_traffic(args.term2_traffic_root, start, end)
        status = "OK" if want in seen else ("NO DATA" if not seen else "MISMATCH")
        if status == "MISMATCH":
            bad.append(cand)
        print("%-16s want=%-20s seen=%-40s %s"
              % (cand, want, ",".join(sorted(seen))[:40] or "-", status))
    if bad:
        print("\nMISMATCH in: %s" % ", ".join(bad), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
