# Manual coordination

The phase procedure for work the [driven runtime](../SKILL.md#driven-runtime)
does not cover: provisioning, task records started before the driven runtime,
and interactive Herdr workers. Every reference this path uses is linked from
[References](#references) below; read each one when its row says so.

## Contents

- [Goal and stop rules](#goal-and-stop-rules)
- [0. Entry and durable state](#0-entry-and-durable-state)
- [1. Establish the goal and decision policy](#1-establish-the-goal-and-decision-policy)
- [2. Understand, then decompose](#2-understand-then-decompose)
- [3. Assign bounded work](#3-assign-bounded-work)
- [4. Supervise and inspect](#4-supervise-and-inspect)
- [5. Accept and integrate](#5-accept-and-integrate)
- [Heal as you drive](#heal-as-you-drive)
- [References](#references)
- [Output](#output)

## Goal and stop rules

**Goal:** the authorized outcome, integrated and verified against every
goal-level criterion, with a durable task record another coordinator can resume.
Own the goal, plan, assignments, verification, and integrated result; workers own
bounded outcomes.

**Done when:** every goal-level criterion, non-goal, and constraint is verified
on the combined result (or explicitly blocked), `coord_claimcheck.py` passed for
each accepted report, any real-use gate passed or was waived by the user, owned
workers and background processes have exited, and the task record is
checkpointed with the outcome or exact next action.

**Evidence:** command output from your own checks, inspected artifacts,
claimcheck results, and base-branch runs before calling a failure pre-existing.
Reports, quiet terminals, and process exit are signals, not proof of success.

The helpers enforce several rules, so a refusal is the rule working, not a bug
to route around:

- `coord_lifecycle.py start-worker` refuses a route outside the task's
  user-confirmed selection.
- `coord_lifecycle.py dispatch` lints the brief and refuses contract gaps unless
  `--lint-override '<reason>'` records an authorized exception.
- `coord_outcomes.py verify` runs claimcheck on the report; `accept` refuses
  unresolved citations.
- Completion and archive refuse while a linked lifecycle worker is unreconciled
  or a required real-use gate is neither passed (`coord_state.py real-use
  --status passed --evidence <file>`) nor waived by the user.

Stop rules:

- Wait for the user's harness/model selection before execution or dispatch.
  History, defaults, and running workers alone do not satisfy this gate.
- Discovering a solution does not authorize implementation. Host configuration
  never grants task authority. A heal does not widen task authority or weaken
  acceptance. Replanning never authorizes weaker success criteria.
- Seek user direction if the goal itself is in question; otherwise ask only when
  missing information blocks useful work or makes a wrong assumption consequential.
- Transport acceptance is not worker admission. After a dispatch or helper error,
  report the exact failure and recovery step; preserve uncertain attempts and
  reconcile before retrying.
- Never forward a review wholesale. Stop a worker or verify it is idle before
  editing its branch; a report is not proof of idle state.
- The memory sidecar stays disabled; write decisions into task-state `notes` by hand.

## 0. Entry and durable state

Read [Host profile](host-profile.md). If it is missing or a required capability
changed, run the `coordinator-setup` skill before using host helpers. Bundled task
state needs Unix locking; the process runtime is Linux-only.

Read [Task state](task-state.md), then create and own a record with
`../scripts/coord_state.py`, or load, reconcile, and claim the existing one. Keep a
concise snapshot of the goal, rationale, acceptance criteria, authority,
decisions, owned work, blockers, evidence, and next action; link reports rather
than copying a narrative.

On resume, run `coord_state.py resume --task <id>` first. Treat
`commits_since_update` and `checks` as staleness evidence. Recover the original
goal and unfinished work, and reconcile saved workers and background resources
before dispatching replacements. Finishing the saved action is not finishing the task.

New delivery work with runnable acceptance checks follows
[Outcome contracts](outcome-contracts.md). Existing records keep their workflow.

Checkpoint before dispatch, on material state change, right after integration
before dependent work starts, and before ending a session. Capture coordination
hiccups at the next checkpoint per [Retro](retro.md).

*Check:* the record exists and is claimed.

## 1. Establish the goal and decision policy

Identify the observable outcome, rationale, success criteria, constraints,
non-goals, and authority, separating the user's need from any suggested
implementation. Classify the work:

- **Research** returns knowledge or recommendations.
- **Delivery** produces an authorized change or consequential output.
- **Provisioning** sets up workspaces, panes, or sessions for human use; do it
  directly with the relevant tools or tool skill, with no further phases.

Before a new coordinated task, read [Choice history](choice-history.md), verify
the available harness/model options, recommend one, and wait for the user's
selection. An explicit current-task choice, including an unambiguous reuse
request, satisfies this gate. Keep the selection for same-task follow-ups; ask
before replacing an unavailable choice or adding a role it does not cover.
Read-only discovery and bookkeeping may proceed while it is pending.

Read [Decision policy](decision-policy.md) and record the goal and policy in task state.

*Check:* goal, criteria, authority, and policy recorded; choice confirmed.

## 2. Understand, then decompose

Inspect the relevant system before dividing work. Resolve unknowns that could
change boundaries, shared interfaces, or the solution, directly or with bounded
read-only scouts in the selected pool. Record findings and plan implications.

Give each outcome one accountable owner. Split only where independence pays: at
independently mergeable seams checked against real consumers, since disjoint
files alone do not make work independent. Keep a step that depends on another's
context with that owner; hand it to a separate worker only when a fresh context
is the point, such as an independent review. Settle shared interfaces and
behavior before dependent work starts, recording the agreement, owner, and
consumers.

Delegate when parallel speed, specialization, or independent validation
outweighs startup and integration cost. Work directly for small tasks,
unavailable workers, or dominant shared-state risk, and own glue and final
synthesis. Prefer suitable native workers within the authorized pool. Read
[Routing](routing.md), [External agents](external-agents.md),
[Large work](large-work.md), or [Execution protocols](execution-protocols.md)
when their row in [References](#references) applies.

*Check:* owned outcomes, explicit dependencies, settled shared decisions.

## 3. Assign bounded work

Read [Communication](communication.md) before the first dispatch and use its
brief and result contract for builders, scouts, and reviewers. Modifying work
needs a runnable focused verification command. Use files for long briefs; keep
completion inboxes and upstream callers out of the worker pool.

Run independent tasks concurrently. Isolate modifying workers where practical,
with reports and inboxes outside their working copies; otherwise use disjoint
write ownership and serialize shared operations such as dependency installs and
Git index changes. Serialize checks that race with mutations; independent
read-only reviews can share a stable artifact. On task-graph surfaces, use stable
IDs and explicit dependency edges, leaving independent nodes unchained.

Record assignments, ownership, contracts, and dependencies before dispatch, then
capture returned identities. Outcome-plan work follows
[Runtime contracts](runtime-contracts.md), binding native handles immediately.
Verify receipt through supported evidence or later worker activity. Dispatch is
complete only with an attributable owner, bounded outcome, decision policy,
supported result channel, and confirmed admission.

*Check:* those five items are recorded for every dispatch.

## 4. Supervise and inspect

Read [Worker observation](worker-observation.md) before supervising terminal
panes or report watchers. Reconcile saved attempt handles before any replacement
dispatch.

When evidence invalidates an assumption, contract, or assignment:

1. Identify affected work and transitive dependents, including accepted or
   integrated results that need revalidation.
2. Hold affected dependents and steer their owners; let independent work continue.
3. Revise the plan, contracts, and assignments within authority, and record why.
4. Resume when briefs are revised and dependencies settled; reverify results
   whose assumptions changed.

Inspect artifacts independently and choose checks from changed behavior and
integration risk. Exercise the real process, filesystem, network, terminal,
browser, or provider boundaries a change touches, and label fixture evidence as
such. Confirm cited tests exist and ran, and run the same gate on the base branch
before calling a failure pre-existing.

Use `finding-triage` when writing reviewer briefs and before routing findings to
implementers. Judge progress against fixed criteria, not finding counts, and
change the method when repeated passes fail the same criterion.

*Check:* evidence inspected; effects on dependents resolved or blocked.

## 5. Accept and integrate

Accept only after required checks pass, evidence is inspected, and blocking
findings are resolved. Run `../scripts/coord_claimcheck.py --cwd <assigned-cwd>
--report <report>` first; unresolved cited commits or test paths block acceptance.
Outcome-plan work follows Outcome contracts for acceptance and integration;
workers and protocol reports cannot make those decisions. Protocol output is
evidence, not acceptance.

Integrate within authority, then checkpoint before dependent work. Verify the
combined result against live consumers and every goal-level criterion, non-goal,
and constraint, at milestones too. If the goal is unmet, find the missing work
and repeat the loop.

Remove a worker's worktree only after it stops and its reports and inboxes are
harvested; reuse a tree by fast-forwarding from the base branch. New or changed
skills and orchestration workflows need [Real-use verification](real-use-verification.md)
before closing, unless the user explicitly waives it.

Before closing, confirm owned workers and background processes have exited (stop
only task-owned resources), then checkpoint the outcome or exact next action.

*Check:* the done condition above holds.

## Heal as you drive

When coordination exposes a skill or helper defect, follow [Healing](healing.md):
capture evidence, apply an authorized narrow heal, verify it, record its
disposition, and announce it. Behavior changes are experiments, not heals.

## References

| Read | When |
|---|---|
| [Host profile](host-profile.md) | At entry, and before using any host helper or adapter |
| [Operational status](operational-status.md) | Before enabling an optional integration or healing host state |
| [Task state](task-state.md) | At entry; whenever you create, claim, resume, or checkpoint a record |
| [Outcome contracts](outcome-contracts.md) | New delivery work with runnable acceptance checks |
| [Runtime contracts](runtime-contracts.md) | Dispatching or observing outcome-plan attempts |
| [Choice history](choice-history.md) | Before recommending a harness/model choice |
| [Decision policy](decision-policy.md) | Before work begins; when a decision may exceed authority |
| [Routing](routing.md) | Choosing models or harnesses, rotating dispatches, reusing workers, or handling acceptance risk |
| [External agents](external-agents.md) | Presenting or dispatching a distinct harness, persistent terminal, or Herdr lane |
| [Inbox](inbox.md) | Setting up or reading file inboxes and wakeups for external workers |
| [Large work](large-work.md) | Staged dependent outcomes, milestones, or ongoing lane supervision |
| [Execution protocols](execution-protocols.md) | Before selecting an engineering method or playbook |
| [Communication](communication.md) | Before the first dispatch; writing briefs and verification asks |
| [Worker observation](worker-observation.md) | Before supervising panes or report watchers |
| [Real-use verification](real-use-verification.md) | Closing a task that changed a skill or workflow |
| [Retro](retro.md) | Recording a coordination hiccup at a checkpoint |
| [Healing](healing.md) | A skill or helper defect surfaced while coordinating |
| [Architecture](architecture.md) | Changing coordination boundaries or validating a new runtime |

## Output

```text
Task: <id>  Record: <path>
Outcome: <done | next action: ...>
Evidence: <checks run, by whom; claimcheck result>
Limitations: <none | list>
Blocker: <none | blocked: <input needed from whom>>
```

Null case: research with no actionable finding reports `Outcome: no material
findings` with the evidence searched; nothing to coordinate reports
`Outcome: worked directly, no delegation` with the evidence.
