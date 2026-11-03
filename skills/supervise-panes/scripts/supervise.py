#!/usr/bin/env python3
"""One control-plane loop for several pane workers. See references/control-plane-loop.md.

usage: supervise.py [--config PATH] [--once] [--dry-run] | --stop | --status

Every interval (default 60s) the loop:
  - forwards new "ready" posts in the inbox to the integrator pane
  - runs assign for "### <coordinator>: next for <lane>: <job>" inbox lines
  - logs inbox posts that match alert_re
  - nudges a lane idle past idle_after that owns a job (at most once per nudge_every),
    logs IDLE for a lane with no job, and ESCALATE for a priority-1 lane after
    escalate_nudges nudges with no post
  - logs CONTEXT when a pane footer shows more than context_limit_k thousand tokens
  - logs CI for the remote branch's head commit, STALL, and LOW DISK
  - optional ship hook: runs ship.command for a new candidate tip after a quiet period
  - optional measure hook: runs measure.command after each ship and logs its last line
One line per event goes to stdout and <dir>/supervise.log. HEARTBEAT every heartbeat_every.

--once     run one live cycle (sends, assigns, logs) without shipping or measuring, then exit
--dry-run  no sends, ships, measures or log writes; prints one STATUS line per lane;
           may run beside the live loop
--stop     SIGTERM the running instance (pid in <dir>/supervise.lock)
--status   print a one-call summary and exit (read-only)
Config: JSON at --config or $SUPERVISE_CONFIG. Lanes are re-read every cycle.
Command and message strings use str.format, so write literal braces as {{ }}.
"""
import argparse, fcntl, json, os, re, shlex, shutil, signal, subprocess, sys, time, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assign as A   # noqa: E402  shared config, lane and delivery helpers

DEFAULTS = {
    "coordinator": "coordinator",
    "integrator": "",                      # pane id that receives ready posts
    "integrator_message": "New ready entry in the inbox. Integrate it and post the new candidate tip: {entry}",
    "integrator_authors": [],              # extra names the integrator posts as (its pane short id is always included);
                                           # their "ready" posts are not forwarded back
    "ready_exclude_re": r"not ready|ready to ship|claim|retract|integrated",
    "alert_re": r"blocked|blocker|decision|reject|urgent|candidate tip",
    "nudge_message": "Continue your job {jobs}.",
    "watch_only": {},                      # name -> pane: context watch only
    "repo": "", "remote": "origin", "branch": "main",
    "ship": None,      # {"ref", "command", "shipped_command", "lock", "quiet": 300, "max_wait": 1200, "min_gap": 1200}
    "measure": None,   # {"command"}
    "interval": 60, "idle_after": 600, "nudge_every": 1800, "escalate_nudges": 2,
    "context_limit_k": 400, "stall_after": 2700, "heartbeat_every": 1800,
    "ci_every_loops": 5, "min_free_gb": 8,
    # [regex, divisor to thousands]: term2 "Ctx last 126k"; "ctx 833,493" is a custom
    # Claude Code statusline, not stock Claude Code (replace it to match yours)
    "context_res": [[r"Ctx last (\d+)k", 1], [r"\bctx ([\d,]{4,})", 1000]],
    "quota_res": {"codex 7D": r"7D (\d+%)", "claude 5h/7d": r"5h (\d+%).*?7d (\d+%)"},
    # a descendant matching this means the lane is busy even if its footer looks idle; "" disables
    "child_busy_re": r"\b(vitest|jest|pytest|cargo|tsc|gradle|mvn)\b",
}

CFG, DRY, ONCE = {}, False, False


def cfg(key):
    return CFG.get(key, DEFAULTS.get(key))


def path(name):
    return os.path.join(CFG["dir"], name)


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    if not DRY:
        with open(path("supervise.log"), "a") as f:
            f.write(line + "\n")


def git(*a):
    if not cfg("repo"):
        return ""
    rc, out = A.run("git", "-C", cfg("repo"), *a)
    return out.strip() if rc == 0 else ""


def remote_head():
    return (git("ls-remote", cfg("remote"), f"refs/heads/{cfg('branch')}").split() or [""])[0]


def shell(cmd, **kw):
    return subprocess.Popen(["sh", "-c", cmd], stdin=subprocess.DEVNULL, **kw)


def author(header):
    """'### builder-d: x' -> 'builder-d'."""
    head = header[4:].split(":", 1)[0].split()
    return head[0] if head else ""


def headers():
    try:
        with open(cfg("inbox")) as f:
            return [l.rstrip("\n") for l in f if l.startswith("### ")]
    except OSError:
        return []


def footer_ctx(screen):
    for rx, div in cfg("context_res"):
        m = re.search(rx, screen or "")
        if m:
            return int(m.group(1).replace(",", "")) // div
    return None


def child_busy(pane):
    rx = cfg("child_busy_re")
    if not rx:
        return False
    rc, out = A.run("herdr", "pane", "process-info", "--pane", pane)
    try:
        todo = [p["pid"] for p in json.loads(out)["result"]["process_info"]["foreground_processes"] or []]
    except (ValueError, KeyError, TypeError):
        return False
    seen, kids = set(), []
    for pid in todo:
        kids += children(pid)
    while kids:                       # descendants of the pane's foreground processes
        pid = kids.pop()
        if pid in seen:
            continue
        seen.add(pid)
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if re.search(rx, f.read().replace(b"\0", b" ").decode("utf-8", "replace")):
                    return True
        except OSError:
            continue
        kids += children(pid)
    return False


def children(pid):
    try:
        with open(f"/proc/{pid}/task/{pid}/children") as f:
            return [int(c) for c in f.read().split()]
    except OSError:
        return []


def lane_state(pane, screen, status):
    """(idle, source)."""
    st = status.get(pane)
    if st in ("working", "idle", "done"):
        idle, src = st != "working", f"agent:{st}"
    else:
        idle = bool(re.search(cfg("idle_re"), screen)) and not re.search(cfg("busy_re"), screen)
        src = "footer"
    if idle and child_busy(pane):
        return False, "child"
    return idle, src


class Supervisor:
    def __init__(self):
        self.inbox_seen = len(headers())      # only posts after start count
        self.activity = time.time()
        self.flags = set()                    # one-shot log keys: ("idle", lane), ("ctx", lane), ...
        self.idle_since, self.last_nudge, self.p1_nudges = {}, {}, {}
        self.last_ci = None
        self.tick = 0
        self.last_heartbeat = time.time()
        ship = cfg("ship") or {}
        self.tip = git("rev-parse", ship["ref"]) if ship.get("ref") else ""
        self.shipped = self.read_shipped() or self.tip   # without shipped_command, start from the current tip
        self.last_ship, self.pending_since, self.ship_proc = time.time(), 0, None   # never ship on the first cycle
        self.measured, self.measure_want, self.measure_proc = self.shipped, None, None

    def once(self, key, on, msg):
        """Log msg the first time `on` becomes true; re-arm when it clears."""
        if on and key not in self.flags:
            log(msg)
            self.flags.add(key)
        elif not on:
            self.flags.discard(key)

    # --- inbox: ready forwarding, dispatch, alerts
    def check_inbox(self):
        heads = headers()
        new, self.inbox_seen = heads[self.inbox_seen:], len(heads)
        if not new:
            return
        self.activity = time.time()
        if not DRY:
            with open(path("inbox-times.tsv"), "a") as f:
                f.writelines(f"{int(self.activity)}\t{h}\n" for h in new)
        coord = cfg("coordinator")
        lane_map = A.lanes(CFG)
        for h in new:
            who = author(h)
            for lane, pane in lane_map.items():
                if who in A.aliases(lane, pane):
                    self.p1_nudges.pop(lane, None)
                    self.flags.discard(("escalate", lane))
            m = re.match(rf"### {re.escape(coord)}: next for (\S+): (\S+)", h)
            if m:
                lane, job = m.group(1).strip("`*"), m.group(2).strip("`*.,;").removesuffix(".md")
                rc, out = A.assign(CFG, job, lane, DRY)
                log(f"ASSIGN {job} -> {lane}{' (dry-run)' if DRY else ''}: {'ok' if rc == 0 else 'rc ' + str(rc)}: "
                    + " | ".join(out)[:300])
                continue
            if who == coord:
                continue
            integ = cfg("integrator")
            if (integ and who not in {*cfg("integrator_authors"), integ.split(":")[-1]} and re.search(r"\bready\b", h, re.I)
                    and not re.search(cfg("ready_exclude_re"), h, re.I)):
                msg = cfg("integrator_message").format(entry=h[4:200])
                result = A.deliver(CFG, cfg("integrator"), msg, DRY)
                log(f"READY '{h[4:120]}' -> {cfg('integrator')} [{result}]")
                continue
            if re.search(cfg("alert_re"), h, re.I):
                log(f"INBOX {h[4:220]}")

    # --- lanes: idle nudge, escalate
    def check_lanes(self):
        status, now = A.agent_status(), time.time()
        for lane, pane in A.lanes(CFG).items():
            screen = A.visible(pane)
            self.once(("missing", lane), screen is None, f"MISSING {lane} pane {pane} not found")
            if screen is None:
                continue
            self.once(("nohook", lane), pane not in status,
                      f"NOHOOK {lane} not in herdr agent list; using the footer (see the herdr skill)")
            idle, src = lane_state(pane, screen, status)
            jobs = A.owned(CFG, lane, pane)
            if DRY:
                since = self.idle_since.get(lane)
                print(f"STATUS {lane} {pane} {'idle' if idle else 'busy'} ({src})"
                      f"{f' idle {int(now - since)}s' if idle and since else ''} jobs={','.join(jobs) or '-'}")
            if not idle:
                self.idle_since.pop(lane, None)
                self.flags.discard(("idle", lane))
                continue
            if now - self.idle_since.setdefault(lane, now) < cfg("idle_after"):
                continue
            if not jobs:
                self.once(("idle", lane), True, f"IDLE {lane} no job")
            elif now - self.last_nudge.get(lane, 0) >= cfg("nudge_every"):
                q = os.path.basename(cfg("queue"))
                msg = cfg("nudge_message").format(jobs=", ".join(f"{q}/doing/{j}" for j in jobs))
                log(f"NUDGE {lane}: {msg} [{A.deliver(CFG, pane, msg, DRY)}]")
                self.last_nudge[lane] = now
                self.track_p1(lane, jobs, now)

    def track_p1(self, lane, jobs, now):
        p1 = [j for j in jobs if A.field(os.path.join(cfg("queue"), "doing", j), "priority") == "1"]
        if not p1:
            self.p1_nudges.pop(lane, None)
            return
        n = self.p1_nudges.setdefault(lane, [now, 0])
        n[1] += 1
        if n[1] >= cfg("escalate_nudges"):
            self.once(("escalate", lane), True,
                      f"ESCALATE {lane} {p1[0]} no post since {time.strftime('%H:%M', time.localtime(n[0]))}")

    def check_context(self):
        for lane, pane in {**A.lanes(CFG), **cfg("watch_only")}.items():
            k = footer_ctx(A.visible(pane, 10))
            if k is not None:
                self.once(("ctx", lane), k >= cfg("context_limit_k"), f"CONTEXT {lane} {k}k")

    # --- optional hooks
    def read_shipped(self):
        cmd = (cfg("ship") or {}).get("shipped_command")
        if not cmd:
            return ""
        rc, out = A.run("sh", "-c", cmd)
        return out.strip().split()[0] if rc == 0 and out.strip() else ""

    def check_ship(self):
        ship = cfg("ship")
        if not ship:
            return
        if self.ship_proc:
            p, tip, logf = self.ship_proc
            if p.poll() is None:
                return
            self.ship_proc = None
            last = last_line(logf)
            if p.returncode == 0:
                self.shipped = tip              # mark shipped only on success
                log(f"SHIPPED {tip[:8]}: {last}")
            else:
                log(f"SHIP FAILED {tip[:8]} rc {p.returncode}: {last} (retry next window)")
        self.shipped = self.read_shipped() or self.shipped   # re-read: manual ships move it too
        tip, ct = git("rev-parse", ship["ref"]), git("log", "-1", "--format=%ct", ship["ref"])
        if not tip or not ct or same(tip, self.shipped):
            self.pending_since = 0
            return
        now = time.time()
        self.pending_since = self.pending_since or now
        quiet = now - int(ct) >= ship.get("quiet", 300)
        waited = now - self.pending_since >= ship.get("max_wait", 1200)   # tip keeps moving: ship anyway
        if now - self.last_ship < ship.get("min_gap", 1200) or not (quiet or waited):
            return
        self.last_ship, self.pending_since = now, 0
        cmd = ship["command"].format(tip=tip)
        if ship.get("lock"):   # manual ships use the same flock, so the two never overlap
            cmd = f"flock -n {shlex.quote(path(ship['lock']))} sh -c {shlex.quote(cmd)}"
        if DRY:
            log(f"SHIP {tip[:8]} -> would run: {cmd}")
            return
        logf = path(f"ship-{tip[:8]}.log")
        log(f"SHIP {tip[:8]} started (shipped {self.shipped[:8]})")
        with open(logf, "w") as out:
            self.ship_proc = (shell(cmd, stdout=out, stderr=subprocess.STDOUT), tip, logf)

    def check_measure(self):
        m = cfg("measure")
        if not m:
            return
        if self.shipped and not same(self.shipped, self.measured):
            self.measured = self.measure_want = self.shipped    # newest ship wins
        if self.measure_proc:
            p, sha, logf = self.measure_proc
            if p.poll() is None:
                return
            self.measure_proc = None
            log(f"MEASURE {sha[:8]} " + (last_line(logf) if p.returncode == 0
                                          else f"FAILED rc {p.returncode}, see {logf}"))
        if self.measure_want:
            sha, self.measure_want = self.measure_want, None
            cmd = m["command"].format(sha=sha)
            if DRY:
                log(f"MEASURE {sha[:8]} -> would run: {cmd}")
                return
            logf = path(f"measure-{sha[:8]}.log")
            with open(logf, "w") as out:
                self.measure_proc = (shell(cmd, stdout=out, stderr=subprocess.STDOUT,
                                           start_new_session=True), sha, logf)

    # --- CI, stall, disk
    def check_ci(self):
        head = remote_head()   # by commit: --branch listing can return runs in a stale order
        if not head:
            return
        rc, out = A.run("gh", "run", "list", "--commit", head, "--limit", "1",
                        "--json", "databaseId,status,conclusion", cwd=cfg("repo"))
        try:
            r = json.loads(out)[0]
        except (ValueError, IndexError, KeyError):
            return
        if r.get("status") == "completed" and r["databaseId"] != self.last_ci:
            self.last_ci = r["databaseId"]
            log(f"CI {cfg('branch')}: run {r['databaseId']} {r.get('conclusion')} {head[:8]}")

    def check_stall_disk(self):
        ref = (cfg("ship") or {}).get("ref")
        tip = git("rev-parse", ref) if ref else ""
        if tip and tip != self.tip:
            self.tip, self.activity = tip, time.time()
        idle_min = (time.time() - self.activity) // 60
        self.once(("stall",), time.time() - self.activity >= cfg("stall_after"),
                  f"STALL no inbox post or candidate commit for {idle_min:.0f} min")
        free = shutil.disk_usage(CFG["dir"]).free / 2**30
        self.once(("disk",), free < cfg("min_free_gb"), f"LOW DISK {free:.1f}G free")

    def iterate(self):
        checks = [self.check_inbox, self.check_lanes, self.check_context, self.check_stall_disk]
        if not ONCE:   # --once never ships or measures
            checks[2:2] = [self.check_ship, self.check_measure]
        if self.tick % cfg("ci_every_loops") == 0:
            checks.append(self.check_ci)
        for fn in checks:
            try:
                fn()
            except Exception as e:   # keep the loop alive; one line per failure
                log(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
        self.tick += 1
        if time.time() - self.last_heartbeat >= cfg("heartbeat_every"):
            self.last_heartbeat = time.time()
            log(f"HEARTBEAT shipped {self.shipped[:8] or '-'} tip {self.tip[:8] or '-'}")


def same(a, b):
    return bool(a and b) and (a.startswith(b) or b.startswith(a))


def last_line(f):
    try:
        with open(f, errors="replace") as fh:
            lines = [l.strip() for l in fh if l.strip()]
        return lines[-1][:300] if lines else ""
    except OSError:
        return ""


def ago(t):
    m = int((time.time() - t) // 60)
    return f"{m}m ago" if m < 120 else f"{m // 60}h{m % 60:02d}m ago"


def status():
    """--status: read-only one-call summary."""
    s = Supervisor()
    head = remote_head()
    print(f"shipped {s.shipped[:8] or '-'}  candidate {s.tip[:8] or '-'}  "
          f"{cfg('remote')}/{cfg('branch')} {head[:8] or '-'}")
    if head:
        rc, out = A.run("gh", "run", "list", "--commit", head, "--json",
                        "databaseId,workflowName,status,conclusion", cwd=cfg("repo"))
        try:
            runs = json.loads(out)
        except ValueError:
            runs = []
        if not runs:
            print("CI: no run for that commit")
        for r in runs:
            print(f"CI {r['workflowName']} run {r['databaseId']}: {r['status']} {r.get('conclusion') or ''}")
            rc, jout = A.run("gh", "run", "view", str(r["databaseId"]), "--json", "jobs", cwd=cfg("repo"))
            try:
                for j in json.loads(jout)["jobs"]:
                    print(f"  {j['name']}: {j['conclusion'] or j['status']}")
            except (ValueError, KeyError):
                pass
    try:
        with open(path("supervise.log")) as f:
            meas = [l.strip() for l in f if " MEASURE " in l and "would run" not in l]
    except OSError:
        meas = []
    print(meas[-1] if meas else "MEASURE: none yet")
    q = cfg("queue")
    print("doing:")
    for sub in ("doing", "todo"):
        d = os.path.join(q, sub)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            p = os.path.join(d, f)
            if not f.endswith(".md"):
                continue
            if sub == "doing":
                print(f"  P{A.field(p, 'priority') or '-'} {A.field(p, 'lane') or '-':12} {f}")
            elif A.field(p, "priority") == "1" and A.field(p, "lane") in ("", "any"):
                print(f"  unowned P1 in todo: {f}")
    heads, times = headers(), {}
    try:
        with open(path("inbox-times.tsv")) as f:
            for l in f:
                t, h = l.rstrip("\n").split("\t", 1)
                times[h] = int(t)
    except (OSError, ValueError):
        pass
    st, quota = A.agent_status(), {}
    print("lanes:")
    for lane, pane in {**A.lanes(CFG), **cfg("watch_only")}.items():
        screen = A.visible(pane, 10)
        if screen is None:
            print(f"  {lane:12} {pane}: pane not found")
            continue
        idle, src = lane_state(pane, screen, st)
        last = next((h for h in reversed(heads) if author(h) in A.aliases(lane, pane)), None)
        when = ago(times[last]) if last in times else "time unknown"
        k = footer_ctx(screen)
        print(f"  {lane:12} {pane} {'idle' if idle else 'busy'} ({src}){f' ctx {k}k' if k is not None else ''}"
              f"  last post: " + (f"{last[4:100]} ({when})" if last else "none"))
        for label, rx in cfg("quota_res").items():
            m = re.search(rx, screen)
            if m and label not in quota:
                quota[label] = f"{label} {' '.join(m.groups())} ({lane})"
    print(f"disk free {shutil.disk_usage(CFG['dir']).free / 2**30:.1f}G")
    print("quota: " + ("; ".join(quota.values()) or "not visible in any footer"))


def lock_pid():
    try:
        with open(path("supervise.lock")) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def main():
    global CFG, DRY, ONCE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 allow_abbrev=False)
    ap.add_argument("--config")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--stop", action="store_true")
    mode.add_argument("--status", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()          # unknown args print usage and exit 2; never start the loop
    CFG = A.load_config(a.config)
    DRY, ONCE = a.dry_run, a.once
    if a.status:
        return status()
    if a.stop:
        try:   # if we can take the lock, no loop holds it: the pid in the file is stale
            fd = os.open(path("supervise.lock"), os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            sys.exit("supervise: not running (lock is free)")
        except FileNotFoundError:
            sys.exit("supervise: not running (no lock file)")
        except BlockingIOError:
            pass
        pid = lock_pid()
        if not pid:
            sys.exit("supervise: not running (no pid in lock)")
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            sys.exit(f"supervise: pid {pid} not running")
        return print(f"supervise: sent SIGTERM to {pid}")
    if not DRY:   # one live instance: hold the flock for the process lifetime
        fd = os.open(path("supervise.lock"), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(f"supervise: already running, pid {lock_pid()}")
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        signal.signal(signal.SIGTERM, lambda *_: (log("STOP SIGTERM"), sys.exit(0)))
    try:
        s = Supervisor()
        log(f"START supervise{' (dry-run)' if DRY else ''} pid {os.getpid()} "
            f"shipped {s.shipped[:8] or '-'} tip {s.tip[:8] or '-'}")
        while True:
            s.iterate()
            if a.once:
                return
            time.sleep(cfg("interval"))
    except Exception:
        log(f"ERROR {traceback.format_exc().strip().splitlines()[-1]} (exiting)")
        raise


if __name__ == "__main__":
    main()
