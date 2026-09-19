# Optional external-agent branch

Use this branch only when a native worker surface cannot provide a distinct
harness, persistent terminal context, unsupported capability, durable lane, or
terminal-level isolation. The coordinator still owns scope, authority,
dependency ordering, acceptance, and synthesis.

Read [Routing](routing.md) before selecting an external worker. When using
Herdr, discover and read the installed `herdr` skill through the current skill
catalog for prompt admission and lifecycle operations. This package does not
assume a sibling install path. If that skill or a required adapter is absent,
use a verified native route or work directly; preserve unresolved external
requirements as blockers.

## Keep the topology shallow

Use the smallest structure that fits the work:

1. The coordinator translates the outcome into bounded work and verifies it.
2. Add a lane owner only when a durable or concurrent workstream needs ongoing
   supervision.
3. Give each worker one bounded brief and one accountable owner.

Topology never grants authority. Declare two disjoint sets before dispatch:
**sinks** receive blockers, progress, or completion and are never assigned work;
**workers** may receive bounded assignments and must not include the upstream
caller, its return inbox, or a protected human-facing pane.

## Preflight and selection

Run the bundled helper's `doctor` before dispatch. It reports whether the core
Python workflow and built-in file inbox are available and whether the optional
Herdr adapter is configured. Run `inventory` only when the harness adapter is
available. A missing binary, incompatible command, or unavailable live agent
means the capability is unknown or unavailable; report that state and use a
native surface or direct work when possible.

Prefer native subagents for bounded work without persistent terminal state.
Use a configured external adapter for a distinct harness or durable context.
Create a new terminal surface only when persistence or isolation is material.
Record a fresh capacity envelope: session, harness/model, quota owner and
limit, usage/reset, context usage/limit, handoff reserve, telemetry source and
time, active work, and declared children. Record missing data as `unknown`.

## Dispatch and supervise

Resolve `<skill-dir>` to this installed coordinator directory. The helper's
`inventory` reports configured and live capabilities. `run-task` composes sink
setup, worker provisioning, non-blocking admission, file-inbox harvesting, digest
verification, reconciliation, and cleanup. Use the parent durable task ID as `--task-id`, including for milestone runs, and a
coordinator-owned check as `--verify-command '["program","arg"]'`. Reports copy
both from the generated assignment descriptor. The helper runs that argv without
a shell under a hard timeout. File artifacts must remain under the assigned `--cwd`. Pass
`--min-children 1` only when the assigned role must delegate; otherwise direct
execution by that worker is valid. Lower-level commands support recovery.

Use `python3 <skill-dir>/scripts/coord_lifecycle.py` from any working directory
for lifecycle mechanics. Bind lifecycle state to the durable task and pass the
current owner/revision as described in [Task state](task-state.md#bind-lifecycle-actions-to-ownership). Set `COORDINATOR_HERDR_HELPER` to the absolute path of
`scripts/herdr_worker.py` in the installed Herdr skill (or install it as
`herdr-worker` on PATH). `COORDINATOR_HERDR` optionally selects the underlying
Herdr executable. The helper never searches sibling
packages. A missing adapter blocks Herdr operations while the file-inbox,
`doctor`, and digest-verification commands remain usable.

Read [File inbox](inbox.md) before dispatch. It owns report publication,
unread/read/processed state, explicit acknowledgement, and the background Bash watcher.
For multi-day work, use the lower-level prepare/start/dispatch/receive commands
and preserve the lifecycle file alongside task state. `run-task` is a bounded,
synchronous convenience that cleans up resolved failures and preserves uncertain
launches/submissions for recovery; it is not
a multi-day supervisor. Both `start-worker` and `run-task` require `--kind` and `--model`.
Pass the selected `--provider` and `--effort` where applicable. The Herdr helper
supports explicit launch routes for Term2, Pi, Codex, Claude, and agy; it rejects
unsupported routes before creating a tab. Term2 and Pi require a provider;
Claude and agy use their configured provider environments and reject `--provider`.
The launch receipt records these settings and opaque pane/tab IDs. A ready
receipt confirms harness readiness. Route provenance comes from explicit launch
arguments and the harness's banner/configuration, not the model's self-report.
Worker-authored acknowledgements establish receipt of the assignment, not model
identity.

The coordinator delegates terminal operations to that helper. Use its `read`
and `steer --message-file` for supervision, targeting the recorded pane ID.
Use `observe <pane-id>` at fallback check-ins: it combines lifecycle state with
current visible output. Its Term2 `approval_suspected` signal recognizes a
whitespace-normalized approval menu even when lifecycle status says `working`.
It is a heuristic for inspection, never authorization to send approval keys.
Old scrollback markers do not establish a current blocker. For other harnesses,
inspect the returned visible text; no approval detector is claimed.
Term2 uses verified TUI input; other supported harnesses use agent prompting.
Delivery, admission, and acknowledgement are separate receipt states.
Failed launches preserve their resources and recovery receipt. Inspect those
resources before retrying; a recorded worker name cannot be silently relaunched.
Use `recover-worker --state <path> --worker <name> --owner <session-token>
--revision latest` to reconcile recorded resources without restarting them.
A recovered ready worker clears active launch errors but retains the resolution
in event history. If startup is still in progress, `start_unknown` is truthful:
inspect the pane, use the Herdr helper's bounded `wait <pane-id> --until idle`
for the already-starting harness, then recover again. Do not launch a duplicate
or use an arbitrary sleep. An empty CLI acknowledgement is handled only for known Herdr
input commands; unexpected responses retain operation, exit code, stdout, and
stderr in the launch receipt.
Closing requires a settled worker and a task-owned tab containing only that pane.

Before assigning an implementation writer, confirm authority and lane
ownership, and record the exact touch set. Long prompts MUST be written to a
readable file first, then send a short instruction with its absolute path,
avoiding shell escaping and terminal truncation. Name the return-only sink, and
require a digest-bearing completion report. Dispatch without an inline
completion wait. Observe at most one bounded, attributable admission transition,
then run the file-inbox Bash watcher as a harness-managed background job.

Establish the inbox and background watcher before waiting for worker reports.
The assignment names the worker's inbox path and exact run, task, and assignment
IDs. The helper's dispatch contract provides a `report` command whose generated
assignment descriptor supplies the protocol fields. A terminal lifecycle transition can prompt inspection, but does not prove
that the requested result was produced.

Recompute artifact digests within the assigned working directory, inspect the
artifact, and execute the coordinator-owned verification argv under a hard
timeout. Reconcile named children against live harness state and require them to
be settled before acceptance. Reject stale or mismatched reports by their
recorded assignment and run; checkpoint their disposition before acknowledging
them. Read and processed states are transport bookkeeping, not acceptance.

## Preserve context and accept

Reuse a worker context for corrections and re-review of the same task. Before
an unrelated task, harvest artifacts and reconcile declared children. Protect
panes where a human may be typing; never focus, key-send, or poll them as a
substitute for the declared return sink.

Close the branch only after the artifact and digest are independently verified,
declared children and background processes are reconciled, identity and
touch-set ownership still match, focused and required boundary checks pass,
findings are resolved, and the accountable owner records acceptance. Keep
`finished`, `verified`, `accepted`, `integrated`, and `cleanup` distinct.

## Manual verification commands

Prefer lifecycle `verify`, which captures a subprocess exit status directly.
For a manual gate in Bash or zsh, avoid shell-specific pipeline status arrays:

```sh
python3 -m unittest discover > "$gate_log" 2>&1
gate_status=$?
cat "$gate_log"
printf 'gate_exit=%s\n' "$gate_status"
```

Set `gate_log` to a task-owned file first. Capture the status immediately and
record the actual command, output, and numeric exit status. A blank status or
empty log is not a passing check. In scripts using `set -e`, place the command
in an `if` block to capture failure before the shell exits. Use bounded lifecycle
waits and harness-managed background jobs instead of fixed sleeps between
worker checks.
