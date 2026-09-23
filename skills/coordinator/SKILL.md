---
name: coordinator
description: Coordinate work through bounded delegation, dependency management, verification, and integration. Use when the user asks to orchestrate workers or subagents, or when substantial independent work benefits from supervised delegation.
compatibility: Native coordination requires only the available worker tools. The optional external-agent helper uses Python's standard library and explicitly configured harness adapters.
---

# Coordinator

Own the goal, plan, assignments, verification, and integrated result. Workers
own bounded outcomes. Revise the plan when evidence changes; preserve the
authorized goal and success criteria unless the user changes them.

The main agent maintains durable task state on disk with `scripts/coord_state.py`. Read
[Task state](references/task-state.md) at task entry: create and own a record for new
work or load, reconcile, and claim the existing record before continuing. Update it at
each meaningful checkpoint; worker reports and conversation memory do not
replace this record.

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
accountability. Resolve shared decisions before dependent work starts: record
the agreed interface, schema, or behavior, its owner, and affected work items.
Disjoint files alone do not establish independence. Workers can propose a
contract change; its owner coordinates affected consumers before adopting it.

Delegate substantial bounded work when startup and integration costs are
justified by speed, specialization, or independent validation. Work directly
when the task is small, suitable workers are unavailable, or shared-state risk
dominates. Do glue work and final synthesis yourself.

Inspect available worker tools and their actual capabilities. Recommend native
workers for ordinary bounded assignments when suitable, and route within the
user's chosen harness/model pool. Keep assignments within known limits;
split work when needed. Missing optional quota telemetry alone does not block
routine native delegation.

Read additional guidance only for the applicable branch:

- [Routing](references/routing.md) when choosing between model groups or
  harnesses, reusing a persistent worker, or handling material acceptance risk.
- [External agents](references/external-agents.md) before dispatch through a
  distinct harness or persistent terminal, or into a durable workstream.
- [Large work](references/large-work.md) when several dependent outcomes need
  staged delivery, milestone checks, or ongoing lane supervision.

Finish this step with owned outcomes, explicit dependencies, settled shared
decisions for the next dispatch, concrete worker choices, and supported return
channels. Use only operations the selected surface exposes.

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
practical; if sharing one, use disjoint write ownership and serialize shared
operations such as dependency installation or Git index changes.

Record assignments, ownership, contracts, and dependencies in the task state before
dispatch, then capture returned worker identities. On task-graph surfaces, use
stable node IDs and explicit dependency edges; leave independent nodes unchained.
Dispatch is complete when each assignment has an attributable owner, a bounded
outcome, applicable decision policy, and a supported result channel.

## 4. Supervise and inspect

Use supported completion notifications or bounded lifecycle waits. A running
watcher does not prove worker activity. If a completion marker can be omitted,
set a bounded fallback check-in, inspect activity then, and leave active workers
alone. Resolve a blocker or revise an assignment before retrying failed work.

Decide steerability at dispatch. For a mid-flight correction, seek an
attributable acknowledgement or supported delivery receipt. Missing text in
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

Confirm cited tests exist and actually ran. Directory and glob selectors may
select many files; compare intended coverage with discovered tests, not the
number of selectors. Check that evidence attributed to production behavior
exercises the production definition.

Judge progress against fixed acceptance criteria, not falling finding counts.
If repeated passes fail the same criterion, change the execution method rather
than weakening acceptance.
Advance a result only after its evidence and surprises have been inspected and
any effect on dependent work has been resolved or explicitly blocked.

## 5. Accept and integrate

Accept a result when required checks pass, evidence has been inspected, and
blocking findings are resolved. Acceptance means the result is suitable for
incorporation; integration means it has actually been incorporated. Perform
integration within existing authority and check the combined result where
separate changes interact.

Verify the integrated result against the current authorized observable goal
as well as worker acceptance criteria. Record evidence for each goal-level criterion and
check non-goals and constraints. If local checks pass but the goal is unmet,
revisit the understanding and decomposition, identify missing work, and run the
affected loop again. For staged work, apply this check at each milestone too.
Account for material assumptions and pending decisions using the decision
policy; a parked required action remains unfinished work.

Before closing, account for remaining workers and background processes. Stop
only resources owned by this task when they are no longer needed. Report the
outcome, evidence, and unresolved limitations as one coherent handoff.

Checkpoint the final outcome or exact next action in the task state before
handoff. Include its path so the task can be found in a later session.

## Improve from evidence

Record repeatable coordination failures in the task record. A clear local
instruction defect may receive a small, announced correction when skill edits
are authorized and validation fits the current task. Keep incident history out
of reusable instructions. Record broader or uncertain improvements for separate
work; use the installed `workflow-evolution` skill when an experiment is
requested or already authorized. Preserve authority and acceptance criteria.
