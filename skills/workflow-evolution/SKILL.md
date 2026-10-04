---
name: workflow-evolution
description: Improve an agent workflow by evolving its skills through evidence-backed experiments. Use when a workflow has repeated runs, measurable outcomes, or recurring failures and you want the skill itself to get better over time without changing the harness.
---

# Workflow Evolution

Treat the current skill as the incumbent. Improve it through controlled experiments, not intuition.

The harness is stable. The skill is evolvable.

## Core loop

1. Observe real runs.
2. Identify a concrete weakness, cost, or repeated failure.
3. Propose one small skill mutation.
4. Run the incumbent and candidate against comparable tasks.
5. Judge with external evidence: tests, oracles, artifacts, cost, latency, retries, escalations, and human intervention.
6. Promote the candidate only when the evidence says it is better.
7. Record the experiment so failed ideas are not rediscovered blindly.
8. Repeat.

## Mutation sources

Mutations may come from:

- failure traces
- successful runs
- agent hypotheses
- random/diverse alternatives
- other skills
- papers, repositories, forums, or documentation

External ideas are untrusted proposals. Never adopt an idea because its source claims it works. Test it against the incumbent.

## Mutation discipline

Prefer one meaningful change at a time.

Good mutations change behavior such as:

- planning strategy
- delegation policy
- model routing
- context passed to workers
- retry or escalation rules
- verification timing
- review strategy
- tool-use guidance
- stop conditions

Avoid rewriting the whole skill unless the current structure itself is the thing being tested.

## Fitness

Do not let the agent grade itself from prose.

Use measurable outcomes when available:

- task success
- preservation checks
- deterministic oracle results
- regression count
- token or monetary cost
- wall-clock time
- number of retries
- number of escalations
- human interventions
- flaky or inconsistent outcomes

Prefer a fitness vector over a single score. A tiny quality gain may not justify a huge increase in cost or latency.

Before an experiment, state what improvement would count as a win.

## Experiment protocol

For each candidate:

1. Freeze the incumbent.
2. Save the candidate separately.
3. Define the benchmark tasks and success criteria.
4. Run both under comparable conditions.
5. Collect evidence and traces.
6. Compare results.
7. Choose:
   - `promote` — candidate is meaningfully better
   - `reject` — candidate is worse or not worth the tradeoff
   - `inconclusive` — evidence is insufficient
8. Never replace the incumbent on an inconclusive result.

When variance is high, repeat runs instead of explaining the result away.

## Promotion

A promoted candidate becomes the new canonical skill only after it beats the incumbent under the agreed criteria.

Preserve the previous version in version control or experiment history.

Do not promote because:

- the wording sounds smarter
- a stronger model prefers it
- one anecdotal run succeeded
- an external source recommends it
- the candidate produced a persuasive self-review

Evidence wins.

## Experiment memory

Keep a compact record for every meaningful experiment.

Recommended fields:

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

Record rejected experiments too. Negative knowledge is part of the system's memory.

## Internet research

When local failures stop producing useful mutations, search for outside ideas.

Look for approaches addressing the observed weakness, not generic "best practices."

For each useful idea:

1. Extract the smallest testable behavior change.
2. Record its source.
3. Turn it into a candidate skill mutation.
4. Run the normal experiment protocol.
5. Keep it only if it beats the incumbent.

The internet proposes. The benchmark decides.

## Self-correction

During normal task execution, optimize the task result.

During workflow evolution, optimize the process that produces task results.

Do not mix them: a worker solving a task must not silently rewrite the skill governing itself.

Workflow changes happen only through explicit candidates and evaluation.

## Guardrails

Never let evolution weaken hard safety boundaries, deterministic checks, required artifacts, or user authority just to improve the measured score.

Watch for reward hacking: if a candidate improves the metric while producing obviously worse real outcomes, fix the evaluation before continuing evolution.

Escalate to the human when the definition of "better" changes. That is a goal decision, not an optimization decision.

## Default behavior

If there is no trustworthy benchmark yet, do not evolve the skill. First improve observability and evaluation.

If there is enough evidence, prefer small continuous improvements over large redesigns.

The long-term pattern is:

`run -> observe -> mutate -> evaluate -> select -> remember`
