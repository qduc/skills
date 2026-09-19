---
name: slop-audit
description: Audit an entire repository for accumulated design, correctness, testing, duplication, security, dependency, and overbuilding problems, using independent lenses, evidence-based synthesis, and a prioritized repair plan. Use adversarial-review for a single PR, diff, plan, specification, or design document, deep-module-review for one module/API, and proportionality-review only for a specifically overbuilt proposal or design.
---

# Slop Audit

Multi-lens independent codebase review with collective synthesis. Motto: **review independently, synthesize collectively.**

**Portability:** this skill is plain markdown with no platform-specific tooling. It works as a Claude skill, or drop the folder into any coding agent's instruction mechanism — reference it from `AGENTS.md`, add it as a Cursor rule / Codex instruction, or paste sections directly as prompts. Tool commands mentioned (jscpd, knip, git, etc.) are ordinary CLI tools; use whatever equivalents the environment has.

The core insight: modern AI-generated code problems are not bad syntax — they are plausible-but-wrong *decisions* that survive file-level review. This skill audits at the decision layer using independent single-lens passes (so findings don't anchor each other) plus a verifying synthesis pass (so consensus doesn't substitute for evidence).

## Workflow overview

1. **Setup** — gather context, invariants, and pick lenses
2. **Independent lens passes** — each pass sees only: the codebase, its lens instructions, the invariants doc, and the shared reporting format. Never show one lens another lens's findings.
3. **Null-hypothesis pass** — one pass argues the codebase is fine, to counterweight critic bias
4. **Synthesis pass** — merge, *re-verify with file/line evidence*, resolve contradictions, group symptoms under root causes
5. **Human checkpoint** — user sanity-checks the root-cause grouping before any repair plan
6. **Repair plan** — prioritized, incremental, small reviewed chunks

## Step 1: Setup

Before any review pass:

1. **Locate the codebase.** Ask for path/repo if not provided. Get a quick inventory: `git log --stat` summary, language(s), size, most-changed files (`git log --format= --name-only | sort | uniq -c | sort -rn | head -20`).
2. **Collect invariants.** Ask the user for unwritten rules and tribal knowledge (e.g. "orders are immutable after payment", "service A must never call service B", performance constraints, deliberate weirdness). Write these into `invariants.md`. This doc is fed into EVERY lens. If the user has none, note that explicitly — absence of documented invariants is itself a finding.
3. **Pick lenses.** Default set (adapt to the codebase):
   - `architecture` — intent reconstruction, abstraction boundaries, decision-debt
   - `duplication` — redundant logic, parallel implementations, reinvented wheels
   - `correctness` — bugs, invariant violations, edge cases, self-consistent-but-wrong code+tests
   - `tests` — assertion strength, mock-testing-mocks, weakened assertions in git history
   - `security` — input handling, secrets, authz gaps, unsafe defaults
   - `dependencies` — unused deps, duplicated capability, risky/abandoned packages
   - `overbuild` — speculative config, single-use abstractions, dead-but-referenced code, "what breaks if deleted?"
   - `null-hypothesis` — REQUIRED. Argues the codebase is fine and concerns are overblown.
   For small codebases or limited budget, minimum viable set: architecture, correctness, tests, null-hypothesis.
4. **Agree scope with the user**: whole repo vs. hot paths only, how many lenses, and whether cross-model review is available (if the environment supports calling a different model per lens, use it; otherwise fresh-context same-model is acceptable).

## Step 2: Independent lens passes

**Independence is the non-negotiable rule.** Each lens pass must start from a fresh context containing ONLY:
- the codebase (or the agreed scope of it)
- `invariants.md`
- the lens instruction file from `references/lenses.md` (the one section for its lens)
- the reporting format from `references/report-format.md`

Never include: other lenses' findings, the conversation that produced the code, or prior audit results.

**How to run passes (agent-agnostic — adapt to whatever capabilities the current agent has):**
- **If the agent supports isolated parallel workers** (subagents, task/agent spawning, parallel tool sessions — e.g. Claude Code subagents, Codex/Cursor background agents, OpenHands delegates): spawn one worker per lens, in parallel where possible. Each worker's context contains exactly the four inputs above, nothing else, and writes its report to `audit/reports/<lens>.md`.
- **If separate fresh sessions can be started manually** (any chat-based agent): give the user a ready-to-paste prompt per lens (lens section + invariants + report format + codebase pointer), have them run each in a brand-new session, and collect the reports. This achieves true isolation without any special agent features.
- **If neither is available** (single-session agent): run passes sequentially in one session, simulating independence: before each lens, re-read only that lens's instructions and deliberately do not consult earlier reports while reviewing (write each report to file, then move on). Acknowledge to the user this is weaker than true isolation.
- **Cross-model option:** if the user has access to multiple AI tools, running different lenses (or a duplicate synthesis) on a different model than the one that wrote the code breaks shared blind spots. Offer this whenever the user mentions using multiple agents.

**Calibrate paranoia per lens** (details in `references/lenses.md`):
- correctness, security, tests → adversarial ("assume defects exist; find them")
- architecture, overbuild → interrogative ("reconstruct intent; flag where you can't")
- duplication, dependencies → mechanical (tool-assisted where possible: `jscpd`, `knip`, `vulture`, `pip-audit`, `npm audit`, linters at max strictness)
- null-hypothesis → defensive ("argue it's fine; rebut the likely criticisms")

Every finding in every report must be **specific and falsifiable**: file/line references, a concrete claim, and a suggested verification ("function X is unused because no import of X exists outside its own test"). No vibes ("consider improving separation of concerns" is banned).

## Step 3: Synthesis pass

Run AFTER all lens reports exist. Inputs: all reports + invariants.md + codebase access. Its jobs, in order:

1. **Deduplicate** overlapping findings across lenses.
2. **Re-verify.** Any finding that will survive into the repair plan must be re-checked against the actual code with cited file/line evidence. Agreement between lenses is NOT evidence — two lenses can hallucinate the same plausible finding. Mark each finding `verified`, `refuted`, or `unverifiable`.
3. **Resolve contradictions** (e.g., duplication says "merge these"; correctness relied on both) by reading the code, not by voting.
4. **Weigh the null-hypothesis rebuttals.** Findings the null pass convincingly rebutted get downgraded or dropped; findings that survived its best defense get upgraded — they are load-bearing.
5. **Group symptoms under root causes** — but label the causal story explicitly as hypothesis.
6. Write `audit/synthesis.md` per the format in `references/report-format.md`.

## Step 4: Human checkpoint (do not skip)

Present the synthesis to the user BEFORE writing the repair plan. Specifically ask them to sanity-check:
- the root-cause groupings (the most hallucination-prone part — a confident causal narrative can be wrong even when every symptom is real)
- any finding marked `unverifiable`
- anything that contradicts their tribal knowledge

Incorporate their corrections. Only then proceed.

## Step 5: Repair plan

Write `audit/repair-plan.md`: findings ordered by (severity × confidence × blast-radius of fix), grouped by root cause, each with a small incremental fix scoped to be individually reviewable. Rules:
- No big-bang rewrites. Hot modules first (most-changed in git history).
- Every fix that touches tests must state whether assertions are being strengthened or changed, and why.
- Fixes are executed in small chunks with human review between chunks — the audit exists because the human left the loop; the repair must not repeat that.

## Optional: stability calibration

If the user wants to trust the pipeline on a large/critical repo, offer to run the full audit twice and diff the two synthesis reports. High divergence = the report is mostly sampling noise; treat individual findings skeptically and rely only on findings that appear in both runs.

## Reference files

- `references/lenses.md` — per-lens instructions and prompts (read only the section for the lens being run; when using workers or fresh sessions, paste the relevant section into that worker/session's context)
- `references/report-format.md` — the shared reporting format every pass must follow, plus synthesis and repair-plan formats
