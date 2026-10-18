# Judgment: review the checks before implementation

A worker wrote the tests that will decide whether outcome `implements` is done,
before anyone implemented it. Code already confirmed that at least one check
fails today (`red_evidence`), so the tests do exercise something unmet. Your job
is the part code cannot do: decide whether passing these tests would actually
mean the outcome is right.

Read the `patch` (the tests) against `implements` and the task's
`acceptance_criteria`, then try to break it: imagine an implementation that
passes every test and is still wrong. Each such implementation is a missing case.

Look especially for:

- **Criteria with no test.** Every acceptance criterion this outcome touches
  should be exercised by at least one assertion.
- **Only the happy path.** Missing negative cases: inputs that must be rejected,
  look-alike inputs that must *not* trigger the behavior, boundaries, empty and
  malformed input. Over-eager implementations pass happy-path tests.
- **Tests that check the shape, not the behavior.** A function exists, a command
  exits 0, output is non-empty, while the actual result goes unchecked.
- **Tests the implementer could satisfy by special-casing** the exact literals in
  the tests. A few varied inputs per behavior make that much harder.
- **Production code in the patch.** This phase writes tests and fixtures only.

`red_evidence` also lists checks that already pass. Those guard regressions only;
that is fine as long as something else proves the new behavior.

Do not reject for test style, naming, or framework choice. On `reject`, `feedback`
goes to the next test-writing worker verbatim: list the missing cases as concrete
inputs and expected results, so they can be added in one attempt. On `accept`,
`reason` records which criteria you confirmed are covered.
