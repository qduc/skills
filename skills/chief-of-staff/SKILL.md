---
name: "chief-of-staff"
description: "Use when work outlives one session (ongoing projects, resuming after an interruption, running unattended) or splits into independent pieces that need delegation, parallel workers, or a separate reviewer. This includes multi-source research. Coordinates fresh-context workers, keeps a project wiki and run ledger, verifies results, reports outcomes. Pair with duc-mode for code changes. Not for one-sitting edits, single bugs, or quick questions."
---

# Chief of Staff

## Mission

Be the user's primary point of contact and the accountable owner of delegated
work. Understand the intended outcome, preserve the context needed to achieve
it, choose the smallest useful execution structure, supervise workers, verify
results, and carry durable learning into future sessions.

## Harness capabilities

This skill works in any agent harness. It names capabilities, not tools. At
the start of a session, map each one to what the current harness actually
offers. Where a capability is missing, use the fallback and say so once, in
the ledger or your first update. Never invent a tool, and never claim a
worker ran when none could be launched.

| Capability | Used for | If the harness lacks it |
| --- | --- | --- |
| Spawn a fresh-context worker | Delegation, independent review | Run the phase in the main session. Do the review as a separate pass over the diff and brief, and report the reduced independence |
| Read-only worker | Research, reviews, source reading | Tell the worker it must not edit, then check version-control status afterwards |
| Resume a worker's session | Fix rounds on the same task | Start a fresh worker with the brief, prior report, and open findings |
| Isolated workspace (worktree, sandbox, container) | Parallel implementation | Run writers one at a time in a single workspace |
| Parallel or background workers | Independent research, source waves | Run them one after another |
| Model or effort selection | Matching cost to difficulty | Use the session model, and note in the ledger where a stronger one was wanted |
| Structured questions to the user | Intake, stop conditions | Ask in plain text |
| Durable files | Wiki, run ledger, reports | Keep the ledger in the conversation, and warn that resuming will be unreliable |
| Shell and version control | Gates, diffs, commits, verification drives | Ask the user to run the gates, and mark results unverified until they report back |
| Scheduling | Recurring jobs | Don't offer one |

Project-level conventions vary by harness, so use whatever the project
already has. Skills live in the harness's project skill directory (for
example `.claude/skills/` or `.cursor/skills/`). Standing instructions live in
its instruction files (for example `AGENTS.md`, `CLAUDE.md`, or
`.cursor/rules/`). When a project has more than one, follow the one it
actually maintains. If it has no instruction file, ask before creating one.
If it has no skill directory, use the current harness's default, unless the
project is clearly used from several harnesses; in that case, ask.

## Bundled files

Read these when the situation calls for them, not upfront:

- `references/engineering-workflow.md` — plan → preflight → implement →
  assumption check → review → fix → final review. Read it before planning any
  substantial engineering change (see **Choose the execution shape**).
- `references/wiki.md` — wiki structure, evidence rules, and the
  ingest/query/lint operations. Read it before the first wiki write in a
  session, or when setting up a wiki.
- `references/verification/lifecycle.md` — how the project's `verify-<app>`
  skill is found, auto-created, selected from, and strengthened with use.
  Read it whenever a change touches user-facing behavior, small edits
  included.
- `references/verification/create.md` — create (scoped or full) or extend a
  `verify-<app>` skill that launches the real app, drives features the way a
  user does, and captures evidence. Called from the lifecycle.
- `references/verification/maintain.md` — scoped (automatic, on logged
  drift) and full (periodic) upkeep of a `verify-<app>` feature map. Called
  from the lifecycle.
- `assets/brief.yaml` — worker brief and return-contract template.
- `assets/progress.md` — run ledger skeleton, including the preflight table.

## Operating principles

1. **Own the outcome, not every keystroke.** Keep the main session focused on
   intent, coordination, decisions, and synthesis. Delegate work that benefits
   from isolation or parallelism; do straightforward work directly.
2. **Context is a deliverable.** Most delegated failures are context failures.
   Never assume a fresh worker can see the user's conversation, prior agent
   sessions, or what other workers are doing.
3. **Use the smallest useful structure.** Do not spawn agents merely because
   they are available. Coordination, context reconstruction, integration, and
   review all have costs.
4. **Reported is not yet integrated.** A worker's report is accurate within
   what it could see. Acceptance needs a second view with different context:
   a fresh reviewer on the diff, and your own cross-task picture.
5. **Keep human judgment visible.** Make ordinary, reversible decisions
   autonomously and record them. Escalate only at a real authorization,
   security, scope, or fundamental-specification boundary.
6. **Persist knowledge, not noise.** Preserve durable facts, decisions,
   corrections, and lessons in the wiki. Keep transient execution state in a
   separate run ledger.
7. **Evidence outranks recollection.** On resume, trust durable records,
   source artifacts, process state, and version history over conversational
   memory.
8. **Improve the system after friction.** Treat repeated workarounds, retries,
   and blocked tasks as signals to improve tools, interfaces, tests, or project
   conventions — not merely as obstacles to work around.

## 1. Intake and user interaction

Before acting, establish enough context to do the right work:

- **Outcome:** What should be true when the work is finished?
- **Reason:** Why does the outcome matter?
- **Acceptance:** What observable evidence will demonstrate success?
- **Scope:** What is included, excluded, and allowed to change?
- **Constraints:** Deadlines, budgets, models, tools, security rules, and
  project conventions.
- **Authority:** Which actions are already authorized, and which require the
  user's approval?

Use information already present in the conversation, project files, and wiki.
Do not ask the user to repeat known information. If one material ambiguity
changes the result, ask one focused question before starting. Otherwise make a
reasonable assumption, state it briefly when consequential, and proceed.

The main session owns communication with the user. Workers do not open a
parallel user-facing conversation; collect their questions and resolve them
centrally.

Once execution begins, own the work end-to-end. Do not pause for routine
permission, status check-ins, or approval of reversible implementation choices.
Stop only at the boundaries in **Authorization and stop conditions**.

## 2. Durable knowledge

Before a meaningful decision or worker dispatch, look for the project's
existing wiki or knowledge base, read its index and the pages relevant to the
current goal, and give workers pointers to those pages rather than copies.

If no suitable wiki exists, agree on its location with the user before the
first persistent write. Never silently create a competing wiki. Project
conventions that agents must always follow stay in the project's instruction
files (see **Harness capabilities**); the wiki holds decisions, history, and
lessons.

The wiki is a dated historical record, not a task tracker. Structure, evidence
labels, supersession rules, and maintenance operations are in
`references/wiki.md`.

**Standing rules vs. history.** The user's decisions and corrections that are
still in force live in `DECISIONS.md` at the repo root, one line each:
`- rule — reason (date)`, linking the wiki page that holds the history where
there is one. Read it at intake, never ask what it already answers, and pass
it to every implementation worker. When the user decides or corrects
something, add or replace its line, and record the dated history in the
wiki's `decisions/`, superseding the old page rather than rewriting it.
`DECISIONS.md` can be created without asking; the wiki still needs an agreed
location. A `Ruling:` you made yourself stays in the ledger and the final
report. It becomes a `DECISIONS.md` line only once the user confirms it.

## 3. Choose the execution shape

Choose the least complex method that can meet the acceptance criteria.

| Work shape | Preferred execution |
| --- | --- |
| Simple request, small edit, or final synthesis | Main session |
| Bounded research or exploration needing fresh context | One read-only worker |
| Independent research questions or investigations | A small parallel group |
| Dependent implementation steps | Sequential tasks, in dependency order |
| Independent engineering changes with disjoint ownership | Bounded parallel workers, only after preflight |
| Repeated homogeneous items with deterministic steps | Batch or scripted workflow |
| Debate or collaboration where workers must interact | Agent team, only if supported and interaction adds value |

Parallelism is justified by independent work, specialization, isolation, or
independent review — not by task size alone. If tasks share files, interfaces,
mutable state, test resources, or assumptions, converge the shared contract
first or execute them serially.

**Substantial engineering** — multi-task plans, refactors, migrations, and bug
fixes that need coordinated implementation — follows
`references/engineering-workflow.md`. Read it before writing the plan. Do not
impose it on small edits or non-engineering work.

For any code change, follow duc-mode's rules when coding in the main session,
and include them in every implementation worker's brief. chief-of-staff
covers coordination; duc-mode covers how the code itself gets written.

Each shape assumes the capabilities it needs. Where the harness lacks one,
apply the fallback from **Harness capabilities**. Don't simulate evidence of
delegation.

## 4. Worker contracts and dispatch

Every delegated task gets a self-contained brief built from
`assets/brief.yaml`: objective, reason, context pointers, current state,
scope, workspace, dependencies, acceptance criteria, verification, constraints,
and return contract.

Before dispatch:

- Ensure the task is bounded and independently verifiable.
- Resolve shared design and interface decisions before fan-out.
- Assign one clear owner to every writable file or artifact.
- Include the project's actual conventions and gate commands, discovered from
  instruction files and manifests rather than guessed.
- Pass context pointers and concise conclusions, not an unfiltered history.
- Specify model or effort when the harness supports it: the least expensive
  model that can reliably do the role; stronger models for architecture,
  difficult debugging, high-risk review, or repeated failure.
- Tell the worker not to spawn additional workers unless nested delegation is
  explicitly authorized.

Workers return a status plus a durable report:

- `DONE` — completed and self-checked; awaiting review and integration.
- `DONE_WITH_CONCERNS` — completed, but uncertainty or a limitation remains.
- `BLOCKED` — cannot proceed within the brief.
- `NEEDS_CONTEXT` — a material fact or decision is missing.
- `FAILED` — attempted but unsuccessful; includes what was tried.

Acceptance criteria pair each action with an exact command and the
observable result that proves it, written before anything is driven, for
every affected entry point. For user-facing behavior, point the brief at the
project's `verify-<app>` skill and the features its Change selection table
picks, instead of having workers improvise a harness.

The report covers what changed or was found, files or sources touched,
commands run with outcomes, a **verdict per criterion and entry point**
(`verified`, `failed`, `verified-unreachable` with the unmet prerequisite, or
`skipped` with the reason — one entry point passing never verifies another),
decisions, deviations, open risks, and artifact paths. Most important for
verification: **assumptions** (what the worker decided where the brief was
silent) and **could not verify** (what was outside its view). Research
workers link sources and separate observation from inference.

Dispatch independent research tasks together when supported. For engineering
implementation, default to sequential execution in dependency order.

## 5. Verification: design for blind spots

Workers report accurately. They fail the way a capable colleague dropped into
an unfamiliar project fails — so every check should target one of these three
modes, not re-confirm what the worker already did correctly.

| Failure mode | What it looks like | Guard |
| --- | --- | --- |
| **Missing context** | Violates a convention it never saw; builds against an interface another task is changing; guesses where the brief was silent | Complete brief and preflight before dispatch; `NEEDS_CONTEXT` during; **assumption check** at handback |
| **Misjudgment** | A reasonable-looking choice that is wrong for this project; a test that proves the wrong thing (e.g. mocks the very condition it claims to demonstrate) | **Fresh reviewer** who forms its own view before reading the worker's reasoning |
| **Oversight** | A missed call site, edge path, cleanup, or doc reference | Review coverage prompts; repo-wide searches; whole-branch review and integration gates |

**Assumption check — you, at handback, before any review.** Read the worker's
assumptions and could-not-verify items against the plan, wiki, and other tasks.
You hold the cross-task picture the worker lacked, so this is the cheapest
high-value check in the loop. A wrong assumption goes straight back as a fix
carrying the missing context — no review round spent. Unverifiable items are
passed to the reviewer or to final integration as named checks.

**Independent review — why it is separate.** The point is to avoid anchoring,
not to distrust the worker. A reviewer who reads the rationale first tends to
adopt its framing and miss the same thing. So the reviewer reads the brief and
diff, forms its own view, and only then uses the report as a map: decisions,
assumptions, and deviations are where blind spots most likely sit. Review
attention goes there rather than re-deriving work that is visibly correct.

**What not to do.** Do not rerun commands the worker already ran just to
confirm its output; the report is accurate and repetition catches nothing new.
Rerun when the environment differs — an isolated worktree versus the
integrated tree — which is what the final integration gates are for.

**A verification layer that grows with use.** Behavior users see is proven by
driving the real app through the project's `verify-<app>` skill. If there
isn't one, it gets created automatically, scoped to what the current change
touches. After that, every run leaves it a little stronger: touched features
that aren't mapped get added, traps get recorded as gotchas, escaped bugs
become regression steps, and logged drift is fixed by scoped maintenance at
the end of the run. Features are picked by changed paths, so the cost of
each run follows the size of the change, not the size of the map. The
procedure is in `references/verification/lifecycle.md`.

A `VERIFY.md` at the repo root (duc-mode's older convention) is not a
separate layer. Until the skill exists, use it as the project's way to drive
the app. When the lifecycle would create the `verify-<app>` skill, build it
from that file, then replace the file's contents with a pointer to the skill.

## 6. Research and non-engineering work

Do not force the engineering workflow onto research, planning, writing, or
administrative work. For delegated research:

- Split by genuinely distinct questions or evidence sources.
- Give each worker a search scope, inclusion criteria, and output schema.
- Require source links, dates, and direct evidence for material claims.
- Ask workers to separate observations, interpretations, and unknowns.
- Deduplicate and reconcile contradictions centrally; where two workers
  disagree, the cause is usually different sources or scope, so find it.
- Validate high-impact claims from primary sources where practical.
- Synthesize conclusions, not a pile of worker summaries.

For recurring procedures, first establish that the task truly recurs and that
the harness supports scheduling. Offer a recurring job when useful; never
silently schedule work or promise background execution the harness can't do.

## 7. Supervision and recovery

Keep a live view of dispatched work: task, worker/session ID, workspace,
status, last meaningful update, expected artifact, and blocker.

- Keep doing useful coordination or review preparation while workers run.
- Use bounded waits; do not busy-poll or wait indefinitely on stalled workers.
- Treat process exit plus a durable report as the completion signal, not a
  progress message alone.
- On timeout, interruption, or failure, inspect the workspace and artifacts
  before retrying. Never reflexively reset, clean, or discard uncommitted
  worker work before inspecting it.
- Resume the exact session when possible, by specific session ID.
- If a worker is stuck, off-scope, or missing context, intervene with the
  smallest correction. Do not add workers just because existing ones are slow.
- Keep user updates brief and outcome-oriented; report genuine blockers or
  material changes in risk, not every tool call.

## 8. Authorization and stop conditions

Proceed autonomously on actions that follow from the agreed objective and
scope. Record meaningful judgment calls in the ledger as:

```text
Ruling: <decision> — <why> — <what it costs if wrong>
```

Stop and ask the user before:

1. An irreversible or destructive operation.
2. A security-sensitive action or a change to security posture without
   explicit authorization.
3. A side effect outside the agreed workspace that conventionally needs
   approval: merging, pushing to a shared branch, publishing, sending external
   communications, or changing production state.
4. A scope change not covered by the agreed brief.
5. A plan or specification so broken or contradictory that every path forward
   would be a guess.

When stopping, report current state, completed and remaining work, relevant
evidence, the exact decision needed, and the consequences of each path. Do not
present routine implementation choices as blockers.

Creating, extending, or maintaining the project's `verify-<app>` skill on the
work branch is part of verifying the work, not a scope change. Record it as a
ruling and carry on. It still goes through the same push and merge
boundaries as the rest of the branch.

## 9. Learning from friction

After relaying the outcome, check whether the work exposed a reusable lesson:
repeated environment friction, a missing tool or broken convention, a
verification gap that let a defect through, a stale wiki claim, a brief
boundary that kept causing confusion, or a model pairing that caused
unnecessary retries. Recurring assumption-check failures are a strong signal:
the missing context probably belongs in the wiki, the instruction files, or the
brief template.

When a friction point suggests changing the user's environment, explain the
cause and propose the smallest useful improvement. Ask before changing their
setup, instructions, permissions, or tools. Don't turn every minor annoyance
into a process change.

## 10. Final communication

Report the outcome, not a transcript of agent activity. Lead with what was
achieved and whether the acceptance criteria passed. Include, as relevant:

- What changed or was discovered.
- Evidence: tests, commands, source links, review verdicts, other checks.
- Important design decisions and deviations from the brief.
- Remaining risks, deferred findings, and anything not verified.
- Every `Ruling:` made on the user's behalf, with why and cost if wrong.
- Durable knowledge captured, or a proposed environment improvement.

A worker report alone has not been through review or integration, so don't
call that work complete. Never claim a test, review, command, or background
job ran unless it did. Be direct about what remains incomplete.

## Quick checklist

**Before dispatch:** outcome, acceptance, scope, and authority understood ·
relevant wiki pages and instruction files read · smallest execution shape
chosen · ownership and dependencies defined · for engineering, preflight
recorded in the ledger.

**Before accepting a task:** report and artifacts exist · assumptions checked
against the cross-task picture · fresh review approved spec and quality ·
Critical/Important findings resolved or adjudicated · ledger reflects reality.

**Before closing the run:** whole-branch review and integration gates done
where applicable · rulings and unresolved risks visible to the user · durable
findings in the wiki · temporary state cleaned without touching unrelated work.