# Architecture review dispositions — 2026-10-04

Scope: opt-in file outcomes; trusted Coordinator and check commands; cooperative
native workers and Linux local processes; durable recovery; separate acceptance;
legacy compatibility. Commands must not detach from their owned group. Host tool
permissions supply isolation. No hostile same-user sandbox, arbitrary protocol
equivalence, automatic retries, or distributed scheduling is promised.

Each routed finding was reproduced by the parent before repair. Duplicate findings
are grouped below. All routed work is closed; final P2 and P5 closure reviews found
no remaining must-fix issue. Original reports are retained under
`/home/qduc/.local/state/coordinator/architecture-implementation/`.

| Finding and source | Verdict and harm | Adequate fix and mechanism cost | Remove/narrow alternative considered |
| --- | --- | --- | --- |
| Goal edits prevent observation/stop required by replan; P1/P2/P3 | Route; reachable stuck state and inability to stop old-authority work | Remove current-goal guard only from existing-attempt observation/stop; retain execution/acceptance fences | Forbid goal updates while working; conflicts with authority withdrawal and required replanning |
| Post-spawn working-receipt write fails but publishes terminal failure; P1/P2 | Route; live worker falsely settled, duplicate execution possible | Settle a created process before terminal error receipt; preserve uncertainty if settlement fails | Ignore I/O failures; cannot establish recovery truth |
| Binary successful check output raises UnicodeDecodeError; P1 | Route; valid check cannot become evidence | Shared bounded replacement decoding with actual exit status | Restrict check encoding; unnecessary input restriction |
| No explicit settlement/non-delivery transition for unknown native/process delivery; P4 | Route; permanently stuck task after independently established settlement | One owner/revision/attempt-fenced reconciliation with retained evidence and live-resource rejection | Automatic retry risks duplicates; prohibit restart recovery conflicts with the goal |
| Worker leader exit leaves writer subprocess alive; P5 | Route; false completion and later artifact mutation | Shared group settlement before terminal receipt | Disallow ordinary tool subprocesses; makes the worker path impractical |
| Check timeout leaves child running; P5 | Route; runaway work | Same group settlement for checks, including timeout/error | Remove check timeouts; leaves foreground blocked |
| Missing identity equals missing observed identity; final P2/P5 | Route; false liveness, stop failures, reconciliation blocked | One positive-identity predicate used at all three boundaries | Special-case each consumer would duplicate the invariant |
| Report edits after acceptance evade later acceptance checks; parent probe | Route; stale evidence can support completion | Rehash accepted report alongside artifact at later gates | Assume reports immutable; filesystem does not enforce that |
| Generic checkpoints can edit legacy work-item fields; P3 examined | Accept; protected outcome acceptance and completion still independently gate results | Preserve current legacy API and authoritative outcome checks | New universal state model would expand scope without a demonstrated bypass |
| Same-user security sandbox/escaped descendants | Narrow; explicitly outside cooperative runtime scope | Document host-owned permissions and no detaching | Add an OS isolation subsystem; not required for this version |
| Framework/registry/database additions; P6 examined | Reject as unnecessary for this implementation; no proportionality finding filed | Two direct runtime adapters and existing protocol resolver suffice | Generic platform would add unsupported mechanism |

Parent red/green evidence: `regressions-red.log`, `regressions-green.log`,
`descendants-red.log`, `descendants-green.log`, `recovery-checks.log`,
`identity-red.log`, and `final-tests.log`. Closure evidence:
`review-p2-closure.md`, `review-p5-closure.md`. These are recorded inspections,
not unresolved requests for permission.
