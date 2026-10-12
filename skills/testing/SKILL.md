---
name: testing
description: Produce proportionate evidence for software claims, with optional behavioral verification when product behavior is part of the task. Use when writing or selecting checks, checking a regression or requirement, investigating a test failure, or assessing whether evidence supports a claim. Compose with debugging, implementation, browser QA, and code review as needed; do not require behavioral tests for every kind of verification.
---

# Testing

**Goal:** provide bounded evidence for the caller's criteria, each mapped to PASS, FAIL, or UNCERTAIN when applicable. Behavioral verification is one optional form of verification; use it when the task makes claims about observable software behavior. Contribute PLAN through check selection, ACT through bounded check changes and execution, OBSERVE through results, VERIFY through evidence evaluation, and ADAPT through failure classification. Let the caller own implementation, task progression, and completion. Loop vocabulary follows [agentic-loop](../agentic-loop/SKILL.md).

## Phases

1. **Establish the evidence target.** Start from requirements, the relevant change or reproducer, current code state, existing checks and fixtures, environment constraints, and authority. Inspect repository instructions and nearby checks before selecting a framework. If requirements are ambiguous, distinguish a reversible assumption from a material missing decision; never redefine correctness to match current output. For behavioral verification, state the specific observable claims the change is expected to satisfy. Translate each important claim into a condition, action, and observable result. Name tests for behavior and derive expected values independently of the implementation. Assert returned data, persisted effects, public errors, or contractual non-effects (for example: a rejected withdrawal leaves the balance unchanged and reports insufficient funds). Avoid repeating production algorithms, private call sequences, or snapshots with no reviewed meaning. Check: every in-scope behavioral claim has an observable result; do not infer unrelated claims from a general success statement.

2. **Choose proportionate coverage.** Choose the cheapest reliable check that can exercise the actual risk, using existing tooling. A probe is a test, check, or inspection used to produce evidence for one or more claims. Prefer suitable maintained probes already in the project. Select by what the probe reaches and observes, its reliability, cost, and relevant scope; a probe name or green result alone does not establish coverage.
   
   For nontrivial behavioral verification, keep a small claim-to-probe map so it is clear which observations support which claims. This can be an informal note; do not create a catalog or report for a trivial task. One probe may support several claims only when it directly observes each; one claim may need several complementary probes when no single check covers it. Evaluate each claim against the evidence that actually bears on it; do not count unrelated passing probes or treat repeated runs as independent coverage. Reuse prior probe results when the relevant code, setup, and conditions remain unchanged; retain the tested revision as provenance, but do not treat unrelated commits alone as invalidating evidence. Promote repeated manual checks to maintained probes when recurrence, stability, and risk justify the upkeep cost. Keep project-specific scripts and fixtures in their projects.

| Risk or question | Useful evidence |
| --- | --- |
| Logic, boundaries, transformations | Focused unit tests with independently chosen examples |
| Wiring, serialization, persistence, migrations | Component or integration tests across the affected real boundary |
| Critical journey or browser-specific behavior | A small end-to-end test of the relevant observable journey |
| Third-party protocol compatibility | Contract checks or controlled integration evidence, with environment limits stated |

   Include the normal path and meaningful boundary, rejection, recovery, or regression cases according to impact. Broaden only for a concrete remaining risk or required gate. Do not mandate TDD, exhaustive suites, coverage percentages, or tests that merely mirror implementation. For trivial reversible edits, use an existing relevant check or direct inspection when sufficient; explain any remaining behavior gap. Preserve required host and repository checks (a repository rule against permanent unit tests overrides the table).

3. **Isolate execution.** Load [isolation-and-run-checklist.md](references/isolation-and-run-checklist.md) and complete its Isolation section.

4. **Run and interpret.** Complete the checklist's Run section: confirm discovery, show regression sensitivity when feasible, classify each failure, keep the reproducer. Record enough context to judge evidence scope and freshness: tested revision or change state, relevant environment/setup, and what path or conditions the probe exercised. Keep evidence within that observed scope; list important unverified boundaries. A relevant code, fixture, dependency, configuration, or environment change can stale dependent evidence; rerun only affected checks.

   Preserve material failures and retries in the result. A later pass can show that a behavior passed on a later attempt or under changed conditions; by itself it does not erase an earlier failure or establish why it occurred. Report intermittent or eventually-green results as such, and limit confidence to what the successful probe actually supports.

5. **Return bounded evidence.** Map each in-scope claim to the probe results that support or contradict it, and identify gaps. Report PASS only when current evidence directly supports the claim; FAIL when observed behavior contradicts it; UNCERTAIN when evidence is absent, stale, incomplete, or conflicting. Include tested scope and unverified boundaries without implying full correctness.

## Ownership and stop rules

- Testing validates that probes ran as intended, evaluates their evidence against claims, and reports gaps. It does not own causal diagnosis of product failures (debugging), corrective changes (implementation), or routing and overall completion (agentic loop).
- Do not weaken assertions, delete failing tests, or rerun until green to conceal a failure.
- Treat results as stale after relevant code, fixtures, dependencies, configuration, or environment changes; rerun affected checks before relying on them.
- Keep automated assertions distinct from browser QA of appearance and usability, and from code review of design and static risks. Load those neighboring methods only when their evidence addresses a remaining gap.
- Stop optional testing once the requested evidence is sufficient; do not claim total correctness.

**Done when** every relevant criterion has a verdict backed by executed, discovered checks (or a stated reason it is UNCERTAIN), and the checklist sections used are complete or marked not applicable.

## Evidence to report

Commands, tested revision or change state, environment, discovered and executed scope, outcomes, and useful logs or artifacts. For nontrivial behavioral verification, include the claim-to-probe mapping and unverified boundaries; omit the map when it adds no value.

## Output

```
Commands: <...>   Revision/state: <...>   Environment: <...>
Scope: discovered <n>, executed <n>, skipped <n: names>
Claims / criteria:
- <claim> — PASS | FAIL | UNCERTAIN — <probe and relevant observation>
Failures and retries: <attempt/result/classification | none>
Untested boundaries: <... | none>
```

Null case: `No new tests needed: <existing check or inspection> covers <criterion>; remaining gap: <... | none>`.

Consult [source provenance](references/sources.md) only to inspect the sources and adaptations behind this method.
