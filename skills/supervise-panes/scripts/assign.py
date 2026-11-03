#!/usr/bin/env python3
"""Give one queued job to one pane lane, and refuse a second job for that lane.

usage: assign.py [--config PATH] [--dry-run] <job> <lane>

The job comes from <queue>/todo/<job>.md, or from <queue>/doing/ when its
"lane:" line is empty or "any". The lane must be in the lanes file
(lane name -> herdr pane id); the pane's short id is accepted as an alias.
The script moves the job to doing/, writes "lane: <lane>", sends the lane the
assign_message, and confirms the turn started (one resend). Exit 0 delivered,
1 refused or bad input, 2 sent but delivery unconfirmed.

Config is the same JSON file supervise.py reads (--config or $SUPERVISE_CONFIG).
Message strings in it use str.format, so write literal braces as {{ }}.
This module also holds the helpers supervise.py shares.
"""
import argparse, json, os, re, subprocess, sys, time

DEFAULTS = {
    "queue": "queue",
    "lanes_file": "lanes.json",
    # footer patterns: term2 first, then Claude Code
    "busy_re": r"Enter steer|esc to interrupt",
    "idle_re": r"/ commands|\? for shortcuts",
    "assign_message": ("Your job is {queue}/doing/{job}.md. Read it and post a claim in the inbox. "
                       "Work only on jobs with lane: {lane}; never edit the lane: line. "
                       "When finished, record the evidence in the job file and post "
                       "'{lane}: {job} ready' in the inbox."),
}


def load_config(path):
    path = path or os.environ.get("SUPERVISE_CONFIG")
    if not path:
        sys.exit("no config: pass --config PATH or set SUPERVISE_CONFIG")
    with open(path) as f:
        cfg = {**DEFAULTS, **json.load(f)}
    base = os.path.dirname(os.path.abspath(path))
    cfg["dir"] = os.path.normpath(os.path.join(base, cfg.get("dir", ".")))
    for key in ("queue", "lanes_file", "inbox"):     # relative paths are relative to "dir"
        if cfg.get(key):
            cfg[key] = os.path.normpath(os.path.join(cfg["dir"], cfg[key]))
    return cfg


def run(*cmd, timeout=60, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout + r.stderr
    except (subprocess.TimeoutExpired, OSError) as e:
        return 1, str(e)


def lanes(cfg):
    """lane name -> pane id. Re-read on every call so edits apply without a restart."""
    with open(cfg["lanes_file"]) as f:
        return json.load(f)


def aliases(lane, pane):
    return {lane, pane.split(":")[-1]}


def field(path, name):
    try:
        with open(path) as f:
            for line in f:
                if line.startswith(name + ":"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def owned(cfg, lane, pane):
    d = os.path.join(cfg["queue"], "doing")
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d)
                  if f.endswith(".md") and field(os.path.join(d, f), "lane") in aliases(lane, pane))


def visible(pane, n=8):
    rc, out = run("herdr", "pane", "read", pane, "--source", "visible", "--lines", str(n))
    return out if rc == 0 else None


def agent_status():
    """pane -> herdr lifecycle status. A pane missing here has no status integration."""
    rc, out = run("herdr", "agent", "list")
    try:
        return {a["pane_id"]: a.get("agent_status") for a in json.loads(out)["result"]["agents"]}
    except (ValueError, KeyError, TypeError):
        return {}


def agent_at(cfg, pane):
    """True when an agent, not a bare shell, owns the pane: herdr lists it or its footer matches."""
    if pane in agent_status():
        return True
    screen = visible(pane) or ""
    return bool(re.search(cfg["idle_re"], screen) or re.search(cfg["busy_re"], screen))


def deliver(cfg, pane, msg, dry=False):
    """Type msg into the pane, press Enter, and wait for the busy footer. One resend.
    Sends nothing unless an agent owns the pane: in a bare shell the text would run as a command."""
    if dry:
        return "dry-run"
    if not agent_at(cfg, pane):
        return "NOTSENT: no agent at pane"
    for attempt in (1, 2):
        run("herdr", "pane", "send-text", pane, msg)
        time.sleep(0.8)
        run("herdr", "pane", "send-keys", pane, "enter")
        for _ in range(10):
            time.sleep(1)
            if re.search(cfg["busy_re"], visible(pane) or ""):
                return f"delivered try {attempt}"
    return "admission UNCONFIRMED"


def set_lane(path, lane):
    with open(path) as f:
        lines = f.read().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("lane:"):
            lines[i] = f"lane: {lane}\n"
            break
    else:
        lines.insert(0, f"lane: {lane}\n")
    with open(path, "w") as f:
        f.writelines(lines)


def assign(cfg, job, lane, dry=False):
    """Returns (exit code, output lines)."""
    lane_map = lanes(cfg)
    lane = {p.split(":")[-1]: l for l, p in lane_map.items()}.get(lane, lane)
    if lane not in lane_map:
        return 1, [f"unknown lane {lane}; known: {' '.join(lane_map)}"]
    pane = lane_map[lane]
    if "/" in job or ".." in job:
        return 1, [f"bad job name {job}"]
    job = job if job.endswith(".md") else job + ".md"
    q = cfg["queue"]
    src = os.path.join(q, "todo", job)
    if not os.path.exists(src):
        src = os.path.join(q, "doing", job)
        if not os.path.exists(src):
            return 1, [f"{job}: not in todo/ or doing/"]
        if field(src, "lane") not in ("", "any"):
            return 1, [f"{job}: already in doing with lane: {field(src, 'lane')}"]
    others = [f for f in owned(cfg, lane, pane) if f != job]
    if others:
        return 1, [f"REFUSED: {lane} already owns: " + " ".join(others)]
    dst = os.path.join(q, "doing", job)
    msg = cfg["assign_message"].format(job=job.removesuffix(".md"), lane=lane, queue=os.path.basename(q))
    if dry:
        return 0, [f"DRY-RUN move {src} -> {dst}", f"DRY-RUN set lane: {lane}",
                   f"DRY-RUN message {pane}: {msg}"]
    if not agent_at(cfg, pane):
        return 1, [f"NOTSENT: no agent at {pane}; {job} left in place"]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if src != dst:
        os.rename(src, dst)
    set_lane(dst, lane)
    result = deliver(cfg, pane, msg)
    return (0 if result.startswith("delivered") else 2), [f"assigned {job} to {lane} ({pane}): {result}"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 allow_abbrev=False)
    ap.add_argument("--config")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("job")
    ap.add_argument("lane")
    a = ap.parse_args()
    rc, out = assign(load_config(a.config), a.job, a.lane, a.dry_run)
    print("\n".join(out))
    sys.exit(rc)


if __name__ == "__main__":
    main()
