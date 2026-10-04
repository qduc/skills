# Recovery retrospective — 2026-10-04

Preventable: yes. The new controller needed explicit invariants at the process,
evidence, and recovery boundaries; happy-path execution alone did not establish them.

Bug: initial implementation could block settlement after a goal change, record a
live process as terminal after receipt publication failed, leave subprocesses
running after worker exit or check timeout, mistake absent process identities for
liveness, and omit a supported transition from inspected uncertain delivery.
Successful checks with binary diagnostics also failed to produce evidence, and
accepted report edits were insufficiently guarded at completion.

Origin: latent in this new implementation, discovered before release by independent
review and parent-run fault injection. No Git history is available in this workspace.

Root cause: leader exit and receipt errors were mistaken for resource settlement;
equality of nullable identities was mistaken for positive process identity;
current-goal guards applied to recovery as well as execution; acceptance relied on
an earlier report hash rather than rechecking it at later gates.

System weakness: separate runtime/check paths duplicated lifecycle assumptions and
the first tests concentrated on normal exits and stale reports before acceptance.

Fixed: positive `process_live` identity is shared by observation, control, and
reconciliation. Shared `coord_process.settle` establishes group settlement before
terminal receipts and after independent checks, including timeout/error paths.
Diagnostics use bounded UTF-8 replacement decoding. Existing-attempt observation
and stop remain possible after a goal change. Explicit owner/revision/attempt-fenced
reconciliation records inspected terminal/non-delivery evidence. Later acceptance
gates rehash reports as well as artifacts.

Hardened: these shared helpers and boundary gates are structural prevention;
real-process fault-injection tests cover the class across launch, observe, stop,
reconcile, timeout, verification, and completion. Final suite: 252 tests passed.

## System checklist

1. Representability: uncertainty is represented explicitly; absent identity cannot
   satisfy liveness. Terminal state requires settlement or an inspected decision.
2. Single source of truth: three liveness consumers use `process_live`; worker and
   check execution share group settlement rather than separate cleanup recipes.
3. Boundary contract: persisted attempt/report identity, goal snapshot, file hashes,
   positive process identity, and coordinator-owned reconciliation are enforced.
4. Implicit coupling: terminal receipt publication and resource cleanup now occur
   in the same launcher path; check timeout cleanup uses the same primitive.
5. Wrong assumptions: nullable identity equality, leader-only exit, infallible
   receipt publication, UTF-8-only output, and immutable accepted reports were wrong.
6. Detection gap: initial tests missed post-spawn I/O faults, surviving descendants,
   fast-exit/missing terminal receipts, changed-goal recovery, and post-accept edits.
   Added tests use actual local processes instead of mocking away the boundary.
7. Automation gap: focused negative tests now mechanically reject these cases;
   the complete baseline-plus-extension suite is the deterministic release gate.
8. Siblings: searched current runtime/outcome/process/state sources for process
   identity, subprocess launch, settlement, current-goal fences, and file references.
   Checked observe/control/reconcile, launch success/error, check success/timeout,
   accept/integrate/verify-goal/complete/archive. Legacy Git staleness inspection and
   protocol resolution are read-only subprocesses, outside worker settlement; no
   additional lifecycle defect established. No sibling left filed as an open fix.
9. Knowledge gap: recovery and separate acceptance were specified, but the missing
   failure transitions needed reachable probes. Runtime documentation now states
   positive identity, process-group settlement, and explicit reconciliation rules.
10. Observability: defects were found during this implementation, before release.
    Durable receipts, raw logs, red/green probes, review files, and closed review
    verdicts preserve the evidence needed to diagnose the same failure quickly.
11. Origin: these invariants were initially unprotected rather than regressed from
    the baseline. The remedy establishes them without changing legacy task behavior.

Later: OS isolation and descendants deliberately escaping their process group are
outside this cooperative Linux version. No additional subsystem is needed for its
declared scope; a future host sandbox must establish its own containment contract.
