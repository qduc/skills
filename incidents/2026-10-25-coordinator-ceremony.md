# 2026-10-25: Coordinator ceremony slowed term2 work to a crawl

## Summary

A term2 coordinator (supervise-panes, Herdr panes) took hours to land
fixes whose code was written in under an hour. Almost all of that time went to
verification ceremony: per-stage private clones and sandboxes, one authorized test
run followed by a mandatory stop, preservation hashing, citation and claim checks,
and separate commit and "combined" stages. The gates were added one incident at a
time by agents, never removed, and never costed.

Removing the rules from the skill was not enough. A restarted coordinator
re-derived the same gates from its own task plans, STATUS file and live worker
briefs. Once those were cleaned too and the live workers were steered onto a
plain worktree, the remaining five reviewed changes merged and passed full
verification within about 30 minutes.

## Impact

Wall-clock times from the coordinator's durable records. They include waiting
and overlap with each other.

| Task | Elapsed | Note |
|---|---|---|
| Tool-call recovery fix | 12h 08m | implementation phase alone 2h 54m |
| Removing a confirmation prompt | 8h 38m | |
| Input queue fix | 4h+ | blocked on a guard repair, then on build-cache drift |
| Goal-check redesign | 3h 16m+ | finished, waiting in line behind the input queue merge |
| New messaging integration | 3h 08m+ | |
| Provider registry fix | 1h 28m+ | code written in about 20 minutes |
| Provider timeout retry | 1h 15m+ | code written in 44 minutes, review passed, not merged |

- **Disk:** the coordinator workspace's `tasks/` folder reached 24 GB. One task
  folder alone held 7 full repository clones (about 301k files) and about 2,600
  documents, 189 of them pure bookkeeping.
- **Defects found:** the bespoke harness produced its own "setup defects" (an
  IPC denial, a broken `execFile` wrapper, a missing `provider-presets.json` in a
  hand-assembled `dist`). None of them were term2 bugs.

## Timeline (UTC)

| Time | Event |
|---|---|
| earlier on 10-24 and 10-25 | Gates accumulate in supervise-panes and in the coordinator's briefs, one per incident. |
| 01:34 | A skills pull request merged after the user declared the session itself the real-use check (35 minutes from review to merge). |
| about 06:51–08:27 | Registry fix: code done by 07:11, then four review rounds (07:12–08:05) about the reviewer's own setup, never the code, then a separate commit stage and a separate combine stage. |
| morning | The user asks for task timings. The coordinator's waste analysis lists symptoms ("late environment discovery") and counts the gates as required work. |
| morning | Independent trace of the raw records finds the mechanism (below) and traces the gates' authorship: mostly coordinator briefs and agent-written skill text. The user's own decisions mostly loosened rules. |
| 09:01 | Skill cleanup committed: `c8a4d11`, removal only (16 files, +54/−1083 lines). Workspace notes trimmed. |
| 09:02 | Coordinator restarted in a fresh session. |
| 09:02–09:21 | Relapse: it inherits gates from task plans and STATUS, blocks the queue merge on `tsconfig.build.tsbuildinfo` drift, and starts a review of a one-line cache exclusion. |
| 09:21–09:27 | User decisions relayed (generated caches aren't work to preserve; keep five historical metadata changes as an exception). Task plans and STATUS cleaned; coordinator restarted again. |
| 09:28 | Input queue merge lands. Acceptance still talks about citation gates, hashes and preservation reports, coming from old briefs and checkpoints. |
| about 09:40 | User-directed steer: stop the bespoke verification rig, verify in a plain detached worktree with `pnpm install && pnpm build` and the standard test commands; acceptance is the diff and test results. |
| 09:43 | Verifier creates `.worktrees/final-verify`; the rig is gone. Installing `socat` was the only environment fix needed. |
| 09:45 | Goal-check merge lands. |
| 09:52 | The first briefs written after the steer contain no gates, which confirms the leftovers were inherited state, not regenerated. |
| 09:55 | The messaging integration, registry fix and timeout retry merge. Final verification on the merged main branch: integration 273 passed / 1 skipped, e2e 36 passed, provider 222 passed / 1 skipped, build and typecheck pass. |
| about 10:20 | Workspace cleaned; 24 GB of finished-task state deleted. Housekeeping step and template cleanup committed (`e420be3`, `40e7658`). |

## Root cause

Verifying the code cost far more than writing it, for four connected reasons.

1. **Every stage built its own test environment from scratch:** a private clone,
   a bwrap sandbox, a network block, custom runner scripts, preflight checks and
   file-hash snapshots. Nothing was shared, so the same environment bugs were
   rediscovered stage after stage (logging, `/dev/null`, `socat`, `/tmp`,
   `XDG_STATE_HOME`).
2. **The rules turned every setup glitch into a round trip.** A reviewer got one
   authorized full test run and had to stop and report on any problem. It
   couldn't fix its own script and rerun in a minute. Instead it wrote a report
   and an 11-point retro, the coordinator wrote a new brief and checkpoint, and
   the worker rebuilt its environment. That's about 10–15 minutes per glitch.
   The full provider suite itself runs in about 1–1.5 minutes.
3. **Gates were only ever added.** Each came from a real incident, such as
   fabricated commit citations, a worker touching uncommitted work, or an
   unwanted dependency install. None were removed or priced, so the
   coordinator's own waste analysis couldn't see them.
4. **Reasonable seed rules were amplified.** "Independent verifier for high-risk
   changes" became nearly everything labelled high-risk. "Preserve others'
   uncommitted work" became byte- and index-level hash snapshots at every stage.
   The user's own decisions to loosen things (risk-scaled review, permission to
   repair test fixtures, more autonomy) were recorded but never reached the
   briefs the coordinator actually wrote. One brief allowed a single full test
   run and required a stop on any setup failure, which directly contradicted the
   user's fixture-repair permission.

### Why the first cleanup relapsed

The ceremony lived in state as well as in rules: task READMEs, STATUS, decision
glosses, checkpoints and the live briefs of running workers. A restarted
coordinator reads that state as its plan and re-derives the gates from it. The
workspace's "never delete evidence without approval" rule also let all of that
state, and 24 GB of clones, pile up indefinitely.

## Contributing factors

- **No setup doc:** term2's docs say how to create a worktree and run
  `pnpm install`, but not that `pnpm build` is needed (it copies prompts and
  provider presets into `dist`) or which command runs which test tier. Every
  stage improvised.
- **Reviewer independence was read as needing a separate environment,** instead
  of separate judgment.
- **The coordinator graded its own process** when asked where time went, and
  counted the ceremony as necessary work.

## What went well

- The user's instinct to measure, then ask for the root cause rather than
  accept the symptom list.
- Removal-only cleanup: no replacement rules were needed. The coordinator
  behaved correctly once the gates and the state carrying them were gone.
- Delivery to workers was confirmed through their own output, not echoes.
- After the steer, the verifier fixed its one environment problem (`socat`)
  itself and reran without a round trip.

## Resolution

| Change | Where |
|---|---|
| Removed preservation oracle, mandatory claimcheck, merge-preservation and combined-result review, intent checkpoints, outcome contracts, retro and healing references (11 reference files) | qduc-skills `c8a4d11` |
| Cleaned inherited gates from the coordinator workspace's AGENTS, STATUS, decisions and task plans | coordinator workspace (local) |
| Steered live workers onto plain-worktree verification; recorded as a user decision | coordinator workspace (local) |
| Added a housekeeping step after each task: summary into STATUS and the task record, then delete scratch, worktrees and merged branches; archive the task record | qduc-skills `e420be3` |
| Template cleanup: removed session diaries, hashes and report copies as evidence | qduc-skills `40e7658` |
| Deleted 24 GB of finished-task state; reset the workspace to a clean snapshot | coordinator workspace (local) |

## Lessons for skill authors

Skills affected: supervise-panes, delegate, coordinator-setup. The lessons apply
to any skill that adds checks, gates or retained state.

1. **Price every gate.** A check added after an incident needs its cost stated
   (time, round trips, files) next to the failure it prevents. Prefer narrowing or
   removing an existing rule over adding a new one.
2. **Let the owner fix environment failures and rerun.** Reserve stop-and-report
   for product failures and missing authority. A rule that makes an agent stop on
   any setup problem turns a one-minute fix into a round trip.
3. **Independence means separate judgment, not a separate environment.** Point
   reviewers at the project's standard setup instead of having each stage build
   its own.
4. **Write a rule's scope with the rule.** Agents amplify short rules
   ("high-risk", "preserve") into the strictest reading. State what the rule does
   not require.
5. **Rules leak into state.** Agents copy skill text into briefs, plans and
   checkpoints. Removing a rule also means cleaning the state derived from it,
   or it comes back on the next restart.
6. **Retention needs an end.** Anything a skill tells agents to keep needs a
   matching cleanup step, or it grows without limit and gets reread as
   instructions.
7. **Don't let a process grade itself.** Agents asked where time went counted
   their own ceremony as necessary work. Measure from raw records.

## Follow-ups

- [ ] Publish the qduc-skills commits (needs the user's approval).
- [ ] Check whether the supervise-panes evals still test deleted rules.
- [ ] Decide whether `references/inbox.md` still needs its hash-checked
      `preserve` step now that finished-task scratch gets deleted.
- [ ] Watch the next finished task for the housekeeping step actually running.
- [ ] If gates reappear in briefs written from scratch, add the term2 setup doc
      (worktree, install, build, test tiers). It was held back because the
      relapse turned out to be inherited state.
- [ ] Unexplained: one provider repeated-question/cancellation test timed out
      once and then passed in two full runs.

## Measurement limits

The provider registry fix and the timeout retry were traced from raw task
records. The tool-call recovery and confirmation-prompt timings come from the coordinator's summary and were not traced
independently.
