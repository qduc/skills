# Evidence: refactor lessons from the term2 rewrite (2026-10/11)

Consolidated from about 1,400 incidents mined from the coordination inbox, jobs, reports, git log and transcripts. Parenthesised pointers name records in the private coordination archive; they are kept for traceability.

### Tie every gate, score and verdict to the exact commit, build and pin it ran on, and re-run after any move, rebase or hook rewrite
The candidate moved constantly. Evidence carried forward from donors, earlier tips, dirty trees or pre-hook snapshots was repeatedly wrong and had to be withdrawn, which cost whole gate cycles.
- evidence: 48; best incidents:
  - The reported 4/9 was a fix-branch score, and candidate fbdd441b lacked `onNativeToolSlots`. A 13:18 build scored against a 13:22 commit gave a meaningless 0/9. (supervisor-steer-2 items 1, 3)
  - The owner ruled "No evidence transfers to another pin without checking relevant changes". Merge-gate reuse of c907/19cfd248 evidence was withdrawn and the full gate re-ran on ce24d83a. (inbox-12; supervisor-steer-79/114)
  - Commit hooks grew `direct-parse.ts` from 200 to 384 lines after PTY runs on the pre-commit snapshot. Later lanes compared committed and tested tree hashes. (inbox-21 "p4B: note-154 donor committed"; inbox-22)

### Before counting a run as evidence, confirm which binary, build and configuration it actually launched
Fixtures defaulted to the legacy `dist/cli.js`, artifacts were stale, and harness settings changed the product. The result was false headlines and unmeasured configurations.
- evidence: 47; best incidents:
  - "E2e 56/56" mostly exercised the legacy CLI. The real direct subset was 8 pass / 16 fail / 3 skip, and 17 of the "passes" were source or package-wiring checks. (issue-65-body-before-20261103.md; supervisor-steer-14/30)
  - Augmenting mock pools enabled `ask_mentor` and dropped both CLIs to 7/9. The rerun with unchanged fixtures gave 9/9. (supervisor-steer-53/99/100)
  - A missing `rewrite/dist` made 43 tests fail at the harness wait, and CI built only the legacy dist. Build freshness is now tied to content receipts for HEAD, not mtimes. (inbox-19 "p1M"; inbox-24 d00f99dd; m6-candidate-suite-baseline-final.md)

### Classify every red as product, fixture, harness or environment, with captured raw evidence, before changing product code
Most first-contact failures were test bugs. Fixing the product to match a wrong oracle would have shipped regressions.
- evidence: 50; best incidents:
  - A PTY harness split 3-byte characters across reads. A raw-byte capture proved it, and the fix was three `setEncoding` lines. (inbox-07 "p1B note56")
  - The bench R2 expectation came from wire output that already contained `\n\n`. Four probes were test bugs, not product failures. (bench-fix-report.md Blocker 2; legacy-editor-race-fix-final.md)
  - One shared fixture used a single directory for HOME and conversations, so all 33 cases failed at startup on the `conv_` check. (m6-queue1-startup-final.md 9384a104)

### Report each result under its own scope and keep blocked, NOT RUN, dropped and deferred separate from pass and fail
Combined headlines repeatedly overstated progress and had to be corrected publicly on the tracking issue.
- evidence: 50; best incidents:
  - A raw 157 pass / 90 fail was really 35 executed failures, 53 admission NOTRUN and 2 legacy N/A. The "39 regressions" were admission blocks. (inbox-06 note54/55)
  - 24/44 included 16 in-process source cases. The direct result was 7 pass / 4 fail / 16 blocked. (coordinator-checkpoint-current.md note 30; inbox-04 note46)
  - "26 composer blocks cleared" was not 26 whole passes. A pass at an earlier assertion exposed later failing contracts. (m6-note43-current.md; m6-provider-readiness-note42-final.md)

### When the new stack cannot truthfully provide an operation or value, refuse it or leave it absent; never return fake success, zero, a proxy or an invented ID
Stubs that report success or default values hide gaps and corrupt cost, replay and authority guarantees. Explicit `unavailable` kept every gap visible until it was really wired.
- evidence: 47; best incidents:
  - Configure, rollover, compact and retry rejected as `unavailable`. `Promise<void>` callbacks would otherwise have reported rejections as accepted. (app-next-final.md; direct-commands-integration-contract.md 22:25)
  - Empty observed usage was not treated as zero cost. Attach time as `createdAt`, guessed `count:1` and synthesized seq/IDs for live-only events were all refused. (parallel-m3-policy-final-report.md; server-canonical-next-final; server-integration-contract-needs §1)
  - The owner rejected a *permanent* unavailable seam. Refusals were temporary and removed in the commit that landed the consumer. (parallel-control-integration-needs.md; parallel-cli-fork-integration-note.md)

### Make oracles discriminating: assert the exact effect, use unique markers, and pair every negative check with a positive control
Many checks passed regardless of behaviour, because of exit code only, substrings real data contains, vacuous zero-counts or markers present in the input.
- evidence: 45; best incidents:
  - R7 matched `2026-10`, which any October timestamp satisfies. The fix asserts that the torn record's `"seq":99` is gone. R12 asserted only exit 0. (bench-fix-report.md Blocker 1; final-review.md)
  - The PTY check used `toContain`, so it passed while every search_replace showed its first edit twice. (inbox-13 8b2872e0)
  - `proof.txt` also appeared in the goal criteria, so assertions passed with zero probes. A host-only nonce was required. (t11 session 1e306875)

### Prove a fix with a check that fails on the unfixed base and passes on the fix, or show the check catches a mutation
Passing tests that never ran red proved nothing. Red-then-green settled disputes quickly and exposed checks that could never fail.
- evidence: 44; best incidents:
  - A reviewer said R17 could never fail. Swapping `process.exit` for `process.exitCode` made it fail 3 of 3. (final-review-delta.md)
  - The pool probe was trusted only after it caught two mutants. A near-trigger probe still passed with the feature disabled. (t11 adopted-removal-model-evidence-independent; inbox-27 "p3S")
  - The replay-ledger probe accepted 18 of 52 replays before the fix and 0 after. (replay-ledger-repair/RESULT.md)

### Publish and pin shared contracts before lanes code against them, land readers before writers, and trace every field and event through every layer
Lanes wrote against unpublished unions and dropped fields in projections. Unknown kinds fell through silently, so features "worked" while data vanished.
- evidence: 45; best incidents:
  - Server and TUI lanes coded against protocol 0a27e134 that "cannot compile" in isolation. The Fact union gained command facts before the decoder registered them. (parallel-server-report.md; m34-lead-session-checkpoint.md 22:30)
  - `FactLine.at` existed in the store but `WireEvent` dropped it. Structured origin was stripped to `kind/id` in the submission body. (server-protocol-final-reconciliation; protocol-origin-contract.md)
  - The v2 adapter had no cases for `message`/`task_changed`, and a non-LogEvent fact appended then vanished in the reducer's default branch. (m6-v2-remaining-vocabulary-final.md; deepseek-session-map.md §3)

### Give each log, decision and shared resource exactly one writer or owner, enforced across processes
Multiple synthesizers and writers produced duplicate terminals, misclassified parks as crashes, and corrupted sequence numbers.
- evidence: 35; best incidents:
  - Two store instances on one session both wrote seq 2. This had been latent since `c319ffeb`, and a single SQLite `BEGIN IMMEDIATE` lock fixed it. (m6-par-session-final.md; m6-serial-session-final.md)
  - Close, `closeInteractions` and replay each synthesized `budget_closed`. (budget-park-needs.md)
  - Over SSH, the first session to drain closed the shared connection for its siblings. (rollover-next-final)

### Never weaken assertions, goldens, oracles or fixtures to reach green; keep the original red and label adapted companions separately
Holding the bar kept real defects visible. A "604 intended differences" proposal turned out to be a real binding bug.
- evidence: 28; best incidents:
  - The 604 tool-schema differences proposed as intended drift were a real bug, fixed at `0f0fac30`. (inbox-01 note31)
  - Golden repair stayed at 2/3 with the runner unnormalized, and the scheduling seam was routed to its owner. (m6-par-goldens-final.md)
  - Legacy-header tests were marked N/A only after a native companion passed on the exact commit, with original counts unchanged. (inbox-07 note61; supervisor-steer-51/52)

### Measure the old implementation's real behaviour, including under interruption, before designing, porting or asserting parity
Specs and plausible simplifications were wrong about error text, partial-text durability and flag gating.
- evidence: 37; best incidents:
  - The old CLI resumes partial text from a `.deltas` sidecar after SIGKILL. That reversed "deltas are live-only" and made partial text a durable fact. (issue-76-approved.md D7; m1-draft.md D7)
  - The spec said `error boom` but the old CLI prints `error 500 boom` twice, so the wrong text shipped. (partial-integration-report.md; bench-report.md)
  - Removing the interactive background shell was halted because the trace showed the old CLI gated it per mode. (inbox-04 note45; supervisor-steer-44/45)

### Treat a flaky or racy failure as unexplained until reproduced on a forced schedule; a rerun pass is not a fix
Random reruns rarely entered the race window. Load-sensitive reds moved between tests, and waits on visible text or ticks were the usual cause.
- evidence: 37; best incidents:
  - Six instrumented reruns passed, while a controlled early-Enter schedule still failed with the 3→4 revision signature. (m6-provider-suite-failure-state.md)
  - A loaded run scored 19/24 at a load average of about 65 on 4 cores, so only at-rest runs counted. (supervisor-steer-29; coord-exam-run-opus-09)
  - A `setImmediate` yield let a child take the parent's response. The fix waits on an engine lifecycle barrier and committed-input acknowledgments, not ticks. (m6-golden-ordering-final.md; inbox-20 "builder-a")

### Attribute a failure or lint error as pre-existing only by running the base under the same harness and comparing by name or bytes
Unbuilt or unrun bases produced false "pre-existing" claims. Byte-identical path comparisons let teams move on without waiving anything.
- evidence: 37; best incidents:
  - The 59-error rewrite build was not called pre-existing because no base comparison had run. (m6-consumer-build-final.md)
  - verify-07's first base comparison was invalid because base was unbuilt. After building 9bbd, restart.e2e failed there too. (verify-07-web-rebased)
  - 54 failing format paths: 52 were byte-identical to base and 2 were failing on both. (m6-provider-keypress-note43-final.md)

### Keep outcomes truthful through every layer: unknown is not "no effect", no-op is not settled, admitted is not completed, and lost commands are never re-executed
Collapsed outcomes turned stale aborts into success and refused cancels into "cancelled". Blind replay would have duplicated side effects.
- evidence: 41; best incidents:
  - Abort `no_op` covered both already-cancelling and stale turns. The protocol now forwards `terminal_accepted`, `cancellation_requested` and `not_current`. (resume-m6-protocol-final.md; server-canonical-completion-final)
  - Pending commands recover as interrupted/`unknown` via read-only `command_status` and never replay. (control-commands-next-final.md; parallel-interfaces-report.md §2A)
  - Commands must carry stable caller keys and a target turn. An unqualified cancel hit queued turn-2. (app-next-final.md Blocker 6; m6-headless-cancel-repair-final.md)

### Write durably with a poisoned handle, ordered atomic batches and strict readers, and prove it with injected faults and real signals
Short writes glue onto torn lines and silent readers lose data. Reasoning missed violations that fault injection found.
- evidence: 35; best incidents:
  - An LD_PRELOAD shim forced short writes, and later appends were refused. A best-effort `turn_ended failed` would have made the log unreadable. (log-report.md; spec-revision)
  - 200-trial signal stress found death after a durable result and a signal before listeners existed. (final-integration-report.md)
  - `readFacts` throws on unknown or torn interior records, but listing skips one corrupt header instead of failing the whole root. (coord-files-16 §3; m6-r8-isolation-final.md)

### Migrate user data copy-first with checksums, keep originals through soak, and keep the new engine out of the old store on every path
Real conversations were at stake. Copy-first plus a namespace guard meant a revert only cost code.
- evidence: 20; best incidents:
  - The owner changed the plan from live migration to copy-first, with no live migration without an explicit go. (issue-65-migration-body.md)
  - Eight copies were converted, and SHA-256 matched before and after with live logs untouched. (m6-conversation-migration-final.md)
  - `conversations-next` refuses any non-`conv_` entry, and a `TERM2_CONVERSATIONS_DIR` override could otherwise point writes at legacy data. (issue-76-approved.md D9; inbox-26 builder-c)

### Derive replay and projections only from persisted accepted facts, at one consistent cut, with one wire frame per accepted boundary
Snapshots plus old tails, regenerated timestamps and split frames made reconnecting clients diverge from replay.
- evidence: 46; best incidents:
  - Catch-up returns `(fromSeq,seq]` with no snapshot prepended, and sequence continues across files with `afterSeq`. (direct-session-store-followup-report.md; lead-rollover-codec-needs.md)
  - Rebuilding the memory notice from today's store would change input on reopen, so the admission snapshot is persisted. (parallel-m4-context-api.md)
  - Reasoning and progress deltas were made explicitly live-only by owner decision, not claimed as replay parity. (m6-v2-raw-retention-contract.md; m6-ephemeral-retention-final.md)

### Exercise the exact shipped build through real use (PTY, real keys, real browser) before calling it ready
Green suites repeatedly missed visible defects that a few minutes of real use caught.
- evidence: 35; best incidents:
  - `/cl` + Enter ran `/clear`, a "Stopped" label appeared on every live reply, and raw JSON showed under shell blocks. (done-jobs-01; inbox-19; supervisor-steer-130/131)
  - The modal was visible while keys went to the composer, because Ink's `useInput` doesn't recheck `isActive`. (m6-provider-keypress-note43-final.md)
  - Host, socket and source checks passed, but the built interactive CLI died with `table index is out of bounds`. (m6-par-workflows-final.md)

### Before a tree-replacement or long-diverged merge, review every main-only change for fixes it would silently drop
A security fix was nearly lost in the landing merge.
- evidence: 13; best incidents:
  - The supersession review found replay-ledger fix 9e18cad7 missing. A PoC was accepted before the port (86fda210) and rejected after. (merge-08-web-whole-landing; inbox-12)
  - 203 main-touched files were classified as identical, formatting-only, older, semantic or absent before landing. (inbox-11 merge-08)
  - Before the push, the agent confirmed that the gated SHA's merge tree equalled the gated tree and that origin was an ancestor. (10:29–10:41)

### Integrate exact original commits serially in dependency order, verified by parent SHA and patch-id, not ancestry
Patch-id checks prevented duplicate and empty picks and caught amended chains that ancestry would miss.
- evidence: 31; best incidents:
  - `04903afc` amends a commit the candidate already had, so `d81c5195` alone would have omitted the drain. (headless-drain-final.md)
  - Five lead-local commits were already on the candidate by patch-id and were skipped. (integration-lead-final.md)
  - Picking `5451b43c` before `77bca90b` would have caused a modify/delete conflict. When the parent was the tip, `merge --ff-only` was used. (integration-next-final.md; integration-rollover-protocol-final.md)

### Before changing, deleting or gating something, find every consumer, sibling path and entry point
Fixes repeatedly covered one path while a sibling kept the bug, and moves broke unchanged callers.
- evidence: 28; best incidents:
  - The draft-loss fix covered plain, `/steer` and `/followup`, but `/skills` still lost drafts. (review-29; c29f729a)
  - Moving the memory item broke unchanged `direct-history-capture.ts:30`, so `/rewind` and both retry commands failed. (t10 session b08cc14f)
  - A parallel sibling could call `runNested` after the stop because admission skipped `#checkStart`. (m6-par-engine-final.md)

### Don't accept a build, typecheck or readback as behaviour; verify through the real consumer and the wire
Compiles passed while tools vanished, settings were never consumed and lint linted nothing.
- evidence: 27; best incidents:
  - `useFlexServiceTier` true and false both omitted `service_tier` on the wire. A persisted `disable=true` still wrote traffic. (m6-inventory-measure-final.md; m6-inventory-privacy-final.md)
  - Four named-role read tools vanished from the catalog while build passed (FAIL 0/5 → PASS 5/5). (m6-subagent-child-catalog-final.md)
  - Root ESLint and tsconfig excluded `rewrite/`. The rewrite tsconfig found two real errors. (m6-complexity-note42-working.md; m6-kernel-complexity-final.md)

### When a structural guard goes red, split cohesive modules or move the contract down; never raise ceilings or widen allowlists, and verify cuts by what actually loads
Raising budgets or relocating code into bridge dirs would have hidden coupling. Runtime load walks showed what static regexes missed.
- evidence: 37; best incidents:
  - conversation.ts went from 499 to 525 lines. The owner refused to raise the 500 limit and the code was extracted back to 499. A hook moved into `adopted/` was stopped. (inbox-10 note91/93; inbox-07 note63)
  - The import regex flagged type-only imports, while a "clean leaf" table missed transitive reach. The runtime probe cut 320 modules to 288. (issue-76-approved.md §8; m1-draft.md D12)
  - Allowlist entries are exact importer-to-file pairs with provenance, never wildcards. (source-boundary-next-final; m6-layers-fix-final.md)

### Check every claimed API, identifier or doc statement against committed source before planning around it
Planning notes, stale contract files and mismatch warnings cited superseded states.
- evidence: 26; best incidents:
  - The app wrote against `port.state().backingSessionId`, which did not exist. (app-rollover-seam-followup.md)
  - The lead's ID-mismatch warning cited superseded notes, while committed engine and replay already aligned. (m2-engine-notes.md)
  - The spec said `openLog` truncates a torn tail, while D6 said reopen is pure. `Tool.idempotent` was documented but never read. (bench-integration-report.md; git-log-03 f1712612f)

### Compile and run cheap guards at every owner commit, then verify the combined candidate where lanes overlap
Deferred builds and hook-disabled commits piled up unverified cross-lane debt that failed at first contact.
- evidence: 26; best incidents:
  - About 21 app commits were made with hooks disabled, "expect compile errors at first contact". The native source with a deferred build produced 23 diagnostics. (app-next-final.md; m6-build-native-final.md)
  - The layer guard failed at integration on a client→source import that runtime checks had passed. (m6-goal-oracles-integration-final.md)
  - Separately verified repairs both changed `headless/direct.ts`, and the combined result was never built. (m6-goldens-independent-final.md)

### Measure on real data and scope every size, speed or ratio claim to the sample measured
Synthetic numbers and aggregates repeatedly looked like gate passes.
- evidence: 31; best incidents:
  - A synthetic 73% reduction came out at 28.86% on real data. The 25.7% aggregate hid that only 29 of 53 logs migrated. (m6-native-format-final.md; supervisor-steer-39)
  - Measuring real logs showed `assistant_turn` repeating 99.1% of content, and that drove the format design. (supervisor-steer-16; m6-native-storage-measurement.md)
  - The first full copy projected about 6.3 h and was stopped for a stratified sample. (coordinator-checkpoint-current.md R10)

### Settle a root cause with a discriminating experiment or trace before acting on a report or first hypothesis
Stack traces and first theories pointed at the wrong layer.
- evidence: 21; best incidents:
  - The BFF returned 400 while the gateway returned 200 for the same body, which located the fault in assertion creation. (m6-config-discovery-fix-final.md)
  - A minimal React/Ink script showed `renderToString` crashing in a passive effect. (m6-par-tui-final.md)
  - A CPU profile found the busy loop in a cached `nextEvent()` promise. (m6-json-workflow-final.md)

### Accept a change only after an independent verifier re-runs it on the exact candidate
Author-tree passes repeatedly missed defects that a separate reviewer caught.
- evidence: 18; best incidents:
  - Slice 92c986d was rejected for a shutdown drain leak and budget consumption. (coordinator-checkpoint-current.md notes 61–64)
  - `direct-session.close` awaited a rejected drain and leaked the lock while 70 existing tests passed. (inbox-07)
  - Non-TTY SSH from home showed the wrong warning (CHANGES REQUESTED, 26/28). (m6-serial-cli-final.md)

### Escalate parity-dropping simplifications and deliberate behaviour differences to the owner, and record each as a decision
Silent drops removed features. Documented differences let the owner decide.
- evidence: 17; best incidents:
  - Disposing a budget-paused session as an interrupted stop removed park-and-resume without approval. (app-next-final.md Blocker 3)
  - Cross-process budget park had no restorable checkpoint, so the lane stopped and recommended the simpler behaviour. (m6-budget-resume-final.md)
  - Deliberate differences were written up in `DELIBERATE-DIFFERENCES-EVIDENCE.md`. (inbox-12 merge-08)

### Keep the old path, safety veto or closed gate in place until the replacement is staged and covers every consumer
Removing vetoes or opening gates early would have exposed half-built paths, while opt-in transports kept rollback trivial.
- evidence: 14; best incidents:
  - The queued/live-task veto removal stayed uncommitted until native transfer existed. (app-rollover-combined-final.md)
  - Canonical SSE stayed 503 with blockers listed until all producers existed. (server-canonical-completion-final)
  - v2 sat behind explicit negotiation with no silent v1 fallback. (m6-v2-server-final.md)

### Preserve evidence: unique per-run output dirs, failed attempts kept, raw captures over summaries, hashes recorded at run time
Overwritten evidence and summary-only reports blocked later audits.
- evidence: 14; best incidents:
  - A path collision overwrote the author's 35 raw files. (coord-files-51; inbox-08)
  - The n88 probes hashed all target files and git state before and after every run. (n88 report "Integrity")
  - A fidelity failure was kept beside the corrected pass. (m6-conversation-migration-final.md)

### Swap configuration by preparing a candidate generation and installing it with a no-throw swap, and test every rebuild or successor path
Global swaps would move running work onto new authority, and successor paths silently dropped settings.
- evidence: 14; best incidents:
  - Configure refuses `busy` instead of cancelling the turn, and an uninstalled candidate is disposed on failure. (configure-session-needs.md; lead-session-current.md bb1cb1a1)
  - Rollover and MCP refresh call `configure({})` and re-derive from defaults. `/clear` reverted auto-approve. (inbox-22; t09 15:53)
  - The configured generation still used the initial surface resolver. (lead-configuration-owner-current-integration.md)

### Keep a stable logical identity, separate from physical storage, and re-resolve stored identity against the current grant
Leaking backing IDs broke attached clients. Path-only identity confused local and remote sessions.
- evidence: 13; best incidents:
  - The app-side rollover changed the public ID, so attached clients could not follow. (lead-next-rollover-gap.txt)
  - `sessionDetails` resolved `${sessionId}.jsonl` and read the predecessor after rotation. (server-rollover-protocol-final)
  - A path-only record is never relabelled as SSH, and a digest-based check stranded sessions after upgrades. (parallel-direct-fork-final-report.md; parallel-app-composition-needs.md §3)

### Account budgets and retries per physical request, count the request about to be sent, and surface hidden retry layers
Stacked or turn-wide accounting mischarged replays and admitted one request too many.
- evidence: 13; best incidents:
  - Transient retries spent the replay allowance until a discriminated `RecoveryChoice`. (parallel-m3-policy-retry-followup-report.md)
  - `turnBackstop: N` sent N+1 requests, and was fixed by counting the upcoming request. (build-24; turn-budget.ts 14b858e7)
  - Children get a fresh budget clamped to the parent's remaining budget. (lead-run-budget-contract.md)

## Smaller lessons
- One-shot notices need an explicit admission seam, never a reusable `request.notice` field. (parallel-app-composition-needs.md §3; route-profile-notice-stage)
- Don't time-gate approval input: the 20 ms guard dropped deliberate keys and was reverted. (coordinator-rollover-20261102-note108.md; build-00-single-key-approval)
- Gate manual actions separately from automatic scheduling. (ca82758f)
- When disabling a framework default (`exitOnCtrlC: false`), new code must own the behaviour. (m6-tui-exit-hint-final.md)
- Insert stored data with a replacement callback; `replace(marker, suffix)` expanded `$&`. (m6-goldens-literal-final.md)
- Round-trip persisted state through JSON in tests, because `undefined` fields vanish. (inbox-01 291bd77d)
- Wrappers must propagate the child's exit or signal code. (t08 14:35; t09 14:50)
- Test teardown must kill child process groups and check for orphans. (inbox-07 fd99)
- Exercise a closed gate only in a derived build that differs by one verified line. (n97-web80-open-gate-verification.md)
- Compaction must confirm it shrank the context and back off: 162 compactions occurred in one turn. (build-core-compaction-thrash)
- Route scripted mocks by method, path and content, never arrival count. (t12 session 55411cf0)
- Cancelling must not silently discard queued user input. (inbox-15 c9e3b5db; inbox-16)
- Before signalling a pid from a marker file, confirm it via `/proc/<pid>/cmdline`. (inbox-12)
- Keep behaviour fixes out of pure-move refactor commits, and verify moves by hash or token equivalence. (m6-complexity-note42-working.md; t10 CLAUDE-AUDIT.md)
- Persisted-format changes need a resume check on logs written by the pre-change build. (inbox-27 "p3S"; session 9a205090 12:35)
