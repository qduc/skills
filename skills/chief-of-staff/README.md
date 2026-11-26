# chief-of-staff

A skill for acting as a long-running chief of staff: owning delegated work,
briefing and supervising fresh-context workers, verifying their output, and
keeping a project wiki and run ledger for continuity.

## Layout

- `SKILL.md` — core loop, loaded whenever the skill triggers.
- `references/engineering-workflow.md` — the full plan → preflight → implement
  → assumption check → review → fix → final review workflow.
- `references/wiki.md` — wiki structure and maintenance.
- `references/verification/` — the verify layer: `lifecycle.md` (find,
  auto-create, select by changed paths, strengthen with use), `create.md`
  (scoped, extend, or full creation), `maintain.md` (scoped upkeep that runs
  automatically on drift, and a periodic full audit with pruning), plus an
  example feature map with a change-selection table, smoke steps, a
  regression step, and a drift log. Adapted from pstack
  under MIT; see `references/verification/LICENSE-pstack`.
- `assets/brief.yaml`, `assets/progress.md` — brief and ledger templates.

## Harness support

Plain Markdown with `name`/`description` frontmatter, and no harness-specific
tool names. SKILL.md's **Harness capabilities** table lists what the skill
needs (fresh workers, read-only workers, isolation, resume, model choice, and
so on) along with a fallback for each, so it degrades cleanly in harnesses
that lack a capability.

## Verification model

Workers are treated as accurate but bounded: they fail through missing
context, misjudgment, or oversight, not fabrication. Checks are designed
around those three modes — an orchestrator assumption check at handback, a
fresh reviewer who reads the diff before the worker's rationale, and
whole-branch integration gates — rather than re-confirming reported work.

## Design lineage

Ideas drawn from these public projects (references, not dependencies):

- [Matt Pocock — Chief of Staff](https://github.com/mattpocock/skills/tree/main/skills/in-progress/chief-of-staff): user-facing delegation, a dated interlinked wiki, ingest/query/lint, learning from friction.
- [obra — Superpowers: Subagent-Driven Development](https://github.com/obra/superpowers/tree/main/skills/subagent-driven-development): plan-specific ledgers, fresh implementers, independent task reviews, bounded fix loops, final whole-branch review.
- [Lauren Tan — pstack: create/maintain-verification-skill](https://github.com/cursor/plugins/tree/main/harness/pstack/claude-code/skills) (MIT): project-local verification skills, feature maps from the user's point of view, proof standards, drift vs regression triage. Adapted copies live in `references/verification/`.
- [obra — Superpowers: Dispatching Parallel Agents](https://github.com/obra/superpowers/tree/main/skills/dispatching-parallel-agents): independence checks, focused briefs, parallel dispatch only when work doesn't interfere.
