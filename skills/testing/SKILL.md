---
name: testing
description: Produce proportionate automated evidence for software behavior. Use when writing or selecting tests, checking a regression or requirement, investigating a test failure, or assessing whether passing tests support a claim. Compose with implementation, debugging, browser QA, and code review as needed; do not take over their workflows or require tests for every trivial reversible edit.
---

# Testing

**Goal:** behavioral evidence for the caller's criteria, each mapped to PASS, FAIL, or UNCERTAIN. Contribute PLAN through test selection, ACT through bounded test changes and execution, OBSERVE through results, VERIFY through criterion verdicts, and ADAPT through failure classification. Let the caller own implementation, task progression, and completion. Loop vocabulary follows [agentic-loop](../agentic-loop/SKILL.md).

## Phases

1. **Establish the evidence target.** Start from requirements, the relevant change or reproducer, current code state, existing test commands and fixtures, environment constraints, and authority. Inspect repository instructions and nearby tests before selecting a framework. If requirements are ambiguous, distinguish a reversible assumption from a material missing decision; never redefine correctness to match current output. Translate each important requirement into a condition, action, and observable result. Name tests for behavior and derive expected values independently of the implementation. Assert returned data, persisted effects, public errors, or contractual non-effects (for example: a rejected withdrawal leaves the balance unchanged and reports insufficient funds). Avoid repeating production algorithms, private call sequences, or snapshots with no reviewed meaning. Check: every criterion has condition / action / observable result.

2. **Choose proportionate coverage.** Choose the cheapest level that exercises the actual risk, using existing tooling.

| Risk or question | Useful evidence |
| --- | --- |
| Logic, boundaries, transformations | Focused unit tests with independently chosen examples |
| Wiring, serialization, persistence, migrations | Component or integration tests across the affected real boundary |
| Critical journey or browser-specific behavior | A small end-to-end test of the relevant observable journey |
| Third-party protocol compatibility | Contract checks or controlled integration evidence, with environment limits stated |

   Include the normal path and meaningful boundary, rejection, recovery, or regression cases according to impact. Broaden only for a concrete remaining risk or required gate. Do not mandate TDD, exhaustive suites, coverage percentages, or tests that merely mirror implementation. For trivial reversible edits, use an existing relevant check or direct inspection when sufficient; explain any remaining behavior gap. Preserve required host and repository checks (a repository rule against permanent unit tests overrides the table).

3. **Isolate execution.** Load [isolation-and-run-checklist.md](references/isolation-and-run-checklist.md) and complete its Isolation section.

4. **Run and interpret.** Complete the checklist's Run section: confirm discovery, show regression sensitivity when feasible, classify each failure, keep the reproducer.

5. **Return bounded evidence** in the output format below.

## Stop rules

- Do not weaken assertions, delete failing tests, or rerun until green to conceal a failure.
- Treat results as stale after relevant code, fixtures, dependencies, configuration, or environment changes; rerun affected checks before relying on them.
- Keep automated assertions distinct from browser QA of appearance and usability, and from code review of design and static risks. Load those neighboring methods only when their evidence addresses a remaining gap.
- Stop optional testing once the requested evidence is sufficient; do not claim total correctness.

**Done when** every relevant criterion has a verdict backed by executed, discovered tests (or a stated reason it is UNCERTAIN), and both checklist sections are ticked or marked not applicable.

## Evidence to report

Commands, tested revision or change state, environment, discovered and executed scope, outcomes, and useful logs or artifacts.

## Output

```
Commands: <...>   Revision/state: <...>   Environment: <...>
Scope: discovered <n>, executed <n>, skipped <n: names>
Criteria:
- <criterion> — PASS | FAIL | UNCERTAIN — <test name / output>
Failures: <test> — product | assertion/fixture | environment | nondeterminism — <reproducer>
Untested boundaries: <... | none>
```

Null case: `No new tests needed: <existing check or inspection> covers <criterion>; remaining gap: <... | none>`.

Consult [source provenance](references/sources.md) only to inspect the sources and adaptations behind this method.
