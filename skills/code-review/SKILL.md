---
name: code-review
description: Inspect code changes for evidence-backed correctness, security, and compatibility risks. Use for reviewing a diff, pull request, commit, or proposed patch, or as an inspection method within a larger verification workflow. Produce actionable findings and coverage limits; do not silently fix code or manage the whole development lifecycle.
---

# Code Review

Supply a bounded inspection method. Contribute to PLAN by choosing review coverage, OBSERVE by tracing behavior, VERIFY by testing candidate findings, and ADAPT by identifying missing evidence. Let the caller own orchestration, remediation, and acceptance decisions.

## Establish inputs and scope

Resolve the target revision or working-tree snapshot, comparison base, intended behavior, review scope, relevant repository instructions, and available checks. Inspect the supplied diff and current task context before asking questions. Use the requested base; otherwise determine the appropriate merge base or parent from repository evidence and state the choice. Never compare unrelated revisions just because a command defaults to them.

For uncommitted changes, include relevant staged, unstaged, and untracked files within scope without overwriting user work. If only a snippet is supplied, review it with explicit context limits. Record exclusions such as generated files, unavailable dependencies, or security-only scope. Establish callers, affected contracts, deployment assumptions, and existing behavior where these can change the judgment.

Use available host tools and honor their access and authorization rules. Review means inspection: do not edit reviewed code, commit, publish comments, approve, or merge unless separately authorized. Choose isolated, proportionate checks; avoid executing unknown scripts or live-service operations without understanding their effects. Load another skill only for an actual methodology gap.

## Trace relevant behavior

Read every in-scope handwritten change, including deletions. Expand into surrounding implementations, callers, tests, configuration, and documented contracts as needed to establish consequences. Prioritize paths with changed outputs, state transitions, trust boundaries, error handling, or compatibility promises.

Check applicable risks rather than mechanically filling a checklist:

- Behavior: boundary values, missing data, error paths, resource lifetime, ordering, concurrency, retries, and idempotency.
- Security: untrusted input reaching sensitive operations, authorization enforcement, secret exposure, and isolation boundaries.
- Compatibility: API or schema changes, migrations, older clients, supported platforms, configuration defaults, and rollout ordering.

Tie each concern to a reachable path and an affected contract. A hypothetical attacker, unsupported input, or imagined future requirement is insufficient. Conditional bugs remain valid when their trigger is supported by code, documented usage, or a reproducible scenario. Label existing defects separately; identify regressions introduced or exposed by the change.

## Validate candidate findings

For each candidate, trace the triggering input or state through the changed code to the incorrect outcome. Search for safeguards, alternate paths, and intentional contract changes that could disprove it. Compare the base when attributing a regression. Use the smallest useful reproduction, targeted test, type check, or source trace; record what it actually demonstrates.

Passing tests support only the paths and assertions they cover. Check whether relevant tests would detect the suspected failure. Do not turn missing test coverage alone into a correctness bug. Treat unavailable execution as a limitation, not proof of failure. Drop disproven candidates and duplicates. Do not require any minimum number of findings.

Stop expanding when the agreed scope is covered and remaining candidates have a supported disposition. If missing requirements or access prevent judgment, return the specific question or blocked coverage and the next evidence needed. Recheck affected evidence if the target changes during review.

## Return actionable evidence

Lead with findings, ordered by impact and urgency. For each, include a concise problem title, the smallest useful current-code location, triggering conditions, observable consequence, evidence, and a remedy direction when clear. Explain severity through impact and realistic exposure; keep uncertainty separate from severity. Use the caller's scale when supplied; otherwise use critical, high, medium, or low with a brief rationale.

Distinguish **blockers** (demonstrated violations of acceptance requirements), **questions** (missing information that changes the verdict), and **nits** (optional improvements). Do not promote personal style preferences to blockers. Preserve any requested output schema and omit irrelevant categories.

Finish with reviewed scope, meaningful checks and results, and material limitations. If no actionable issues survive, say so within that scope; do not imply universal correctness or authorize release. Return evidence the caller can use to fix, investigate, or accept risk.

Read [source provenance](references/sources.md) only when attribution or methodological comparison is useful.
