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

## Judgment within safety boundaries

Distinguish **invariants** from **mechanisms**. Authority, attributable ownership,
lossless preservation, required review, actual verification, and durable recovery
are invariants. Worker count, scouting, milestones, extra reports, and observer
snapshots are mechanisms to choose when they help. The established task's helper
contracts remain binding; “use judgment” is not permission to bypass a gate.

- Stay within user authority, including role and harness/provider/model limits.
  A configured route, discovered solution, protocol, or heal grants no new scope.
  Record concrete route identity and its actual authorization source before
  dispatch; never silently substitute an explicit user choice. Honor billing
  boundaries: obtain permission for paid usage or an unclear billing route.
- Give each outcome one accountable owner and isolate modifying workers, or use
  disjoint write ownership and serialize shared mutations. Keep upstream callers,
  return-only inboxes, and protected human panes out of the worker pool. A report
  is not proof a worker is idle; stop or verify idle before editing its branch.
- Preserve unrelated work. Establish what must survive before inspecting a
  protected checkout. If exact bytes/index preservation is required, capture the
  entry oracle and recoverable originals before any Git inspection; inspect a
  disposable copy with its own/copied index (`GIT_INDEX_FILE`), not the protected
  index. Observational Git can refresh index bytes even with optional locks off.
  A late snapshot proves only later consistency; changed index stats are not
  proof of lost staged content. For overlapping dirty work, rehearse lossless
  reconciliation in isolation and retain independent preservation review. Never
  reset, overwrite, stash away, or commit unrelated work for convenience.
- Preserve uncertain launches and delivery. After an error or timeout, inspect
  recorded operations, resources, and partial output before retrying. Transport
  acceptance is not admission; silence is not affirmative non-delivery.
- Accept evidence, not assertions. Keep required independent source/behavior and
  merge-preservation review, claimcheck, combined-result verification, and the
  [risk-based real-use policy](references/real-use-verification.md). Helper success, a review
  verdict, process exit, or a quiet pane alone proves none of these.

On an observed failure, use [bounded recovery](references/healing.md), not a blind
retry or an in-flow rewrite of the governing rules.
The memory sidecar remains disabled; write material decisions into task notes.

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
work. Keep required intent/ownership checkpoints and publish updates alongside
execution, not instead of it.

## Choose the smallest effective ownership structure

Recover the observable goal, rationale, criteria, non-goals, constraints, and
authority before assigning work. Treat suggested implementations as hypotheses.
Inspect enough of the system to avoid dividing work across an unknown shared
contract; settle material interfaces with an owner and affected consumers.

Keep discovery, implementation, focused checks, and authorized integration with
one cohesive owner when that preserves useful context. A read-only scout does
not acquire write authority: give a new bounded assignment when changing its
scope. Split work at independently useful seams, not merely different files or
stages. Add lane owners or milestones only when dependencies or scale warrant
them. Use a fresh context when independence or exhausted context is the point,
not automatically at each checkpoint.

Routine checks—reading an exact report path, checking cwd/Git root, resolving a
cited file, checking receipt identity, or comparing timestamps—are coordinator
work. A worker's “file missing” report calls first for narrow path/access/context
reconciliation, not a reviewer of the report and then a reviewer of that review.
If the discrepancy reveals a real source or preservation question, route that
substantive question for investigation or independent review. Direct bookkeeping
does not override a task's restriction on substantive coordinator work.

Use independent review where consequence, uncertainty, or integration risk is
material, and wherever the task or project requires it. Give the reviewer the
artifact, goal, constraints, and raw evidence before the builder's conclusions;
keep the rationale available for a second pass. Use `finding-triage` for reviewer
briefs and findings. Ask for reachable defects against the criteria, not a quota
of findings. Packaging-only corrections normally need direct inspection and the
relevant check, not recursive review. New source changes or unresolved substantive
findings still need their required review.

## Use durable contracts without turning them into the plan

At entry, read [Task state](references/task-state.md) and the
[host profile](../delegate/references/host-profile.md). Use `coordinator-setup`
if required host capabilities are missing or changed; bundled persistence needs
Unix locking and the process runtime is Linux-only. For a resumed task, run
`coord_state.py resume --task <id>`, load the full record, reconcile workers and
incomplete operations, then claim or take over with current owner/revision.
Saved checks and commits since update are staleness evidence, not live status.

Keep a concise snapshot of goal, authority, selection, owned work, decisions,
blockers, evidence, and next action. Link reports rather than copying a diary.
Checkpoint intent before dispatch or consequential actions, material changes,
integration before dependent work, and the next action before ending a session.
Capture actual coordination incidents at the next checkpoint per
[Retro](references/retro.md), not a retrospective for every normal transition.

Before dispatch, verify configured route availability and record the selected
pool using [Choice history](references/choice-history.md). Already authorized
repairs allow coordinator selection of an implementation-appropriate configured
route without a new approval pause, unless explicit route/role or billing limits
forbid it. Record the new implementation selection and its reason; do not reuse a
review-only dispatch or relabel review confirmation as implementation approval.
Preserve explicit model restrictions and same-task selections for unchanged roles;
history alone authorizes neither a route nor paid usage. Use
[Decision policy](references/decision-policy.md) for genuinely missing authority.

New delivery work with runnable checks uses [Outcome contracts](references/outcome-contracts.md).
Existing records retain their workflow; do not replace one merely to simplify
bookkeeping. For outcome-plan dispatch use [Runtime contracts](references/runtime-contracts.md)
only on the task's supported surface. Those references describe binding APIs,
not compulsory extra workers or reviews.

For assignment and return contracts, read [Communication](references/communication.md)
and, for pane workers, [External agents](references/external-agents.md),
[Inbox](references/inbox.md), and [Worker observation](references/worker-observation.md).
Keep generated descriptors and reports unchanged. Bind returned handles immediately
and confirm admission through supported receipts or worker activity, not an
acknowledgement request. Long briefs belong in files. Select any needed engineering
method through [Execution protocols](references/execution-protocols.md).

Wait through the supported background watcher, not repeated pane polling. Inspect
notification bodies and live workers on wake, resolve actual blockers, and leave
active owners alone. If evidence invalidates an assumption or contract, hold its
transitive dependents—including accepted results needing revalidation—revise
within authority, and continue independent work. Neither replanning nor healing
authorizes weaker criteria.

## Accept, integrate, and finish the goal

Inspect the actual artifact and checks, map assigned deliverables to changed
behavior, and resolve blocking findings. Run
`<delegate-dir>/scripts/coord_claimcheck.py --cwd <assigned-cwd> --report <report>`
before accepting each report; unresolved cited commits or test paths block
acceptance. Run the same gate on the base branch before calling a failure
pre-existing. Exercise the real boundaries the change touches and distinguish
fixtures, worker reports, independent checks, and unrun verification.

Incorporate compatible accepted results as soon as safe and authorized; avoid
batching them behind unrelated stages. For outcome plans, use `verify`, `accept`,
`integrate`, and `verify-goal` as specified by the contract. Workers and protocol
reports cannot accept themselves. Checkpoint actual integration before dependent
work; verify the combined result against live consumers, all goal criteria,
non-goals, and constraints. If anything remains, continue the ownership loop
above. Passing component tests or completing the last brief is not goal success.

Completion requires verified goal criteria, passed claimchecks, resolved required
decisions and blockers, any explicitly requested or consequential real-use checks
satisfied, and owned workers/background processes reconciled and exited.
If blocked, report a resumable blocked outcome, not successful completion.
Preserve reports/inboxes/artifacts before retiring workspaces; remove a worktree
only after the worker stops or is verified idle, never on a report signal alone.
Reuse a suitable tree by fast-forwarding from the base branch. Stop or close only
task-owned resources, and checkpoint the final outcome or precise next action.

## References

Read the operational reference for the action you are taking, not a ritual tour
of every reference at every stage.

| Reference | Use |
| --- | --- |
| [Task state](references/task-state.md), [Host profile](../delegate/references/host-profile.md) | Entry, resume, ownership, persistence, and host capabilities |
| [Choice history](references/choice-history.md), [Decision policy](references/decision-policy.md) | Route identity, authorization, material assumptions, or human input |
| [Outcome contracts](references/outcome-contracts.md), [Runtime contracts](references/runtime-contracts.md) | New delivery contracts and supported attempt APIs; not a runtime migration |
| [Communication](references/communication.md) | Briefs, evidence, review, and result contracts |
| [External agents](references/external-agents.md), [Inbox](references/inbox.md), [Worker observation](references/worker-observation.md) | Pane dispatch, return-only sinks, delivery recovery, waits, and preservation |
| [Routing](references/routing.md) | Capability/risk, capacity, and worker reuse decisions |
| [Large work](references/large-work.md) | Real dependency waves, shared contracts, or lane supervision |
| [Execution protocols](references/execution-protocols.md) | Select a task-specific engineering method |
| [Real-use verification](references/real-use-verification.md) | Risk-based activation policy and a separate exercise when useful or required |
| [Operational status](references/operational-status.md), [Healing](references/healing.md), [Retro](references/retro.md) | Optional integration status, authorized repairs, and evidence-backed lessons |

## Report the result, not the ceremony

Include the task ID/record, actual outcome or next owned action, checks and who
ran them, claimcheck result, limitations, and any precise blocker. Do not describe
checkpointing as execution. For research with no actionable finding, say so and
identify the evidence searched. For small authorized work done directly, report
“worked directly, no delegation” with its evidence; do not invent workers.
