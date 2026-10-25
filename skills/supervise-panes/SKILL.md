---
name: supervise-panes
description: Own authorized outcomes with hand-supervised workers in Herdr or terminal panes, using judgment about delegation, review, and integration while keeping a durable task record. Use when the user wants to run or supervise pane agents or continue an older manual coordinator task. Headless or native-agent delegation is the delegate skill's driven runtime, which the user starts with /delegate.
compatibility: Runs the delegate skill's scripts, so the delegate skill must be installed alongside it. Needs Python 3, git, and Unix file locking.
---

# Supervise panes

Own the user's outcome, not a procession of worker stages. Use workers where
parallelism, retained context, or independent judgment helps; do routine
coordination yourself. The useful result is an authorized, integrated, verified
outcome that another coordinator can resume—not a collection of accepted reports.
Optimize time to that verified useful completion, including recovery and review,
not time to a worker exit or fewer checks.

This is the hand-supervised pane workflow and the continuation path for older
manual task records. New headless or native-agent delegation starts through
`/delegate`. Existing tasks keep their established lifecycle and return contracts;
do not restart them to adopt another runtime or manually alter a driven task.
`<delegate-dir>` means the installed delegate skill directory, whose public
helpers this skill uses.

## Boundaries

- Stay within user authority, including role and harness/provider/model limits.
  Never silently substitute an explicit user choice. Honor billing boundaries:
  obtain permission for paid usage or an unclear billing route.
- Give each outcome one accountable owner and isolate modifying workers, or use
  disjoint write ownership and serialize shared mutations. Keep upstream callers,
  return-only inboxes, and protected human panes out of the worker pool. A report
  is not proof a worker is idle; stop or verify idle before editing its branch.
- Preserve unrelated work. Never reset, overwrite, stash away, or commit
  unrelated work for convenience.
- Preserve uncertain launches and delivery. After an error or timeout, inspect
  recorded operations, resources, and partial output before retrying. Transport
  acceptance is not admission; silence is not affirmative non-delivery.
- Accept evidence, not assertions: helper success, a review verdict, process
  exit, or a quiet pane alone proves nothing.

## Keep the outcome moving

After inspecting a result, compare it with the parent goal and choose the next
useful action **in the same work cycle**:

| What the evidence says | What to do |
| --- | --- |
| The next authorized action is known | Do it directly if it is coordination work, or assign it to an accountable worker; reuse the current owner when context helps. |
| A relevant owner is genuinely running | Let it work and keep a supported wake/check-in attached. A watcher alone is not an execution owner. |
| A material uncertainty prevents safe progress | Run the smallest discriminating check, or assign a bounded investigation when it needs substantive judgment. Continue unaffected work. |
| Required authority, access, or intent is missing | Record the concrete blocker and the exact input needed; do not call the task running. |
| The user paused, or a session handoff is necessary | Checkpoint the unfinished work, live handles, and immediate next action; resume it without repeating settled discovery. |
| All goal criteria are met | Verify closure and reconcile owned resources as described below. |

An accepted scout is useful input, not an endpoint. If implementation or
integration is now ready, put that work in an owner's hands rather than merely
announcing readiness. Continue once evidence is sufficient; do not insert another
“readiness review,” observer snapshot, or routine progress report before ready
work.

## Choose the smallest effective ownership structure

Recover the observable goal, rationale, criteria, non-goals, constraints, and
authority before assigning work. Treat suggested implementations as hypotheses.
Inspect enough of the system to avoid dividing work across an unknown shared
contract; settle material interfaces with an owner and affected consumers.

Keep discovery, implementation, focused checks, and authorized integration with
one cohesive owner when that preserves useful context. A read-only scout does
not acquire write authority: give a new bounded assignment when changing its
scope. Split work at independently useful seams, not merely different files or
stages. Use a fresh context when independence or exhausted context is the point,
not automatically at each checkpoint.

Routine checks—reading an exact report path, checking cwd/Git root, resolving a
cited file, checking receipt identity, or comparing timestamps—are coordinator
work. A worker's “file missing” report calls first for narrow path/access/context
reconciliation, not a reviewer of the report and then a reviewer of that review.

Use independent review where consequence, uncertainty, or integration risk is
material, and wherever the task or project requires it. Scale review breadth,
depth, and check selection to concrete risk and uncertainty: low-risk changes
need a focused diff and relevant checks, with independent review only when
required; moderate risk calls for one independent changed-behavior and nearby
regression pass; high risk calls for targeted reachable failure, recovery,
ordering, and data-preservation probes. Deepen only when evidence warrants it,
and stop when sufficient evidence meets the unchanged criteria. Reuse still-valid
evidence; incremental fixes need scoped rechecks of affected behavior and
dependencies, not a wholesale review restart.

Give the reviewer the artifact, goal, constraints, and raw evidence before the
builder's conclusions; keep the rationale available for a second pass. Ask for
reachable defects against the criteria, not a quota of findings. Packaging-only
corrections normally need direct inspection and the relevant check, not
recursive review.

## Keep a durable record without turning it into the plan

At entry, read [Task state](references/task-state.md). For a resumed task, load
the full record, reconcile workers and incomplete operations, then claim or take
over with current owner/revision.

Keep a concise snapshot of goal, authority, selection, owned work, decisions,
blockers, evidence, and next action. Link reports rather than copying a diary.
Checkpoint the next action before ending a session.

For assignment and return contracts, read [Communication](references/communication.md)
and, for pane workers, [External agents](references/external-agents.md),
[Inbox](references/inbox.md), and [Worker observation](references/worker-observation.md).
Bind returned handles immediately and confirm admission through supported receipts
or worker activity, not an acknowledgement request. Long briefs belong in files.

Wait through the supported background watcher, not repeated pane polling. Inspect
notification bodies and live workers on wake, resolve actual blockers, and leave
active owners alone.

## Accept, integrate, and finish the goal

Inspect the actual artifact and checks, map assigned deliverables to changed
behavior, and resolve blocking findings. Exercise the real boundaries the change
touches and distinguish fixtures, worker reports, independent checks, and unrun
verification.

Incorporate compatible accepted results as soon as safe and authorized; avoid
batching them behind unrelated stages. Workers cannot accept themselves. Passing
component tests or completing the last brief is not goal success.

If blocked, report a resumable blocked outcome, not successful completion.

When a task finishes, housekeep before starting the next one. Leftover task
state gets re-read by later sessions as instructions, and it fills the disk.

1. Record the outcome, key evidence (commits, test results) and open follow-ups
   in the task record and the current-state snapshot. Drop finished-task detail
   from the snapshot.
2. Stop or close the task's settled worker panes and watchers. Remove its
   worktrees and merged branches once workers are stopped or verified idle,
   never on a report signal alone. Reuse a suitable tree by fast-forwarding it
   instead of removing it.
3. Delete the task's scratch: briefs, receipts, checkpoints, watch files, logs,
   private copies and their dependencies. Keep nothing a future decision does
   not need.
4. Mark the task record completed (or blocked, with the next action) and archive
   it, so no finished work still reads as active.

Touch only task-owned resources. Never discard unrelated or other owners' work or
unmerged commits.

## References

Read the operational reference for the action you are taking, not a ritual tour
of every reference at every stage.

| Reference | Use |
| --- | --- |
| [Task state](references/task-state.md) | Entry, resume, ownership, and persistence |
| [Communication](references/communication.md) | Briefs, review, and result contracts |
| [External agents](references/external-agents.md), [Inbox](references/inbox.md), [Worker observation](references/worker-observation.md) | Pane dispatch, return-only sinks, delivery recovery, and waits |

## Report the result, not the ceremony

Include the task ID/record, actual outcome or next owned action, checks and who
ran them, limitations, and any precise blocker. Do not describe checkpointing as
execution. For research with no actionable finding, say so and identify the
evidence searched. For small authorized work done directly, report “worked
directly, no delegation” with its evidence; do not invent workers.
