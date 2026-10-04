---
name: coordinator
description: Coordinate work through bounded delegation, dependency management, verification, and integration. Use when the user asks to orchestrate workers or subagents, or when substantial independent work benefits from supervised delegation.
---

# Coordinator

Native coordination uses the available worker tools. The optional external-agent
helper uses Python's standard library and explicitly configured harness adapters.

Own the goal, plan, assignments, verification, and integrated result. Workers
own bounded outcomes. Revise the plan when evidence changes; preserve the
authorized goal and success criteria unless the user changes them.

The main agent maintains durable task state on disk with `scripts/coord_state.py`. Read
[Task state](references/task-state.md) and [Memory sidecar](references/memory-sidecar.md) at task entry: create and own a record for new
work or load, reconcile, and claim the existing record before continuing. Keep
it as a current snapshot of the goal, acceptance criteria, authority, owned
work, blockers, evidence, and next action. Update it when one of those changes
and before ending a session. Link to worker reports and artifacts instead of
copying a running narrative into the record.

The memory sidecar is **paused** (2026-09-28): its judge runs as a full term2
agent and can act on transcript content. Don't bind sessions, install its hooks,
or run `coord_memory.py flush`. Write decisions into task-state `notes` by hand.
See [Memory sidecar](references/memory-sidecar.md).
On resume, run `coord_state.py resume --task <id>` first and treat its
`commits_since_update` and `checks` as evidence that the record may be stale
before acting on `next_action`.
Reconcile every still-running worker and watcher from the saved `workers` and
`background_work` lists (pane, worktree, report, watch-state path); restore
those lists before deriving any new locator.

When continuing in a fresh chat, locate the unfinished task record by task ID,
conversation, or project; a pasted handoff can provide a shortcut. Recover the
original goal, rationale, acceptance criteria, authority, decisions, and
unfinished work from that record before acting on its `next_action`. After
finishing that action, choose the next action against the original goal and keep
going within existing authority. Completing the saved next action does not
complete the task; verify the goal or identify a specific unresolved blocker
before stopping work on it.

## 1. Establish the goal and decision policy

Identify the target project, desired observable outcome, why it matters,
success criteria, constraints, non-goals, and existing authority. Separate the
user's need from a suggested implementation so a failed approach does not erase
the goal. Infer these from the request and available evidence; ask a focused
question only when missing information blocks useful work or makes a wrong
assumption consequential. State the resulting understanding concisely; require
confirmation only for a material unresolved choice.

- **Research** returns knowledge or recommendations. A discovered solution does
  not itself authorize implementation.
- **Delivery** produces an authorized change or consequential output.
- **Provisioning** sets up workspaces, panes, or sessions for human use. Perform
  it directly with the relevant tools or installed tool skill.

Before starting each new coordinated task, read the recent choices using
[Choice history](references/choice-history.md), inspect available options, and ask
the user to choose the harness and model (or a harness/model pool for multiple
workers). Present verified available choices and a recommendation, then wait
for their selection before execution or worker dispatch. Scope clarification,
read-only capability discovery, and task-state bookkeeping may proceed while
the choice is pending.
An explicit harness/model choice in the current task request, including “same
as previous” resolved against that history, satisfies this step. History alone,
defaults, and running workers do not authorize a selection. Record each confirmed
choice so it can be reused in later tasks.
Keep the choice for follow-ups within the same task. If it becomes unavailable
or needs to change, ask the user to choose a replacement before continuing.
A choice covers only the roles it was confirmed for, such as review or
implementation. When a task adds a role, such as a review turning into fixes,
ask for that role's selection before dispatch, recommending the user's recent
choice for that role. <!-- lesson: pool-scoped-to-role promoted 2026-09-27 -->

Establish how to decide under uncertainty using existing user preferences and
authority. Read [Decision policy](references/decision-policy.md) before work
begins; it defines when to decide and log, batch questions, or seek input.
Record the goal, criteria, non-goals, and policy in task state. This step is
complete when the outcome is checkable and the authorized scope and decision
boundaries are clear enough for the next work.

## 2. Understand, then decompose

Inspect the relevant system and evidence before dividing implementation.
Identify unknowns that could change task boundaries, shared interfaces, or the
proposed solution. Resolve those through focused investigation, directly or
with bounded read-only scouts in the selected pool. Implementation can proceed
where it is independent of the unknowns. Finish investigation with findings,
remaining uncertainty, and the implications for the plan.

Decompose into outcomes that each serve the goal, with exactly one accountable
owner per active outcome. Contributors and reviewers do not share that
accountability. Split along seams where each piece can merge on its own and is
checked against the real boundary (not only stubs): splitting by file can turn
one contract into a mismatch between two workers, and disjoint files alone do
not establish independence. Resolve shared decisions before dependent work
starts: record the agreed interface, schema, or behavior, its owner, and
affected work items. Workers can propose a contract change; its owner
coordinates affected consumers before adopting it.
After each merge, verify the combined result against its live consumers: each
slice being green is not the same as the whole working.
<!-- lesson: decompose-at-mergeable-seams promoted 2026-09-29 --> <!-- evidence: tonight's heals: phase required by SKILL.md rejected by coord_state.py; watcher CLI change broke live orchestrator -->

Delegate substantial bounded work when startup and integration costs are
justified by speed, specialization, or independent validation. Work directly
when the task is small, suitable workers are unavailable, or shared-state risk
dominates. Do glue work and final synthesis yourself.

Inspect available worker tools and their actual capabilities. Recommend native
workers for ordinary bounded assignments when suitable, and route within the
user's chosen harness/model pool. For repeated or concurrent dispatches, spread
them across the available pools the local [host inventory](references/host-inventory.md)
lists: run `scripts/coord_route.py pick --dry-run`, check the chosen
candidate's quota and availability, record the pick without `--dry-run` or
exclude the candidate and re-pick, unless a task's risk calls for one specific
model. Keep assignments within known limits;
split work when needed. Missing optional quota telemetry alone does not block
routine native delegation.

Read additional guidance only for the applicable branch:

- [Routing](references/routing.md) when choosing between model groups or
  harnesses, reusing a persistent worker, or handling material acceptance risk.
- [External agents](references/external-agents.md) before dispatch through a
  distinct harness or persistent terminal, or into a durable workstream.
  Before any external dispatch, including options you present for selection,
  read [Routing](references/routing.md) and the local
  [host inventory](references/host-inventory.md). The inventory's model profiles
  and default roles override model names remembered from earlier sessions.
  <!-- lesson: routing-reference-skipped promoted 2026-09-27 -->
- [Large work](references/large-work.md) when several dependent outcomes need
  staged delivery, milestone checks, or ongoing lane supervision.
- [Execution protocols](references/execution-protocols.md) when a bounded
  assignment's engineering method is `bug-fix`, `architect`, `refactor`,
  `arena`, `swarm`, or `interrogate`. Resolve with
  `python3 <skill-dir>/scripts/coord_protocol.py resolve --protocol <name> --catalog <installed-skill-dir>`.
  A missing protocol falls back to the normal bounded-worker workflow, and
  protocol output is evidence, not acceptance.

Finish this step with owned outcomes, explicit dependencies, settled shared
decisions for the next dispatch, concrete worker choices, and supported return
channels. Use only operations the selected surface exposes.
See [Management principles](references/management-principles.md) for the transferable systems ideas behind this workflow and candidate experiments.

## 3. Assign bounded work

Read the [communication contract](references/communication.md) before first
dispatch. Use its outcome brief and result contract for builders, scouts, and
reviewers. Give workers the parent intent and discretion within their scope,
including permission to challenge an assignment with evidence.

For modifying work, include a runnable focused verification command. Research
can return findings and citations directly in the native result channel.
Put long briefs in a file when workers can read it; otherwise use the supported
message transport. Keep completion inboxes and upstream callers out of the
worker pool.

Run independent tasks concurrently. Serialize overlapping writers and checks
that would race with mutations; independent read-only reviews may inspect the
same stable artifact. Give modifying workers isolated working copies when
practical, and keep each worker's report and inbox paths outside that copy; if
sharing one, use disjoint write ownership and serialize shared operations such
as dependency installation or Git index changes.

Record assignments, ownership, contracts, and dependencies in the task state before
dispatch, then capture returned worker identities. On task-graph surfaces, use
stable node IDs and explicit dependency edges; leave independent nodes unchained.
Dispatch is complete when each assignment has an attributable owner, a bounded
outcome, applicable decision policy, and a supported result channel.
After each dispatch/helper error, surface the exact failure and recovery step,
then verify receipt from supported evidence or the worker's subsequent activity.
A helper return proves transport acceptance, not admission. If delivery remains
unknown, reconcile the worker before retrying; never count an unverified
dispatch as active work.

## 4. Supervise and inspect

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

Treat surprises as planning input even when a worker can complete its assigned
task. When evidence invalidates an assumption, contract, or assignment:

1. Identify affected work items and their transitive dependents, including
   already accepted or integrated results that now need revalidation.
2. Hold affected dependent work and steer active owners through supported
   controls; let independent work continue. Reconcile unconfirmed corrections
   before accepting more output from those assignments.
3. Investigate remaining uncertainty, then revise the plan, contracts, and
   assignments within existing authority. Record the evidence and what changed.
4. Resume affected work once owners have the revised brief and dependencies
   are settled; reverify results whose supporting assumptions changed.

An assignment shown to be unnecessary or wrong is a useful finding. Preserve
the goal; seek user direction if the evidence calls the goal itself into
question. Replanning does not authorize weaker success criteria.

Treat reports as claims to inspect. Select checks from the changed behavior and
integration risk, and inspect the resulting artifact independently. For changed
process, filesystem, network, terminal, browser, plugin, or provider boundaries,
exercise the actual boundary and retain concise evidence. Label fixture-based
checks accurately. Add an independent verifier when the risk warrants one,
using the reviewer guidance in the communication contract.

Confirm cited tests exist and actually ran. Run that same gate on the base
branch before treating a failure as pre-existing or unrelated. <!-- lesson: preexisting-gate promoted 2026-09-26 -->
Directory and glob selectors may
select many files; compare intended coverage with discovered tests, not the
number of selectors. Check that evidence attributed to production behavior
exercises the production definition.

Use the `finding-triage` skill when you write a reviewer brief and before you
route any finding to an implementer. Findings go to the implementer only after
triage; never forward a review wholesale.
<!-- lesson: triage-review-findings promoted 2026-09-28 -->

Judge progress against fixed acceptance criteria, not falling finding counts.
If repeated passes fail the same criterion, change the execution method rather
than weakening acceptance.
Advance a result only after its evidence and surprises have been inspected and
any effect on dependent work has been resolved or explicitly blocked.

## 5. Accept and integrate

Accept a result when required checks pass, evidence has been inspected, and
blocking findings are resolved. Before acceptance, run
`python3 <skill-dir>/scripts/coord_claimcheck.py --cwd <assigned-cwd> --report <report>`:
an unresolved cited commit or test path is a blocking finding. An
execution-protocol report is worker evidence and is not acceptance; acceptance
is still the coordinator's inspection. Acceptance means
the result is suitable for incorporation; integration means it has actually been
incorporated. Perform integration within existing authority and check the
combined result where separate changes interact. Checkpoint immediately after
each merge or incorporation — updating `next_action`, the affected work item's
status, and `phase` — before dispatching or starting any work that depends on
the integrated result; until that checkpoint lands, the record still presents
the merged phase as pending.

Stop the worker, or verify it is idle, before editing its branch. A report file
is not that idle state. <!-- lesson: stop-worker-before-editing-its-branch promoted 2026-09-26 -->
Remove a worktree only after its worker has stopped and its reports and inbox
have been harvested. Keep those paths outside the worktree. To reuse the worker,
fast-forward its tree with `git merge --ff-only` from the base branch. <!-- lesson: worktree-removed-under-worker promoted 2026-09-26 -->

Verify the integrated result against the current authorized observable goal
as well as worker acceptance criteria. Record evidence for each goal-level criterion and
check non-goals and constraints. If local checks pass but the goal is unmet,
revisit the understanding and decomposition, identify missing work, and run the
affected loop again. For staged work, apply this check at each milestone too.
Account for material assumptions and pending decisions using the decision
policy; a parked required action remains unfinished work.

Before closing, account for remaining workers and background processes,
including `tail -f` and orphan processes, and confirm each has exited. Stop
only resources owned by this task when they are no longer needed. Report the
outcome, evidence, and unresolved limitations as one coherent handoff.

Checkpoint the final outcome or exact next action whenever ending a session,
without waiting for the user to request a handoff. Keep the chat handoff short:
include the task ID and record path, the current outcome or next action, and any
blocker that needs attention. The record holds the full goal and reasoning for
the next session.

## Hiccup intake

At the next checkpoint, capture each orchestration hiccup as one incident note
in the existing task-record retro stream: what happened, an evidence path or
exact output, and its class (`host`, `general`, or `one-off`). Append through
`coord_state.py checkpoint` while preserving existing notes; `coord_retro.py`
harvests those notes. Do not create a separate log.

<!-- lesson: coordinator-hiccup-intake promoted 2026-09-29 -->

## Heal as you drive

This skill and the helper skills it drives (`herdr`, `term2`) have defects that
only show up in real use. The agent driving the skill **heals** them in-flow:
when you find a defect while coordinating, fix it in that same task, and don't
leave it behind as a workaround. The user gave standing authority for the lanes
below (2026-09-28). A heal never widens a task's authority or its acceptance
criteria.

A **defect** is evidence that the skill or a helper told you something false:
- a helper errors on valid input;
- a helper refuses an operation the evidence shows is safe;
- a helper reports a false positive or false negative;
- an instruction or host fact is contradicted by what you observed.

A manual workaround is the signature: an extra keypress, a blocker you had to
ignore, a result you re-derived by hand.

1. **Capture** an `incident` note at the next checkpoint (schema in
   [retro](references/retro.md)) with `heal: open`, the exact command and
   output, and the workaround you used.
2. **Heal by lane:**
   - *Host fact* (a tool quirk, model profile, path, or quota): correct its
     entry in the [host inventory](references/host-inventory.md).
   - *Instruction defect* (wording in this skill or a helper skill that is
     unclear, missing, or contradicted): make a small edit and mark it
     `<!-- lesson: <key> promoted <date> -->`.
   - *Helper defect* (a script under a skill's `scripts/`): add a test to that
     skill's suite that reproduces the observed output and fails, then fix the
     script. If your harness is review-only, route the fix to an implementer.
     Before changing a helper's CLI or output format, check for running
     consumers (for example `ps` for live invocations and other coordinators'
     watch commands), and keep the old form working or migrate them first.
     <!-- lesson: live-consumer-compat promoted 2026-09-29 -->
   - *Behavior rule* (changes planning, delegation, routing, verification, or
     stop behavior): record it in [Candidate experiments](references/experiments.md).
     It is an experiment, not a heal.
3. **Gate:** the owning skill's tests pass
   (`python3 -m unittest discover -s <skill-dir>/scripts`), and a changed
   instruction reads correctly in its context. Make a refusal accurate: fix what
   it detects and keep what it guards.
4. **Record:** set `heal: done` with the commit or changed paths.
   - If the heal would take more than about 30 minutes, or would change a
     contract other skills depend on, set `heal: deferred` with the next step.
   - Commit a heal by its paths (`git commit -- <paths>`). If a healed file also
     holds another session's uncommitted edits, leave the heal uncommitted and
     say so in the note.
5. **Announce** each heal in your next update to the user: the defect, its
   lane, and the evidence the fix works.

A heal is complete when its note reads `heal: done` with passing-test evidence,
or `heal: deferred` with a named next step. Before a session ends, move every
`heal: open` note to one of those two states. The [retro](references/retro.md)
handles lessons that recur across tasks, and pruning. Use the installed
`workflow-evolution` skill for authorized experiments.

