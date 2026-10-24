# Native workers and file artifacts — acceptance, 2026-10-18

Accepted for the declared cooperative-host scope. The driving agent can use the
same public `coord.py` interface for process/native workers and Git/file delivery.
Native host tools remain a requested-call bridge; the runtime owns attempts,
packaging, checks, acceptance, integration, retries and completion. Provisioning,
interactive Herdr and old-record adoption still use manual coordination.

## Expected and observed

| Criterion | Evidence | Result |
| --- | --- | --- |
| Public native Git and artifact workflows | Actual CLI sessions, workspaces, checks and integration; fixture host observations in test_coord_delivery.py | Pass |
| No-Git artifacts, source preservation, dependencies and binary bytes | Full no-PATH artifact journey plus stall, dependent-outcome and binary tests | Pass |
| Lost issuance, stale/wrong handles, retries and halt | CLI negative journeys plus injected intent-before-queue interruption; independent review probe | Pass in fixtures |
| Existing process/Git compatibility | Original 337 tests plus 17 added tests: 354 passed in 105.132s | Pass |
| Fresh skill-guided native report delivery | Actual native worker, public completion, independent semantic inspection and parent rerun of checks | Pass |
| Public interface hides lifecycle internals | New trace: 26 public coord.py commands; no private lifecycle calls. Independent instruction/code review agrees | Pass |

Final full command: `python3 -m unittest discover -s skills/delegate/scripts`.
Compilation and `git diff --check` also passed. Generic skill-creator validation
rejects the existing `disable-model-invocation` frontmatter key on both HEAD's old
skill and the changed skill; it is not a new failure and that host-specific key
was preserved.

## Genuine real-use task

A fresh coordinator `/root/real_use_native_artifact` read the shipped skill and
produced a useful operator report about this extension, using actual native
worker `/root/real_use_native_artifact/coord_operator_report_1fbb5b44`. User
selection: “Use native subagents with this chat’s settings”. The agent chose its
plan, checks, commands, recovery and acceptance. Task
`6b1a8d8d353e42c8a11ce9c654abfc5a` reached public `done=true` with no outstanding
host actions. Both coordinator and worker were independently observed completed.

The first native admission genuinely failed at the shared worker limit. Repeated
host-next requested reconciliation; explicit tool rejection plus host inspection
supported not_started. The runtime retried after capacity became available. No
duplicate worker was launched. A malformed inspection judgment was rejected and
corrected from the public schema. Both events are retained, not counted as extra
successful deliveries.

The parent read the complete delivered report, inspected its source-backed claims,
validated 16 source citation locations, reran both outcome and integrated goal
checks successfully, and verified SHA-256
`3d851ce019f35bedb126b66079b8f40b0f47680f69b0be022920eeda34204754`.
Source read-only behavior is an authority/instruction boundary, not a sandbox.

Real-use coverage is normal native file delivery and failed-admission recovery.
Lost *successful* spawn responses, live halt/resume and dependent workers were not
exercised by this live run; their negative and dependency evidence is CLI fixtures
plus independent inspection. No arbitrary-host reliability claim follows.

## Old-skill comparison and caller burden

Fresh baseline `/root/baseline_native_artifact` used an archived HEAD skill and
actual inherited native worker `/root/baseline_native_artifact/source_worker`.
It delivered the same kind of source-backed report successfully. The old skill
routed it through manual coordination: 12 procedural references, explicit task
creation/selection/checkpointing, direct supervision and separate citation check.
The new agent used the skill, driven guide and request-specific judgment guides,
then public coord.py calls and requested native host calls. Source reading for
report content is separate from orchestration knowledge. This one paired run
shows the interface burden changed; it does not establish speed, cost or quality
superiority. Reliable token/duration metrics were unavailable.

## Versions, interventions, inspection and retained evidence

Raw workspace: `/home/qduc/qduc-skills/skills/coordinator-workspace/native-artifacts-20261018`. Its `contract.json` states criteria before execution;
`version.json` is the initial content-hash snapshot and `final-version.json` pins
the final executable/guides/tests. Old package snapshot is under
`/home/qduc/.local/state/coordinator/native-artifact-extension-20261018/old-package`.

The implementation owner disclosed concurrent pre-acceptance prompt-intent and
crash-before-queue halt fixes, then froze behavior before successful acceptance.
The parent reported capacity availability after failed admission. No private
helper sequence or prescribed plan was supplied. These interventions limit the
run's evidence for crash timing, which remains separately tested.

`eval-native-artifact/with_skill/outputs` retains the full driving trace, plan,
configuration, worker receipts, inspection, public final status, source hashes,
handoff, delivered report and durable runtime records. `old_skill/outputs` retains
its report, worker contribution, manual trace, raw commands and completed state.
The workspace's `inspection/` retains both independent reviews, reviewed snapshot,
full test logs, parent public status and independent-check results. `review.html`
provides a generated side-by-side evidence viewer; grading.json records the
bounded assertions. All owned workers and the test subprocess have settled.

Independent inspection found one must-fix no-Git stall issue, corrected and
reproduced successfully. Follow-up inspection of crash cancellation, prompt
persistence and public instructions found no remaining must-fix finding.
[Boundary retrospective](native-artifact-retro.md) records the fixes, sibling
inspection and category-level regression protection.
