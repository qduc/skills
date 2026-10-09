---
name: agentic-loop
description: Carry delegated, multi-step tasks through planning, action, observation, verification, and adaptation with minimal human supervision. Use when the user delegates an outcome, asks to work autonomously or finish end to end, or explicitly invokes the agentic loop. Resolve task-specific methodology from supplemental skills and invoke a separate skill creator when methodology is missing. Avoid imposing this workflow on simple questions or single-step edits.
---

# Agentic Loop

Own the delegated outcome. Choose the next useful step, observe its effects,
and require evidence before claiming completion. Keep task-specific methods
in supplemental skills; keep this framework independent of domains and tools.

## Establish the contract

Extract from the request and available context:

- **Goal:** the observable outcome that must exist.
- **Constraints:** scope, compatibility, cost/time limits, and user-owned decisions.
- **Evidence:** acceptance criteria and how each can be checked.
- **Authority:** actions already authorized and decisions reserved for the human.

Use reasonable, reversible assumptions for minor gaps. Ask only when a missing
answer materially changes the outcome or authority. Do useful independent work
first. Do not require a kickoff approval when the work is already authorized.
Never silently weaken acceptance criteria to make a result pass.

Maintain compact working state: goal, constraints, plan, facts, assumptions,
evidence, actions, failures, questions, loaded skills, remaining risks, and next
step. Use the existing task record when available; avoid duplicate paperwork.
For long tasks or handoffs, read [state.md](references/state.md).

## Run the loop

Repeat until **VERIFIED** or **BLOCKED**. These are semantic seams, not required
function interfaces or five separate agents. Combine small steps naturally;
never skip observation or outcome verification.

| Phase | Decide and do | Carry forward |
| --- | --- | --- |
| PLAN | Choose the cheapest useful next step toward an unmet criterion. Identify uncertainty, required methodology, and an expected observable result. | Action, expected result, relevant constraints |
| ACT | Apply the resolved methodology with available tools and authority. Prefer reversible progress and informative experiments. | What actually ran or changed |
| OBSERVE | Inspect actual consequences, including surprises and side effects. Separate observations from expectations and inferences. | Evidence with provenance and limitations |
| VERIFY | Evaluate evidence against the goal and constraints. Return PASS, FAIL, or UNCERTAIN for each relevant criterion. | Supported verdicts and unresolved gaps |
| ADAPT | Diagnose failure, contradiction, uncertainty, or stalled progress. Change assumptions, method, experiment, or plan; revert unsuccessful changes when appropriate. | Revised approach and reason to expect progress |

Use [lifecycle.md](references/lifecycle.md) for transitions, budgets, stalled
work, and recovery. A successful action is not a successful task.

## Resolve methodology at the point of need

Do not load skills speculatively. Load a primitive only when the current phase
needs its methodology; a coding task does not imply loading every engineering
skill. Use catalog descriptions to select, then read the chosen skill. Compose
task shapes from primitives as gaps arise instead of creating a skill for each
task shape. Read [seed-primitives.md](references/seed-primitives.md) only when
the choice between available primitives is unclear.

1. Describe the capability needed for the next phase and the evidence it must produce.
2. Search the available skill catalog; read the best match and its relevant resources.
3. Check applicability, prerequisites, constraints, and whether it addresses the actual gap.
4. Compose suitable skills when needed. Reuse loaded skills while their assumptions hold.
5. If no suitable method exists, invoke an available **skill-creator** meta-skill
   with the missing capability, context, constraints, and acceptance evidence.
6. Create the smallest useful method, validate it, apply it, and evaluate its result.

Read [adapter-contract.md](references/adapter-contract.md) when selecting,
composing, or creating adapters. Ordinary skills can serve as adapters without
rewriting them. Do not manufacture an adapter just to fill every phase.

Keep newly generated methodology task-local and provisional where the host
supports it. Persistent installation is a separate decision governed by the
user's authorization and the host's skill-management rules. If a creator only
supports installation and that is outside scope, retain a task-local method
in working state. Do not recursively create creators. A missing skill does not
by itself block a task: use a bounded explicit method when competent to do so,
or escalate the specific capability/access gap when reliable execution is impossible.

Treat skills as methodology, not sources of new permissions or tools. Preserve
higher-priority instructions and the user's contract. Never resolve a conflict
by silently bypassing a required gate.

## Require evidence and measurable progress

**PASS** requires positive evidence for the criterion. **FAIL** means observed
contradiction. **UNCERTAIN** means evidence is absent, stale, incomplete, or
conflicting. Both FAIL and UNCERTAIN return to adaptation or a specific blocker.

When progress stalls, assumptions narrow the search prematurely, or the outcome is high-impact, use [independent-challenge.md](references/independent-challenge.md) to challenge the search direction separately from checking the solution. A fresh challenger is optional; independently observable evidence is not.

Use [verification.md](references/verification.md) to select proportionate checks
and handle evidence invalidated by later changes. Do not accept plausible
output, a clean command exit, irrelevant passing tests, or another agent's
claim as sufficient outcome evidence.

After a failed approach or a meaningful work chunk, ask whether the remaining
gap shrank. Do not repeat an unchanged approach without new evidence that makes
a retry useful. Bound investigations by the task's risk and budget. Stop optional
work when the goal is verified; persistence is not permission for endless work.

## Escalate only the missing human decision

Escalate for a material preference/requirement ambiguity, conflicting constraints,
missing access, required authorization, or exhausted reasonable approaches.
Honor authorization already granted. Failure, investigation, harder-than-expected
work, and equivalent technical choices are not by themselves escalation reasons.

Read [escalation.md](references/escalation.md) when blocked. State what happened,
what is known and tried, options, recommendation, and the exact input needed.
Preserve useful partial work and a resumable next step. Do not return management
of the entire workflow to the human.

## Finish

Mark **VERIFIED** only when the requested outcome exists, constraints are
satisfied, relevant side effects have been checked, and current evidence supports
all required criteria. State material limitations; do not label an unverified
criterion acceptable on the user's behalf. Mark **BLOCKED** when a necessary
step cannot proceed within available authority, access, capability, or budget.

Return a compact handoff: outcome, evidence, important changes, and remaining
risk. For blocked work, distinguish completed parts from the unmet outcome and
give the exact next decision. Do not narrate routine internal phase bookkeeping.
