# Chief of staff vs. agentic loop

## Summary

Both skills delivered all three matched tasks. Keep `agentic-loop` as the
single outcome-owning skill. It used less recorded session time on each pair
and needed less coordination. Keep `chief-of-staff`'s assumption check for
actual worker handoffs.

The trials used the proposed skill versions at
[`ca45783`](https://github.com/qduc/skills/commit/ca45783ba2b53112bb7b8f9e8c01c7117d163cde)
and the same Codex defaults. Fresh sessions invoked one skill by name and
worked in isolated checkouts. Each installer trial paused after the failing
test commit. A fresh session resumed from the arm's own durable record.

## Impact and timeline (UTC)

These are wall-clock seconds calculated from the trial start and end markers
and the separate audit markers. Active time sums both installer sessions and
excludes the planned break. The local verification clock also includes the
break and the auditor's scheduling delay.

| Task | Active, agentic-loop / chief-of-staff | To local verification, agentic-loop / chief-of-staff | Result |
| --- | ---: | ---: | --- |
| One sitting, correct the installer header | 41.0 / 53.6 | 172.5 / 163.9 | Both invocation paths verified after local fast-forward. Comment-only changes. |
| Two sessions, preserve edits to the generated catalog | 189.6 / 259.9 | 239.5 / 303.8 | Both failed first, then passed two independent LF probes and all 13 offline integration tests after local fast-forward. |
| Research, trace optional `/delegate` protocols | 239.9 / 286.1 | 423.5 / 390.8 | Both reports explained why the driver selects a bounded worker and why a stale catalog can still block it. |
| Total active time | 470.5 / 599.6 | | About 22% less recorded active time for agentic-loop. |

Trials began at 17:54. Both documentation candidates were locally integrated
by 17:57:11. Installer integration finished at 17:58:35 and 17:59:52.
Both research notes were ready by 18:00:16 and checked by 18:02:01.

- There was one human kickoff and zero subsequent human interventions. The
  experiment harness dispatched each arm and scheduled the two fresh
  installer resumptions. Human attention is tied by the observed count.
- `chief-of-staff` used one independent installer review and one independent
  research review, plus one research worker. The installer review found no
  blocking issue. The research review led to one revision for source and
  recovery details. `agentic-loop` used zero independent worker or review
  calls. Each installer arm implemented one patch with zero corrective code
  rounds. The research probes needed two and one author retries respectively.
- Each documentation candidate changed one tracked file and each installer
  candidate changed two. Both research branches stayed clean. The installer
  trials each left an ignored Python bytecode cache at handback. The
  external evidence areas held 6 / 13 files for docs, 16 / 26 for the
  installer, and 12 / 15 for research. These counts include the requested
  timestamps, verification logs and trial artifacts. The installer handoff
  used a state file in one arm and a plan, ledger and two task reports in
  the other. Neither arm left a project wiki or verification skill.

## What drove the difference

The documentation change fit in one edit and one check. Both arms worked
directly. The chief-of-staff arm ran the full existing setup suite and both
invocations against real fixture clones. The independent check accepted both
comment-only outputs.

Both installer resumptions recovered the reproduction from disk and preserved
both clones when an extra LF was appended or the catalog's final LF was removed.
The chief-of-staff handoff and independent review added state and a round
trip. In this case the baseline reproduction and independent real-CLI
checks settled acceptance. The installer review took about 42 seconds from
dispatch to return, with elapsed review and main-session work potentially
overlapping.

The research worker and reviewer gave a second implementation trace and a
separate CLI probe. The two reports reached the same operational answer.
Agentic-loop also traced the historical routing table. Both showed that
clearing the stale export let the same task proceed. The review revision
made the recovery evidence explicit in the chief-of-staff note.

## Lessons for skill authors

- Match the review cost to a specific risk. Existing real-entry-point checks
  exposed the installer failure and verified both fixes.
- Keep enough state to make a fresh session runnable. Both formats worked
  when they preserved the failing test, its commit and the remaining check.
- When a worker hands work back, inspect the assumptions and unverified
  paths that can change the acceptance verdict.

## Resolution and limits

Route multi-session coding from `duc-mode` to `agentic-loop`, keep
`/delegate` as the user-invoked worker workflow, and remove the duplicate
outcome-owning skill introduced for the experiment. The handoff check now
lives in [agentic-loop's verification guidance](../skills/agentic-loop/references/verification.md).
Keep real-app verification in `duc-mode` using the project's existing checks
and guides, including a `verify-<app>` skill or `VERIFY.md` where available.
Both code fixes were merged into separate local audit branches and research
was delivered as local notes. The trial patches and `/delegate` research
findings are independent of the skill decision.

Several start markers omit an initial read, so the measured session totals
are lower bounds. The sessions shared a host and ran partly in parallel.
The local verification clocks include auditor queueing, especially the
batched documentation and research checks. Use active time for the within-pair
comparison. Both clocks stop within the local experiment.

This was one sample of each task shape in one repository and harness. The
installer was split deliberately at a test commit. Large engineering fan-out,
long-lived wiki upkeep, and unattended production work remain open questions.
Independent verification passed every acceptance criterion. Escaped-defect
rates are unknown because the experiment ended at local verification.
Session durations, verification times and file counts came from saved
timestamps, Git and file inventories. Round counts also use the retained
review, probe and handoff records.
