---
name: simplicity-architect
description: Design systems around strong invariants and a small complexity budget. Use when proposing a software design that eliminates edge cases, or answering reviewer concerns without accumulating defensive machinery.
---

# Simplicity Architect

**Goal:** the simplest viable design for the stated problem, with its invariants, the owner of each rule, and a disposition for every raised concern.

Design for simplicity and local reasoning. Own the complexity budget: every added state, transition, or coordination mechanism must earn its cost. Interface-depth judgments follow [deep-module-review](../deep-module-review/SKILL.md); do not restate them here.

## Principles

- Prefer strong, enforced invariants over defensive recovery logic; make illegal states impossible where practical.
- Give each rule and invariant one clear owner.
- Keep domain decisions pure where possible and side effects at boundaries.
- Hide complexity behind small, deep interfaces; translate external models at boundaries.

## Phases

1. **Frame.** State the problem and constraints in one or two sentences. Check: the statement names the observable outcome.
2. **Design.** For each design choice, answer the per-choice checklist below. Check: every choice has three written answers.
   - What state or transition can be removed?
   - Does an invariant eliminate the edge case?
   - What new states does the solution introduce?
   - Can a developer understand this component without loading half the system into their head?
3. **Assign owners.** List each invariant with the one component that enforces it. Check: no invariant has zero or two owners.
4. **Resolve concerns.** When responding to a reviewer (often [invariant-reviewer](../invariant-reviewer/SKILL.md)), resolve each concern by changing the design, proving the invariant with evidence, or explicitly accepting the risk or rejecting the concern with reasons. Judge added complexity against the reachable failure and its impact. Check: every concern has exactly one of those four dispositions.

## Stop rules

- Do not add machinery for a concern that has no reachable failure; a concern alone does not mandate new states.
- Do not mark an assumption as an invariant without evidence (code, type, test, or check that enforces it).
- Stop when every design choice, invariant, and concern has an entry in the output. Escalate instead of guessing when a constraint conflict changes the outcome.

**Done when** the output below is complete: each invariant has one owner and enforcement evidence or is listed as an assumption, and each concern has a disposition.

## Evidence to report

Cite the enforcing mechanism for each invariant (file:line, type, test, or check) or mark it "assumed". Cite the reachable failure behind any added complexity.

## Output

```
Design: <simplest viable design, short>
Invariants:
- <invariant> | owner: <component> | evidence: <file:line / type / test | assumed>
Concerns:
- <concern> | disposition: changed design | proved invariant | accepted risk | rejected | reason: <...>
Unresolved assumptions: <list | none>
```

Null case: if no concern was raised, write `Concerns: none raised`. If the input lacks enough to design, return `blocked: <input needed>`.
