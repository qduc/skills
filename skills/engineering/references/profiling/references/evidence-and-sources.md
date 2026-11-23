# Evidence and methodology sources

## Compact evidence record

Extend the existing task record rather than creating duplicate paperwork.
Retain raw artifacts with enough context to repeat the measurement.

| Field | Record |
| --- | --- |
| Contract | Operation, input/data identity, load model, metric/units, target, guardrails, budget |
| Reproduction | Revision, build/runtime/tools, commands, environment and resource limits |
| Conditions | Cold/warm policy, resets, timing boundaries, instrumentation, concurrent load |
| Baseline | Raw run values, successful work/errors, sample count, summary and spread |
| Diagnosis | Actual profile/trace/counter paths; observed mechanism and attribution limits |
| Experiment | Hypothesis, expected outcome, discriminating check, authorized change/diff |
| Result | Comparable raw after-runs, correctness checks, metric/guardrail verdict, keep/revert |
| Limits | Representativeness, noise, missing observations, confounders, next useful check |

For a lower-is-better nonzero metric, express relative reduction as
`(baseline − after) / baseline × 100%`; state the summarized values and absolute
delta too. Use the appropriate direction for throughput. Avoid averaging
percentages with different denominators or treating a computed delta as proof
of a reliable improvement.

## Measurement pitfalls

- Choose elapsed time for user-visible waiting and CPU time for CPU cost;
  make asynchronous or accelerator completion part of the measured boundary.
- Check that the harness performs real work and observes its outputs; compiler
  elimination or cached results can make a benchmark misleading.
- Separate tail-latency evidence from averages. Retain enough observations for
  the percentile claim and state inadequate coverage when budget is too small.
- Treat allocation rate, live/retained memory, and peak memory as different
  questions; a busy allocator alone does not establish a leak.
- Explain profile percentages using their measured population. CPU sample share
  is not wall-time share, and inclusive call-tree totals can overlap.
- Do not change system-wide frequency, scheduling, cache, or isolation settings
  merely to improve a result. Match the intended deployment conditions where
  feasible and record differences otherwise.

## Sources and adaptations

Inspected on 2026-10-05. Use these as provenance or optional deeper reading,
not as mandatory tool dependencies. This skill is an original synthesis;
published availability or popularity does not demonstrate its effectiveness.
No repeated-use effectiveness claim is made for this seed skill.

- **Public agent skill:** [borghei/Claude-Skills, Performance Profiler](https://github.com/borghei/Claude-Skills/blob/main/engineering/performance-profiler/SKILL.md).
  Adapt the baseline → observed bottleneck → change → remeasurement sequence
  and the requirement to inspect profiler evidence. Leave out its runtime
  inventory, scripts, broad optimization catalog, and integration bundle.
- **Primary methodology:** [Brendan Gregg, Active Benchmarking](https://www.brendangregg.com/activebenchmarking.html).
  Adapt concurrent observation to establish what a benchmark measures and what
  limits it. Bound run duration by task budget rather than requiring long runs.
- **Primary methodology:** [Brendan Gregg, USE Method](https://www.brendangregg.com/usemethod.html).
  Adapt checking resource utilization, saturation, and errors to distinguish
  busy resources from limiting mechanisms. Avoid a mandatory exhaustive sweep.
- **Primary documentation:** [Google Benchmark User Guide](https://google.github.io/benchmark/user_guide.html).
  Adapt deliberate warmup, repeated observations, recorded statistics, and
  separate profiler runs. Generalize these choices beyond its C++ API.
- **Primary documentation:** [Google Benchmark, Reducing Variance](https://google.github.io/benchmark/reducing_variance.html).
  Adapt awareness of environment and system-state noise. Retain authority and
  representativeness constraints rather than prescribing machine-wide tuning.
