# Create or extend a project verification skill

Adapted from pstack's `create-verification-skill` (MIT, © 2026 Lauren Tan —
see `LICENSE-pstack`). Changes: harness-neutral paths; a scoped mode for
creating the skill automatically during normal work; an extend mode; a
change-selection table and smoke steps; every seeded feature proven or
marked unproven; a fixed report format with failure classification and a
drift log; firmer guidance on control wrappers; a CI appendix.

**When to use:** `lifecycle.md` decides. In short: automatically, as task T0
of an engineering run, when the project has no verify skill and the change
touches user-facing behavior (**scoped mode**); when a run touches a
user-facing path the map doesn't cover (**extend mode**); or when the user
asks for a full survey (**full mode**).

Every serious project needs a scripted way to drive the real app and prove
behavior: launch it, exercise a feature the way a user would, and capture
evidence. This produces that as a project-local skill, `verify-<app>/`, in
the project skill directory of the harness the project uses (for example
`.claude/skills/` or `.cursor/skills/`). If the project is used from more
than one harness and it isn't clear which directory to use, ask. The skill
is plain Markdown and scripts, so any harness that can read files and run
commands can follow it.

Write it for the next agent, not for a human: it will be read cold, mid-task,
by an agent that has never seen the app.

## Modes

| Mode | Seeds | Use |
| --- | --- | --- |
| **Scoped** | Launch, Doctor, Report, and Cleanup, plus a feature file for each user-facing feature the current change touches | Auto-creation inside a run; cost stays proportional to the change |
| **Extend** | One new feature file and its selection row, in an existing skill | A changed user-facing path matched no feature |
| **Full** | The top 3–5 features, from routes, commands, menus, or docs | The user asks for a broad survey |

Every mode follows the same standards below. Extend mode skips steps 1–2 and
only adds to the map (step 3), then proves what it added (step 4).

## 1. Interview the repo, not the user

Answer these from the codebase and only ask the user what you cannot observe:

- **Surface:** what does a user actually touch? A web UI, a CLI/TUI, a
  desktop app, an API, a mobile app, a library? A repo can have several; pick
  the primary one and note the rest.
- **Run:** how does the app start locally? Prefer the repo's own documented
  dev command (package scripts, Makefile, README quickstart). Note ports, env
  vars, seed data, auth.
- **Drive:** how can an agent interact with it programmatically? Existing
  harnesses first — Playwright/Cypress specs, expect scripts, PTY helpers,
  curl-able endpoints, a debug port. Only then a generic recipe: browser/CDP
  for web and Electron, tmux/PTY for CLI/TUI, plain HTTP for services.
- **Observe:** what evidence can be captured? Screenshots, accessibility
  snapshots, terminal transcripts, response bodies, logs, exit codes, DB
  state.
- **Isolate:** can two instances run side by side (ports, data dirs,
  profiles)? If not, say so in the generated skill: refusing to double-drive a
  shared instance beats corrupting the user's session. The orchestrator's
  preflight reads this answer to decide whether live verification can run in
  parallel.

If the checkout doesn't build or start as-is, fix that first, or report it
precisely, before generating: a skill written against a broken base teaches
wrong steps. When an irrelevant missing asset blocks startup (a static dir the
API never serves, a sample config), the generated skill may create it,
clearly marked as verification scaffolding, and remove it in cleanup.

If the app can't reach a usable state without something the run doesn't
have (secrets, hardware, a paid external service, a manual login), stop and
report a **dead end** with the exact reason. Don't scaffold around it: a
verify skill that fakes the hard part proves nothing. The coordinator records
it on the wiki so later runs don't try again.

## 2. Generate the skill

Write `verify-<app>/SKILL.md` with YAML frontmatter — `name: verify-<app>`
and a `description` naming the app, the surface, and when to reach for it
(without frontmatter, harnesses that support skills won't register it) — and
these sections, each grounded in what the interview found, with no
placeholders left:

- **Launch:** the exact command that starts the app for verification, and
  how to tell it's ready (a log line, a prompt). Launch must reach a usable
  state from an empty data dir, including migrations and seed data. Ready
  means usable, not just that a process answers: a database health check can
  pass while its init scripts are still running. Include teardown. For a
  short-lived CLI or TUI there is no server to keep alive: build the binary
  (or install deps) once, then start each drive in its own isolated PTY or
  tmux session.
- **Doctor:** one read-only check that answers "is this instance worth
  driving?" — process up, right version/build, port owned by us, auth valid.
  Run it first, and again whenever anything looks off.
- **Drive:** the harness recipe with real selectors and commands from this
  repo, not examples. Prefer stable handles (ARIA roles and names, data
  attributes, prompt strings, route paths) over coordinates and tab order.
- **Select:** how to choose features for a change. Match changed paths
  against the Change selection table in `features/README.md`. Few matches:
  drive them in full. Many matches (shared code): drive each match's smoke
  steps, plus full drives for the features the change targets directly. A
  user-facing path with no match: coverage is missing; report it so the map
  can be extended.
- **Evidence:** what to capture and where it goes. Proof standards: exercise
  the real user path, not internal setters or test-only endpoints; capture the
  action and the resulting state, not just the final screen; verify side
  effects (files written, rows inserted, messages sent) alongside what's
  visible; for a state change, prove it with a second read-only view of the
  stored value, not a success message; mock only where a production boundary
  already isolates the external system. When the safe path is a dry-run or
  test mode, verify what it actually skips by observing (files, network, git
  refs) rather than trusting its name — some dry-runs still touch the network.
- **Report:** the result format callers rely on. One line per sub-feature and
  entry point: `verified` or `failed` with the artifact path,
  `verified-unreachable` with the unmet prerequisite and the route tried, or
  `skipped` with the reason. Never report an entry point as verified through a
  different one. Classify each failure:
  - `environment` — Doctor fails or the instance is wedged. Fix or relaunch,
    then retry before blaming anything else. If the fix wasn't obvious, add
    it to that feature's `Gotchas` (or the README baseline if it applies
    everywhere).
  - `map-drift` — the app works but the recipe is wrong (renamed control,
    moved route, changed output, a selection path that no longer exists).
    Append a dated line to `features/DRIFT.md` with the feature, step, and
    what was observed.
  - `product` — the app no longer does what the map says. Report it; never
    adjust the map to match broken behavior.

  Adding knowledge mid-run is fine: a gotcha, a regression step, a missing
  feature. Changing an expected result to match what you just saw is not.
  That belongs to maintenance, after reading the source.
- **Cleanup:** tear down instances the run created. Never kill by process
  name; kill what you started. Cleanup removes instances and scratch state,
  never the evidence: proof survives teardown, in a location the skill names.
- **Helpers:** if driving takes more than a short command per step, ship a
  thin control wrapper (e.g. `scripts/control-<app>` with `doctor`,
  `browser click --role … --name …`, `cli -- …`) so feature recipes stay one
  readable line each, as in the example map. A wrapper also makes the
  recipes scriptable later (see the CI appendix). Every shipped script is
  executable and its invocation is shown in the skill body; a helper the
  reader has to reverse-engineer is not a helper.

## 3. Seed or extend the feature map

Create `verify-<app>/features/README.md`, an empty `features/DRIFT.md`, and
one file per feature the mode calls for. Follow the shape in
`feature-map-example/`.

**README.** Baseline preconditions, driving conventions, proof rules, and a
**Change selection** table: one row per feature file with the source paths
behind it — routes, components, command handlers, API handlers — as
specific globs. Read them from the source, not from file names. Keep globs
tight: a pattern like `src/**` selects everything and makes selection
useless. Shared code that genuinely serves many features gets its own row
listing all of them, which tells callers to use smoke steps.

**Feature files.** From the user's point of view: what the feature is, how
to reach it, how to drive it, and what observable end state proves it. The
four H2s are `Sub-features`, `How to get to it (user POV)`,
`Driving it with <harness>`, and `Gotchas`. `Driving` starts with
`Preconditions:`, then a `Smoke:` line naming the one or two steps that
prove the feature is basically alive, then labeled steps that each pair a
user action with an exact command and its observable result, written before
the step is run. Source paths stay in the selection table, out of feature
files: the files describe what users do; the table describes where that
lives in code.

**Regression steps.** When a fix closes a bug that a drive should have
caught, add a step reproducing it to the relevant feature file as
`**Regression (<date>, <ref>).**`. Show it failing before the fix and passing
after. Fold it into the existing file rather than creating a new one.

If seed data lacks a precondition a journey needs, the journey reports a
failure and the reason goes in that feature's `Gotchas`. Never weaken a
journey to make it pass. A proof that drives one convenient entry point is
incomplete when the map lists others.

## 4. Prove it before handing it over

Run the skill's own instructions end to end: launch, doctor, drive **every
feature you seeded or added** once, capture evidence, clean up. In scoped or
extend mode that's only what the change touched, so it's cheap, and a recipe
that has never run is a draft. If a missing prerequisite stops you short,
mark each feature you didn't drive `(unproven)` in the README index so the
next agent treats it as a draft.

Check the selection table too: every glob matches at least one existing file.

After cleanup, confirm the evidence still exists at the named location — a
cleanup that eats the proof fails this step. Fix what fails, and run the
generated cleanup after every failed iteration too, so broken attempts don't
strand processes and ports.

If you proved it in a stand-in for the real target (a container instead of a
fresh VM, a local stack instead of a remote one), list every setup step the
stand-in did that the target won't. Those stay unverified until a run on the
real target covers them.

## 5. Hand off

Report what the skill covers, which features are proven, the Isolate answer,
and any stand-in caveats. The coordinator records the skill's location,
status, and Isolate answer on the wiki's verification page.

## Appendix: running journeys in CI

None of this runs in CI by default: the journeys are recipes an agent
follows. If the project wants them in CI, keep CI time proportional as the
map grows:

- **Script the recipes.** With a control wrapper, each driving step is
  already an exact command plus an expected result, so turning a feature file
  into a script is mostly mechanical. Keep the feature file as the source;
  regenerate the script when it changes.
- **Select by changed paths** using the Change selection table, the same way
  agent runs do.
- **Tier the runs:** smoke steps for selected features on each PR; the full
  map nightly or before release.
- **Shard in parallel** only if the Isolate answer says instances can run
  side by side.
- **Keep regression steps inside feature files**, so they run with their
  feature's tier instead of piling up as a separate suite.
