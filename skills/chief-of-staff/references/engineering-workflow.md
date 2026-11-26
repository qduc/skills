# Engineering execution workflow

Use for substantial engineering changes: multi-task plans, refactors,
migrations, and bug fixes that need coordinated implementation. Small edits go
straight to the main session or a single worker.

Contents:

1. Plan before implementation
2. Run workspace and ledger
3. Preflight conflict scan
4. Isolate and dispatch each task
5. Assumption check
6. Task review
7. Bounded fix loop
8. Final whole-branch review
9. Finish and clean up

The verification steps (5–8) follow the failure model in SKILL.md: workers
report accurately but can lack context, misjudge, or overlook. Each step aims
at one of those, not at re-confirming reported work.

## 1. Plan before implementation

1. Understand the request and inspect the relevant code and project guidance.
2. Define the desired outcome, non-goals, global constraints, and observable
   acceptance criteria in the shape `assets/brief.yaml` uses: action → exact
   command → observable result, for every affected entry point.
3. Break the work into small, verifiable tasks.
4. Express dependencies explicitly. A later task must not build on an earlier
   one until that output is accepted.
5. Identify the verification for each task and for the final result. For
   user-facing behavior, follow `references/verification/lifecycle.md`:
   find the project's `verify-<app>` skill; if it's missing and no dead end
   is recorded, add task **T0** (scoped auto-create) ahead of the tasks that
   depend on it; use its Change selection table to name the features each
   task must drive; and plan an extend step wherever a touched user-facing
   path has no feature. For a bug fix the verify layer should have caught,
   the task also adds a regression step that fails before the fix and passes
   after.
6. Identify irreversible operations, security-sensitive changes, and external
   side effects before execution.

Settle architectural choices with meaningful alternatives before assigning
implementation. Implementers should not be making unbounded architecture
decisions that belong to the orchestrator or the user — they lack the context
to make them well.

## 2. Run workspace and ledger

Create a plan-specific workspace in an ignored project state directory or the
harness's durable workspace, separate from the wiki:

```text
runs/<plan-id>/
  plan.md
  progress.md      # start from assets/progress.md
  briefs/
  reports/
  reviews/
```

The first line of `progress.md` identifies the plan:

```text
# Run ledger — plan: <plan path or stable plan ID>
```

The ledger is the recovery map; update it as work happens, not at the end. Per
task, record:

- Task ID, objective, dependencies, owner, workspace.
- Status: `queued`, `working`, `reported`, `reviewing`, `fixing`, `accepted`,
  `blocked`, or `deferred`.
- Brief, report, and review paths; worker/session ID; commit(s).
- Verification evidence and reviewer verdict.
- Assumption-check outcome, fix rounds, open findings, and rulings.

A worker's `DONE` means `reported`. Only mark `accepted` after the assumption
check and review gate pass.

On resume, confirm the ledger belongs to this exact plan, read it, inspect
worker/process/session state, and reconcile with artifacts and version
history. Do not redispatch completed tasks. Resume an in-progress fix loop at
its next round. Never infer completion from memory alone.

## 3. Preflight conflict scan

Before the first implementation dispatch, scan the whole plan and record the
results in the ledger as a visible table — not just "preflight clean". This is
the main guard against missing context: it catches what no single worker could
see from inside its own task.

Check:

1. **Task-to-task overlap:** Which pairs touch the same files, interfaces,
   schemas, or shared state? What does one produce that another consumes?
2. **Internal consistency:** Does each task's description agree with its own
   tests, files created, and files later modified?
3. **Global constraints:** Does any task contradict the specification,
   project conventions, security requirements, or another task?
4. **Write ownership:** Is every writable file owned by one worker at a time?
5. **Git/index contention:** Would workers stage, commit, or mutate shared
   repository state concurrently?
6. **Test interference:** Would concurrent tests see each other's in-progress
   changes or contend for shared services? If the verification skill says
   two instances can't run side by side, live verification is serial even
   when the code changes are independent.

One row per overlapping task pair and one per task's internal consistency.
Resolve conflicts before dispatch; prefer serial execution when ownership or
dependencies are unclear. If the plan requires a questionable implementation,
compare it with the binding spec and record a ruling rather than following a
defective plan.

## 4. Isolate and dispatch each task

Use a dedicated worktree (or whatever isolation the harness offers: sandbox,
container, separate checkout), or verify that the plan workspace is isolated.
Never begin
implementation on `main`/`master` without explicit user consent.

For each task:

1. Record the base commit.
2. Write a brief from `assets/brief.yaml` with the task's full requirements
   and the relevant global constraints.
3. Dispatch one fresh implementer with the brief path and exact workspace.
4. Ask the implementer to raise material ambiguities before coding; resolve
   them centrally.
5. Require focused tests while working and the task's gates before reporting,
   with commands and outcomes in the report, plus one verification verdict
   per acceptance criterion and entry point (`verified`, `failed`,
   `verified-unreachable` with the unmet prerequisite, or `skipped` with the
   reason).
6. Require a self-review for completeness, scope, edge cases, tests, and
   unnecessary complexity.
7. Require the report's **assumptions** and **could not verify** sections.
   An empty assumptions list on a non-trivial task usually means the worker
   didn't notice it was deciding — ask once.
8. If the worker cannot safely or correctly proceed, it reports `BLOCKED` or
   `NEEDS_CONTEXT` rather than guessing.

Implementers do not dispatch reviewers; review is the orchestrator's job.

## 5. Assumption check

When a report arrives, before dispatching review, read its assumptions and
could-not-verify items against the plan, wiki, ledger, and other tasks' briefs
and reports. You hold the cross-task picture the worker lacked.

- **Assumption conflicts with something you know** (another task's interface,
  a convention, a ruling): send it back as a fix round with the missing
  context. No review round is spent on work built on a wrong premise.
- **Assumption is fine:** note it in the ledger; if it reflects a gap in the
  brief, fix the template or downstream briefs so later workers don't need
  to guess.
- **Could-not-verify items, and `verified-unreachable` or `skipped`
  verdicts:** forward to the reviewer as named checks, or schedule them for
  final integration. An unreachable prerequisite you can supply (auth, seed
  data, a running dependency) goes back to the worker with it.

Keep this quick — it is a read against context you already have, not a review.

## 6. Task review

Dispatch a fresh, read-only reviewer with:

- The task brief and binding global constraints.
- The exact base/head range and a prepared diff or review package.
- The implementer's report, to be read **after** forming a view of the diff.
- Any could-not-verify items from the assumption check.

**Order matters.** The reviewer reads the brief and diff, forms its own
assessment, then reads the report. The report is an accurate account of what
the worker did and saw; its value is as a map of where judgment was exercised.
Reading it first anchors the reviewer to the same framing and the same blind
spots.

Review attention goes to:

- **Misjudgment:** the worker's listed decisions, assumptions, and deviations,
  judged against the spec and project conventions. Tests that pass but prove
  the wrong thing — e.g. a test that mocks the very condition it claims to
  demonstrate.
- **Oversight:** other call sites of changed interfaces, error and edge paths,
  cleanup of replaced code, and docs or config that reference changed behavior.
- **Spec fit:** missing, extra, or misunderstood requirements.
- **Verdict coverage:** every acceptance criterion and entry point has a
  verdict, and each `verified` one's proof actually shows its stated
  observable — for state changes, a second read-only view rather than a
  success message.

Don't re-derive work that is visibly correct, and don't rerun broad suites to
repeat reported results. Run a focused check when the diff gives a specific
reason to doubt that something covers what it's meant to. The reviewer does
not edit the workspace, change Git state, dispatch workers, or crawl unrelated
code; inspect unchanged code only to check a concrete named risk.

Findings:

- **Spec compliance:** missing, extra, or misunderstood requirements.
- **Strengths:** specific things done well.
- **Critical:** correctness, security, or blocking failures.
- **Important:** material requirement, reliability, or maintainability gaps.
- **Minor:** non-blocking improvements.
- **Cannot verify:** needs a separate integration check.
- **Verdict:** `APPROVED` or `NEEDS_FIXES`.

Each finding cites file and line, says why it matters, and suggests a fix when
useful. Calibrate severity; not every preference is a blocker. A defect the
brief itself mandated is labeled `plan-mandated`, and the orchestrator rules
on it against the binding spec.

## 7. Bounded fix loop

Critical or Important findings, or a confirmed real gap, start a fix loop.
Minor findings go to the ledger for final triage; they don't expand the task.

Maximum **five rounds per task**; each round is one fix dispatch plus one
scoped re-review.

- **Rounds 1–3:** resume the original implementer with the exact open
  findings (or start a fresh one with the brief, report, and findings if the
  harness can't resume). It has the most context on its own change.
- **Rounds 4–5:** fresh implementer, stronger model when available, with prior
  attempts included. Repeated failure usually means the original framing is
  the problem, and fresh context is what breaks it.
- Each fix report states what changed, with covering tests and outcomes.
- Re-review only the fix range and the open findings, checking for new
  breakage the fix introduced.
- Record every round and each finding's state in the ledger.

At round five, adjudicate what remains:

- Reviewer wrong or point contestable → park with the reason; surface it in
  the final report.
- Real issue, safely deferrable, nothing depends on it → park as deferred with
  the risk stated.
- Real issue blocking dependent work or exposing a plan defect → make the
  smallest justified ruling, record it, update downstream briefs.
- Stop and ask only when every path forward would be a guess or an
  authorization boundary is reached.

Don't silently discard findings, and don't patch implementation defects in the
coordinator's own context — send a scoped fix through the same review so the
coordinator stays free for cross-task judgment. (If the harness can't spawn
workers, this isn't possible; use the fallback in SKILL.md **Harness
capabilities**.)

## 8. Final whole-branch review

Task-level approval doesn't show tasks work together; oversight across task
boundaries only appears here.

1. Prepare a review package for the whole branch against its merge base: full
   diff and commit summary.
2. Dispatch one fresh reviewer on the strongest suitable model to evaluate the
   branch against the original goal, spec, global constraints, and task-level
   findings.
3. Point it at deferred minor findings, parked issues, and could-not-verify
   items in the ledger.
4. If findings remain, dispatch **one** fix worker with the full list, then one
   scoped re-review of that fix wave.
5. Adjudicate residual findings, record rulings, and report unresolved risks.
   No second fix wave.
6. Run the final integration gates on the complete tree: relevant tests, lint,
   typecheck, build, and domain-specific behavioral checks; repo-wide searches
   or migration round-trips where the change demands them. If the project has
   a verification skill, select features by matching the branch's changed
   paths against its Change selection table (`lifecycle.md` §2), drive them
   following its Launch, Doctor, and Cleanup, and record a verdict per entry
   point. This is where environment differences between isolated worktrees
   and the integrated tree surface. Keep command and result evidence.
7. Classify every verification-skill drive failure as the skill's Report
   section says: `environment` (fix, retry, and add a gotcha if the fix
   wasn't obvious), `map-drift` (the app works but the recipe is stale — log
   it to `features/DRIFT.md`; don't change expected results mid-run), or
   `product` (a real regression — a finding).
8. If `features/DRIFT.md` has entries, run scoped maintenance
   (`references/verification/maintain.md`, scoped mode) on those features
   before closing the run. It edits only the verify skill's directory on the
   work branch. Offer a full audit only on the triggers `lifecycle.md` §5
   lists.

## 9. Finish and clean up

Before removing the run workspace, collect every `Ruling:` from the ledger for
the final report, with reasoning and cost if wrong.

Transfer durable discoveries and verified decisions to the wiki — including
context gaps the assumption checks kept catching, and the verify layer's
status (created, extended, dead end with reason, features pruned). Then remove only this plan's
temporary workspace, preserving anything the project or user needs.
