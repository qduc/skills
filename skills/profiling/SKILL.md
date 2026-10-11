---
name: profiling
description: Measure performance, locate limiting mechanisms, and verify bounded optimizations with comparable evidence. Use for slow workloads, latency or throughput regressions, excessive CPU or memory use, and performance claims needing validation. Supply a composable measure–locate–optimize–remeasure method; leave implementation, general debugging, releases, and production operations to their applicable methods and authority.
---

# Profiling

**Goal:** an evidence-backed performance decision (keep, revert, or diagnostic finding only) for a defined workload. Supply measurement and interpretation within a larger task; do not take over its whole lifecycle. Read [evidence-and-sources.md](references/evidence-and-sources.md) when choosing an evidence format (its record table is the evidence checklist), resolving measurement pitfalls (phases 2–3), or inspecting methodology provenance.

## Phases

1. **Define the measurement contract.** Identify the target operation, representative input sizes and distributions, concurrency or arrival rate, environment, and symptom. Choose the user-relevant metric and units: elapsed latency with relevant percentiles, completed work per second, CPU cost, peak or retained memory, or another justified measure. Record the target or minimum worthwhile improvement, correctness requirements, and time, run-count, and resource budget. Separate primary success metrics from guardrails such as errors, memory growth, or degraded tail latency. Resolve material ambiguities from available context before asking. If a target is absent, establish a baseline and present a bounded diagnostic finding; do not invent an acceptance threshold. Identify authorized observation and change scope. Prefer existing tools and isolated representative workloads.

2. **Measure a repeatable baseline.** Inspect what the benchmark actually executes and how it counts successful work. Check that setup, asynchronous completion, retries, and errors are handled consistently. Confirm correctness before interpreting speed. Record revision, executable or build mode, runtime/tool versions, input or seed, command/configuration, hardware/resource limits, and measurement window. Choose cold-start or warmed steady-state behavior deliberately; retain the same cache, JIT, initialization, and reset policy for comparisons. Note background load, frequency changes, thermal effects, and shared-host interference. Collect repeated runs within budget; retain individual observations and a summary with spread or uncertainty and sample count. Investigate drift or large variance before ranking changes. Interleave or alternate comparable variants when time-dependent conditions could bias them.

3. **Locate the limiting mechanism.** Capture and inspect an actual profile, trace, query plan, allocation/heap snapshot, or resource measurement during the target workload, chosen for the suspected mechanism: CPU execution, waiting/I/O, contention, allocation, retained memory, or another cost. If profiling is unavailable or disproportionate, use justified timings/counters and explicitly limit what they establish. Distinguish a frequently executed hot path from the bottleneck that constrains the chosen metric. Explain the denominator, attribution, and connection to critical-path time or resource capacity. Check waiting, queueing, saturation, errors, and benchmark-client limits when CPU samples cannot explain latency. Account for profiler overhead and incomplete sampling or symbols. Separate observations from hypotheses; correlation alone does not establish causality.

4. **Optimize one supported hypothesis.** State the mechanism, proposed change, expected metric movement, and a check that could contradict the hypothesis. Prioritize useful end-to-end gain over local hot-spot improvement. Choose the smallest reversible experiment that discriminates between plausible explanations; change one causal factor when practical. For code edits, use an available implementation method when needed, supplying evidence, constraints, and the proposed experiment. Load other methodology only for a concrete gap; do not auto-load neighboring skills. If changes are outside scope, return the measured finding and proposed experiment without claiming optimization.

5. **Remeasure and decide.** Verify relevant correctness, then repeat the original measurement contract on the changed version with comparable instrumentation. Keep diagnostic profiles separate from minimally instrumented acceptance runs. Compute before/after with `scripts/compare_runs.py baseline.txt after.txt [--higher-is-better]` (raw values, one per line); it refuses fewer than 2 runs per side and warns when ranges overlap. Reprofile only when needed to test the mechanism or explain an unexpected result. Keep a change only when evidence supports the required gain without violating constraints; revert unsuccessful experimental changes within authority, or report why the result is uncertain.

## Stop rules

- Treat one run as exploratory evidence, never a percentage improvement proof.
- Do not fabricate traces or infer measurements from source inspection.
- Do not require paid products, privileged settings, or production load. Apply changes only within existing authority; obtain missing authority before an action that needs it and preserve useful read-only progress.
- Stop at the target, exhausted budget, or diminishing expected benefit; do not optimize indefinitely.

**Done when** the decision is recorded with comparable before/after runs (or a baseline-only diagnostic finding), correctness evidence, guardrail outcomes, and stated limits.

## Evidence to report

Preserve commands, raw results/profiles, relevant revision or diff, interpretation, and limits in the existing task record. Bound claims to the tested environment and workload.

## Output

```
Workload: <operation, inputs, load, environment>  Metric: <name, units, target>
Before: <summary, spread, n>  After: <summary, spread, n>
Change: <absolute> / <relative %>  Guardrails: <outcomes>
Supported bottleneck: <mechanism + profile/trace path>
Decision: keep | revert | diagnostic only | uncertain — <reason>
Correctness evidence: <...>
Unresolved uncertainty: <...>
```

Null case: `Diagnostic only: baseline <values>; no supported bottleneck / no change made; next useful check: <...>`.
