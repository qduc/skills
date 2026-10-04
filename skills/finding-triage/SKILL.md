---
name: finding-triage
description: Gate between a review and the fixes. It sets the must-fix bar, costs each proposed fix in added mechanism, and decides route, narrow, accept or reject per finding. Use when writing a reviewer brief, when review findings or PR comments arrive, before acting on them or routing them to an implementer, or when fix rounds keep producing new bugs.
---

# Finding triage

Review findings are input to a decision, not a work order. Handling an edge case costs complexity, and complexity is where the next round's bugs live. This skill sits between the reviewer and the implementer, whether the implementer is a delegated worker, a teammate, or you. It keeps scope fixed, holds findings to a harm bar, and makes each fix pay for the **mechanism** it adds.

**Mechanism** is anything a fix adds that must itself stay correct: a new branch or special case, a config flag or option, a state field or cache, a validation layer, a retry or fallback path, a lock or queue, a background process, a cross-component handshake.

## 1. Fix the scope

Write down the scope the work is judged against:
- the settled decisions;
- the supported environments;
- the realistic usage pattern (who runs it, how often, how many at once);
- the deliberate non-goals.

A finding outside this scope isn't a defect of this work. The scope is complete when a reviewer could tell from it alone whether a scenario is reachable.

## 2. The must-fix bar

A finding is **must-fix** only when both are true:

1. It's **reachable in scope** under realistic use. It doesn't depend on hand-edited or externally corrupted state, or on a configuration the scope excludes.
2. It causes one of these harms:
   - **Wrong result:** the main path produces incorrect output, or fails the purpose or acceptance criteria the work exists for.
   - **Regression:** existing behaviour, or a contract other code or users rely on (an API, a file format, a CLI flag), breaks.
   - **Silent loss:** work, data or a decision disappears without an error.
   - **Stuck state:** no later retry, run or restart recovers without manual repair.
   - **Corruption:** stored state is overwritten or made inconsistent.
   - **Blocked foreground:** the user's turn, request or interactive path hangs or fails.
   - **Exposure:** secrets or private data leak into prompts, logs or output, or a security boundary is crossed.
   - **Runaway process:** recursive, orphaned or unbounded processes or spend.

Everything else is **should-fix at most**. That includes failures the next run heals by itself, a wasted call, a harmless duplicate, a noisy log, style, and cases reachable only through tampering. If the scope names a domain requirement (compliance, accessibility, a performance target), a violation of it joins the harm list. Add it only when the scope names it.

## 3. Cost each fix

For every fix that adds mechanism, name a **remove-or-narrow alternative**:
- **Remove:** drop the feature or path that makes the case possible.
- **Narrow:** restrict inputs, environments or concurrency so that the case can't occur, and state that restriction.
- **Accept and document:** the harm is below the bar, the recovery path exists, and one sentence tells users what to expect.

Prefer the alternative whenever it's adequate. Choose the mechanism only when the harm is on the bar and no alternative removes it.

## 4. Brief the reviewer with the bar

When you commission a review, put the scope from step 1, the bar from step 2 and the costing rule from step 3 in the brief. Ask for **one pass** that reports every must-fix it finds. For each finding, ask for a reproducing probe, the simplest adequate fix and a proportionality note. Name any known observations and ask the reviewer to rate them against the bar, rather than just listing them. A reviewer never questions scope unless it's asked to; this step is the asking.

## 5. Triage what comes back

Give every finding exactly one verdict, with a one-line reason:
- **Route:** must-fix, and its fix is the simplest adequate one. Only routed findings go to the implementer.
- **Narrow:** fix it by removing or restricting scope instead of adding mechanism.
- **Accept:** below the bar. Document the behaviour where users will see it.
- **Reject:** not reachable in scope, or wrong. Say why, citing your own check of the evidence.

Verify at least one probe yourself before routing on it. Record every verdict where later rounds will see it, so a rejected finding isn't re-raised as new. Triage is complete when every finding has a verdict and a reason, and the routed list contains nothing below the bar.

## 6. Watch the rounds

Across fix-and-review rounds, the healthy signal is that routed findings fall to zero. Two signals mean the scope is too large for its mechanism:
- New must-fix findings keep appearing in the code the last round's fixes added.
- Each round's fixes add more mechanism than they remove.

When either shows up, stop fixing. Re-scope with the decision owner (remove or narrow the feature), then review the smaller design fresh. Another round on the same scope isn't progress.

## Neighbours

`proportionality-review` asks whether a whole design is overbuilt. `adversarial-review` and `code-review` find the defects. This skill decides which of those findings earn their fixes.
