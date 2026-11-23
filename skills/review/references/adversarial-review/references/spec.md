# Specifications & Requirements — review profile

Applies when the artifact is a functional spec, requirements doc, RFC (behavioral portion), API contract, or acceptance criteria. Use alongside SKILL.md; do not restate its rules.

A spec's defects are things that will make two reasonable implementers build different systems, make a tester unable to decide pass/fail, or make the built thing fail its actual purpose.

## Reading order

1. Stated goals / success criteria first — everything else is judged against them.
2. Definitions and terminology.
3. Requirements, in order, building a running list of every term, actor, state, and quantity introduced.

## Persona focus adjustments

- **P1 Assumption Challenger:** undefined terms used as if defined ("quickly", "valid user", "the system"); implicit actor capabilities; assumed happy-path ordering of user actions; assumed data volumes; "obvious" behaviors never written down (what happens on cancel? on re-submit? on empty?). Negate each: what if the user does it twice, out of order, or never?
- **P2 Failure-Path Prober:** for every specified behavior, is the failure behavior also specified? Error states, timeout behavior, partial-completion states, what the user sees when a requirement's precondition is unmet. A spec that only specifies success is a lattice of P2 findings — but file them per-requirement with location, not as one vague blob.
- **P3 Consistency Auditor:** requirement vs. requirement contradictions; text vs. table/diagram; MUST in one section, MAY for the same behavior in another; terminology drift (same concept, three names — or worse, one name, two concepts); acceptance criteria that test something the requirements don't require.
- **P4 Scope & Omission Detector:** goals with no requirement that achieves them; actors mentioned in goals but absent from requirements; non-functional requirements (perf, scale, availability, compliance) implied by the purpose but unstated; no acceptance criteria for a testable claim; lifecycle gaps (creation specified, deletion/expiry not).
- **P5 Adversary:** requirements a malicious or careless user can satisfy while defeating the intent (letter-vs-spirit gaps); abuse cases absent (rate limits, quota, permissions on every operation, not just the flagship one); requirements that force implementers into insecure designs (e.g., mandating URL-passed credentials).
- **P6 Proportionality Skeptic:** requirements serving no stated goal; premature precision (specifying internals the goal doesn't constrain); gold-plated NFRs (five nines for an internal batch tool).

## Evidence norms

Cite the requirement ID / section for every finding. **Untestability findings** must show the two divergent readings: "Reading A: … Reading B: … — both satisfy §4.2 as written." **Contradiction findings** must cite both locations. **Omission findings** must cite the goal/constraint that implies the missing requirement.

## Severity anchors

- **critical:** contradiction between two MUST requirements; a stated primary goal with no requirement path to achieve it; ambiguity on the core behavior such that conforming implementations can be mutually incompatible.
- **high:** untestable acceptance criterion on a primary flow; unspecified failure behavior for an operation that will fail routinely; letter-vs-spirit gap exploitable by ordinary users.
- **medium:** terminology drift likely to cause implementer confusion; missing edge-case behavior on a secondary flow; non-functional requirement implied but unquantified.
- **low:** ambiguity where all plausible readings are acceptable; redundant requirements that agree.

Reject: wording preferences, document structure opinions, "add more examples" without a demonstrated divergent reading, tone.

## Type-specific notes

- **Low-yield persona:** P2 partially overlaps P4 on specs (unspecified failure behavior is both a failure-path and an omission). Rule: if the failure case is *mentioned but underspecified*, it's P2; if *entirely absent*, it's P4. The judge merges any duplicates that slip through.
- **API contracts:** P3 additionally cross-checks examples against the schema — a sample response violating its own schema is a classic high.
- **Acceptance criteria:** run the tester test on each — could a tester decide pass/fail with only this document and the product? Each "no" is a located finding.
