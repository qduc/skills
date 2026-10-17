---
name: agentic-loop
description: Carry delegated, multi-step tasks through planning, action, observation, verification, and adaptation with minimal human supervision. Use when the user delegates an outcome, asks to work autonomously or finish end to end, or explicitly invokes the agentic loop. Resolve task-specific methodology from supplemental skills and invoke a separate skill creator when methodology is missing. Avoid imposing this workflow on simple questions or single-step edits.
---

# Agentic Loop

**Goal:** own the delegated outcome until it is VERIFIED with current evidence or BLOCKED on a specific human decision. Keep task-specific methods in supplemental skills; keep this framework independent of domains and tools.

## Phases

1. **Write the contract.** Before acting, write down:
   - **Goal:** the observable outcome that must exist.
   - **Done predicate:** acceptance criteria as falsifiable checks, and how each is checked.
   - **Constraints:** scope, compatibility, cost/time limits, and user-owned decisions.
   - **Authority:** actions already authorized and decisions reserved for the human.

   Check: each criterion names a check that could FAIL. Use reasonable, reversible assumptions for minor gaps. Ask only when a missing answer materially changes the outcome or authority. Do useful independent work first. Do not require a kickoff approval when the work is already authorized. Never silently weaken acceptance criteria to make a result pass.

   Maintain compact working state (goal, constraints, plan, facts, assumptions, evidence, actions, failures, questions, loaded skills, remaining risks, next step) in the existing task record; avoid duplicate paperwork. For long tasks or handoffs, read [state.md](references/state.md).

2. **Run the loop** until VERIFIED or BLOCKED. These are semantic seams, not required function interfaces or five separate agents. Combine small steps naturally; never skip observation or outcome verification.

| Phase | Decide and do | Carry forward |
| --- | --- | --- |
| PLAN | Cheapest useful next step toward an unmet criterion; uncertainty, required methodology, expected observable result. | Action, expected result, constraints |
| ACT | Apply the resolved methodology within tools and authority. Prefer reversible progress and informative experiments. | What actually ran or changed |
| OBSERVE | Inspect actual consequences, including surprises and side effects. Separate observations from expectations and inferences. | Evidence with provenance and limits |
| VERIFY | Evaluate evidence against goal and constraints: PASS, FAIL, or UNCERTAIN per relevant criterion. | Verdicts and unresolved gaps |
| ADAPT | Diagnose failure, contradiction, uncertainty, or stalled progress. Change assumptions, method, experiment, or plan; revert unsuccessful changes when appropriate. | Revised approach and reason to expect progress |

   Use [lifecycle.md](references/lifecycle.md) for transitions, budgets, stalled work, and recovery. A successful action is not a successful task.

3. **Resolve methodology at the point of need.** Do not load skills speculatively; a coding task does not imply loading every engineering skill. Select from catalog descriptions, then read the chosen skill. Follow the resolution procedure in [adapter-contract.md](references/adapter-contract.md) when selecting, composing, or creating adapters, including when to invoke a **skill-creator** and keeping generated methods task-local. Read [seed-primitives.md](references/seed-primitives.md) only when the choice between primitives is unclear. Treat skills as methodology, not sources of new permissions or tools. Preserve higher-priority instructions and the user's contract. Never resolve a conflict by silently bypassing a required gate.

4. **Verify with evidence.** **PASS** requires positive evidence for the criterion. **FAIL** means observed contradiction. **UNCERTAIN** means evidence is absent, stale, incomplete, or conflicting. Both FAIL and UNCERTAIN return to ADAPT or a specific blocker. Use [verification.md](references/verification.md) to select proportionate checks and handle evidence invalidated by later changes. Do not accept plausible output, a clean command exit, irrelevant passing tests, or another agent's claim as sufficient outcome evidence.

5. **Escalate only the missing human decision.** Escalate for a material preference/requirement ambiguity, conflicting constraints, missing access, required authorization, or exhausted reasonable approaches. Honor authorization already granted. Failure, investigation, harder-than-expected work, and equivalent technical choices are not by themselves escalation reasons. Read [escalation.md](references/escalation.md) when blocked. Preserve useful partial work and a resumable next step. Do not return management of the entire workflow to the human.

## Stop rules

- After a failed approach or a meaningful work chunk, ask whether the remaining gap shrank. Do not repeat an unchanged approach without new evidence that makes a retry useful.
- Bound investigations by the task's risk and budget. Stop optional work when the goal is verified; persistence is not permission for endless work.
- Mark **BLOCKED** when a necessary step cannot proceed within available authority, access, capability, or budget.

**Done when** (VERIFIED) the requested outcome exists, constraints are satisfied, relevant side effects have been checked, and current evidence supports every criterion in the done predicate. State material limitations; do not label an unverified criterion acceptable on the user's behalf.

## Evidence to report

Per criterion: verdict plus the evidence that supports it (command output, file, test result, observation), not a self-assessment.

## Output

Return a compact handoff; do not narrate routine internal phase bookkeeping. Null case: if the outcome already holds, return `Status: VERIFIED` with `Important changes: none` and the evidence that shows it.

```
Status: VERIFIED | BLOCKED
Outcome: <what now exists>
Criteria: <criterion> — PASS/FAIL/UNCERTAIN — <evidence>
Important changes: <...>
Remaining risk: <... | none>
(BLOCKED only) Completed: <...> | Unmet: <...> | What happened / tried / options / recommendation | Exact input needed: <...>
```
