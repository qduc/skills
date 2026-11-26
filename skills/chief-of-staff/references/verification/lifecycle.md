# Verification layer lifecycle

The project's `verify-<app>` skill is the scripted way to drive the real app
and prove user-facing behavior. It should cost little on day one and get
stronger with every run, without the user having to look after it. This file
is the coordinator's decision procedure. `create.md` and `maintain.md` are
the procedures it calls.

The core loop: **find it → pick the features → drive them → classify
failures → leave it better than you found it.**

## 1. Find it

Look in the harness's project skill directory for a `verify-*/` skill with a
feature map. Then check the project wiki's verification page (see
`../wiki.md`) for a recorded status.

| State | Action |
| --- | --- |
| Skill exists | Go to **Pick the features**. |
| No skill, and the wiki records a dead end or the user declined | Don't try again. Verify with the project's own test commands and mention the recorded reason in the final report. Only retry if the reason is clearly gone (e.g. the missing service now exists). |
| No skill, no record, and the change touches user-facing behavior | **Engineering run:** add task T0, "create the verify skill, scoped to this change" (`create.md`, scoped mode), ahead of every task whose verification depends on it. **Small edit in the main session:** don't create one. Verify with the project's commands. |
| No skill, and the change isn't user-facing | Nothing to do. |

T0 doesn't need the user's approval. It adds files only inside the verify
skill's directory, on the work branch, never on `main`/`master`, and it is
dropped as easily as any other commit. Record it as:

```text
Ruling: created verify-<app> scoped to <features> — no scripted way to prove
user-facing behavior — cost if wrong: an unwanted directory on the branch
```

The one thing to ask: if the project is used from more than one harness and
it isn't clear which skill directory to use, ask where the skill should live.

If T0 finds the app can't reach a usable state without things the run
doesn't have (secrets, hardware, a paid external service, a manual login),
stop T0. Record the dead end and its exact reason on the wiki's verification
page, and fall back to the project's test commands. A dead end recorded once
saves every later run from rediscovering it.

## 2. Pick the features

Each feature map's README has a **Change selection** table mapping each
feature file to the source paths behind it. Match the branch's changed paths
against it:

- **A path matches one or a few features:** drive those features in full.
- **A path matches many features** (shared components, layout, auth): drive
  the **smoke** steps of each matched feature, and drive in full the ones
  the change targets directly.
- **A user-facing path matches nothing:** coverage is missing. Extend the
  map: the task that touches it (or a small follow-up task) adds a feature
  file and a selection row, and drives it once. That is how coverage follows
  your work.
- **A selection path no longer exists in the repo:** that's map drift. Note
  it for the scoped maintenance below.

Features marked `(unproven)` are drafts: drive one before relying on its
verdict.

Small edits use the same table. If an edit in the main session touches a
mapped feature, drive that feature's smoke steps before reporting.

## 3. Drive and classify

Follow the skill's Launch, Doctor, Drive, Report, and Cleanup. Record one
verdict per sub-feature and entry point. Classify each failure:

- `environment` — fix or relaunch, then retry.
- `map-drift` — the app works but the recipe is stale. Append it to
  `features/DRIFT.md`.
- `product` — a real regression. It becomes a finding.

**What you may change mid-run, and what you may not.** Adding knowledge is
fine: a gotcha, a regression step, a missing feature file. Changing an
expected result to match what you just saw is not. That rewrites the
standard instead of meeting it, and it belongs to maintenance, after source
reading.

## 4. Leave it better than you found it

Each of these is small, happens during normal work, and builds on the last:

- **Gotchas from fixed traps.** When an `environment` failure needed a
  non-obvious fix (slow init, port clash, focus trap, a required env var),
  add it to that feature's `Gotchas`, or to the README's baseline if it
  applies everywhere.
- **Escaped bugs become regression steps.** When the work fixes a defect
  that a verify drive should have caught, the fix includes a driving step
  that reproduces it. Show it **failing before the fix and passing after**,
  and keep both verdicts as evidence. Add it to the existing feature file as
  `**Regression (<date>, <ref>).**` rather than as a new file, so the map
  grows in depth, not sprawl. If the project runs a bug retrospective, a
  bug judged preventable is a prompt to add one.
- **Coverage from touched features**, as in **Pick the features**.
- **Scoped maintenance on drift.** At the end of the run, if
  `features/DRIFT.md` has entries (this run's or earlier ones), run
  `maintain.md` in scoped mode on just those features. It edits only the
  verify skill's directory, on the work branch, so no approval is needed.
  This keeps drift from piling up until the layer gets weaker with use.

## 5. Periodic full audit

The full `maintain.md` pass drives every feature, so its cost grows with the
map. Keep it periodic: offer it when the user asks, after a large change to
user-facing behavior, or when scoped passes keep turning up drift in
neighboring features. Besides fixing drift, it prunes features the app no
longer has and tightens selection paths, so the map doesn't just grow.

## Cost

Per run, the cost follows the size of the change, not the size of the map:
selection picks the touched features, broad matches drive only smoke steps,
and scoped maintenance covers only drifted features. Only the periodic full
audit scales with the map. If the project later moves these journeys into
CI, see the appendix in `create.md`.
