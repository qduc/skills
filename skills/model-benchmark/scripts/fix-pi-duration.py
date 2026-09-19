#!/usr/bin/env python3
"""Recover pi's real wall clock, which its exit code misreports.

pi --print can finish its work, emit `agent_settled`, and then keep the process
alive; the runner's `timeout` kills it and records TIMEOUT for a run that
actually completed minutes earlier. Both the status and the duration are wrong,
and the edits on disk are complete either way.

The last event timestamp in the JSONL is when pi actually stopped working, so
that is what gets recorded as the effective duration.
"""
import argparse
import json
import os


def last_timestamp_ms(path):
    latest = None
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            for ts in _timestamps(ev):
                if latest is None or ts > latest:
                    latest = ts
    return latest


def _timestamps(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "timestamp" and isinstance(v, (int, float)) and v > 1e12:
                yield v
            else:
                yield from _timestamps(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _timestamps(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark-dir", required=True)
    args = ap.parse_args()
    control = os.path.join(args.benchmark_dir, "control")
    with open(os.path.join(control, "meta.json")) as f:
        meta = json.load(f)

    for cand in meta["candidates"]:
        if meta["candidate_specs"][cand]["harness"] != "pi":
            continue
        log = os.path.join(control, "%s.run.log" % cand)
        start_path = os.path.join(control, "%s.start_epoch" % cand)
        # A run still in flight has a log but no epoch marker yet.
        if not (os.path.exists(log) and os.path.exists(start_path)):
            continue
        with open(log, errors="replace") as f:
            settled = "agent_settled" in f.read()
        with open(start_path) as f:
            start = float(f.read().strip())
        end_ms = last_timestamp_ms(log)
        eff = int(end_ms / 1000 - start) if end_ms else None

        with open(os.path.join(control, "%s.settled" % cand), "w") as f:
            f.write("yes" if settled else "no")
        if eff is not None and eff > 0:
            with open(os.path.join(control, "%s.effective_seconds" % cand), "w") as f:
                f.write(str(eff))
        status_path = os.path.join(control, "%s.run.status" % cand)
        with open(status_path) as f:
            status = f.read().strip()
        if settled and status == "TIMEOUT":
            with open(status_path, "w") as f:
                f.write("OK_LINGERED")
            status = "OK_LINGERED"
        with open(os.path.join(control, "%s.seconds" % cand)) as f:
            raw = f.read().strip()
        print("%-14s settled=%-3s status=%-12s raw=%ss effective=%ss"
              % (cand, "yes" if settled else "no", status, raw, eff))


if __name__ == "__main__":
    main()
