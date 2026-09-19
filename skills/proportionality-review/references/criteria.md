# Proportionality Criteria

Use these criteria when assessing whether a proposal or design is more complex than its current needs justify.

## Minimum sufficient solution

Ask:

> What is the smallest complete solution that safely satisfies the current requirement?

“Smallest” does not mean shortest. Keep complexity that protects correctness, security, privacy, data integrity, reliability, accessibility, compliance, real performance requirements, or recovery from realistic failures.

## Requirement-to-solution trace

Separate the actual problem and required outcomes from solution choices presented as requirements. Classify each proposed element as:

- necessary now;
- useful soon; or
- merely possible later.

For every meaningful feature, component, layer, dependency, workflow, or approval stage, identify the present requirement or realistic risk it serves, the failure it prevents, a simpler alternative, and its ongoing cost. Remove, reduce, reuse, or defer elements whose justification depends only on speculation.

## Reversibility and validation

Demand stronger evidence for expensive or irreversible commitments such as public APIs, persistent data formats, service boundaries, framework adoption, and migrations. When a decision depends on an unverified assumption that is costly to reverse, validate the assumption before committing to substantial machinery.

## Full cost

Count build cost and operating cost: deployment, monitoring, on-call, security updates, configuration, documentation, testing, and the cost of understanding the system over time. A boundary or abstraction earns its cost when something currently differs across it—responsibility, security, failure behavior, lifecycle, or scaling—not merely because it looks architecturally clean.

## Artifact-specific checks

For plans and specifications, check that the document is not more complicated than the work: repeated requirements, decisions hidden in prose, phases without a concrete need, unresolved decisions presented as settled, and acceptance criteria that test implementation details rather than required outcomes.

## Finding categories

Classify significant findings as:

- **Remove** — contributes to no current requirement or realistic risk.
- **Simplify** — necessary, but implemented with avoidable complexity.
- **Defer** — potentially valuable later, but not needed now.
- **Reuse** — an existing capability already covers it.
- **Validate** — depends on an assumption that should be tested first.
- **Justify / Clarify** — may be appropriate, but lacks evidence or hides ambiguity.
- **Keep** — clearly earns its cost.
