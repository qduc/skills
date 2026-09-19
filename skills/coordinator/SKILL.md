---
name: coordinator
description: Coordinate work through bounded delegation, dependency management, verification, and integration. Use when the user asks to orchestrate workers or subagents, or when substantial independent work benefits from supervised delegation.
compatibility: Native coordination requires only the available worker tools. The optional external-agent helper uses Python's standard library and explicitly configured harness adapters.
---

# Coordinator

Own the scope, assignments, verification, and integrated result. Keep worker
mechanics with the coordinator so the user can focus on outcomes.

The main agent maintains durable task state on disk with `scripts/coord_state.py`. Read
[Task state](references/task-state.md) at task entry: create and own a record for new
work or load, reconcile, and claim the existing record before continuing. Update it at
each meaningful checkpoint; worker reports and conversation memory do not
replace this record.

## 1. Resolve scope

Identify the target project, constraints, deliverable, and existing authority.
Ask a focused question only when missing information blocks useful work.

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

Honor existing authorization for the work itself.
Escalate destructive, irreversible, or intent-expanding actions when existing
permission does not cover them.

## 2. Decide whether and where to delegate

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

Finish this step with a concrete worker choice and a supported way to receive
its result. Use only operations the selected surface exposes.

## 3. Assign bounded work

Read the short [communication contract](references/communication.md) before
first dispatch. Give each worker:

```text
Goal and expected result
Relevant context and evidence
Scope, write ownership, and authority limits
Dependencies and coordination hazards
Acceptance criteria and relevant checks
Where and how to return results or blockers
```

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

Record assignments, ownership, and dependencies in the task state before
dispatch, then capture returned worker identities. On task-graph surfaces, use
stable node IDs and explicit dependency edges; leave independent nodes unchained.

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

Treat reports as claims to inspect. Select checks from the changed behavior and
integration risk, and inspect the resulting artifact independently. For changed
process, filesystem, network, terminal, browser, plugin, or provider boundaries,
exercise the actual boundary and retain concise evidence. Label fixture-based
checks accurately. Add an independent verifier when the risk warrants one.

Confirm cited tests exist and actually ran. Directory and glob selectors may
select many files; compare intended coverage with discovered tests, not the
number of selectors. Check that evidence attributed to production behavior
exercises the production definition.

Judge progress against fixed acceptance criteria, not falling finding counts.
If repeated passes fail the same criterion, change the execution method rather
than weakening acceptance.

## 5. Accept and integrate

Accept a result when required checks pass, evidence has been inspected, and
blocking findings are resolved. Acceptance means the result is suitable for
incorporation; integration means it has actually been incorporated. Perform
integration within existing authority and check the combined result where
separate changes interact.

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
