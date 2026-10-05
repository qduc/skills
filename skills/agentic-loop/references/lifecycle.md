# Lifecycle and recovery

Track task status separately from the current phase. Use ACTIVE while work is
possible, VERIFIED for an evidence-backed outcome, and BLOCKED for a concrete
dependency that prevents necessary progress. Record a user cancellation as
CANCELLED, not as success; stop when the user cancels or pauses the task.

## Transitions

| Observation or verdict | Next step |
| --- | --- |
| Action produced its expected result | Check the relevant criterion; plan the next unmet one |
| Action failed or produced a surprise | Inspect consequences before another action; adapt |
| Verification FAIL | Diagnose the contradiction and choose a different or corrected approach |
| Verification UNCERTAIN | Identify the missing evidence and the least costly way to obtain it |
| Local verification PASS, other criteria open | Return to PLAN; preserve this evidence until invalidated |
| All required criteria PASS | Check relevant side effects and complete |
| Necessary action exceeds authority or resources | Complete useful independent work, then report BLOCKED |
| User changes the goal | Update the contract explicitly and reassess affected work and evidence |

Run as many cycles as needed within the delegated scope. A phase need not be a
tool call or a user-facing message. Let an observation revise the plan immediately;
do not finish an obsolete sequence merely to obey its original order.

## Progress and stopping

Choose a progress signal tied to the task: an uncertainty resolved, a required
behavior observed, a reproducible failure isolated, or an artifact validated.
Activity counts and the number of skills loaded are not progress measures.

When a strategy repeats without reducing the gap:

1. Record the failed hypothesis and evidence, including any side effects.
2. Determine whether the failure is in the method, assumptions, tools, or contract.
3. Choose a discriminating check or materially different approach.
4. Estimate whether its likely information or outcome justifies its cost.
5. Continue only within the remaining budget and authority; otherwise surface
   the smallest actionable blocker with partial results.

A retry can be reasonable for a documented transient failure, but bound retries
and name what would make you stop. Do not add arbitrary global retry counts to
every task. Honor explicit time, cost, and tool limits; for open-ended delegation,
use bounded work chunks and reassess before any substantial expansion.

## Resume safely

Read the current task record, recover its contract and next step, then inspect
only external state that may have changed. Reuse stable facts. Mark affected
evidence stale when artifacts, environments, or requirements changed.

After an interrupted write or external action, inspect the destination before
retrying. An absent response does not establish that the action failed. Avoid
duplicate sends, deployments, purchases, or other repeated side effects.
