# Worker observation and runtime mechanics

Read this before supervising persistent terminal workers or file-report watchers.
Native host workers use the host wait/inspection tools; process-runtime workers use
receipts and process identity through `coord_runtime.py observe`.

Arm one background wait on a report file or process exit, debounced across
status flips such as a brief `done` between tool calls, and confirm that wake
fires before relying on it. For Herdr workers, the wait must also watch
lifecycle status, because a worker can end its turn without writing the
report: run `python3 <skill-dir>/scripts/watch_workers.py watch --state
<task-dir>/watch-state.json --worker <pane>=<report> --worker-progress
<pane>=<worktree> --worker-progress <pane>=<report-or-output> ...` in the
background. Associate each worktree and report/output path only with its
worker; `--progress-path` is accepted for a single-worker watch and rejected
for multi-worker watches (use `--worker-progress PANE=PATH`).
It wakes on any unread report, on a sustained non-`working` status without a
report (stall), or on a frozen footer while `working` (no_progress), and lists
every event at once.
Without `--follow` the watcher exits after its first wake and must be re-armed
each time, so a report that lands while you are busy can go unseen. Prefer
`--follow` under the Monitor tool: it stays alive, prints each new report,
stall, or no_progress event once as its own line, and exits with an
`all_reported` line when every worker has reported (or on timeout), so nothing
needs re-arming per event. Monitor caps a run at 30 minutes, so re-arm only on
its expiry notice; unread reports are re-announced then.
<!-- lesson: watcher-follow-mode promoted 2026-09-30 --> Reports stay unread until `watch_workers.py mark-read
--state <same> <report>`, so a report that lands while you are busy fires on
the next run; mark it read only after reading it. Each wake starts with a
`wake` line giving the current time and how long the watch waited; use it to
judge elapsed time before acting. <!-- lesson: watch-herdr-status promoted 2026-09-27 --> On every wake, run `date`, sweep every live worker
and report mtime, and read every notification's output before steering,
merging, or closing; then reconstruct the run from its transcript and logs.
Use this wait in place of a fixed sleep or a pane poll. <!-- lesson: one-wait-not-poll promoted 2026-09-26 --> <!-- lesson: wake-sweep promoted 2026-09-26 -->
A running watcher does not prove worker activity. Leave its script unchanged
while it runs, re-arm it after it exits, and anchor pane-scraping patterns to
error phrasing rather than a bare number. <!-- lesson: watcher-hygiene promoted 2026-09-26 -->
If a completion marker can be omitted, the same wait is the fallback check-in:
inspect activity then, and leave active workers alone. Resolve a blocker or
revise an assignment before retrying failed work.
Treat `blocked` and `unknown` events as coordinator work: answer only decisions
covered by recorded authority; otherwise escalate the exact blocker. After
assessing a report, mark it read and remove that worker from the next watch map;
retire its watcher so stale completion notices cannot re-enter. On every stall or
unknown event, compare report/output, commit, and worktree activity since the
last checkpoint; a quiet footer alone does not establish no progress. Record
`last_progress_at` when evidence changes.
A stall whose pane shows an upstream provider error (`service_unavailable_error`,
the TUI's `Use /retry-turn` hint) is a worker parked at its prompt, not a
finished one: steer `/retry-turn` + Enter at the idle prompt to resume it,
confirm the turn restarts, and re-dispatch only if the retry fails again.
<!-- lesson: upstream-error-retry-turn promoted 2026-09-29 -->
After each checkpoint publish an observer snapshot with
`python3 <skill-dir>/scripts/coord_progress.py --state <task-dir>/state.json`;
it exposes phase, next_action, worker locators/status/progress time with
dispatch→report and report→merge durations, merges, and done/total.

Decide steerability at dispatch. For a dispatch or mid-flight correction,
confirm receipt from the worker's subsequent activity or a supported delivery
receipt; never ask the worker to reply with an acknowledgement, which some
models send and then stop. <!-- lesson: no-ack-request promoted 2026-09-27 --> Missing text in
stdout leaves delivery unconfirmed unless the harness guarantees complete input
logging. Reconcile worker activity and partial output before relaunching a task
that cannot accept corrections.
