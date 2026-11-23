# Testing: isolation and run checklist


## Isolation (phase 3)

- [ ] Synthetic fixtures, temporary storage, clean state per test.
- [ ] Teardown runs after failure.
- [ ] Clocks, randomness, locale, environment variables, ports, and background tasks controlled where relevant.
- [ ] Waits await observable conditions with bounded timeouts, not arbitrary sleeps.
- [ ] Unintended external network traffic blocked.
- [ ] No production credentials, no live-data mutation, no real paid APIs by default; existing authorization and host rules checked before any external test with cost or side effects.
- [ ] Mocks/fakes sit at an explicit dependency boundary while the behavior under test is exercised; real local collaborators used when their interaction is the risk.
- [ ] Doubles match documented contracts and cover relevant errors, not only convenient successes.
- [ ] Mock gaps recorded: a mocked response proves handling of that fixture, not provider availability, authentication, or actual compatibility. Contract or integration evidence chosen only when needed.

## Run and interpret (phase 4)

- [ ] Discovery confirmed: which tests ran, which were skipped, whether assertions executed. A clean exit with zero relevant tests is no evidence.
- [ ] Regression: failure on the old behavior shown when feasible, or a safe bounded negative control used to check assertion sensitivity when that adds value.
- [ ] The failure is the expected behavioral mismatch, not an import, setup, or unrelated error.
- [ ] Any temporary mutation restored.
- [ ] Each failure classified: product behavior | assertion/fixture error | environment failure | nondeterminism.
- [ ] Useful output and the smallest reproducer retained.
- [ ] No assertion weakened, no failing test deleted, no rerun-until-green. Flakiness diagnosed and intermittent results reported explicitly.
