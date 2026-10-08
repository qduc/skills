---
name: research-lab
description: Run an autonomous, budgeted research investigation that decomposes a goal into claims, gathers and challenges evidence, verifies quotes against saved sources, and promotes settled findings to a reusable knowledge base. Use when the user hands over a research goal with a budget and wants judgment-level conclusions with minimal supervision. For a quick question or a single lookup, use research instead.
---

# Research Lab

Own a research goal end to end inside a budget. The human receives conclusions
that need judgment, the evidence behind them, and what stayed uncertain — not a
transcript. This skill is the research instance of the autonomy contract in
[references/autonomy-contract.md](references/autonomy-contract.md); it composes
`agentic-loop` (ownership, stop rules) and `research` (sourcing, comparison).

All durable state lives in a run directory managed by `scripts/lab.py`
(stdlib Python). Model context holds only the current step. Run
`lab.py <cmd> -h` for arguments. Every command appends to `events.jsonl`.

## 0. Contract (once)

```sh
LAB="python3 <skill-dir>/scripts/lab.py"
$LAB init runs/<slug> --goal "<question>" --max-searches 20 --max-fetches 20 \
     --max-minutes 45 --kb <kb-dir>
```

Take the budget from the user; if none is given, use the defaults above and say
so. The budget is a hard ceiling, not a target.

## 1. Observe

- `$LAB kb-search <kb-dir> <terms> --lessons` — reuse prior settled claims and
  past lessons before searching the web. Cite reused claims by their original
  sources; re-check any that are time-sensitive.
- `$LAB status runs/<slug>` at the start of every cycle. It prints budget left,
  open key claims and counts in two lines.

## 2. Decide

**Scan before you decompose.** Claims written from prior knowledge only cover
what you already believed. Spend 2–3 charged searches on breadth — surveys,
benchmarks, independent evaluations, critiques — and record the evidence
families (lineages) you find:

```sh
$LAB scan runs/<slug> --query "<breadth query>" --lineages "benchmark X; vendor evals; equal-budget studies"
```

Then decompose the goal into 3–7 **key claims** that together cover the
lineages bearing on the answer: statements that, if settled, answer the
question. Phrase each so evidence could refute it, and include the live
hypotheses you expect to fail, not only those you expect to hold. For
"does X beat Y" goals, include a claim about whether the comparison is
controlled (same inputs, tools and budget) — it is usually the decisive lens. Add
supporting claims only when a key claim depends on them.

```sh
$LAB claim-add runs/<slug> "<falsifiable statement>" --key
```

Each cycle, pick the open key claim whose resolution most changes the answer
per unit of budget. Prefer one decisive primary source over many mentions.

## 3. Act

Before **every** web search, page fetch, or experiment, charge the meter:

```sh
$LAB charge runs/<slug> search|fetch|experiment --note "<why>"
```

Exit code 3 means the budget is spent: perform no further actions; go to
Verify and Report with what you have. Never work around the meter.

- **Source.** Follow the `research` skill: primary sources first (papers,
  official benchmark results, original engineering posts); secondary sources
  for discovery. Search results and summaries are leads, not evidence.
- **Snapshot.** Save the passage you inspected — verbatim text from the page,
  not your paraphrase — then link evidence to a claim with an exact quote:

  ```sh
  $LAB snapshot runs/<slug> --url U --title T --type primary|secondary|tertiary --year Y < passage.txt
  $LAB evidence runs/<slug> C1 --snapshot S3 --stance supports|contradicts|context --quote "<exact words>"
  ```

  When a fetch tool returns processed text, ask it for verbatim passages and
  record `--via` accordingly. Save exactly what it returned, fragments
  included; never rebuild surrounding sentences from memory. For numbers in
  results tables, fetch the full-text/HTML version, not the abstract. A quote that does not match its snapshot is
  flagged immediately; fix it, do not reword the snapshot to fit.
- **Challenge.** For every key claim, run at least one search designed to find
  counter-evidence (failed replications, critiques, negative results,
  equal-budget comparisons). Record it either way:
  `$LAB challenge runs/<slug> C1 --query "..." --found yes|no`.
- **Experiment** when a claim is cheaply testable inside the workspace (a
  calculation, a re-analysis of published numbers, a small script). Record the
  hypothesis, command, result and artifact with `$LAB experiment`. Do not run
  paid APIs or deploy anything without explicit approval.

## 4. Verify

Settle each claim with a status and confidence:

```sh
$LAB claim-set runs/<slug> C1 --status supported|refuted|contested|unresolved \
     --confidence low|medium|high --note "<why; how contradictions were resolved>"
$LAB verify runs/<slug>
```

The verifier is deterministic and checks: a breadth scan preceded the key
claims and a gap-check scan followed them; every quote matches its snapshot;
every key claim is settled with verified evidence and a confidence; every key
claim was challenged; high confidence rests on a primary source; supported
claims with contradicting evidence carry a resolution note. Treat each
`ISSUE` line as a task: gather evidence, downgrade confidence, or mark the
claim `contested`/`unresolved`. Never delete inconvenient evidence.

Use `contested` when credible evidence points both ways and `unresolved` when
budget ran out first. Visible uncertainty is a valid result.

**Gap check before stopping.** Once every key claim is settled, run one more
breadth scan aimed at what the ledger lacks (independent replications, other
benchmarks, negative results) and record it with `scan ... --new yes|no`. If it
reveals a lineage that could change the answer and budget remains, add a key
claim and continue. Settling your own claims is not the same as answering the
question; do not stop with half the budget unspent unless the gap check came
back empty.

## 5. Report

Write `runs/<slug>/synthesis.md` with exactly these sections:

- `## Answer` — the bottom line in 3–6 sentences, with overall confidence.
- `## Findings` — one short paragraph per key claim, citing claim IDs.
- `## Judgment calls for the human` — decisions the evidence cannot make.
- `## Follow-up questions` — a bullet list of the most promising next questions.

Then `$LAB finish runs/<slug> --reason "<answered | budget | blocked: ...>"`
(this freezes the clock) and `$LAB report runs/<slug>` renders `findings.md` (synthesis + claim ledger
+ contradictions + budget accounting). A failing verifier marks it DRAFT.

## 6. Learn

Write `runs/<slug>/lessons.md`: 1–5 bullets on what wasted budget or caught an
error, phrased as a rule for the next run. Then:

```sh
$LAB learn runs/<slug>      # promotes settled, verified claims + follow-ups + lessons
```

If the same lesson appears in two runs, propose a change to this skill or the
verifier instead of only appending it again.

## Parallel workers

Default to one worker. Fan out only when key claims are independent and each
needs several fetches. Pre-charge each worker's share of the budget, have it
return verbatim passages with URLs and proposed quotes, and record them in the
ledger yourself (`lab.py` is single-writer). Never parallelize the synthesis.

## Finish

Return to the human: the `## Answer` and `## Judgment calls` sections, the
verifier result, budget spent, and the path to `findings.md`. Nothing else.
