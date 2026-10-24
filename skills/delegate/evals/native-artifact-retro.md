# Native/artifact boundary retrospective — 2026-10-18

Both defects were preventable and introduced during this uncommitted extension,
then found before acceptance. No released regression is claimed.

An artifact worker that stalled on a host without Git caused assessment to raise
`FileNotFoundError`, despite artifact readiness requiring no Git. Independent
review reproduced it through public CLI. The immediate fix omits Git diff evidence
for artifact delivery. The system weakness was that normal developer environments
implicitly supplied Git. The full artifact success journey now runs with no
executables on PATH, in addition to a targeted zero-threshold stall regression.
That environment-level test protects other accidental dependencies in the path.

A parent fault-injection probe interrupted dispatch after the runtime persisted
native intent but before the driver queued its host action. Halting then allowed
observation to recreate a spawn. The new test failed before correction and passed
afterward. Stop now cancels both absent and pending host requests: neither was
issued to a host. Issued requests remain uncertain and require actual inspection.
Prompt and packaging metadata are prepared before the durable launch intent, so
an interrupted intent already has the material required to resume dispatch. No
host call or process launch precedes that intent.

## System checklist

1. Representability: absent driver queue is a valid interrupted native intent;
   absence of an issued request proves only that this driver did not dispatch it.
2. Single source: issuance is recorded in the existing host-action record;
   no second dispatch ledger or automatic replacement path was added.
3. Boundary: host-next persists issuance before returning; host-result validates
   current attempt and matching handle. Prompt exists before intent publication.
4. Coupling: lower-runtime intent and driver queue are separate durable writes;
   recovery and cancellation explicitly cover the gap between them.
5. Assumptions: optional Git availability and uninterrupted dispatch were false.
6. Detection: ordinary PATH hid a dependency; initial halt tests started after
   enqueue and missed the earlier durable-write boundary.
7. Automation: no-Git full journey and stall tests plus injected enqueue failure
   protect these boundaries in the normal unittest suite.
8. Siblings: searched every `git(` in coord_drive.py. Worktree creation/reset,
   base/head lookup, clean/diff, test selection, integration and start/package
   calls are delivery-gated or reached only from a Git workspace. Reviewed native
   start/observe/stop/reconcile and issued-spawn retry transitions; unresolved
   issuance is preserved. Independent review also probed issued spawn -> halt ->
   recovered handle -> stop -> terminal -> resume without duplicate dispatch.
9. Knowledge: public docs state no-Git artifact delivery and observed settlement;
   the prompt-before-intent invariant is now stated beside the durable write.
10. Observability: failures were found in this implementation session; retained
    review, public CLI traces and regression names permit rapid reproduction.
11. Origin: latent in the new extension, rather than an existing behavior changed
    by a released commit. The changes establish previously uncovered boundaries.

Evidence: test_coord_delivery.py, independent review and final test logs linked
from [the acceptance record](native-artifact-results.md). Native observations in
fixtures are supporting evidence; fresh-agent real use is recorded separately.
