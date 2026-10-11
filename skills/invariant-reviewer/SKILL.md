---
name: invariant-reviewer
description: Stress-test a software design or implementation for reachable failures and broken invariants. Use when challenging architectural assumptions or reviewing edge concerns while weighing the complexity of proposed fixes.
---

# Invariant Reviewer

**Goal:** a list of concrete, reachable ways the design or code can fail, each with evidence and one disposition, or an explicit statement that none survived investigation.

Find concrete ways the design or code can fail. Attack correctness, failure modes, hidden assumptions, unenforced invariants, and ownership or boundary leaks.

## Phases

1. **Enumerate.** List candidate concerns across all five attack areas: correctness, failure modes, hidden assumptions, unenforced invariants, ownership/boundary leaks. Check: each area was considered (write "none found" for an empty area).
2. **Establish each concern.** For each concern, establish:
   - A reachable trigger or sequence, supporting evidence, and impact.
   - The layer that should own the rule and the invariant meant to prevent failure.
   - Whether the condition can be eliminated instead of handled.
   - The new states a fix introduces and whether their complexity is justified by the risk.
   Check: all four fields are filled, or the concern is dropped or marked as needing verification.
3. **Classify.** Distinguish demonstrated defects from assumptions needing verification; keep unsupported speculation out of required fixes. Check: every concern is labelled `demonstrated` or `needs verification`.
4. **Dispose.** Recommend one disposition: **fix**, **strengthen/assert invariant**, **document as unsupported**, **accept risk**, or **reject as implausible**. Check: exactly one per concern.

## Pairing and stop rules

- When paired with an architect (for example [simplicity-architect](../simplicity-architect/SKILL.md)), challenge their evidence and counterexamples. The architect owns the complexity budget; a concern alone does not mandate new machinery.
- Do not put a `needs verification` concern into required fixes.
- Do not invent a minimum number of findings; a clean result is valid.
- Stop when every concern from phase 1 has a disposition or was dropped with a reason.

**Done when** each surviving concern has trigger, impact, evidence, owner, and disposition, or the null result is stated with any material uncertainty.

## Evidence to report

Each finding cites its evidence: file:line, a reproducing sequence, a test, or a design-document passage. A plausible story without one is `needs verification`, not `demonstrated`.

## Output

```
Findings:
1. <concern> [demonstrated | needs verification]
   trigger: <reachable sequence> | impact: <...> | evidence: <file:line / repro>
   owner: <layer> | eliminable: <yes/no + how> | fix adds states: <...>
   disposition: fix | strengthen/assert invariant | document as unsupported | accept risk | reject as implausible
Material uncertainty: <list | none>
```

Null case: `No concrete defect survived investigation.` followed by `Material uncertainty: <...>`.
