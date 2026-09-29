#!/usr/bin/env python3
"""Rotate candidate selections across worker pools; callers verify before dispatch.

Left to memory, dispatches stack on one well-known pool until its quota or
context runs out. This helper makes the rotation mechanical: it picks the
candidate pool that has gone longest without a recorded pick (never-picked first,
input order breaking ties). It does not check quotas or availability. Use
--dry-run to inspect a candidate without updating history; after checking it,
run again without --dry-run to record the rotation, excluding unavailable pools.
--inventory is optional metadata and is not validated beyond file existence.

Usage:
  coord_route.py pick --pool NAME [--pool ...] --history FILE
                  [--exclude NAME ...] [--inventory PATH] [--dry-run]

Prints one JSON line with the chosen candidate and exits 0. Errors (no candidate,
missing specified inventory, corrupt history) print `{"error": ...}` and exit 1.
Dry runs do not write; confirmed picks update the history file.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone


def load_history(path):
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {"picks": []}
    except (json.JSONDecodeError, OSError):
        raise SystemExit(error_line("corrupt_history", history=str(path)))
    picks = data.get("picks")
    if not isinstance(picks, list) or any(not isinstance(p, dict) or "pool" not in p for p in picks):
        raise SystemExit(error_line("corrupt_history", history=str(path)))
    return {"picks": picks}


def error_line(code, **extra):
    return json.dumps({"error": code, **extra})


def save_history(path, data):
    path = Path(path)
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".route-history-")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def cmd_pick(a):
    if a.inventory and not Path(a.inventory).is_file():
        print(error_line("missing_inventory", inventory=a.inventory))
        return 1
    pools = list(dict.fromkeys(a.pool))
    available = [p for p in pools if p not in set(a.exclude)]
    if not available:
        print(error_line("no_available_pool", pools=pools, excluded=a.exclude))
        return 1
    history = load_history(a.history)
    last = {}
    for pick in history["picks"]:
        last[pick["pool"]] = pick.get("at", "")
    chosen = min(available, key=lambda p: (last.get(p, ""), available.index(p)))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not a.dry_run:
        history["picks"].append({"pool": chosen, "at": now})
        save_history(a.history, history)
    counts = {}
    for pick in history["picks"]:
        counts[pick["pool"]] = counts.get(pick["pool"], 0) + 1
    print(json.dumps({
        "event": "candidate" if a.dry_run else "pick", "pool": chosen, "at": now, "counts": counts,
        "excluded": a.exclude,
        "inventory": a.inventory,
        "quota_check": "caller must verify quota and availability before dispatch",
    }))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pick = sub.add_parser("pick", help="choose the least-recently-used available pool")
    pick.add_argument("--pool", action="append", required=True, help="candidate pool, in preferred order")
    pick.add_argument("--history", required=True, help="rotation history file (keep beside the task record)")
    pick.add_argument("--exclude", action="append", default=[], help="pool to skip (quota exhausted, unavailable)")
    pick.add_argument("--inventory", help="optional host inventory path; fails if specified but missing")
    pick.add_argument("--dry-run", action="store_true", help="show candidate without recording it")
    pick.set_defaults(func=cmd_pick)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
