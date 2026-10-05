# Seed primitives

Treat these names as discovery hints, not required dependencies or a bundle to
preload. Resolve each against the host's current catalog. Read only a skill whose
methodology is needed now; the catalog may contain a better specialized match.

| Primitive | Load for this immediate gap | Useful result |
| --- | --- | --- |
| investigation | An engineering unknown needs evidence from the system or artifacts | Bounded findings, evidence, remaining unknowns |
| debugging | A failure needs a causal explanation or discriminating experiment | Supported hypothesis, experiment results, next intervention |
| implementation | An authorized code change needs controlled execution | Coherent change, preserved invariants, validation evidence |
| testing | A behavioral claim needs executable checks | Relevant results, coverage boundaries, untested risks |
| code-review | A change needs inspection for correctness and risk | Actionable evidence-backed findings or explicit review limits |
| research | A question needs external sources compared and synthesized | Traceable conclusions, conflicts, uncertainty |
| browser-qa | User-visible behavior needs observation in a real browser | Journey evidence, reproduction details, environment limits |
| profiling | Performance needs measurement and bottleneck localization | Comparable measurements, attributable costs, optimization evidence |

For a performance regression, investigation may first establish the affected
workload. Load profiling when measurement is needed, debugging if causal
uncertainty remains, implementation when a change is justified, and testing or
review when their evidence is needed. Do not prescribe that full sequence to
every regression; stop when the delegated outcome is verified.

Prefer a reusable methodology that contributes to many tasks. Do not seed a
new skill merely to name a composition such as fix-a-bug, build-a-web-app, or
refactor-a-module. A specialized skill may still be justified later by a recurring
methodology gap, not just by a new task title.
