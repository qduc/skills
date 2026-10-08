---
name: research-lab
description: >-
  Investigate a research goal unattended under a fixed budget, using the
  autonomy contract: decompose into claims, source and challenge them, run
  experiments when feasible, and leave a short conclusions brief plus reusable
  knowledge. Use when a human hands over a research goal and a budget and
  wants conclusions, not a transcript. For a bounded question you can answer
  in one pass, use research instead.
---

# Research lab

Research application of [autonomy-contract](../autonomy-contract/SKILL.md).
That skill owns the run directory, budget, stop rule, and citation check. This
skill says what each phase means for research. Methodology comes from existing
skills; load them at the phase that needs them:

- [research](../research/SKILL.md): sourcing, comparison, synthesis.
- [adversarial-review](../adversarial-review/SKILL.md): the challenge pass
  (P1 assumption challenger, P3 consistency auditor, P4 scope and omission).
- [investigation](../investigation/SKILL.md): experiments on a concrete system.

`LAB` below means `python3 skills/autonomy-contract/scripts/lab.py`.

## Start

1. `$LAB init RUN --goal-file goal.md --store STORE ...` with the budget you
   were given. Never raise a limit yourself.
2. OBSERVE: `$LAB recall RUN`. Read what surfaced. For each entry you will rely
   on, log `$LAB log RUN observe knowledge_used --data '{"ids":[...],"why":"..."}'`.
   Lessons (`kind: lesson`) are surfaced every run; apply them or say why not.
3. Reused knowledge is a lead, not proof. To cite it, re-record its source with
   `"via": "<K-id>"` and re-check the excerpt if the claim is decisive.

## Decompose (first DECIDE)

Split the goal into 3–7 investigable claims. A claim is a statement that
evidence could support or contradict, not a topic. Include at least one claim
that would **refute** the obvious answer.

```sh
$LAB add RUN claim '{"id":"C1","text":"...","status":"open","why":"what decision this informs"}'
```

Rank claims by how much they change the conclusion. Work the top open claim
first.

## Cycle

Start each cycle with `$LAB charge RUN cycle --note "<claim id + plan>"`.
Stop the loop the moment `charge` exits 3 or `check` exits 10.

**ACT: source.** Follow the research skill. Charge **each** search or fetch
first (`$LAB charge RUN web --note "<query or URL>"`). Prefer primary sources
(papers, benchmark reports, official documentation, first-party data) for
decisive claims. Use secondary sources to find primaries. Open the original
and quote the passage that carries the claim:

```sh
$LAB add RUN source '{"id":"S1","url":"https://...","title":"...","kind":"primary",
  "date":"2025-06-13","excerpt":"verbatim passage that supports or refutes the claim"}'
```

A search-result snippet is not an inspected source. If you could not open the
original, say so in the source `notes` and lower the confidence.

**ACT: experiment, when feasible.** If a claim can be checked by running
something cheap and local (a command, a script, a small reproduction), do it
with the investigation skill. Save the command and output under `RUN/experiments/`
and record it as a source with a `file:` URL and the output line as the excerpt.
If an experiment is not feasible, log why once:
`$LAB log RUN decide experiment_not_feasible --data '{"claim":"C2","why":"..."}'`.

**VERIFY: record findings.**

```sh
$LAB add RUN finding '{"id":"F1","claim_ids":["C1"],"source_ids":["S1","S3"],
  "statement":"...","confidence":"medium","kind":"evidence",
  "uncertainty":"what would change this; what was not checked"}'
```

Then update the claim's status (`supported`, `contradicted`, or `unresolved`)
by appending a new claim line with the same id. `kind` is `evidence` when a
source states it, `inference` when it is your reasoning across sources.

**VERIFY: challenge.** Before a claim leaves `open` as `supported` with high
confidence, do one challenge pass:

1. Search once for counter-evidence or a failed replication (charged like any
   other web call).
2. Apply adversarial-review P1, P3, and P4 to your own findings: unstated
   assumptions, findings that contradict each other, and parts of the goal
   no claim covers. These run sequentially in one context, so they are not
   independent reviews. Record that in the run log
   (`$LAB log RUN verify challenge_pass --data '{...}'`), not in the brief. The
   brief may state only the limitation ("findings were not independently
   reviewed"), without naming stages, personas, or the process.
3. Record what you found. Contradictions get their own finding with both
   sources cited. Do not average them away.

**LEARN.** Write knowledge entries a later run would be glad to find:

```sh
$LAB add RUN knowledge '{"kind":"finding","finding_ids":["F1"],"statement":"...",
  "confidence":"medium","tags":["..."]}'
$LAB add RUN knowledge '{"kind":"lesson","statement":"...","evidence":"what happened","tags":["..."]}'
```

Store findings that are general and sourced, not run-specific chatter. Store a
lesson when an approach failed or wasted budget in a way that will recur.

**REPEAT.** `$LAB check RUN`. Exit code 10 means stop.

## Parallel workers

Default: none. Split work across workers only when two or more claims are
independent, each needs several fetches, and the budget covers both. Give each
worker one claim, its own `--note` prefix, and the same run directory. The
lead alone writes findings and the brief.

## Finish

After the stop, spend no more web budget. Write `RUN/brief.md` in this format:

```markdown
# <question>

## Answer
<≤150 words: the conclusion the evidence supports, with its confidence>

## Key findings
- <finding, one or two sentences> [n] (confidence: high|medium|low)

## Contradictions and counter-evidence
- <where sources disagree, and the likely reason; or "none found" plus what was searched>

## Uncertainty and gaps
- <what is unknown, what was not checked, what would change the answer>

## Follow-up questions
- <questions worth a next run, most valuable first>

## References
[n] <title> — <author/org>, <date>. <URL>
    > "<verbatim excerpt that supports the cited finding>"
```

Keep the body under 1,500 words, excluding references. Use only URLs you
recorded as sources. Store each follow-up question for later runs:
`$LAB add RUN knowledge '{"kind":"question","statement":"...","tags":["..."]}'`.

Then run `$LAB validate RUN` and fix every `ERROR` line. Then run `$LAB audit RUN`.
The run is finished when the brief exists, `validate` prints `VALID`, and
`audit` prints `AUDIT OK`.
