# Manual coordination

The phase procedure for work the [driven runtime](driven-runtime.md) does not cover:
provisioning, existing task records, and interactive Herdr workers. Native host
agents and report/file-artifact work, including research outside Git, use the
driven runtime. This was the whole skill before
the driven runtime existed and is unchanged apart from link paths.

Several of its rules are now enforced by the helpers, so a refusal from one of
them is the rule working, not a bug to route around:

- `coord_lifecycle.py start-worker` refuses a route outside the task's
  user-confirmed selection.
- `coord_lifecycle.py dispatch` lints the brief and refuses contract gaps unless
  `--lint-override '<reason>'` records an authorized exception.
- `coord_outcomes.py verify` runs claimcheck on the report; `accept` refuses
  unresolved citations.
- Completion and archive refuse while a linked lifecycle worker is unreconciled
  or a required real-use gate is neither passed (`coord_state.py real-use
  --status passed --evidence <file>`) nor waived by the user.

Own the goal, plan, assignments, verification, and integrated result. Workers
own bounded outcomes. Revise the plan when evidence changes; preserve the
authorized goal and success criteria unless the user changes them.

**Goal:** the authorized outcome, integrated and verified against every
goal-level criterion, with a durable task record another coordinator can resume.

**Done when:** every goal-level criterion, non-goal, and constraint is verified
on the combined result (or explicitly blocked), `coord_claimcheck.py` passed for
each accepted report, any real-use gate passed or was waived by the user, owned
workers and background processes have exited, and the task record is
checkpointed with the outcome or exact next action.

**Evidence to report:** command output from your own checks, inspected
artifacts, claimcheck results, and base-branch runs before calling a failure
pre-existing. Reports, quiet terminals, and process exit are signals, not proof
of success.

**How to use this file:** each phase below lists its gate rules. Before acting
in a phase, read that phase's section in
[Phase details](phase-details.md), plus the references it names.
Nothing in phase details is optional.

## Stop rules

- Wait for the user's harness/model selection before execution or dispatch.
  History, defaults, and running workers alone do not satisfy this gate.
- Discovering a solution does not authorize implementation. Host
  configuration never grants task authority. A heal does not widen task
  authority or weaken acceptance. Replanning never authorizes weaker success
  criteria.
- Seek user direction if the goal itself is in question; ask only when missing
  information blocks useful work or makes a wrong assumption consequential.
- Transport acceptance is not worker admission. After a dispatch/helper error,
  report the exact failure and recovery step; preserve uncertain attempts and
  reconcile before retrying.
- Never forward a review wholesale. Stop a worker or verify it is idle before
  editing its branch; a report is not proof of idle state.
- Keep the memory sidecar disabled with the shipped implementation.

## Phases

0. **Entry and durable state.** Read [Host profile](host-profile.md)
   and [Task state](task-state.md); create or claim the record with
   `../scripts/coord_state.py`. On resume run `coord_state.py resume --task <id>`
   first; finishing the saved action is not finishing the task. New delivery
   work with runnable acceptance checks follows
   [Outcome contracts](outcome-contracts.md). Checkpoint before
   dispatch, on material change, right after integration, and before ending a
   session; log hiccups per [Retro](retro.md).
   *Check:* record exists and is claimed.
1. **Establish the goal and decision policy.** Classify research, delivery, or
   provisioning. Read [Choice history](choice-history.md) and
   [Decision policy](decision-policy.md); recommend a harness/model
   choice and record the confirmed one.
   *Check:* goal, criteria, authority, and policy recorded; choice confirmed.
2. **Understand, then decompose.** Investigate unknowns that could change
   boundaries; one accountable owner per outcome; settle shared interfaces
   first. Read [Routing](routing.md),
   [External agents](external-agents.md),
   [Large work](large-work.md), or
   [Execution protocols](execution-protocols.md) when their branch
   applies.
   *Check:* owned outcomes, explicit dependencies, settled shared decisions.
3. **Assign bounded work.** Read [Communication](communication.md)
   before first dispatch; modifying work needs a runnable focused verification
   command. Outcome-plan work follows
   [Runtime contracts](runtime-contracts.md).
   *Check:* attributable owner, bounded outcome, decision policy, supported
   result channel, and confirmed admission recorded.
4. **Supervise and inspect.** Read
   [Worker observation](worker-observation.md) before supervising
   panes or watchers. On invalidated assumptions, hold dependents, revise, and
   reverify. Use `finding-triage` for reviewer briefs and findings.
   *Check:* evidence inspected; effects on dependents resolved or blocked.
5. **Accept and integrate.** Run `../scripts/coord_claimcheck.py --cwd
   <assigned-cwd> --report <report>` before acceptance; unresolved cited
   commits or test paths block it. Verify the combined result against live
   consumers. New or changed skills/workflows need
   [Real-use verification](real-use-verification.md).
   *Check:* the finish condition above holds.

Throughout: when coordination exposes a skill/helper defect, follow
[Healing](healing.md); read [Architecture](architecture.md)
when changing coordination boundaries or validating a new runtime.

## Output

Keep the chat handoff short:

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
