---
name: workflow-evolution
description: Improve an agent workflow by evolving its skills through evidence-backed experiments. Use when a workflow has repeated runs, measurable outcomes, or recurring failures and you want the skill itself to get better over time without changing the harness.
---

# Workflow Evolution

Treat the current skill as the incumbent. Improve it through controlled experiments, not intuition.

The harness is stable. The skill is evolvable.

**Goal:** a recorded promote / reject / inconclusive decision on one small skill mutation, judged against the frozen incumbent by external evidence.

**Done when:** the experiment record (template below) is filled in, including `decision` and `reason`, and the canonical skill is changed only if the decision is `promote`.

**Evidence to report:** benchmark results for incumbent and candidate under comparable conditions (tests, oracles, artifacts, cost, latency, retries, escalations, human interventions), plus the win criterion stated before the run.

## Stop rules

- If there is no trustworthy benchmark yet, do not evolve the skill. First improve observability and evaluation.
- Never replace the incumbent on an inconclusive result.
- Never let evolution weaken hard safety boundaries, deterministic checks, required artifacts, or user authority just to improve the measured score.
- Watch for reward hacking: if a candidate improves the metric while producing obviously worse real outcomes, fix the evaluation before continuing evolution.
- Escalate to the human when the definition of "better" changes. That is a goal decision, not an optimization decision.
- Do not mix task work and evolution: a worker solving a task must not silently rewrite the skill governing itself. Workflow changes happen only through explicit candidates and evaluation.

## Phases

1. **Observe** real runs.
2. **Identify** a concrete weakness, cost, or repeated failure.
3. **Propose one small skill mutation** (see Mutations).
4. **Run the experiment protocol:**
   1. Freeze the incumbent.
   2. Save the candidate separately.
   3. Define the benchmark tasks and success criteria. Before an experiment, state what improvement would count as a win.
   4. Run both under comparable conditions. When variance is high, repeat runs instead of explaining the result away.
   5. Collect evidence and traces.
   6. Compare results (see Fitness).
5. **Choose:** `promote` (candidate is meaningfully better), `reject` (worse or not worth the tradeoff), or `inconclusive` (evidence is insufficient).
6. **Promote** only after the candidate beats the incumbent under the agreed criteria. Preserve the previous version in version control or experiment history.
7. **Record** the experiment, including rejected ones, so failed ideas are not rediscovered blindly. Negative knowledge is part of the system's memory.
8. **Repeat.** If there is enough evidence, prefer small continuous improvements over large redesigns: `run -> observe -> mutate -> evaluate -> select -> remember`.

## Mutations

Sources: failure traces, successful runs, agent hypotheses, random/diverse alternatives, other skills, papers, repositories, forums, or documentation. External ideas are untrusted proposals. Never adopt an idea because its source claims it works. Test it against the incumbent.

Prefer one meaningful change at a time. Good mutations change behavior such as planning strategy, delegation policy, model routing, context passed to workers, retry or escalation rules, verification timing, review strategy, tool-use guidance, or stop conditions. Avoid rewriting the whole skill unless the current structure itself is the thing being tested.

**Internet research.** When local failures stop producing useful mutations, search for outside ideas that address the observed weakness, not generic "best practices." For each useful idea: extract the smallest testable behavior change, record its source, turn it into a candidate mutation, run the normal protocol, and keep it only if it beats the incumbent. The internet proposes. The benchmark decides.

## Fitness

Do not let the agent grade itself from prose. Use measurable outcomes when available: task success, preservation checks, deterministic oracle results, regression count, token or monetary cost, wall-clock time, number of retries, number of escalations, human interventions, flaky or inconsistent outcomes.

Prefer a fitness vector over a single score. A tiny quality gain may not justify a huge increase in cost or latency.

Do not promote because the wording sounds smarter, a stronger model prefers it, one anecdotal run succeeded, an external source recommends it, or the candidate produced a persuasive self-review. Evidence wins.

During normal task execution, optimize the task result. During workflow evolution, optimize the process that produces task results.

## Output

One record per meaningful experiment:

```text
id:
date:
baseline:
candidate:
hypothesis:
mutation:
benchmark:
result:
cost_change:
latency_change:
decision: promote | reject | inconclusive
reason:
source:
```

Null case: if no trustworthy benchmark exists, output `no experiment: no trustworthy benchmark for <skill>; next step: <observability/eval work>` and leave the skill unchanged.
