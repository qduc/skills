#!/usr/bin/env python3
"""Wake the coordinator when Herdr workers report or stall, without missing any.

A report-file wait alone misses workers that end their turn without writing
the report, and a watcher that only compares against its own start time
misses reports that land while the coordinator is busy. This watcher keeps a
persistent read/unread state file instead:

  * A report is UNREAD until `mark-read` records that exact version (mtime and
    size). A rewritten report becomes unread again.
  * Unread reports fire immediately on start, so reports that arrived between
    watcher runs are never lost.
  * A wake lists every event at once, one JSON object per line, after a
    `wake` header with the current local time, when the watch started, and
    how long it waited. Report events carry the report's modified time and
    age; stall/no_progress events carry since-when and for-how-long.

Events:
  report       a worker's report is unread
  stall        a worker stayed non-working (idle/done/blocked/unknown) for
               --idle-grace seconds with no unread report — including a
               lifecycle `done`/`idle` whose expected report never landed.
               Status is debounced (majority of the last --debounce samples)
               because Herdr flips. When the pane shows an upstream provider
               error (`service_unavailable_error` and the TUI's `Use
               /retry-turn` hint), the stall carries a `hint`; resume that
               worker by steering `/retry-turn` + Enter at its idle prompt.
  no_progress  a worker reported `working` but its visible footer (token
               counters) did not change for --stall-minutes
  gone         the pane no longer exists (drop it from --worker once handled)
  timeout      --timeout-minutes elapsed with no event

Usage:
  watch_workers.py watch --state S --worker PANE=REPORT [--worker ...]
      [--worker-progress PANE=PATH ...]
  watch_workers.py unread --state S --worker PANE=REPORT [--worker ...]
  watch_workers.py mark-read --state S REPORT [REPORT ...]

Mark a report read only after you have actually read it; seeing the wake is
not reading. Read-only toward workers: it only runs `herdr agent get` and
`herdr pane read`, and writes nothing but the state file.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter, deque
from datetime import datetime


def herdr(*args):
    try:
        out = subprocess.run(["herdr", *args], capture_output=True, text=True, timeout=20)
        return out.stdout
    except Exception:
        return ""


# term2's footer hint: "⏎ steer │ Alt+⏎ queue" while a turn runs,
# "/ commands │ @ paths" at rest. Other harnesses fall back to activity words.
BUSY = re.compile(r"⏎ steer|Generating|Calling tool|Processing|Thinking")


def status(pane):
    raw = herdr("agent", "get", pane)
    try:
        return json.loads(raw)["result"]["agent"].get("agent_status", "unknown")
    except Exception:
        pass
    # Herdr can lose agent classification for a live pane (agent_not_found).
    # Fall back to the pane itself: gone only if it can no longer be read.
    text = herdr("pane", "read", pane, "--source", "visible", "--lines", "12")
    if not text.strip():
        return None
    return "working" if BUSY.search(text) else "idle"


# An upstream/provider failure parks the worker idle at its prompt with the
# TUI's own hint. Anchor to that phrasing, not a generic error word.
UPSTREAM_ERROR = re.compile(r"service_unavailable_error|/retry-turn", re.I)


def error_hint(pane):
    """Matched upstream-error phrase in the visible pane text, or None."""
    match = UPSTREAM_ERROR.search(
        herdr("pane", "read", pane, "--source", "visible", "--lines", "12"))
    return match.group(0) if match else None


FOOTER = re.compile(r"↑[\d.]+k ↓[\d.]+k?")


def footer(pane):
    text = herdr("pane", "read", pane, "--source", "visible", "--lines", "12")
    found = FOOTER.findall(text)
    return found[-1] if found else text[-200:]


def stamp(t):
    """Local wall-clock time with offset, to the second."""
    return datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def span(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def fingerprint(path):
    """Version of a report file, or None when it does not exist."""
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return None
    return f"{st.st_mtime_ns}:{st.st_size}"


def progress_fingerprint(paths):
    """Fingerprint git commits/edits and named output files for stall detection."""
    digest = hashlib.sha256()
    for raw in sorted(paths):
        path = os.path.abspath(raw)
        digest.update(path.encode())
        if os.path.isdir(path):
            try:
                result = subprocess.run(["git", "-C", path, "status", "--porcelain", "--untracked-files=all"],
                                        capture_output=True, text=True, timeout=10)
                head = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and head.returncode == 0:
                    digest.update(head.stdout.encode())
                    digest.update(result.stdout.encode())
                    continue
                for root, directories, files in os.walk(path):
                    directories[:] = sorted(d for d in directories if d not in {'.git', 'node_modules', '.venv'})
                    for name in sorted(files):
                        item = os.path.join(root, name)
                        try:
                            stat = os.stat(item)
                            digest.update(f'{item}:{stat.st_mtime_ns}:{stat.st_size}'.encode())
                        except OSError:
                            pass
            except (OSError, subprocess.SubprocessError):
                digest.update(b'unavailable')
        else:
            digest.update((fingerprint(path) or 'missing').encode())
    return digest.hexdigest()


def load_state(path):
    try:
        with open(path) as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {"read": {}}
    data.setdefault("read", {})
    return data


def save_state(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".watch-state-")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def parse_workers(specs):
    workers = {}
    for spec in specs:
        pane, report = spec.split("=", 1)
        workers[pane] = os.path.abspath(report)
    return workers


def parse_worker_progress(specs, workers):
    progress = {pane: [] for pane in workers}
    for spec in specs:
        pane, path = spec.split("=", 1)
        if pane not in progress:
            raise ValueError(f"progress path has no matching worker: {pane}")
        progress[pane].append(path)
    return progress


def unread_reports(state_path, workers):
    read = load_state(state_path)["read"]
    events = []
    for pane, report in workers.items():
        fp = fingerprint(report)
        if fp is not None and read.get(report) != fp:
            modified = os.stat(report).st_mtime
            events.append({
                "event": "report", "pane": pane, "report": report, "version": fp,
                "modified": stamp(modified), "age": span(max(0, time.time() - modified)),
            })
    return events


def cmd_mark_read(a):
    data = load_state(a.state)
    marked = []
    for report in a.reports:
        report = os.path.abspath(report)
        fp = fingerprint(report)
        if fp is None:
            print(json.dumps({"error": "missing", "report": report}))
            return 1
        data["read"][report] = fp
        marked.append({"report": report, "version": fp})
    save_state(a.state, data)
    for m in marked:
        print(json.dumps({"marked_read": m["report"], "version": m["version"]}))
    return 0


def cmd_unread(a):
    for event in unread_reports(a.state, parse_workers(a.worker)):
        print(json.dumps(event))
    return 0


def emit(started, events):
    """Print a wake header with wall-clock context, then each event."""
    now = time.time()
    print(json.dumps({
        "event": "wake", "now": stamp(now), "watch_started": stamp(started),
        "waited": span(now - started), "events": len(events),
    }))
    for e in events:
        print(json.dumps(e))


def cmd_watch(a):
    started = time.time()
    workers = parse_workers(a.worker)
    legacy_progress = getattr(a, 'progress_path', [])
    if legacy_progress and len(workers) != 1:
        raise ValueError("--progress-path supports exactly one worker; use --worker-progress PANE=PATH")
    progress_by_pane = parse_worker_progress(getattr(a, 'worker_progress', []), workers)
    if legacy_progress:
        progress_by_pane[next(iter(workers))].extend(legacy_progress)
    track = {
        pane: {
            "idle_since": None,
            "footer": footer(pane),
            "footer_since": time.time(),
            "status": "working",
            "window": deque(maxlen=a.debounce),
            "progress": progress_fingerprint(progress_by_pane[pane]),
            "progress_since": time.time(),
        }
        for pane in workers
    }

    follow = getattr(a, 'follow', False)
    announced = set()  # follow mode: an event is announced once, not on every poll
    reported_panes = set()
    end = time.time() + a.timeout_minutes * 60
    while time.time() < end:
        events = unread_reports(a.state, workers)
        reported = {e["pane"] for e in events}
        for pane, w in track.items():
            now = time.time()
            raw = status(pane)
            if raw is None:
                events.append({"event": "gone", "pane": pane})
                continue
            # Debounce: the effective status is the strict majority of the
            # last --debounce samples; otherwise it stays unchanged.
            w["window"].append(raw)
            top, n = Counter(w["window"]).most_common(1)[0]
            if n * 2 > len(w["window"]):
                w["status"] = top
            st = w["status"]
            if st != "working":
                w["idle_since"] = w["idle_since"] or now
                idle = now - w["idle_since"]
                if idle >= a.idle_grace and pane not in reported:
                    event = {"event": "stall", "pane": pane, "status": st,
                             "since": stamp(w["idle_since"]), "for": span(idle)}
                    hint = error_hint(pane)
                    if hint:
                        event["hint"] = hint
                    events.append(event)
            else:
                w["idle_since"] = None
            f = footer(pane)
            if f != w["footer"]:
                w["footer"], w["footer_since"] = f, now
            progress_paths = progress_by_pane[pane]
            current_progress = progress_fingerprint(progress_paths)
            if current_progress != w["progress"]:
                w["progress"], w["progress_since"] = current_progress, now
            stalled_since = max(w["progress_since"], w["footer_since"])
            if st == "working" and now - stalled_since >= a.stall_minutes * 60:
                events.append({"event": "no_progress", "pane": pane, "since": stamp(stalled_since),
                               "for": span(now - stalled_since), "footer": f,
                               "progress_paths": progress_paths})
        if follow:
            events = [e for e in events if (e["event"], e["pane"], e.get("version") or e.get("since")) not in announced]
        if events:
            if any(e["event"] == "report" for e in events):
                time.sleep(a.settle)  # let a worker finish writing, then re-list
                events = [e for e in events if e["event"] != "report"] + unread_reports(a.state, workers)
                if follow:
                    events = [e for e in events
                              if (e["event"], e["pane"], e.get("version") or e.get("since")) not in announced]
            if not follow:
                emit(started, events)
                return 0
            for e in events:
                announced.add((e["event"], e["pane"], e.get("version") or e.get("since")))
                if e["event"] == "report":
                    reported_panes.add(e["pane"])
            emit(started, events)
            sys.stdout.flush()
            if reported_panes >= set(workers):
                print(json.dumps({"event": "all_reported"}), flush=True)
                return 0
        time.sleep(a.interval)
    emit(started, [{"event": "timeout"}])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("watch", help="wait for unread reports or stalled workers")
    w.add_argument("--state", required=True, help="read/unread state file (keep beside the task record)")
    w.add_argument("--worker", action="append", required=True, help="PANE=REPORT_PATH")
    w.add_argument("--progress-path", action="append", default=[], help=argparse.SUPPRESS)
    w.add_argument("--worker-progress", action="append", default=[], metavar="PANE=PATH",
                   help="pane-specific worktree, output directory, or report for no-progress detection")
    w.add_argument("--idle-grace", type=int, default=90)
    w.add_argument("--stall-minutes", type=float, default=15)
    w.add_argument("--timeout-minutes", type=float, default=180)
    w.add_argument("--interval", type=int, default=15)
    w.add_argument("--settle", type=int, default=20, help="seconds to wait after a report before listing")
    w.add_argument("--follow", action="store_true",
                   help="keep running after an event: announce each new report/stall once, exit when every "
                        "worker has reported (or on timeout). Use with the Monitor tool so no re-arming is needed")
    w.add_argument("--debounce", type=int, default=5, help="sliding window of samples; the majority status counts")
    w.set_defaults(func=cmd_watch)

    u = sub.add_parser("unread", help="list unread reports without waiting")
    u.add_argument("--state", required=True)
    u.add_argument("--worker", action="append", required=True, help="PANE=REPORT_PATH")
    u.set_defaults(func=cmd_unread)

    m = sub.add_parser("mark-read", help="record the current version of reports as read")
    m.add_argument("--state", required=True)
    m.add_argument("reports", nargs="+")
    m.set_defaults(func=cmd_mark_read)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

