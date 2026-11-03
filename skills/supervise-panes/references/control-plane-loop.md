# Control-plane loop

Use one control-plane loop when you supervise several pane workers for hours.
For one or two short assignments, the watcher in
[Worker observation](worker-observation.md) is enough.

The loop is [scripts/supervise.py](../scripts/supervise.py). Dispatch is
[scripts/assign.py](../scripts/assign.py). Both read one JSON config; copy
[scripts/supervise.example.json](../scripts/supervise.example.json) into the task
directory and edit it. The keys and their defaults are at the top of each script.
Shipping and measuring are optional hooks that run your own commands.

The scripts expect these formats:

- The inbox is one markdown file that workers and the coordinator append to. Each
  post starts with a `### <author>: <text>` header, and the author is the first
  word before the colon. It is not the report/receive inbox in [Inbox](inbox.md).
- The queue directory has `todo/` and `doing/` subdirectories of job files. A job
  file is markdown with a `lane:` line (empty or `any` means unowned) and an
  optional `priority:` line, where `1` is the top priority.
- Command and message strings in the config use Python `str.format` (`{tip}`,
  `{sha}`, `{job}`), so write a literal brace as `{{` or `}}`.

Start the loop from the task directory:
`setsid nohup python3 <skill-dir>/scripts/supervise.py --config config.json >/dev/null 2>&1 &`.
`--once` runs a single live cycle (it sends and assigns) but never ships or
measures; `--dry-run` sends nothing.

## What the loop does

Once a minute:

- forwards new "ready" posts in the shared inbox to the integrator pane;
- runs assign when the coordinator writes a dispatch line in the inbox;
- logs inbox posts that look like blockers or decisions;
- nudges a lane that has sat idle with a job, and escalates a priority-1 lane
  that stays silent;
- flags a lane whose footer shows high context;
- reports CI for the remote branch, a stalled task, and low disk;
- optionally ships a new candidate tip, then measures what shipped.

It writes one line per event to `<dir>/supervise.log`, with a fixed first word
(READY, ASSIGN, NUDGE, ESCALATE, SHIPPED, MEASURE, ...) so the log is easy to filter.

## Guardrails

- **One detached loop, not several monitors.** Start it with `setsid nohup`. A
  harness monitor expires after about 30 minutes, and several watchers
  double-assign work and flood the coordinator.
- **Unknown arguments print usage and exit.** A `--help` that starts the live
  loop can ship a build.
- **One instance only.** The loop holds a flock on `<dir>/supervise.lock` for its
  lifetime; stop it with `--stop`, which checks the lock before trusting the pid. Don't use `pkill -f`: the pattern matches the
  shell that runs it.
- **One lanes file** (`lane name -> pane id`), re-read every cycle and also read by
  assign. Opening or closing a lane is one edit, with no restart.
- **Builders post "ready" in the inbox** as a `### <lane>: <job> ready` line. The
  loop forwards those to the integrator, skipping "not ready", claims, retractions,
  "integrated", and the integrator's own posts. A file-drop ready queue was tried
  and builders didn't use it.
- **Dispatch through the inbox.** The coordinator writes
  `### <coordinator>: next for <lane>: <job>`. The loop runs assign, which refuses
  a second job for a lane and checks that the turn actually started.
- **Never type into a bare shell.** A message is sent only when herdr lists the
  pane as an agent or its footer matches the busy or idle pattern; otherwise the
  log says NOTSENT. Inbox text sent to a shell would run as a command.
- **Don't ship on start.** The first ship waits one full `min_gap` after the loop
  starts, so restarting the loop doesn't ship.
- **Idle nudge with limits.** A lane idle for 10 minutes, with no test or build
  running under it, gets a nudge at most once per 30 minutes. ESCALATE fires when
  a priority-1 lane has had two nudges and no post. It catches both a silent lane
  and a busy lane that has stopped reporting; check which before acting.
- **Query CI by commit.** Look up the remote branch's head commit, then
  `gh run list --commit <sha>`. Listing by `--branch` can return runs in a stale
  order and report an old success.
- **Ship carefully.** Wait for the candidate tip to be quiet (5 minutes), but ship
  anyway after 20 minutes if it keeps moving. Mark a tip shipped only when the
  ship command succeeds. Put manual and loop ships under the same flock (the
  `ship.lock` key). Re-read the shipped commit every cycle, because a manual ship
  moves it too.
- **Measure after every ship.** Run the main suites in the background, in a
  worktree kept for that purpose, and have the command print one summary line;
  the loop logs it as MEASURE. This keeps current numbers on hand and can catch a
  flake locally with its diagnostics.
- **Watch context.** Flag a lane above about 400k tokens, read from its footer.
  Compacting or restarting a large integrator cuts quota drain a lot.
- **Prove it's alive.** A HEARTBEAT line every 30 minutes; any error is logged as
  ERROR, and an uncaught one is logged before the loop exits.

Footer parsing (busy, idle, context, quota) uses regexes in the config, with
term2 and Claude Code defaults. When herdr reports a lane's lifecycle status, the
loop uses that instead of the footer. A NOHOOK line means herdr can't see the lane;
the herdr skill covers the term2 cause.

## The coordinator's side

Watch two things: the log, filtered to actionable events, and whether the loop
process is alive. For example, run
`tail -F <dir>/supervise.log | grep -E 'READY|ASSIGN|NOTSENT|ESCALATE|IDLE|INBOX|SHIP|MEASURE|CI|STALL|LOW DISK|CONTEXT|ERROR'`
under the harness's background facility, and on each wake check the pid in the
lock file. Re-arm the tail when the harness expires it; the loop keeps running.

For the periodic "are we on track" check, run `supervise.py --status`. It prints
the shipped and candidate commits, CI jobs for the remote head, the last MEASURE,
doing jobs with owners, lanes with the age of their last post, disk, and quota.

The loop moves messages; judgment stays with you:

- deciding the next job for each lane, and writing the dispatch line;
- steering a lane that is stuck or going the wrong way;
- reviewing ready claims, which the integrator checks before taking them;
- answering ESCALATE, IDLE, and INBOX alerts.

A lane stuck in repeated compaction with no diff should be restarted fresh, with
a short brief stating what is already known, rather than nudged again.

When the task finishes, run `supervise.py --stop`, end your log tail, and delete
the config, log, lock and any measure worktree with the rest of the task scratch.
