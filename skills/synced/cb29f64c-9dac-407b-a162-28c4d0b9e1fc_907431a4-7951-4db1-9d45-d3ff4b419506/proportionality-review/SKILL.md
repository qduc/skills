---
name: proportionality-review
description: Review a plan, specification, design, architecture, implementation, code change, or process for unnecessary scope, complexity, speculation, and maintenance cost before approval or finalization. Use whenever the user asks whether a solution is too complex, over-engineered, gold-plated, or "more than we need," or asks to review/critique/sanity-check a proposal, spec, design doc, PR, or plan — even if they don't say "proportionality."
---

# Proportionality Review

Goal: ensure every meaningful part of the solution earns its cost. Proportionate, not minimal — do not optimize for fewest words, files, or lines, and never remove complexity that protects correctness, security, privacy, data integrity, reliability, accessibility, compliance, real performance requirements, or recovery from realistic failures.

## Core question

> What is the smallest complete solution that safely satisfies the current requirement?

Don't just ask whether the proposal is correct — ask whether it is proportionate.

## Process

**1. Separate the problem from the solution.** Restate the actual problem in 1–2 sentences. Distinguish required outcomes, explicit constraints, and known risks from *solution choices dressed as requirements* ("use an event bus" is a choice; "process requests asynchronously" may be a requirement). Classify what must be true as: necessary now / useful soon / merely possible later. Only the first belongs in the minimum solution by default.

**2. Trace every major element to a present need.** For each feature, component, layer, dependency, workflow, phase, or approval stage, ask: which current requirement makes this necessary, what failure does it prevent, what simpler alternative exists, what ongoing cost does it create, and could it wait until evidence appears? Elements without a strong present justification should be removed, reduced, or deferred. Watch especially for: unrequested features, abstractions built for a single case, premature extensibility/configurability, parallel mechanisms duplicating existing ones, broad platforms for narrow problems, and safety language used to justify unrelated complexity. Future concerns aren't invalid — but require evidence that acting now is cheaper than waiting, and prefer preserving a path to change over building the change in advance.

**3. Check reversibility and assumptions.** Irreversible or expensive commitments (public APIs, persistent data formats, service boundaries, framework adoption, migrations) need stronger evidence than local implementation choices. Don't build substantial complexity on an unverified assumption that is costly to reverse — recommend validating it first.

**4. Count the full cost.** Include operating cost, not just build cost: deployment, monitoring, on-call, security updates, configuration, documentation, and the cost of understanding the thing over time. A boundary or abstraction is justified only when it separates something that *currently* differs (responsibility, security, failure behavior, lifecycle, scaling) — not because it looks architecturally clean.

**5. Review the artifact itself.** For plans and specs, check that the document isn't more complicated than the work: repeated requirements, decisions hidden in prose, phases without concrete need, acceptance criteria testing implementation details, unresolved decisions presented as settled. A short document that exposes uncertainty beats a long one that disguises it. Specs should state what must be true, not how every part must be built; plans should take the shortest path that produces useful evidence.

## Findings

Classify each significant finding (skip minor style nits):

- **Remove** — contributes to no current requirement or realistic risk
- **Simplify** — necessary, but done with avoidable complexity
- **Defer** — possibly valuable later; not needed now
- **Reuse** — an existing capability already covers this
- **Validate** — depends on an assumption that should be tested before commitment
- **Justify / Clarify** — may be appropriate, but lacks evidence or hides ambiguity
- **Keep** — clearly earns its cost

## Output

Scale the depth to the subject — a 30-line code change gets a few findings and a verdict; a system architecture gets the full treatment.

1. **Problem** — the actual problem and minimum success condition
2. **Findings** — for each: category, element, cost introduced, why disproportionate, smallest reasonable correction
3. **Complexity budget** (larger subjects only) — new concepts, components, dependencies, operational duties, and irreversible commitments the proposal adds; is the total justified?
4. **Minimum sufficient solution** — the smallest complete solution that safely meets the requirement, preserving necessary safeguards
5. **Deferred possibilities** — brief list of ideas to keep possible but not build now
6. **Verdict** — one of: **Accept** / **Accept after simplification** / **Reduce scope or rework** / **Validate first** (or escalate if the trade-off needs human product judgment)

## Constraints

Do not reject complexity solely because it's unfamiliar. Do not recommend a "simpler" alternative without weighing migration, compatibility, and operational costs. Do not redesign unrelated parts of the system or invent future requirements. When uncertainty remains, prefer reversible decisions and make the uncertainty explicit.
