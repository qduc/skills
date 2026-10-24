# Automatic model selection verification

> Paths: this evidence predates the coordinator split. `shipped.sha256` and the logs name the old `skills/coordinator/` paths, which now live under `skills/delegate/` (runtime) and `skills/supervise-panes/` (manual procedure).

Request: remove the coordinator gate requiring user confirmation of model selection.

## Acceptance criteria

- A valid harness judgment records and applies its configured route pool without
  opening a new `confirm_selection` question, and advances to task planning.
- Route identity (including optional effort and role) remains validated; workers
  outside the recorded pool are rejected.
- Selection history records the actual coordinator recommendation and rationale,
  not fabricated user consent. Explicit user constraints reach the harness judge.
- Documentation, manual coordination, and eval expectations agree. Other authority,
  independent-check, integration, and real-use completion gates remain intact.

## Supporting evidence

Automated fixtures use temporary repositories/workspaces, local scripted workers
and judges, and bounded waits; they do not exercise real model providers. Run:

```sh
python3 -m unittest discover -s skills/delegate/scripts -p 'test_coord*.py'
git diff --check
```

Unsuccessful development runs (not acceptance evidence): the initial 326-test
run had 24 errors; an intermediate 42-test driver run had one failure and two
errors; a later 327-test run still had one failure and 19 CLI fixture errors.
These exposed obsolete consent expectations, the fixture judgment-retry budget,
and the missing continuation
from automatic selection into planning plus obsolete fixture expectations. The
runtime now reloads selection state and proceeds to planning after persisting the pool; the existing CLI delivery and
end-to-end story checks cover that transition. Invalid-route recommendations
are exercised with a larger explicit test retry budget rather than bypassing
judgment validation.

## Required real-use gate: PENDING

No fresh-agent run using the shipped skill on a genuine additional authorized
repository task has been performed, and no waiver has been requested or granted.
The scripted-worker fixtures are supporting evidence only, not the full-skill
real-use gate. Needed handoff: an authorized representative repository task and
fresh agent execution through the shipped coordinator, followed by independent
inspection and retained execution/task records per
`skills/supervise-panes/references/real-use-verification.md`. Do not treat automated
passes as overall real-use acceptance. No independent real-use inspection exists.

Compatibility: legacy `confirm-selection` questions/commands and `--confirmed`
remain accepted for previously created tasks; newly recommended pools do not
create those questions.

## Proportional retro

Preventable development defect: selection persistence previously ended the advance
call because planning was behind `elif`. Replacing a user-interactive boundary
with an automatic step exposed that implicit coupling. `advance` now reloads the
persisted state and independently checks whether planning can run. The end-to-end
story asserts the next judgment is immediately available with no user questions;
the 17 CLI delivery tests also pass without the old confirmation command. Other
user-question gates and route-admission checks were retained.

Design friction: the driven runtime and manual helpers share the historical
`--confirmed` flag. It remains accepted for caller compatibility, but selection
requires concrete route identifiers and an actual provenance source, not consent.

## Observed final checks

- Full coordinator discovery: **327 tests passed**, exit 0, 105.415 seconds;
  see `coordinator-suite.log`. The `inner-timeout: fails` line is expected output
  from the suite's negative-control fixture, not a suite failure.
- CLI delivery alone: **17 tests passed**, exit 0; see `cli-delivery.log`.
- `git diff --check`: passed.
- `python3 -m json.tool skills/coordinator/evals/evals.json`: passed.
- `shipped.sha256` identifies the tested skill entrypoint, selection runtime,
  state helper, and harness-judgment instructions.
- Tabletop eval definitions were updated but not executed with a model.
- No worker/provider sessions were launched for real-use verification.

Overall acceptance remains **real-use unverified**, not waived. The unrelated
pre-existing change in `skills/term2/SKILL.md` was left untouched.
