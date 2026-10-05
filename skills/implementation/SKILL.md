---
name: implementation
description: Make bounded, controlled code changes while preserving contracts, surrounding conventions, and user work. Use when applying an understood change, implementing a resolved decision, or supplying the code-editing method within a larger task. Supports local change validation; does not own feature discovery, architectural redesign, full code review, release, or deployment.
---

# Implementation

Produce a coherent change whose behavior and limits can be checked. Supply
primarily ACT, with local PLAN, OBSERVE, VERIFY, and ADAPT support. Let the
caller own the overall goal, sequencing, and completion verdict. Scale this
method to the change; a simple edit needs no separate planning document.

## Establish inputs and the contract

Resolve from the request and current task state:

- Intended behavior, acceptance criteria, and what must remain true.
- Relevant source, callers, tests, configuration, and repository instructions.
- Current workspace state, existing edits, available tools, and authorized effects.
- Known assumptions, compatibility requirements, and validation constraints.

Distinguish required behavior from a suggested implementation. Identify concrete
invariants at the touched boundary: inputs and outputs, error handling, state
transitions, data formats, ownership, or externally visible behavior. Record
only those relevant to the change. Resolve reversible technical choices from
local evidence. Ask only when an unresolved requirement materially changes the
result or exceeds existing authority; useful independent inspection can proceed.

## Understand the surrounding code

Read the affected path and enough nearby code to understand its role. Trace
relevant callers and dependencies rather than guessing from a symbol name.
Use existing patterns for naming, types, errors, dependencies, and test location.
Inspect build and validation conventions before choosing commands. Do not assume
a familiar framework version or invent an unavailable tool.

Establish a baseline sufficient to distinguish this change from existing work
and failures. Inspect current edits before writing; preserve user changes and
untracked files. An already dirty workspace is not permission to clean it.
When edits overlap, integrate deliberately from the current content; stop the
affected edit if authorship or intent cannot be resolved safely.

## Apply a small coherent change

Choose the smallest change that fully satisfies the local contract. Include
necessary consumers and supporting changes so the result remains usable;
minimize conceptual scope rather than chasing a line-count target. Split work
only at meaningful boundaries that preserve valid intermediate states.

Edit the authoritative source using tools supported by the host. Keep unrelated
formatting, cleanup, dependency upgrades, and architectural changes outside the
patch. Reuse suitable abstractions already present. Introduce new abstraction
only for a demonstrated need in this change, not imagined future requirements.
Follow repository rules for generated files and lockfiles.

Inspect the resulting diff and affected surrounding code. Check unintended
deletions, changed interfaces, omitted consumers, and accidental artifacts. If
another actor changed a touched file, re-read and reconcile before overwriting.
Revert only attributable changes of your own when safe; never use broad resets
or cleanup to recover from a local mistake.

## Validate the local result

Map each relevant acceptance criterion or invariant to observable evidence.
Choose proportionate checks: focused behavioral tests for changed logic, caller
or integration checks for boundary changes, and applicable type, build, lint,
or direct inspection checks. Use existing meaningful coverage first; add tests
when they address a concrete regression risk or required gate. Follow required
repository gates without imposing TDD or new tests on every edit.

Read actual outputs and compare them with expected behavior. A passing command
does not prove a criterion it never exercises. Distinguish new failures from
baseline failures and infrastructure limits. Recheck evidence invalidated by
later edits. Broaden validation only for a remaining risk or required gate.

## Adapt and hand off

On contradiction or unexpected scope growth, identify the cause, shrink the
patch, revise the approach, or return the specific gap to the caller. Do not
weaken acceptance criteria or repeatedly patch symptoms. Load another skill
only for an actual gap, such as unresolved diagnosis or specialized validation.

Honor host policies and authorization already granted. This method supplies no
new permission to commit, publish, deploy, or modify external systems. Stop the
affected action for missing access, conflicting mandatory constraints, or a
necessary human decision; preserve useful work and a resumable next step.

Return changed artifacts, intended behavior, relevant checks and observed
results, deviations, and unresolved risks. State unverified criteria explicitly.
Stop optional work once the local contract is supported; leave overall review
and release decisions to their owning methods.

Read [provenance.md](references/provenance.md) only when evaluating this method's
source influences or adaptation boundaries.
