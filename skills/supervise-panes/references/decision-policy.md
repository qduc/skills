# Decisions, assumptions, and human input

Use existing authorization and expressed preferences to establish the policy.
When the user has given no implementation preference, favor the simplest
reversible approach consistent with the existing system and the goal. State
material defaults once. A request for unattended work reduces interruptions;
it does not enlarge authority or resolve missing intent.

## Decide, continue, or ask

| Situation | Action |
| --- | --- |
| Authorized, reversible choice with sufficient context | Decide and continue. Record it only if material. |
| Nonblocking uncertainty with a reasonable reversible default | Apply the default, record a material assumption, and collect any question for batch review. |
| Missing authority or ambiguity whose wrong resolution would materially change the goal, scope, cost, or consequences | Seek focused input before dependent work; continue independent authorized work. |
| Consequential action outside current authorization | Prepare a concrete draft, dry run, or other authorized reversible result, then request the needed decision. If the user is unavailable, park the action and record what is needed to resume. |
| Previously authorized consequential action with its conditions satisfied | Proceed within that authorization; do not invent a new approval gate. |

Assess reversibility by effects, not labels: a branch can contain a destructive
command, and a library choice can impose significant migration cost. A parked
action is not completed. When an authorized unattended run reaches a decision
it cannot make, preserve the prepared result and continue independent work;
report the unresolved decision at handoff.

Distinguish required unfinished decisions from optional proposals outside the
goal. Record an optional out-of-scope action as a deferred note, including that
it was not performed and would require separate authorization. It does not
become a prerequisite or a completion-blocking pending decision unless the
authorized goal actually depends on it. If that dependency is discovered,
record it as pending and seek direction without silently expanding scope.

Workers resolve choices within their assignment and escalate beyond it to the
coordinator. The coordinator resolves what its authority covers and owns any
user question. Preserve the main skill's explicit harness/model selection
requirement, including replacement selections.

## Record material assumptions

Log a decision or assumption when being wrong could invalidate other work,
affect acceptance, or require substantial undo. Routine naming and equivalent
local implementation choices need no log. Use the existing task record, with
workers returning proposed entries for the coordinator to reconcile.

For each material assumption record:

- Stable ID, the chosen assumption or decision, and status (provisional,
  confirmed, rejected, or superseded).
- Evidence or reasoning, significant alternatives, and remaining uncertainty.
- Consequence if wrong, reversibility, and how to undo or recover.
- Affected work-item IDs; `depends_on` assumption IDs where assumptions compound.

Use qualitative confidence only with its supporting evidence. These references
are planning information maintained by the coordinator, not automatically
validated dependency edges. On rejection or new contrary evidence, trace both
assumption dependents and work-item dependents; apply the main skill's replanning
loop. Preserve the rejected or superseded entry and link the replacement so
later sessions can explain why work changed.

## Batch review and closure

Collect nonblocking questions at a useful milestone or handoff. Prioritize:

1. Pending decisions requiring user authority or preventing completion.
2. Uncertain assumptions with high consequences if wrong.
3. Decisions with many dependent assumptions or work items.
4. Remaining material choices, summarized briefly.

For each decision that needs input, show the recommendation, evidence,
consequence, affected work, and what accept, reject, or change would mean.
Avoid demanding approval for every authorized implementation choice. Silence
does not confirm an assumption or grant authority. A provisional assumption
may remain documented at completion only when the decision policy permits it,
the goal is verified, and it creates no unresolved required decision. Otherwise
keep it pending and the affected work unfinished.

On a user response, record the decision and apply replanning to affected work.
If the user's desired goal changes, record the new goal and criteria explicitly
with the source of authorization; preserve the previous goal in the history.
