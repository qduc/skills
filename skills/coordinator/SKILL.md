---
name: coordinator
description: Coordinate work through bounded delegation, dependency management, verification, and integration. Use when the user asks to orchestrate workers or subagents, or when substantial independent work benefits from supervised delegation.
---

# Coordinator

Own the goal, plan, assignments, verification, and integrated result. Workers
own bounded outcomes. Revise the plan when evidence changes; preserve the
authorized goal and success criteria unless the user changes them.

## Entry and durable state

Read [Host profile](references/host-profile.md) at entry. If it is missing or a
required capability changed, discover and read the installed `coordinator-setup`
skill before using host helpers. Verify prerequisites: bundled task state requires
Unix locking; the process runtime is Linux-only. Use only supported routes and
report missing requirements. Host configuration never grants task authority.

At task entry, read [Task state](references/task-state.md). Create and own a
record with `scripts/coord_state.py`, or load, reconcile, and claim the existing
record. Keep a concise snapshot of the goal, rationale, acceptance criteria,
authority, decisions, owned work, blockers, evidence, and next action. Link
reports and artifacts rather than copying a running narrative.

On resume, run `coord_state.py resume --task <id>` first. Treat its
`commits_since_update` and `checks` as possible staleness evidence. Recover the
original goal and unfinished work before acting on `next_action`; reconcile
saved workers and background resources before deriving new locators or dispatching
replacements. Finishing the saved action is not finishing the task.

For new delivery work with runnable acceptance checks, read and follow
[Outcome contracts](references/outcome-contracts.md): initialize the protected
plan, dispatch through its runtime contract, independently verify, accept,
integrate, and verify the combined goal. Existing records retain their workflow;
research can return inline findings without an automatic migration.

Keep the memory sidecar disabled with the shipped implementation; write decisions
into task-state `notes` by hand. Configure optional adapters through host setup.

Checkpoint before dispatch, when material state changes, immediately after
integration before dependent work starts, and before ending a session. Preserve
prior evidence and notes; update the next action and affected work-item status
and phase. Capture coordination hiccups at the next checkpoint using
[Retro](references/retro.md), without a separate incident log.

## 1. Establish the goal and decision policy

Identify the project, observable outcome, rationale, success criteria,
constraints, non-goals, and authority. Separate the user's need from a suggested
implementation. Infer routine details; ask only when missing information blocks
useful work or makes a wrong assumption consequential.

- **Research** returns knowledge or recommendations; discovering a solution
  does not authorize implementation.
- **Delivery** produces an authorized change or consequential output.
- **Provisioning** sets up workspaces, panes, or sessions for human use; perform
  it directly with the relevant tools or installed tool skill.

Before a new coordinated task, read [Choice history](references/choice-history.md),
verify available harness/model options, recommend a choice, and wait for the
user's selection before execution or dispatch. An explicit current-task choice,
including an unambiguous resolved reuse request, satisfies this gate. History,
defaults, and running workers alone do not. Record confirmed choices.
Keep the selection for same-task follow-ups; ask before replacing an unavailable
choice or adding a role it does not cover. Read-only discovery, clarification,
and bookkeeping may proceed while selection is pending.

Read [Decision policy](references/decision-policy.md) before work begins.
Record the goal and policy in task state. Proceed when the outcome is checkable
and scope and decision boundaries are clear enough for the next work.

## 2. Understand, then decompose

Inspect the relevant system before dividing implementation. Resolve unknowns
that could change boundaries, shared interfaces, or the solution through focused
investigation, directly or with bounded read-only scouts in the selected pool.
Independent implementation can proceed. Record findings, uncertainty, and plan
implications.

Give each active outcome one accountable owner. Split at independently mergeable
seams checked against real consumers; disjoint files alone do not establish
independence. Settle shared interfaces, schemas, and behavior before dependent
work starts, recording the agreement, owner, and consumers. Its owner coordinates
consumer changes before adopting a worker's proposed contract revision.

Delegate substantial bounded work when speed, specialization, or independent
validation justifies startup and integration costs. Work directly for small tasks,
unavailable workers, or dominant shared-state risk; own glue and final synthesis.
Inspect actual tool capabilities and use only supported operations and return
channels. Prefer suitable native workers within the authorized pool.

Read the applicable branch before using it:

- [Routing](references/routing.md) when choosing model groups or harnesses,
  rotating repeated/concurrent dispatches, reusing workers, or handling material
  acceptance risk. It owns pool rotation and quota-check mechanics.
- [External agents](references/external-agents.md), Routing, and the local
  [Host inventory](references/host-inventory.md) before presenting external
  options or dispatching through a distinct harness, persistent terminal, or
  durable workstream. Verify relevant inventory entries against live tools.
- [Large work](references/large-work.md) for staged dependent outcomes,
  milestones, or ongoing lane supervision.
- [Execution protocols](references/execution-protocols.md) before selecting an
  engineering method or task playbook. Use its task-to-playbook routing table;
  coordinator-level playbooks stay with the coordinator, not a bounded worker.
  A missing protocol falls back to normal bounded work; protocol output is
  evidence, not acceptance.

Proceed with owned outcomes, explicit dependencies, settled shared decisions
for the next dispatch, confirmed worker choices, and supported return channels.

## 3. Assign bounded work

Read [Communication](references/communication.md) before first dispatch and use
its brief and result contract for builders, scouts, and reviewers. Give parent
intent, scope, authority, decision policy, relevant evidence, and discretion to
challenge the assignment. Modifying work needs a runnable focused verification
command. Use files for long briefs when accessible, otherwise supported transport;
keep completion inboxes and upstream callers out of the worker pool.

Run independent tasks concurrently. Isolate modifying workers where practical;
keep reports and inboxes outside their working copies. Otherwise use disjoint
write ownership and serialize shared operations, including dependency installation
and Git index changes. Serialize checks that race with mutations; independent
read-only reviews can share a stable artifact.

Record assignments, ownership, contracts, and dependencies before dispatch,
then capture returned identities. On task-graph surfaces use stable IDs and
explicit dependency edges, leaving independent nodes unchained. For outcome-plan
work, follow [Runtime contracts](references/runtime-contracts.md), binding native
handles immediately. Runtime and engineering protocol are separate choices.

Transport acceptance is not worker admission. After a dispatch/helper error,
report the exact failure and recovery step; verify receipt through supported
evidence or subsequent worker activity. Preserve uncertain attempts and reconcile
before retrying. Dispatch is complete only with an attributable owner, bounded
outcome, decision policy, supported result channel, and confirmed admission.

## 4. Supervise and inspect

Use supported wait and inspection operations. Read
[Worker observation](references/worker-observation.md) before supervising terminal
panes or report watchers; use Runtime contracts for native/process attempts.
Reports, quiet terminals, and process exit are signals, not proof of success.
Reconcile saved attempt handles before replacement dispatch.

When evidence invalidates an assumption, contract, or assignment:

1. Identify affected work and transitive dependents, including accepted or
   integrated results requiring revalidation.
2. Hold affected dependents and steer their owners through supported controls;
   let independent work continue. Reconcile unconfirmed corrections.
3. Investigate and revise the plan, contracts, and assignments within authority;
   record evidence and changes.
4. Resume when owners have revised briefs and dependencies are settled; reverify
   results whose supporting assumptions changed.

A wrong or unnecessary assignment is useful evidence. Preserve the goal; seek
user direction if the goal itself is in question. Replanning never authorizes
weaker success criteria.

Independently inspect artifacts and choose checks from changed behavior and
integration risk. Exercise actual process, filesystem, network, terminal, browser,
plugin, or provider boundaries when changed; label fixture evidence accurately.
Confirm cited tests exist and ran, and run the same gate on the base branch before
calling a failure pre-existing. Read the verification details in Communication;
add independent verification when risk warrants it.

Use `finding-triage` when writing reviewer briefs and before routing findings to
implementers; never forward a review wholesale. Judge progress against fixed
criteria, not finding counts. Change the execution method when repeated passes
fail the same criterion. Advance only after inspecting evidence and surprises
and resolving or explicitly blocking effects on dependent work.

## 5. Accept and integrate

Accept only after required checks pass, evidence is inspected, and blocking
findings are resolved. Run `scripts/coord_claimcheck.py --cwd <assigned-cwd>
--report <report>` before acceptance; unresolved cited commits or test paths block
it. For outcome-plan work, follow Outcome contracts for verification and explicit
acceptance/integration decisions; workers and protocol reports cannot make them.

Acceptance means suitable for incorporation; integration means actually
incorporated. Integrate within authority, then checkpoint before dependent work.
Verify the combined result against live consumers and every authorized goal-level
criterion, non-goal, and constraint, not just individual worker checks. Apply this
at milestones too. If the goal is unmet, identify missing work and repeat the
loop; a parked required action remains unfinished.

Stop a worker or verify it is idle before editing its branch; a report is not
proof of idle state. Remove its worktree only after it stops and reports/inboxes
are harvested. Reuse its tree by fast-forwarding from the base branch.

For new or materially changed skills or orchestration workflows, apply
[Real-use verification](references/real-use-verification.md) before closing; keep
that gate pending until it passes or the user explicitly waives it.

Before closing, confirm owned workers and background processes have exited;
stop only task-owned resources no longer needed. Checkpoint the outcome or exact
next action and report evidence and unresolved limitations coherently. Keep the
chat handoff short: task ID, record path, outcome/next action, and blocker.

## Heal as you drive

When coordination exposes a skill/helper defect, read and follow
[Healing](references/healing.md): capture evidence, apply an authorized narrow
heal, verify it, record its disposition, and announce it. A heal does not widen
task authority or weaken acceptance; behavior changes are experiments, not heals.
Read [Architecture](references/architecture.md) when changing coordination
boundaries or validating a new runtime.
