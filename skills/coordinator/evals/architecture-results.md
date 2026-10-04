# Outcome-centered Coordinator: verification results

Component and fixture gates verified on 2026-10-04 in the local Linux workspace.
The enhanced default real-use gate is now **passed**: a fresh agent used the shipped
Coordinator skill to complete a genuine repository repair, and the parent
independently verified its delivered workflow and protected completion. Details,
failures, version hashes and limits are in [real-use-results.md](real-use-results.md).
The original completion claim covered component/fixture gates; the later pending
status remained in effect until this real task passed.

The implementation adds protected outcome contracts and separate verification,
acceptance, integration and goal gates to the existing task store. Native/process
execution and engineering methods are separate choices; legacy records adopt the
new plan explicitly. Actual use also prompted a narrow claimcheck helper repair:
labeled compact Coordinator IDs no longer become false commit citations.

## Results

| Gate | Required result | Observed result |
| --- | --- | --- |
| Full skill on a real repository task | Fresh agent reads shipped skill, owns the real workflow end to end, and produces an independently checked deliverable | **Passed:** genuine optional protocol setup repair; native delegation/review/correction, protected completion, 9 parent workflow checks and 12 setup tests |
| Baseline compatibility | All existing tests remain green | Original 219 tests passed; all retained in final suite |
| Deterministic release | Contracts, owner/revision fences, evidence identity, recovery, dependencies, independent completion checks | Original release: 252 tests passed (219 baseline + 33 outcome/runtime), 37.773 seconds; real-use helper heal added one regression, final owning suite 253 passed in 36.143 seconds |
| Runtime fixture delivery | 2 runtimes × 2 methods × 3 successful repetitions | All 12 combinations/repetitions passed on the isolated loader task |
| Process confirmation after recovery fixes | Repeat all six process deliveries | Six successful Term2 deliveries; one interrupted provider attempt retained before explicit replacement |
| Instruction preservation | Old/current skill handle surprises and missed parent goals | Each passed 11/11 assertions across two paired tabletop cases |
| Independent review | No remaining routed must-fix issue | Six initial review lenses; recovery/adversary closure checks clean after fixes |
| Saved evidence audit | Completion gates still pass; checks/artifacts unchanged; process resources settled | All 18 successful deliveries rechecked with current completion guard; 19 attempts accounted for |
| Skill structure | Valid skill metadata | `quick_validate.py skills/coordinator` passed |

The final live matrix uses these successful runs:

| Runtime | Method | Repetitions and saved evidence |
| --- | --- | --- |
| Native host workers | Ordinary bounded worker | `live-v1/result-00.json` through `result-02.json` |
| Native host workers | Installed architect protocol | `live-v1/result-03.json` through `result-05.json` |
| Term2 process | Ordinary bounded worker | `live-final/result-06.json` through `result-08.json` |
| Term2 process | Installed architect protocol | `live-final/result-09.json` through `result-11.json` |

Term2 used the user's selected currently configured route: provider `codex`, model
`gpt-6.1-sol`. The task held goal, authority, artifact scope, and local/integrated
check definitions fixed while varying runtime and method. Workers implemented a
configuration loader preserving legacy input, supporting nested input, and
rejecting invalid ports/forms. Coordinator inspected source, ran independent
checks, accepted evidence explicitly, incorporated the file, verified the integrated
goal, and completed the task through the guarded task-state API.

The architect fixture is an installed representative protocol, not pstack itself.
Initial six process deliveries also passed; the six confirmation deliveries ran
after the process-recovery fixes. Native handle delivery/settlement was recorded
from actual host workers, rather than simulated native receipts.

One final Term2 attempt encountered `Invalid previous_response_id` and its provider
retry streamed an oversized tool argument without editing the artifact. Coordinator
requested stop, observed terminal settlement, checked no known process resources
remained live, preserved the attempt, explicitly revised the assignment, and
launched one replacement on the same selected route. The replacement passed.
The interrupted attempt was never counted as successful or accepted. There was
no automatic redispatch.

## What the negative tests establish

- Worker claims, terminal execution alone, stale reports, wrong owner/revision,
  wrong native handle, changed artifact/report bytes, and stale dependencies cannot
  authorize acceptance or completion.
- Revising an outcome invalidates transitive dependents and preserves independent
  outcomes. Explicit replanning preserves history after a material authorized
  goal change; observation and stop can settle existing old-goal attempts first.
- Missing receipts/handles retain uncertainty. Inspected reconciliation is fenced
  to the current owner, revision, and attempt, refuses known live resources, and
  permits progress through explicit revision rather than automatic replacement.
- Real post-spawn receipt-write faults, launcher loss, fast exits with missing
  identity/terminal receipt, leader exit with surviving children, and timed-out
  checks exercise the recovery boundary. Terminal process publication and check
  cleanup settle the owned group; binary diagnostics retain actual exit status.
- A fresh CLI can use durable evidence and recover incorporation performed before
  its checkpoint. Independent global checks and existing task blockers, decisions,
  and background-work gates still control completion and archive paths.

Review dispositions and mechanism alternatives are in
[finding-dispositions.md](finding-dispositions.md); the class-level prevention and
sibling audit are in [recovery-retro.md](recovery-retro.md).

## Evidence and reproduction

All raw execution/review evidence is retained under
`/home/qduc/.local/state/coordinator/architecture-implementation/`:

- Final test log: `/home/qduc/.local/state/coordinator/architecture-implementation/final-tests.log`
- Baseline test log: `/home/qduc/.local/state/coordinator/architecture-implementation/baseline-tests.log`
- 18-delivery completion/resource audit: `/home/qduc/.local/state/coordinator/architecture-implementation/release-audit.json`
- P2 recovery closure: `/home/qduc/.local/state/coordinator/architecture-implementation/review-p2-closure.md`
- P5 adversary closure: `/home/qduc/.local/state/coordinator/architecture-implementation/review-p5-closure.md`
- Interrupted attempt record: `/home/qduc/.local/state/coordinator/architecture-implementation/live-final/interruption-11.json`
- Paired instruction results: `/home/qduc/.agents/skills/qduc-skills/skills/coordinator-workspace/iteration-1/benchmark.json`
- Standalone instruction review: `/home/qduc/.agents/skills/qduc-skills/skills/coordinator-workspace/iteration-1/review.html`

From the repository root, run the deterministic gate:

```sh
python3 -m unittest discover -s skills/coordinator/scripts -p 'test_*.py'
```

Live worker runs are explicit, provider-backed evaluations. Use
`evals/live_delivery.py prepare ROOT` in a new isolated directory; start each run,
deliver/bind actual native host requests, inspect returned source, and finish only
after settlement. The script's docstring and saved run records describe the steps.

## Limits of this result

This verifies the implemented boundary through the original fixture/failure probes
and one genuine full-skill repository repair using native workers. The native/Term2
method matrix remains fixture evidence; paired instruction checks remain tabletop
exercises. The real task exercised one owned outcome, independent review and an
explicit correction loop, not complex dependency graphs or full-skill Term2 use.
See [real-use results](real-use-results.md) for version, intervention and acceptance
evidence. It does not establish an arbitrary-model/protocol reliability rate. The two
tabletop cases show preserved decisions; both versions passed, and no speed/cost
measurements were captured, so no performance advantage is claimed.

Version one supports cooperative file artifacts, native host observations, and
Linux process groups. Commands must stay in their owned group. Host tool permissions
and OS isolation enforce containment; coordinator decisions still require semantic
inspection. This is a local implementation and verification result, not a deployment.
