---
name: testing
description: Produce proportionate automated evidence for software behavior. Use when writing or selecting tests, checking a regression or requirement, investigating a test failure, or assessing whether passing tests support a claim. Compose with implementation, debugging, browser QA, and code review as needed; do not take over their workflows or require tests for every trivial reversible edit.
---

# Testing

Supply behavioral evidence to the caller. Contribute PLAN through test selection,
ACT through bounded test changes and execution, OBSERVE through results, VERIFY
through criterion verdicts, and ADAPT through failure classification. Let the
caller own implementation, task progression, and completion.

## Establish the evidence target

Start from requirements, the relevant change or reproducer, current code state,
existing test commands and fixtures, environment constraints, and authority.
Inspect repository instructions and nearby tests before selecting a framework.
If requirements are ambiguous, distinguish a reversible assumption from a
material missing decision; never redefine correctness to match current output.

Translate each important requirement into a condition, action, and observable
result. Name tests for behavior and derive expected values independently of the
implementation. Assert returned data, persisted effects, public errors, or
contractual non-effects. For example: a rejected withdrawal leaves the balance
unchanged and reports insufficient funds. Avoid repeating production algorithms,
private call sequences, or snapshots with no reviewed meaning.

## Choose proportionate coverage

Choose the cheapest level that exercises the actual risk, using existing tooling.

| Risk or question | Useful evidence |
| --- | --- |
| Logic, boundaries, transformations | Focused unit tests with independently chosen examples |
| Wiring, serialization, persistence, migrations | Component or integration tests across the affected real boundary |
| Critical journey or browser-specific behavior | A small end-to-end test of the relevant observable journey |
| Third-party protocol compatibility | Contract checks or controlled integration evidence, with environment limits stated |

Include the normal path and meaningful boundary, rejection, recovery, or
regression cases according to impact. Broaden only for a concrete remaining
risk or required gate. Do not mandate TDD, exhaustive suites, coverage percentages,
or tests that merely mirror implementation. For trivial reversible edits, use
an existing relevant check or direct inspection when sufficient; explain any
remaining behavior gap. Preserve required host and repository checks.

## Isolate execution

Use synthetic fixtures, temporary storage, clean state per test, and teardown
that runs after failure. Control clocks, randomness, locale, environment variables,
ports, and background tasks where relevant. Await observable conditions with
bounded timeouts instead of arbitrary sleeps. Block unintended external network
traffic. Do not use production credentials, mutate live data, or call real paid
APIs by default; check existing authorization and host rules before any external
test with cost or side effects.

Mock or fake at an explicit dependency boundary while exercising the behavior
under test. Prefer real local collaborators when their interaction is the risk.
Keep doubles aligned with documented contracts and cover relevant errors, not
only convenient successes. A mocked response proves handling of that fixture;
it does not prove provider availability, authentication, or actual compatibility.
Record those gaps and choose contract or integration evidence only when needed.

## Run and interpret

Confirm discovery: which tests ran, which were skipped, and whether assertions
executed. A clean exit with zero relevant tests is no evidence. For a regression,
show failure on the old behavior when feasible, or use a safe bounded negative
control to check assertion sensitivity when that adds value. Confirm the failure
is the expected behavioral mismatch, not an import, setup, or unrelated error;
restore any temporary mutation.

Classify failures as product behavior, assertion/fixture error, environment
failure, or nondeterminism. Retain useful output and the smallest reproducer.
Do not weaken assertions, delete failing tests, or rerun until green to conceal
a failure. Diagnose flakiness and report intermittent results explicitly.

## Return bounded evidence

Report commands, tested revision or change state, environment, discovered and
executed scope, outcomes, and useful logs or artifacts. Map relevant criteria to
PASS, FAIL, or UNCERTAIN; list skips and untested boundaries. Treat results as
stale after relevant code, fixtures, dependencies, configuration, or environment
changes and rerun affected checks before relying on them.

Keep automated assertions distinct from browser QA of appearance and usability,
and from code review of design and static risks. Load those neighboring methods
only when their evidence addresses a remaining gap. Stop optional testing once
the requested evidence is sufficient; do not claim total correctness.

Consult [source provenance](references/sources.md) only to inspect the sources
and adaptations behind this method.
