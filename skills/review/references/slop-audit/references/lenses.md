# Lens Instructions

Each section below is a complete, self-contained instruction set for one review pass. When running a pass, use ONLY that pass's section (plus invariants.md and report-format.md). Do not mix lenses in one pass.

Every lens shares these ground rules:
- You see only the codebase, the invariants doc, these instructions, and the reporting format.
- Every finding must be falsifiable: file/line refs, a concrete claim, a way to verify it.
- If you cannot reconstruct why something exists, that IS a finding (category: decision-debt), not a failure.
- Do not soften. Do not pad with praise. Do not invent findings to seem thorough — an empty section is a valid result.

---

## architecture (interrogative)

Role: reconstruct the intent behind the system's structure and flag where intent cannot be reconstructed or is globally wrong despite being locally reasonable.

Tasks:
1. Map the module/layer structure and the top 2–3 user-facing flows end-to-end. For each flow, list every boundary crossed and every data reshape. Flag layers a request passes through that add no decision, transformation, or isolation.
2. For each major abstraction (interfaces, base classes, service boundaries, event buses): state the problem it appears to solve. If no problem is identifiable, flag as decision-debt.
3. Check placement of boundaries against the invariants doc: is any abstraction boundary positioned so that likely next changes must cut across it?
4. Flag "homogenized structure": modules that all share identical shape with no domain concept modeled sharply anywhere. Uniform blandness = nobody decided anything.
5. Check caching, queuing, and consistency choices against stated traffic/scale assumptions in invariants.md; if none stated, flag the assumption gap.

Do NOT report style issues, naming, or duplication — other lenses own those.

---

## duplication (mechanical)

Role: find redundant logic, parallel implementations, and reinvented wheels.

Tasks:
1. Run a duplication detector if available (`jscpd` for JS/TS, `pylint` duplicate-code for Python, or language equivalent). Report clusters with paths and line counts.
2. Manually scan for semantic duplication tools miss: multiple date/currency/string formatters, multiple HTTP client wrappers, parallel validation logic, similar-but-diverged copies of the same function.
3. Find hand-rolled implementations of things an installed dependency already provides (retry loops, deep clone, debounce, date parsing, schema validation). Cross-check the dependency manifest.
4. For each duplication cluster, note whether the copies have diverged (behavioral drift risk) or are identical (pure waste).

Do NOT recommend merges — synthesis decides that after checking correctness implications. Just report.

---

## correctness (adversarial)

Role: assume bugs exist. Find them. Pay special attention to self-consistent wrongness: code, tests, and comments that all agree with each other and are all wrong.

Tasks:
1. Check every invariant in invariants.md against the code. For each: where is it enforced, where could it be violated, is it enforced consistently across all entry points?
2. Trace 2–3 critical flows for edge cases: empty inputs, concurrent access, partial failure mid-flow, retries causing double-effects, timezone/encoding/precision issues.
3. Look for error handling that swallows or mistranslates failures (bare catches, error-to-null conversions, logging-and-continuing where the state is now corrupt).
4. Inspect boundaries between AI-typical layers: data reshaped multiple times is where field mix-ups, unit mismatches, and lossy conversions hide.
5. Distrust comments and docstrings — verify claims against code. Where a comment asserts behavior the code doesn't have, report both the mismatch and which one is probably wrong.

---

## tests (adversarial)

Role: determine whether the test suite would actually catch regressions, or is theater.

Tasks:
1. Sample the highest-coverage test files. Classify tests: (a) asserts real behavior, (b) asserts a mock returns what the mock was told to return, (c) asserts nothing meaningful (snapshot of everything, expect(true), no assertion). Report the ratio.
2. Git-history audit: `git log -p --follow` on test files changed in the same commit as the code they test. Flag every case where an assertion was weakened, deleted, or changed to match new output with no explanation. Command starter: `git log --format='%H %s' --name-only | ...` — adapt per repo.
3. Check for invariants from invariants.md that have NO test at all.
4. Look for tests that would pass even if the feature were deleted (test the test: what code change would this test fail to catch?).
5. Coverage-vs-confidence: identify modules with high line coverage but only type (b)/(c) tests.

---

## security (adversarial)

Role: assume exploitable defects exist; find them.

Tasks:
1. Input handling at every trust boundary: injection (SQL/command/template), path traversal, deserialization of untrusted data, unvalidated redirects.
2. AuthN/AuthZ: endpoints or handlers missing checks that sibling endpoints have; authorization checked in the UI layer but not the API layer; IDs accepted from the client and used without ownership checks (IDOR).
3. Secrets: hardcoded credentials, secrets in logs, secrets in git history (`git log -p | grep`-style spot checks), overly readable config.
4. Unsafe defaults introduced defensively: permissive CORS, disabled TLS verification, broad exception handlers hiding security failures, debug flags.
5. Dependency-adjacent: known-vulnerable versions if an audit tool is available (`npm audit`, `pip-audit`), but the dependencies lens owns the full manifest review.

---

## dependencies (mechanical)

Role: audit the dependency manifest against reality.

Tasks:
1. Unused dependencies: run `knip`/`depcheck` (JS/TS) or `vulture`+import analysis (Python) or equivalent; verify hits manually before reporting.
2. Duplicated capability: two+ libraries doing the same job (two HTTP clients, two date libs, lodash + hand-rolled equivalents).
3. Risk: unmaintained/abandoned packages, packages pulled in for one function, version pins that look accidental.
4. Phantom usage: dependencies that ARE imported but only by dead or single-use speculative code (coordinate with what you can see; overbuild lens owns the deletion argument).

---

## overbuild (interrogative)

Role: find well-integrated pointlessness — code that IS used, but exists for no reason. Dead-code detectors miss this; you are the detector. For deeper proportionality criteria, see `../../proportionality-review/references/criteria.md`.

Tasks:
1. For every config option/flag: how many distinct values does it ever take in the repo, deploy configs, and tests? Options with exactly one value ever used are candidates.
2. For every factory, builder, strategy pattern, or plugin system: how many implementations exist? One implementation behind an interface used in one place = speculative scaffolding.
3. "What breaks if deleted?" — for each suspicious abstraction, state concretely what would break and whether the breakage is real functionality or just other scaffolding.
4. Telemetry/hooks/extensibility points nothing consumes.
5. Defensive code against impossible states: null checks on guaranteed-non-null values, try/catch around pure functions, fallbacks for states the type system or invariants exclude.
6. Estimate the ratio: lines of code serving shipped functionality vs. lines serving hypothetical futures.

---

## null-hypothesis (defensive) — REQUIRED PASS

Role: argue this codebase is fine and typical concerns are overblown. You are the defense attorney. Your rebuttals tell synthesis which findings are load-bearing.

Tasks:
1. Steelman the structure: for each pattern a critic would flag (extra layers, defensive code, uniform module shapes, config options), construct the strongest legitimate justification — team conventions, real past incidents implied by the code, genuine near-term roadmap needs, framework requirements.
2. Identify context critics would lack: constraints visible in the code (legacy integrations, compliance hints, platform quirks) that justify apparent weirdness.
3. Argue proportionality: what is the actual cost of each likely criticism? Distinguish "aesthetically displeasing" from "will cause an incident."
4. Concede honestly: list the (few) things you cannot defend. These concessions are the highest-signal output of this pass.

You do NOT see other lenses' reports. Anticipate criticisms from the code itself.
