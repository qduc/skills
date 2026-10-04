# Skills

Agent skills published from a single locally maintained source. `.skills-publisher` says this tree is generated from that private source: edit the source, not this export.

## Layout

Published skills are the directories directly under `skills/` that contain a `SKILL.md`. A skill may also keep `references/`, `scripts/`, `agents/`, `assets/`, or `evals/` next to that file. `skills/skill-creator/LICENSE.txt` is the license file shipped with that skill.

`skills/synced/` is a separate tracked snapshot under a bucket id. It is not the published set listed below.

`.gitignore` excludes Python bytecode (`__pycache__/`, `*.py[cod]`), `.DS_Store`, `runtime/`, and `.env` files.

## Use

There is no installer in this repository. Read `skills/<name>/SKILL.md`. Its frontmatter `name` and `description` say when the skill applies; the rest of the file is the procedure. Scripts, when a skill has them, are invoked from that skill's own instructions.

## Coordinator execution protocols

`skills/coordinator` coordinates bounded delegation. It owns outcome, scope, ownership, dependencies, authority, acceptance, and integration. See `skills/coordinator/SKILL.md` and `skills/coordinator/references/execution-protocols.md`.

Two scripts do different jobs:

- `skills/coordinator/scripts/coord_route.py` rotates worker pools (`pick`, including `--dry-run`). It does not resolve execution protocols.
- `skills/coordinator/scripts/coord_protocol.py` resolves a generic execution protocol to an installed skill, or falls back. It does not route pools, read or write task state, or accept results.

The protocol names are `bug-fix`, `architect`, `refactor`, `arena`, `swarm`, and `interrogate`. A protocol owns only the task-specific engineering method and local verification.

Resolve before dispatch. The catalog is supplied by the host. Do not assume a sibling install path.

```sh
python3 skills/coordinator/scripts/coord_protocol.py resolve --protocol <name> --catalog <installed-skill-dir>
```

Repeat `--catalog` to search more than one directory. If `COORDINATOR_PROTOCOL_CATALOG` is set, those path-separator-separated directories are added after the flags. `resolve` prints one JSON line.

An installed skill is compatible when its frontmatter `name` equals the protocol, or when `execution-protocol` / `execution-protocols` lists that protocol. Name matches are preferred over a declaration. Cursor pstack skills are compatible only when they are installed and either named as the protocol (`architect`, `arena`, and `interrogate` match by name) or they declare `execution-protocol`. Do not copy those skills into this package.

`protocol_selected` means the worker reads that skill as the method and local verification only (`workflow` is `execution_protocol`). `protocol_fallback` means use the coordinator's normal bounded-worker workflow (`workflow` is `bounded_worker`): `not_installed` when nothing in the catalog matches, `unknown_protocol` when the name is not one of the six. Both fallbacks exit 0. Missing protocols are not blockers. A catalog path that was supplied but is not a directory prints `{"error":"missing_catalog","catalog":"..."}` and exits 1.

Protocol output is worker evidence, not acceptance. Admit it before inspection:

```sh
python3 skills/coordinator/scripts/coord_protocol.py admit --protocol <name> --report <report>
```

`admit` prints one JSON line with `event` `worker_evidence`, `accepted` false, and a SHA-256 of the report. It does not accept the report, including when the report claims acceptance or exits 0. The same treatment applies without the helper. The coordinator still independently inspects the evidence. Acceptance stays section 5 of `skills/coordinator/SKILL.md`: `coord_claimcheck`, inspected evidence, and the coordinator's decision. `finished`, `verified`, `accepted`, and `integrated` stay distinct.

## Published skills

Descriptions are the `description` field from each `SKILL.md`.

- **adversarial-review** — Review a specific software artifact—a PR, diff, specification, design document, architecture document, RFC, or project plan—for concrete, evidence-backed defects and omissions. This is the general artifact-review skill. Use slop-audit for whole-repository health audits, deep-module-review for one module/API’s interface design, and proportionality-review when the sole question is whether a proposal or design is overbuilt or unnecessarily complex.
- **bug-retro** — Post-fix retrospective that turns a single bug fix into a durable improvement for the whole class of bug. Use this whenever a bug has been found, diagnosed, or fixed — when a failing test goes green, a hotfix lands, a regression is resolved, or the user says "fixed it", "that was the bug", "ok it works now", "why did this happen", "post-mortem", "root cause", or asks how to stop a bug recurring. Also run it after YOU fix any non-trivial bug, even if the user only asked for the fix — the fix is the floor, not the deliverable. Do NOT use for feature requests or pure style refactors with no defect involved.
- **coordinator** — Coordinate work through bounded delegation, dependency management, verification, and integration. Use when the user asks to orchestrate workers or subagents, or when substantial independent work benefits from supervised delegation.
- **deep-module-review** — Evaluate or improve the design of one software module or API, focusing on cohesion, information hiding, interface complexity, leakage, side effects, and caller burden. Use adversarial-review when reviewing a change to that module, slop-audit for repo-wide health audits, and proportionality-review only when the specific question is whether the design is overbuilt.
- **finding-triage** — Gate between a review and the fixes. It sets the must-fix bar, costs each proposed fix in added mechanism, and decides route, narrow, accept or reject per finding. Use when writing a reviewer brief, when review findings or PR comments arrive, before acting on them or routing them to an implementer, or when fix rounds keep producing new bugs.
- **herdr** — Use whenever the user mentions Herdr or asks to inspect, control, automate, or coordinate Herdr workspaces, tabs, panes, terminals, or agents. Covers safe CLI usage, workspace targeting, pane operations, agent lifecycle, and non-disruptive coordination.
- **invariant-reviewer** — Stress-test a software design or implementation for reachable failures and broken invariants. Use when challenging architectural assumptions or reviewing edge concerns while weighing the complexity of proposed fixes.
- **model-benchmark** — Benchmark AI models and coding harnesses on real-world engineering tasks from the term2 repository. Use when evaluating coding models, comparing agent harnesses (Codex, Pi, Term2, OpenCode), running controlled coding benchmarks, measuring solve rates, querying or updating the model benchmark database, grading candidate diffs with blind LLM judges, or verifying model capabilities against deterministic real-world tasks.
- **playwright-cli** — Automate browser interactions, test web pages and work with Playwright tests.
- **proportionality-review** — Assess a proposal or design only when the user specifically asks whether it is overbuilt, too complex, over-engineered, gold-plated, or more than they need. Use adversarial-review for general defect-finding in a specific artifact, deep-module-review for one module/API’s interface design, and slop-audit for whole-repository audits.
- **simplicity-architect** — Design systems around strong invariants and a small complexity budget. Use when proposing a software design that eliminates edge cases, or answering reviewer concerns without accumulating defensive machinery.
- **skill-creator** — Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
- **slop-audit** — Audit an entire repository for accumulated design, correctness, testing, duplication, security, dependency, and overbuilding problems, using independent lenses, evidence-based synthesis, and a prioritized repair plan. Use adversarial-review for a single PR, diff, plan, specification, or design document, deep-module-review for one module/API, and proportionality-review only for a specifically overbuilt proposal or design.
- **term2** — Run, configure, and orchestrate term2 instances for interactive coding sessions or non-interactive CLI tasks. Use when launching term2 in terminal multiplexers (herdr, tmux), running non-interactive batch tasks via term2, configuring providers (OpenRouter, Codex, OpenAI), or querying term2 CLI flags and settings.
- **workflow-evolution** — Improve an agent workflow by evolving its skills through evidence-backed experiments. Use when a workflow has repeated runs, measurable outcomes, or recurring failures and you want the skill itself to get better over time without changing the harness.
