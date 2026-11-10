---
name: supervise-panes
description: Own authorized outcomes with hand-supervised workers in Herdr or terminal panes, using judgment about delegation, review, and integration while keeping a durable task record. Use when the user wants to run or supervise pane agents or continue an older manual coordinator task. Not the default for one cohesive piece of work, where one agent with a goal file and its own subagents is faster. Headless or native-agent delegation is the delegate skill's driven runtime, which the user starts with /delegate.
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

## First: does this need a team?

For one cohesive piece of work, the default is one strong agent with a goal file
([template](../coordinator-setup/assets/goal-template.md)) that spawns its own
subagents, one per area, each on its own branch and worktree. In the one
measured comparison ([incident](../../incidents/2026-11-04-team-of-lanes-vs-one-agent.md))
that shape out-produced an eight-lane team with almost no coordination traffic
and no owner input.

Supervise panes only when at least one of these holds:

- the deliverables are separate and share no files;
- the workers must run on another subscription or harness, so they live in panes;
- you want an independent review from a model that hasn't seen the builder's reasoning;
- the work outlasts one context and needs a record another agent can resume.

If none holds, write the goal file and hand it to one agent instead.

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
- After an error or timeout, look at what actually happened (processes, files,
  partial output) before retrying. A sent message isn't proof the worker got it,
  and silence isn't proof it didn't.
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
For several pane workers over hours, run one [control-plane loop](references/control-plane-loop.md).

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

## Lessons from running a large team

These come from a two-week, eight-lane rewrite, revised after its last five days. The incidents are in [team lessons](references/team-lessons.md).

- **Judge the product, not the pipeline.** Green suites, closed jobs and busy lanes say nothing about what the user sees. Regularly have the shipped build used as a user would, by someone without context, against the reference behaviour. Agents doing their own jobs on the build count as stability soak only.
- **Behaviour questions aren't yours to settle by preference.** When a tester, builder or reviewer prefers different behaviour, the spec (or, for a port, the old system) decides. Grade it: behaviour, requests, effects and speed are exact; transient frames and glyphs don't block. Tell the owner, unprompted, what you are copying that looks like a bug. If neither does, ask the owner asynchronously and act on the spec-matching default meanwhile. Never rule "two preferences, not a defect".
- **Verify continuously.** Deferring checks to a late milestone was the costliest decision. Keep cheap guards on every commit and the main acceptance check on every candidate.
- **Acceptance comes only from an execution-capable verifier running the exact commit.** Give verifiers shell and write access before dispatch, and label read-only review as such.
- **One owner per file, seam and shared resource, and one integrator writing the candidate.** Post the overlap before editing a shared hot file. Between peer lanes this rule also left lanes idle waiting on each other; it worked best with the owners as subagents under one head.
- **Gate heavy and timing-sensitive runs on measured load and disk,** and serialize scored runs. Contended results are noise and can't be attributed.
- **Check another lane's claim against source before building on it or repeating it.** This applies to your own claims too: correct them publicly.
- **Put the strongest available model where the goal is held and the work is done.** A strong dispatcher over cheaper builders is the shape that lost to one strong agent with subagents. If you do run a dispatcher, it still needs the strongest model: in a blind exam, Opus scored 8.6 vs 5.8–7.4 for the others, and a weak coordinator leaves lanes idle. A model that tests badly as a coordinator can still be an excellent debugger.
- **Watch for the signal to collapse the team.** If the open backlog grows over a day, or nudges outnumber landed commits, stop adding process and fold the work into one agent.
- **Workers never run on the build being changed.** Its bugs took lanes down five times in one day.
- **The test command names the binary under test.** An environment default let every lane test the old CLI for a week after the trap was written down.
- **Check what a number counted before acting on it.** "56/56", "35–50 idle hours" and "37% coordination" were all softer than they sounded.
- **Removing beats adding.** Process fixes that deleted mechanism held up. Fixes that added schedulers, timing windows or extra gates often backfired. Give every new gate a removal path.

## References

Read the operational reference for the action you are taking, not a ritual tour
of every reference at every stage.

| Reference | Use |
| --- | --- |
| [Task state](references/task-state.md) | Entry, resume, ownership, and persistence |
| [Communication](references/communication.md) | Briefs, review, and result contracts |
| [External agents](references/external-agents.md), [Inbox](references/inbox.md), [Worker observation](references/worker-observation.md) | Pane dispatch, return-only sinks, delivery recovery, and waits |
| [Control-plane loop](references/control-plane-loop.md) | One long-running loop for several pane workers: forwarding, dispatch, nudges, CI, shipping |
| [Team lessons](references/team-lessons.md) | Evidence behind "Lessons from running a large team" |

## Write plainly

Briefs, notes and updates are read by someone who wasn't there: a fresh worker,
the user, or a later session. Use plain words and full sentences. Call things
what they are ("the Discord prompt fix"), not by internal handles; include an ID,
path or commit only when the reader needs it to act. Say what happened and
what's next, and skip process narration.

## Report the result, not the ceremony

Include the task ID/record, actual outcome or next owned action, checks and who
ran them, limitations, and any precise blocker. Do not describe checkpointing as
execution. For research with no actionable finding, say so and identify the
evidence searched. For small authorized work done directly, report “worked
directly, no delegation” with its evidence; do not invent workers.
