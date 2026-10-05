# Verification and evidence

Define acceptance checks before substantial execution, then refine them as the
task becomes clearer without silently reducing the user's requirements. Tie each
check to an observable outcome or constraint and identify the relevant artifact
or environment. Resolve domain-specific checking methods through supplemental skills.

## Verdicts

| Verdict | Required basis | Consequence |
| --- | --- | --- |
| PASS | Current positive evidence directly supports the criterion | Preserve evidence; check other criteria |
| FAIL | Observed behavior contradicts the criterion | Adapt the approach |
| UNCERTAIN | Missing, stale, indirect, incomplete, or contradictory evidence | Gather discriminating evidence or identify a blocker |

Distinguish a command exiting successfully from the intended action taking effect,
and a correct artifact from its successful delivery. Check the outcome at the
boundary relevant to the user. A mock can establish local behavior but cannot
establish that a live integration works.

## Choose sufficient checks

Scale depth to impact, uncertainty, and reversibility. Use the smallest set of
checks that establishes the required claims, including meaningful failure/edge
cases and side effects where relevant. Do not create tests that merely repeat
implementation details or broad suites for trivial edits.

When an agent or tool reports success, inspect its actual evidence. Independent
checking means using an observable basis distinct from the success claim; it
does not always require another agent. Do not coordinate workers from this skill;
resolve that methodology separately if needed and authorized.

Record exclusions: what was not exercised, unavailable environments, limited
samples, and unresolved contradictory results. Do not hide an essential gap in a
footnote under an overall success claim. Distinguish verified partial results
from the unmet task outcome.

## Invalidate selectively

When a change affects an artifact, configuration, environment, or requirement,
mark dependent evidence stale and rerun the relevant checks. Do not discard
unaffected evidence or repeat all checks without a concrete risk. Verify the
final delivered state, not only an earlier intermediate version.

## Completion gate

Confirm that the requested outcome exists, every required criterion has current
support, constraints remain satisfied, and important side effects are checked.
Residual uncertainty must be within the agreed scope and tolerance; seek the
user's decision if accepting it would materially change the contract.

Once sufficient evidence exists, finish. Do not keep adding optional checks,
features, or polishing work in pursuit of certainty beyond the task's needs.
