# Team lessons: running an eight-lane agent rewrite (term2, 2026-10/11)

Consolidated from about 1,050 incidents mined from the coordination inbox, jobs, reports, git log and transcripts. Parenthesised pointers name records in the private coordination archive; they are kept for traceability.


### Give every file, seam, job and shared resource exactly one owner, and make one integrator the only writer of the candidate branch
When ownership overlapped, lanes overwrote or duplicated each other. Six-plus lanes reconciling `session.tsx` kept moving the tip. Where a sole writer was named and overlap was posted before editing, parallel lanes combined cleanly.
- evidence: 46; best incidents:
  - Six or more lanes declared touches to `session.tsx`, so the tip moved 425ac411 → 66a2a8f1 and donors were only verified on older bases (inbox-17 p3V "candidate tip 66a2a8f1")
  - p1T took over p4E's dirty resume donor while p4E was still running suites, so results came from a mixed snapshot (inbox-22 "resume-model ownership collision")
  - Four lanes each branched from d9664a43 and committed only owned paths, and the integrator combined them with no conflicts (m6-build-combined-final.md)

### Check every claim from another lane, subagent, reviewer or report against the actual source or raw artifact before you build on it or repeat it
Wrong claims about APIs, ancestry, defects and status were common. Each one cost a rework round or a false bug report. Reading the code or artifact directly settled most of them in minutes.
- evidence: 45; best incidents:
  - The notice accessor was written as `port.state()`, but the real API is a `backingSessionId` getter. Separately, a "root fields available" claim turned out to be dropped by the HTTP projection (app-rollover-parity-seam.md; m6-browser-cost-goal-gap.txt)
  - A cache mismatch was reported from the footer, but `usage.png` showed 54% cached, which matched the data (inbox-15 "builder-d: usage mismatch evidence correction")
  - p3V's `6df4219f` was described as adding tests but had none (transcripts-19, 08:37)

### Report verification as separate facts: what ran (with output), what was only read, what was inherited, what was deferred, and exactly which scope each verdict covers
Under the "no checks before M6" freeze, the only thing that kept unverified work from being read as ready was explicit labelling. Partial passes called "green" were the main way overclaims crept in.
- evidence: 45; best incidents:
  - Goal oracles stayed at 10/12 with two failures reserved, and the team refused to call M6 green (m6-goal-parity-integration-final.md)
  - Control, Discord and SSH passed while the interactive exit failed, so the verdict stayed FAIL (m6-par-workflows-final.md; coord-files-37)
  - p3V's handoff separated the gates it ran, the gates it inherited from p3S/builder-d, and what it never opened (inbox-27 "Limits:")

### Gate heavy, scored and timing-sensitive runs on measured load, disk and memory, run scored runs in an announced exclusive window, and treat holds as binding until an explicit RELEASE
Contention made results impossible to attribute. A score failed 19/24 and then passed 24/24 depending on what else was running. Runs labelled "exclusive" turned out to have overlapped other lanes' work.
- evidence: 53; best incidents:
  - The score failed 19/24 under load and passed 24/24 once idle TUIs were killed, but an overlapping e2e run left the cause unattributable (coordinator-checkpoint-current.md note 30)
  - Loaded run 1 was posted as "EXCLUSIVE RELEASED" but overlapped p3V's PTY probe by 6–17 s. It was relabelled CONTENDED and rerun (inbox-11 "CORRECTION: loaded run 1 is NOT exclusive")
  - Waiting lanes' TUIs burned 1.2–1.5 cores each, so load sat near 10 with seven jobs queued and none running (supervisor-steer-140/142)

### Count acceptance only from an execution-capable verifier running the exact commit, and give verifiers shell and write access before dispatch
Read-only, sandbox-blocked and timed-out reviewers repeatedly returned conceptual sign-offs or nothing at all. One diff-only "independent review" missed a reproducible regression.
- evidence: 33; best incidents:
  - A diff-only review was marked "independently reviewed", then an executing reviewer found a reproducible regression (m6-goldens-followup-final.md; m6-goldens-followup-independent-final.md)
  - `pelagic-raven-165` could only read source, so its sign-off was rejected; `snug-bobcat-760` reran the probes and accepted (m6-par-engine-final.md; coord-files-36)
  - Ad-hoc `agent.run` specs with a filesystem scope lost shell, and the verifier launches were denied `canRunShell` (inbox-25; inbox-26 supervisor note)

### Tie every result, gate, handoff and brief to the exact SHA and build it ran on, and re-gate when the pin moves
Acceptance silently stopped applying after reverts, resets and stale builds. Briefs aimed at diffs that had already been committed. One coordinator told lanes a fix was integrated after the candidate had been reset without it.
- evidence: 36; best incidents:
  - When da4cb025 was reverted, verify-07c's gate at 3d36b013 stopped applying and a new gate at 318e88ee was needed (inbox-11 p1B)
  - The coordinator announced the thrash fix as integrated, but p3V had reset the candidate to 22bfb245 and the donor was left on a wip branch (transcripts-17, sonnet-04)
  - Before-captures came from compiled parent `4962ab30` while source HEAD was `fbdd441b` (m6-headless-output-integration-final.md)

### Delete worktrees, clones and scratch only after proving you own them, they are clean and merged, and no process references them through cwd, `/proc` maps or open files
One cleanup broke `run_code` for six live sessions. `pgrep`/`pkill` patterns matched their own shells and gave false results. Audits that checked ownership and process references removed hundreds of trees safely.
- evidence: 37; best incidents:
  - Cleanup removed `time-gap-regression-candidate`, which six sessions were running code from, and `run_code` broke (supervisor-steer-37.md)
  - 12 receipt-owned scratch roots were removed only after a cmdline/env/cwd/fd audit, and two verifier trees were kept for lack of completion proof (m6-resume-list-integration-final.md; m6-worktree-cleanup-final.md)
  - A `pkill -f` killed its own shell, and `pgrep` falsely showed pins as in use (transcripts-16, build-17; transcripts-19, 10:18)

### Coordinate through written inbox and note files, and treat a send or "delivered" receipt as unproven until the recipient's durable reply or the file read-back confirms it
Pane typing collided with other lanes' unsent drafts, ran into steer limits, or left text sitting in a composer. Verdicts left on screen or posted to the wrong file blocked builders for tens of minutes.
- evidence: 43; best incidents:
  - Guarded steering into p14 was refused because the pane held a 17-line draft, and the owner then required file-based coordination (lead-native-preview-and-budget-needs.md)
  - The p1B note was only a composer draft despite a successful `pane run` (m6-tool-inventory-working.md; coord-files-46)
  - A verifier reported its verdict as posted, but it had gone to `tasks/supervisor-inbox.md`, and builder-d sat waiting on it (session 9a205090, 09:29/10:20; transcripts-21)

### Run every local CLI launch, including help and negative controls, inside a loopback-only OS fence proven by positive and negative controls, with the mock provider pinned through the real settings resolver
Unfenced probes reached live endpoints and got 401s. Stored config or a cleared environment could quietly restore the real provider. The OS fence then held across hundreds of launches.
- evidence: 21; best incidents:
  - Two headless prompts went unfenced to a live endpoint and got a 401, so the JS-only fence was redone under `unshare -Urn` (m6-par-resume-review-final.md "Incident"; coord-files-36)
  - A fake-provider test hit the default OpenAI gpt-5.1 route (coordinator-checkpoint.md)
  - About 84 later launches were all fenced and resolver-validated, and external IPv4/IPv6 returned ENETUNREACH (m6-serial-goldens-final.md; coord-files-43)

### Don't defer every compile, test and review to one late milestone, and if you must, restate the deferral in every brief and expect a large backlog at the gate
Batching M2–M5 without individual acceptance produced a pile of cross-file bugs that surfaced late. Repo-default instructions also overrode the verbal deferral.
- evidence: 7; best incidents:
  - M2–M5 were staged without individual acceptance, and later checks found background-wait and SIGINT bugs, a golden parity failure, and formatting failures across 55 files (issue65-body-latest.md)
  - The composition handoff said "Expect compile errors at first contact", and the combined assembly had never been compiled (parallel-cli-final-integration-report.md; parallel-server-integration-state.md)
  - Haiku, DeepSeek and the M3 policy owner ran checks despite the deferral (coord-68 checkpoint 22:08)

### Act on an owner or supervisor instruction at exactly its stated scope and latest version, with run counts honoured and no work on a steer that might still be withdrawn
Over-reading ("no overlap" taken as no concurrency), under-reading (extra runs) and acting on soon-withdrawn notes each cost rework. Resumed agents kept following stale instructions until they were restarted.
- evidence: 31; best incidents:
  - Note 117 allowed one synthetic run and p3V ran three more. Separately, `--select-only` read 1462 real logs before selection review (inbox-12 "note 118"; supervisor-steer-120)
  - A push under note 110 and a commit under note 109 were both overtaken when the notes were withdrawn (transcripts-19; transcripts-20)
  - After a restart, the agent still carried ceremony from STATUS and the diary until it was restarted fresh with "new notes win" (transcripts-03, 09:02–09:52)

### Stage each original commit once, by exact SHA or patch-id, in dependency order, and name any superseded or locally duplicated commit
Local cherry-picks and parallel replays created look-alike commits. Five identical "Format native web wire integration" commits landed, and reports named the wrong patch.
- evidence: 30; best incidents:
  - App commit `600bd3f1` was already staged as `9432578b`, and the owner had to say "do NOT stage 600 again" (app-rollover-parity-needs.md)
  - `1741abe2` and `7234a1a3` shared parent and subject but had different patch-ids, and both reports named the wrong one (integration-native-config-task-final.md)
  - 975f5100 was superseded by 9ea5860a, and the integrator was told never to activate 975f5100 alone (mcp-tool-surface-final.md; coord-files-54)

### Keep one short canonical status per lane, and mark superseded handoffs and claims in place instead of stacking deltas
Stale "absent/pending/blocked" claims kept getting copied forward, and resuming agents picked the wrong header as current.
- evidence: 30; best incidents:
  - `STATUS.md` was 437 lines with "Last checked: 2026-10-24" at the top, and five handoffs each named a different starting file (transcripts-01, 38473b5f)
  - The server kept listing `captureFrom`, timestamps and the cancel seam as missing after 9e843615, 16c89381 and 3628ef32 shipped them (server-protocol-final-reconciliation.md)
  - Successive "CONTINUATION DELTA" sections each overrode the HEAD above them (m34-lead-session-checkpoint.md; coord-files-53)

### Separate harness, fixture and environment failures from product failures before counting evidence, and keep the failed attempts on record
A large share of "red" turned out to be setup. Examples: missing builds, over-long socket paths, wrong oracles, missing hooks in a fresh HOME. Counting these as product failures sent lanes chasing ghosts.
- evidence: 30; best incidents:
  - 43 of 105 tests timed out because the rewrite dist was never built, and building it flipped the discriminator to 6/6 (inbox-18 p3S "DISCRIMINATOR RESULT")
  - The registry fix went through four review rounds with no code change because of `DISABLE_LOGGING=1`, launcher and recorder setup, costing about 55 minutes (transcripts-02, 08:21–08:34)
  - An "agent_status unknown" #134 reproduction was really a missing `herdr-status.ts` hook in the fresh HOME (side CORRECTION; transcripts-19)

### Treat red and intermittent results as evidence: never retry or outvote, compare against the base with enough repetitions and a control, and keep the item open until a cause is found
One clean run at a ~1-in-4 failure rate passes by luck often enough to mislead. Blaming the branch, or blaming load, without a base comparison sent fixes to the wrong place.
- evidence: 29; best incidents:
  - 5/5 clean loaded runs happen about 24% of the time by chance at that failure rate, so an unpatched control plus 20 patched runs was required (transcripts-18, `coord-exam-run-opus-08`)
  - The task-menu test failed 3/11 on base and 2/11 on the pin, and setting only the guard window to 0 gave 0/22, which isolated the cause (`n110-taskmenu/`, `n113-guard-investigation/`; transcripts-20)
  - The supervisor tied an Ollama failure to the release branch, then retracted after the base comparison showed an under-load flake (inbox-26 "decisions 18:26")

### Keep test sessions and probes away from the owner's real settings, stores and private data: redirect every XDG directory, use a scratch HOME, and require written authorization for any real-data read
Shared settings files meant test sessions changed the owner's real configuration. One shipped bug persisted approval mode up to YOLO in both CLIs, and a probe read the live conversation store.
- evidence: 14; best incidents:
  - The tour launchers left `XDG_STATE_HOME` unset, so `/auto-approve off` likely wrote the owner's settings (build-tui-approval-default-owner-env.md)
  - Three Shift+Tab presses set YOLO for both CLIs through shared settings, and scratch-HOME tests hid it (supervisor-steer-147; inbox-16 "SAFETY NOTE")
  - A pre-push scan caught a private `.evidence/.../REPORT.md` in unpushed 7b8920b7 (inbox-08 "GitHub sync stopped")

### Route a cross-owner need to that owner as an exact, numbered, typed request, and never relabel an adjacent field, invent wire events or stub success
Inventing contracts at seams created silent mismatches. Failing closed and asking the owner kept the wire honest.
- evidence: 27; best incidents:
  - Native stored `request.task` only as a label, and protocol was about to present it as original input, so the native owner was asked for a genuine `input` (protocol-canonical-producer-needs.md)
  - The app read `metadata.temperature`, but the real API is `DirectRuntimeContext.configuration` (configure-session-needs.md)
  - Lanes kept SSE at 503 and refused stub success or guessed names (parallel-protocol-parity-final-report.md; coord-files-63)

### Have each fix reviewed by a different model than its author, and have that reviewer build its own driver and read raw evidence
Cross-model reviewers repeatedly caught defects the authors' own tests missed. The owner clarified that "a different agent" is not enough.
- evidence: 27; best incidents:
  - An Opus review of build-25 found that a confirm `y` could steal the approval prompt's `y`, and a re-review found pasted images dropped on cancel (transcripts-20)
  - A fresh cross-model review rejected the memory change and found `/rewind` and `/retry` breakage the original review had missed (transcripts-10, d34b2d5e)
  - The owner clarified that cross-review needs a different model and recorded attribution (p1-note71-correction.md; inbox-08)

### Verify that commands, hooks, watchers and wrappers actually ran and exited as claimed, by reading per-stage status and output content rather than a wrapper's exit code
Exit 0 from a pipeline or orchestrator hid real failures. Hooks silently didn't run. Watchers died at once, expired, or fired on intermediate reports.
- evidence: 27; best incidents:
  - `core.hooksPath` pointed at a missing `.husky/_`, so hooks never ran on three pins, and the "hooks ran" claim was retracted (inbox-11 "HOOKS EVIDENCE"; transcripts-20)
  - The score orchestration exited 0 while the scorer and complexity guard returned 1. In another case, "exit=0" came from `cut` (m6-serial-engine-integration-final.md; transcripts-22, 07:22)
  - The first fallback watcher died on `/bin/sh` rejecting `pipefail`, and watcher `a9a31dc7` fired on the protocol-only interim report (m6-dogfood-next-review-final.md; README.md 22:38)

### Never turn a red gate green by casting, suppressing, raising limits or editing another owner's code; report pre-existing failures by owner, file and line against the untouched baseline
Holding the line kept real debt visible and routed it to the right owner. Splitting a file along a real seam beat raising its line limit.
- evidence: 21; best incidents:
  - The integrator refused to patch 59 cross-layer errors with broad casts and asked for bounded owners (m6-consumer-build-final.md)
  - The harness demanded 12 GiB MemAvailable on a 12 GiB host, and the agent left `run.py` alone for the supervisor to decide (inbox-12 "build-17 real-copy FLOORS")
  - A `run_subagent` description edit broke 8 pinned goldens on main, and the fix restored the text rather than editing the goldens (inbox-26; transcripts-18, opus-05)

### Run a separate dogfood or spot-check lane on the shipped build, doing real work that exercises approvals and every advertised path
Gate tests passed while user-facing and safety defects shipped. Real PTY tours and real jobs found them.
- evidence: 21; best incidents:
  - On shipped a96805cc, each Shift+Tab press persisted an approval mode up to YOLO, and only the side spot-check found it (inbox-16/17)
  - 16 read-only dogfood jobs never requested an approval, so "no wrong approval" was vacuous (side steer-124 note; supervisor-steer-125/132)
  - Running the built Luna CLI exposed four bugs the worker reports had missed (transcripts-06, 10:23/11:17)

### Remove each finished worktree in the same step as its landing, enforce free-disk floors, and measure real reclaim before promising it
Worktrees grew from 133 to 160 while disk fell about 2.5 GB/h. pnpm hard links made `node_modules` look several times larger than what deleting it actually freed.
- evidence: 21; best incidents:
  - 145 worktrees at 100 MB+ each, and 59 idle trees were cleared to reach 14 GB (supervisor-steer-25)
  - Removing `node_modules` freed about 457 MB, not the expected ~3.5 GB, at link count 126 (inbox-04 "housekeeping pass target not reached")
  - New worktree-creating dispatches were barred below 10G free (transcripts-18, opus-10)

### Treat review findings as hypotheses: triage them by ordinary-use impact, accept low-severity items as documented limits, and stop when fixes keep adding mechanism
Review rounds that each found a new edge produced machinery nobody needed. Deleting it, or resolving at use time, worked better.
- evidence: 20; best incidents:
  - An alias binding map and refresh were added, then removed by resolving the sender at send time (b0eff7afe → 6593072cb)
  - review-27 and review-28 each found new gaps, and the later ones were accepted as documented limits (build-25-native-cache-rewind.md)
  - Two of three mentor objections assumed a vendored copy that doesn't exist, so they were rejected (legacy-editor-race-fix-state.md)

### Use only subscription providers for live checks and lanes: a quota error leaves that check pending, the lane moves to another subscription model, and nobody falls back to PAYG
Quota pressure tempted silent billing-route changes. One owner of the quota watcher prevented duplicate watchers and premature credit redemption.
- evidence: 18; best incidents:
  - Luna evidence planned on Codex ran on the OpenAI API after quota ran out, with no approval. Separately, the coordinator ran on OpenRouter PAYG (transcripts-06, `model-selection-pool/review.md`; transcripts-04, 23:38)
  - Codex returned 429, so only the Grok live run counted and Codex stayed pending (m1-draft.md §1)
  - An agent was about to self-redeem a quota credit at 96% and the owner stopped it (coord-files-51 "Owner quota correction")

### Freeze shared interfaces in a published commit before parallel work starts, and don't write code against a provisional or unpublished contract
Lanes coding against types that existed only in someone's uncommitted tree chased SHAs and rewrote their work.
- evidence: 17; best incidents:
  - The control lane built against `WireSubmissionRecord`, which existed only in the protocol owner's uncommitted tree (parallel-control-integration-needs.md; coord-files-58)
  - Task 0 froze types, stubs and the layer guard before Tasks 1–4 ran in separate worktrees (issue-76-approved.md §11)
  - The source was at 0.2.0 while consumers pinned 0.1.0 and the server kept a local v2 mirror (m6-browser-integration-final.md)

### Before taking over, reassigning or restarting a lane, verify its real state from its tree and pane, and have lanes write a durable state file before context rollover
Panes that looked halted were still compacting, and worktrees had moved past old handoffs. Nudging lanes on guesses wasted turns.
- evidence: 17; best incidents:
  - A pane read showed active compaction rather than a halt, and the app worktree had moved past the older handoff (app-takeover-assessment.md)
  - p1H hit its Claude limit with auto-resume pending, so the lead cancelled it and confirmed a clean tree before giving the work to p1D (route-takeover-readonly.txt)
  - Lanes showing compaction notices were nudged while they were only waiting on heavy-run (inbox-18 "supervisor correction")

### Keep process lean: post only decisions, blockers, ready work and outcomes; write the final report once; and give every new gate a removal path
Ceremony piled up one incident at a time. 312 of 895 inbox messages were holds or acks, and a skill grew to 1,083 lines.
- evidence: 15; best incidents:
  - Each incident added a gate and none were removed, and the user said "only remove rule, add no new rule" (transcripts-03, 08:52–08:57)
  - 312 of 895 messages were holds or acks, and one lane wrote 326 (timeline-2026-11-02.md)
  - Small fixes accumulated 109 worktrees and 871 task files through a full handoff chain per fix (transcripts-22, 06:21)

### Match model and effort to the job class: keep ordering-sensitive and contract-owning work with a strong owner, give cheap models only settled narrow leaves, and log the model and effort per job
Defaulting to the most expensive model burned weekly quota fast. Unrecorded models made later attribution impossible.
- evidence: 14; best incidents:
  - High-effort workers took weekly Codex quota from 25% to 45% in about 7 hours (supervisor-steer-21/22.md)
  - The owner asked the team to stop using sol/opus for everything, and a Luna/Terra/Sonnet/Haiku ladder at medium replaced it (supervisor-steer-73/74.md)
  - Engine turn ordering stayed with one owner, while provider edge, log/replay, CLI and bench went to Haiku, DeepSeek and Luna (issue-76-approved.md §11)

### Keep the queue stocked with eligible work tied to named failures, and hand a released lane its next item the same turn
Idle lanes cost hours. Side work that cleared no failure-queue entry didn't move the parity numbers.
- evidence: 12; best incidents:
  - There were 8+ idle episodes, one about an hour, and five of seven lanes stopped after a release (timeline-2026-11-02.md; supervisor-steer-50/64)
  - Complexity and dogfooding work left e2e 25/44 and provider 173/247 unchanged (supervisor-steer-27.md)
  - Four lanes reported "available" for several rounds while the only todo was blocked (inbox-20)

### Disclose every skipped hook per commit along with the checks it would have run, and scope formatters to your own changed files
Whole-tree formatter hooks rewrote unrelated files and caused cherry-pick churn. Undisclosed bypasses would have made the stack look checked.
- evidence: 12; best incidents:
  - Decoder owners committed with HUSKY=0 and --no-verify, so the coordinator required a preflight log per candidate (coordinator-rollover-20261102-note108.md)
  - The hook reformatted `protocol/direct-queue.ts` broadly, and lint failed on 30 unrelated files (inbox-16 "p4B")
  - A blanket Prettier run touched three dirty unrelated files, which were reverted (transcripts-20)

### Make evidence discriminating: give the baseline and candidate the same assertion, make sure a negative control fails without the fix, and don't compare runs that differ in prompt, harness or counters
Probes that couldn't fail, and comparisons across different workloads, produced false confidence.
- evidence: 12; best incidents:
  - The first hold probe only counted requests and missed dropped images, and removing `setImages` showed the corrected probe discriminates (`n107-image-cancel/`; transcripts-20)
  - Native scrollback CPU was 23.55% vs 42.27% on different model output, so no improvement was claimed (inbox-19)
  - Pinned and old-CLI reviews used about 65k vs 48k input, and the comparison was declined (m6-dogfood-first-review-final.md)

### Don't post a donor as ready while a reviewer or verifier concern is open; the coordinator decides concerns, not the builder
The integrator auto-integrated ready posts, so a premature "ready" almost landed real bugs.
- evidence: 10; best incidents:
  - builder-d posted ready with p3S's two concerns open, one a real args-sha truncation bug (transcripts-18, opus-02)
  - The skill-display donor was retracted after a re-review found an exposed injected body (inbox-22)
  - builder-b's retry-noise donor fixed duplicate receipts but not the WebSocket 1006, so that half stayed open (inbox-22)

### Scope every push and irreversible action to an explicit authorization naming the branch, commit, remote and purpose, and hold it until the evidence matches
A gatekeeper that checked landing claims against evidence prevented a weak push. Live migration waited for the owner's explicit go.
- evidence: 8; best incidents:
  - Side held the main push because landing-ready rested only on `--version`/`--help`, and pushed after a real interactive PASS (inbox-12)
  - One non-force push of `task/release-flip-builder-c` was authorized for branch CI only (transcripts-17, sonnet-06)
  - Live migration was left for owner approval after verification on private copies (m6-conversation-migration-final.md)

## Smaller lessons
- Pin every command to an explicit worktree path, because the shell's default cwd often pointed at another lane's tree (m2-lead-state.md; m6-native-format-working-state.md).
- Record each decision's real source and note number, and never present coordinator or peer prompts as the owner's words (supervisor-steer-110/111; transcripts-19, steer-111).
- When the owner is away, decide reversible items and list them for confirmation, and park only owner-only decisions (owner-return-list.md).
- Give each supervisor note a unique ID, because a new note 80 overwrote an unread one (supervisor-steer-80.md).
- Write the finish line down. "Ready for daily use" was undefined until `daily-use-ready.md` defined it (timeline-2026-11-02.md).
- Keep a hand-promoted stable build separate from the canary, and make bug reports name their build (supervisor-steer-173.md).
- Install and build before entering a network fence, or run the installed binary directly, because pnpm bootstrap fails offline (m6-native-format-integration-final.md).
- Write each script's evidence and logs to per-run paths and keep full logs for failures (inbox-09 "note86"; transcripts-11).
- Use `set -e` in combined edit-and-commit scripts, because an interrupted script produced partial commit `69eba177` (lead-rollover-implementation-plan.md).
- In zsh, write `${VAR}:refs`, and confirm pushes with `ls-remote` (transcripts-19, 10:39).
- Keep GitHub closing keywords out of PR text for issues the PR doesn't finish (issue-76-approved.md §8).
- A passing guard proves only what it scans, because `check-layers` skipped whole directories (transcripts-10).
- Preserve runtime evidence outside worktree `.cache` before retiring a tree (investigate-dogfood-web80-parity.md).
- Check hosted CI triggers before assuming a branch push runs CI (inbox-26, builder-c).
- Check the actual cpuset and the gate's real resource before assigning cores or reading floors (coord-files-51; transcripts-15).
