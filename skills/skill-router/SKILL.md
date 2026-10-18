---
name: skill-router
description: Use when the user asks which skill to use or whether a skill exists for something.
---

# Skill Router

Decide which skill to use for the current user request.

## Exits

Every route ends at exactly one of these. There is no other ending and no return to the top.

| Exit | Then |
| --- | --- |
| `none` | Do the request directly. Say nothing about routing. |
| one skill | Load it and hand over. It owns the request from here. |
| chain `A → B` | Load `A`; load `B` when `A` finishes. Never more than two. |

Never route to this skill, never load two skills to compare them, and never ask the user to choose a skill.

## Route

Go top to bottom. Take the first row that matches.

### 0. Aftermath (checked first: "fixed it" and "why did that happen" read like conversation)

| Something already happened | Exit |
| --- | --- |
| A bug was found, diagnosed, or fixed, or an agent had to be corrected | `bug-retro` |
| A skill keeps underperforming across repeated, measurable runs | `workflow-evolution` |
| A recurring kind of work has no method | `skill-creator` |

### 1. Fast exit

| The request is... | Exit |
| --- | --- |
| A question, explanation, or conversation answerable without looking into the user's own code, systems, or artifacts ("which module writes X", "could this design fail", "how should we structure X" all need a look: go on) | `none` |
| One small, obvious, reversible edit | `none` |
| A follow-up inside a task a skill already owns | `none` (the owning skill continues) |

### 2. Owner (several steps of work)

| Situation | Exit | Not this |
| --- | --- | --- |
| What to build is unclear and the human must react to examples first | `risk-first-build` → `agentic-loop` | `agentic-loop` assumes the goal is clear |
| The user wants it built, the goal is clear, no design exists yet, and its structure is costly to redo (new subsystem, data model, persistent format, public API) | `simplicity-architect` → `agentic-loop` | going straight to `agentic-loop` builds on the first design that comes to mind |
| The goal is clear and needs several steps (find out, change, verify) carried by one agent to verified done, in any domain | `agentic-loop` | `coordinator` adds overhead one agent doesn't need; `implementation` for one change that is already decided |
| Substantial independent pieces should run in parallel | `coordinator` (first run on a machine: `coordinator-setup` → `coordinator`) | `agentic-loop` runs one agent |

### 3. One-step gap

| The step needs to... | Exit | Not this |
| --- | --- | --- |
| Explain why something fails | `debugging` | `investigation` gathers facts without testing a cause |
| Find facts in the code, config, or running system | `investigation` | `research` looks outward |
| Compare and synthesize outside sources or docs | `research` | `investigation` looks inward |
| Decide how to structure a change that has no design yet, or answer a reviewer's concerns on your own proposal | `simplicity-architect` | Section 4 when a design already exists and is being judged (overbuilt, defects, interface) |
| Make a code change that is already decided | `implementation` | `simplicity-architect` when the design is still open |
| Prove a behavior with automated checks | `testing` | `browser-qa` covers what a user sees |
| See what a user actually sees and does in a browser | `browser-qa` (it drives `playwright-cli`) | `testing` for logic below the UI |
| Measure or fix performance | `profiling` | `debugging` when the output is wrong, not slow |

### 4. Judging

| What is being judged | Exit |
| --- | --- |
| A code diff for correctness and security | `code-review` |
| One module's interface and what it hides | `deep-module-review` |
| A whole repository's accumulated problems | `slop-audit` |
| Only whether something is overbuilt, overkill, or more than needed | `proportionality-review` |
| Whether a design has reachable failures | `invariant-reviewer` |
| Review findings arrived and you must decide which to fix | `finding-triage` |
| Any other defect hunt in one artifact: a PR, spec, design, or plan (the catch-all, so it sits last) | `adversarial-review` |

### 5. Tools

| Need | Exit |
| --- | --- |
| Run a term2 coding session | `term2` |
| Inspect or drive Herdr panes and agents | `herdr` |
| Benchmark models or harnesses | `model-benchmark` |

### 6. Nothing matched

Substantial work exits to `agentic-loop`: it is domain-generic and, when no skill supplies a method, resolves one or invokes `skill-creator` itself. Otherwise exit `none`.

## After the exit

The router runs once per user request. An owner (`agentic-loop`, `coordinator`, `risk-first-build`) picks its own primitives as it works; do not come back here mid-task. Route again only when the user starts a different request.

For any exit except `none`, put one line before starting work:

```
Route: <exit> — <reason>   (Not: <neighbor> — <why>, only when a neighbor was close)
```

## Making it run first

The description asks to be loaded first, but a description alone cannot guarantee it. Add one mechanical trigger in the harness:

- **Instruction file** (CLAUDE.md, AGENTS.md, or the harness equivalent): `Before acting on any new request, load the skill-router skill and follow it to an exit.`
- **Claude Code hook** (stronger, injected on every prompt), in `settings.json`:

  ```json
  {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command",
    "command": "echo 'Load the skill-router skill first and follow it to an exit.'"}]}]}}
  ```

## Keeping this file honest

`scripts/check_router.py` fails when a skill directory is missing from this file, this file names a skill that doesn't exist, or `evals/evals.json` expects an exit that isn't a real skill, or a route row's exit has no eval. Run it after adding, renaming, or removing a skill.

That check cannot see shadowing: a general row placed early quietly answers cases meant for a narrower row below it. `scripts/run_router_evals.py` catches that by having a model route every eval prompt with only this file as instructions, then reporting each case whose exit differs from `expected_exit`. Run it with `--runs 3` after reordering rows or rewording a row's trigger; it costs one model call per case per run. A case that misses in some runs is either shadowed (fix the rows) or on a genuinely fuzzy boundary (give the eval an `also_ok` alternative). Put a narrower row above the general one it overlaps; a catch-all sits last.
