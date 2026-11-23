# Architecture & System Design — review profile

Applies when the artifact is a system design doc, architecture proposal, ADR, component diagram + narrative, or technology selection. Use alongside SKILL.md; do not restate its rules.

An architecture's defects are designs that can't meet their stated load/availability/consistency requirements, couplings that make the system unevolvable, failure domains that take down more than they should, and one-way doors entered without justification.

## Reading order

1. Stated requirements: scale numbers, latency/availability targets, consistency needs, cost bounds. If these are absent, that itself is a P4 finding — and the review must state the assumed numbers it proceeds with.
2. The component/data-flow structure; identify every synchronous chain, every shared datastore, every trust boundary.
3. The decisions and their alternatives (or the absence of considered alternatives).

## Persona focus adjustments

- **P1 Assumption Challenger:** assumed traffic shape (uniform vs. spiky), assumed data growth, assumed network reliability between components, assumed team ability to operate the chosen tech, assumed backward compatibility of dependencies, "we can shard later" style deferrals — test whether "later" is actually reachable from this design.
- **P2 Failure-Path Prober:** for each component: what happens to the system when it's down, slow, or returning garbage? Blast radius per failure domain; cascades (retry storms, thundering herds, queue backpressure or its absence); split-brain and partition behavior for anything stateful; recovery — cold-start order, data restore path and its tested-ness, RTO/RPO vs. stated requirements.
- **P3 Consistency Auditor:** diagram vs. text; stated consistency model vs. flows that violate it (e.g., "strongly consistent" claim with an async replication hop in the read path); latency budget vs. sum of synchronous hops; stated availability target vs. serial composition of component availabilities (do the arithmetic); capacity claims vs. cited limits of the chosen technologies.
- **P4 Scope & Omission Detector:** requirements with no component/mechanism that satisfies them; missing cross-cutting concerns the purpose implies — observability, authn/z between internal services, data lifecycle (retention, deletion, GDPR-type obligations), deployment and migration path from the current system, capacity for the stated growth horizon; no alternatives considered for one-way-door decisions.
- **P5 Adversary:** trust boundaries — internal traffic assumed benign; lateral movement after one component is compromised; multi-tenant isolation; data exfiltration paths (backups, logs, analytics sinks with prod data); denial-of-service amplification points (fan-out endpoints, unbounded queries); supply-chain exposure of load-bearing third-party choices.
- **P6 Proportionality Skeptic:** microservices at a scale one service handles; queues/caches/replicas with no load number demanding them; multi-region for a system with no availability requirement implying it. Must use the doc's own scale numbers as evidence — this is the mirror image of P2, and the same show-the-arithmetic norm applies.

## Evidence norms

Findings must name the component(s)/flow and, wherever the claim is quantitative, **show the arithmetic with stated inputs**: "3 serial hops at p99 50ms each vs. a 100ms budget (§2)"; "99.9% × 99.9% × 99.5% serial = 99.3% vs. the 99.9% target." If the doc gave no numbers, use conservative published/typical numbers and label them as review assumptions. A scaling concern without numbers is speculation — reject it.

## Severity anchors

- **critical:** the design arithmetically cannot meet a stated hard requirement (availability, latency, consistency, compliance); a single failure domain that takes down the whole system when the requirements demand otherwise; an unjustified one-way door (data model, public API, vendor lock) blocking a stated future requirement.
- **high:** a plausible cascade with system-wide blast radius (retry storm, shared-datastore saturation); no workable migration path from the current system; internal trust boundary absent where the threat model implies one; recovery path that cannot meet stated RTO/RPO.
- **medium:** scaling ceiling within the stated growth horizon but with a feasible (if costly) remediation; observability gap that will make the top failure modes undiagnosable; coupling that makes a stated-as-likely change expensive.
- **low:** suboptimal choice with equivalent-cost alternatives and cheap reversal.

Reject: technology taste ("I'd have used X") without a requirement the chosen tech fails; hypothetical scale beyond the stated horizon; patterns-for-patterns'-sake (demanding event sourcing, service splits, or extra layers with no failure scenario they prevent — over-engineering demands are nitpicks too).

## Type-specific notes

- **Low-yield persona:** none at Standard/Deep; architecture is the artifact type where all five personas routinely pay off. Deep budget's extra pass should go to P2 on the stateful components.
- **ADRs / tech selections:** P4's key check is honest alternatives — an ADR whose alternatives section contains only strawmen is a located finding (cite the strawman and the omitted real alternative).
- **Designs replacing an existing system:** P2 must probe the coexistence period — the months when both systems run are usually the riskiest part and the least designed.
