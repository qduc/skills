---
name: "risk-first-build"
description: "Use before a build whose intent is still fuzzy, where the human needs to react to concrete examples before work is worth committing to: discover intent by example, verify in order of risk, report honestly. When the goal is already clear, use agentic-loop instead."
---

# Risk-First Build

The expensive failures are at the top of the ladder: building the wrong thing, or the right pieces that don't fit together. Passing unit tests proves only that the code does what you *thought* was wanted. So check the high-level things early and cheaply, and verify in order of risk, not in order of construction.

## Core principles

- **Humans react, agents write.** Never ask the human to write or read a long spec. Show concrete things; turn their reactions into the spec.
- **Verify in order of risk.** Check the riskiest, highest-level assumptions first.
- **The spec is stable, the plan is fluid.** If the spec keeps changing, go back to discovery. If the plan never changes, you are not learning.
- **Verify outcomes, not claims.** Check the actual result against reality, never your own statement that it worked.

## Scale to the task

- **Trivial** (one or two steps, obvious intent): do it, run the real check, report.
- **Medium**: a short Phase 1 (state your understanding plus 1-3 assumptions), then Phases 3-4.
- **Large or fuzzy** (multi-step, multiple components, unclear intent): run every phase and keep the docs.

## Phase 1: Discover what is wanted

1. **Show, react, record (loop).** Turn the rough idea into concrete things the human can judge in seconds:
   - sample outputs for 2-3 *real* inputs, done by hand or roughly
   - a rough mockup or screenshot
   - 2-3 noticeably different options ("A groups by day, B by category, C only exceptions")
   Record each reaction as a decision in the decision log.
2. **Ask only about forks.** Ask only about decisions that are both high-impact and uncertain. Default everything else silently.
3. **Surface assumptions.** List what you assumed as short lines and ask the human to flip any that are wrong.

Repeat until the human's reactions stop surprising you. If the human is not available, take the most reasonable reading, write it at the top of the summary, and continue.

## Phase 2: Lock the target

4. **Define done.** Write acceptance criteria led by concrete input -> output examples. For each criterion pick the strongest available verifier:
   1. deterministic (compiles, schema valid, totals balance, file exists)
   2. executable / observational (run it on real input and inspect; screenshot; read state back; diff before and after)
   3. cross-check (compute two ways and compare; second source)
   4. rubric judge (fresh context, explicit criteria from this step)
   5. human (taste, intent, irreversible actions)
   Break fuzzy criteria into hard checks plus a small fuzzy remainder. If something cannot be checked at all, flag it now.
5. **Write the agent spec.** The detailed version, derived from the decisions. The human does not need to read it; it is the oracle for independent verification.

## Phase 3: Build, ordered by risk

6. **Attack the riskiest assumption first.** Ask: "If this fails, what is the most likely reason?" Usually: the real data looks different, the approach is not feasible, or the human wants something else. Spike that before the safe work.
7. **Thin slice, full height.** Get one path working end to end on real data through every layer before widening. Keep early work cheap to throw away.
8. **Explicit contracts at every seam.** Types or schemas covering units, nullability, timezone, encoding, ordering and error behavior. Validate at runtime and fail loudly. No silent fallbacks or default values at boundaries.
9. **Widen.** Add features while the end-to-end path stays alive. After every change, run the whole flow on real input, not just unit tests. Before changing an interface, find every caller and state what each one assumes.
10. **Pause at decisions, not at the end.** Confirm interpretation, data model and approach choices when they are made.

## Phase 4: Verify and close

11. **Verify independently.** Where it matters, use a reviewer with fresh context that sees the spec and the output, not your reasoning.
    - tests written from the spec and public interface, not from the implementation
    - differential checks: old vs new on the same real inputs; explain every difference
    - property checks: invariants (debits = credits, round-trip identity, totals preserved) over many generated inputs
    - scope check: "What did this change that was not asked for?"
    - adversarial pass: "Find inputs where this is wrong or silently swallows an error."
    - for important test suites, mutation-check them: break the code and confirm a test fails
    Never weaken, skip or rewrite tests to get green.
12. **Report honestly.** Give the result as something concrete the human can react to, plus a verification status per item: verified by what, spot-checked how much, or unverified and needs human eyes. Never imply a check that did not happen.
13. **Learn from escapes.** When a problem slips through, ask "What check would have caught this?" and add it to the verifiers for this kind of work. When a misunderstanding slips through, add the missing question to Phase 1.

## Documents (large tasks)

Keep them short and alive, in a folder for the task:

- **summary.md (for the human, one screen max):** goal, key decisions, open questions. Only what needs human judgment.
- **decisions.md:** one line each, "chose X over Y because Z", including human reactions. Read before changing anything already decided.
- **spec.md (for agents):** acceptance criteria with examples, contracts, verifiers. Stable.
- **plan.md:** current steps and status. Rewrite freely.

Read these first when resuming work in a new session.

## Anti-patterns

- Asking the human "what do you want?" with no concrete options.
- Handing the human a long document to approve.
- Building wide before anything runs end to end.
- Mocking a dependency based on a guess about its behavior.
- Treating green unit tests as done.
- Catching an error and returning a default at a boundary.
- Saving validation for the end.
