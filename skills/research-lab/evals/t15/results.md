# T15 results: autonomy contract vs a single well-prompted model

**Headline: INCONCLUSIVE.** Arm A (autonomy contract) scored 15/16 and Arm B (single well-prompted pass) scored 14/16.
Under the frozen decision rule a difference of at least 2 points is needed, so a 1-point gap does not count.
A used 0.65× B's web calls and took 1.21× B's time. This is directional at best: one question, one run per arm,
one scorer, an unpinned model, and a blinding check that partly failed. Dollar and token cost was not measured, so
"quality per dollar" is proxied only by web calls and minutes. One agent (coder) built the system, ran the experiment,
and produced the transcript counts, which is a conflict of interest (deviation 7).

Protocol: [protocol.md](protocol.md), frozen at `54d86025aa213040592cd082b5b07146451e0dd6`. The run happened on
2026-10-09, starting 02:44 ICT. The arms ran concurrently. Raw records are in [artifacts/](artifacts/README.md).

**Evaluated version.** Both arms, the scorer, and every number here used the skills as frozen at `54d86025`. The
fixes below landed on this branch **after** the evaluation. They do not change any artifact, score, or label.

| Commit | Post-evaluation fix |
| --- | --- |
| `2b92359` | autonomy-contract/SKILL.md names the ledger fields (`kind`, `what`, `n`) and points to `audit`'s `used` totals. |
| `de68843` | `lab.py charge` rejects `--n < 1`, and `audit` flags any charge with `n < 1` (PR review N1). |
| `de68843` | The docs now say the unkeyed hash chain makes accidental edits evident. A deliberate rewrite is caught only by an outside count (`--observed-*`) (N2). |
| `de68843` | `unresolved` no longer counts as progress for the stall rule, which now needs a claim newly `supported` or `contradicted`. The "no open claims" stop reports resolved and unresolved counts separately, and `check` shows open, resolved, and unresolved (N3). Under this rule, A's stop reason would read "no open claims left (4 resolved, 1 unresolved)". |
| `38fb8e2` | research-lab/SKILL.md no longer tells the agent to describe the challenge pass in the brief. That instruction caused the blinding tell (N5). |
| `5dd22aa` | `examples/smoke/smoke.sh` writes its outputs to a temp dir. The 29 generated files are no longer committed (N9). |
| this commit | Disclosures and corrections in this file, plus dated correction notes appended to the artifact copies of `measurements.md` and `dispatch.log` (N4, N6, N7, N8, N10). |

Question (both arms): *What evidence shows that autonomous research agents outperform a single well-prompted model
on difficult technical research tasks?*

## Scores (blind, by Sol)

The scorer saw X and Y. After scoring, the coin flip (`0`) mapped X to Arm A and Y to Arm B.

| Criterion | A | B | Sol's reason (condensed) |
| --- | --- | --- | --- |
| Factual correctness | 3 | 4 | A: all 6 checked pairs right, but "where that control exists, agent advantages shrink or reverse" overstates. Kim et al. show +80.8% on Finance Agent under matched compute, and the Anthropic source has no matched control. B: all 6 pairs and every extra claim checked were right. One small omission: o3-mini's HLE 13.0 is on the text-only subset. |
| Source quality | 4 | 3 | A: decisive claims rest on primary papers (arXiv, Nature MI) plus Anthropic's first-party post, and every reference is dated. B: mostly primary, but GAIA "GPT-4 <7%" rests on a secondary HF blog, HLE/GAIA numbers come from a vendor launch post, and most references are undated. |
| Contradictions and uncertainty | 4 | 4 | A: three cited conflicts with reasons, clear gaps, and decision-relevant follow-ups. B: four cited conflicts, frames the dispute as "what is held fixed", and lists concrete unknowns. |
| Useful findings | 4 | 3 | A: specific task, metric, effect, and cost findings tied to technical research. B: well hedged, but its large headline gains are web-finding QA against baselines without tools, and its PaperBench item is not an agent-vs-model comparison. |
| **Q (0–16)** | **15** | **14** | |
| Citation integrity | 0.92 | 1.00 | A: 5 Supported and 1 Partial out of 6. B: 6 Supported out of 6. Nothing was unreachable. |

A's one Partial is pair **#17**: "Where the equal-tools/tokens control exists, agent advantages shrink or reverse
[2][5][8]". Kim et al. [8] hold prompts, tools, and compute fixed and find a mean MAS change of 0.0%, with reversals on
PlanCraft and SWE-bench but **+80.8% on Finance Agent**. They also compare multi-agent systems with a single tool-using
agent, not with a "single well-prompted model". Sol's six pairs per answer were 4 drawn at random (seed from the freeze
SHA) plus the 2 most decisive. Full table: [artifacts/blind/scores.md](artifacts/blind/scores.md).

### Citation precision (found in the PR review, not scored)

Sol re-checked all 23 recorded excerpts (Arm A and the reuse run) against the live pages, and the content of every
one is real. Two excerpts are not exact quotes:

- **Arm A, S7** (ScienceAgentBench, `arxiv.org/html/2410.05080v2`) quotes "…than using OpenHands while costing 17
  times less…". The page says "OpenHands **CodeAct**", so the excerpt is not verbatim. The same wording appears in A's
  reference [7]. The reuse run's S15 quotes it correctly.
- **Reuse run, S11–S13** (AutoScientists) cite `arxiv.org/abs/2605.28655` but quote full-text passages that appear
  only on `arxiv.org/html/2605.28655`.

The run artifacts are left unedited.

### Decision rule (frozen)

- Q_A − Q_B = 1, which is less than 2, so the label cannot be "Autonomy helped". Q_B − Q_A = −1, so it cannot be "Autonomy did worse".
  The label is **Inconclusive**.
- The other conditions for "helped" did hold. A is never more than 1 point below B on any criterion, and A's citation
  integrity of 0.92 is at least B's 1.00 minus 0.10. Only the margin failed.
- Neither arm has a budget violation, contamination hit, or rescue intervention. The contamination and
  intervention results are attested from transcripts, not reproducible from this repo (see below).

## Measured (not scored)

Counts come from each arm's transcript, which the dispatcher read
([measurements.md addendum](artifacts/measurements.md)). They replace the log-based counts in the body of that file.

> **Attested, not reproducible.** The web and other tool-call counts, the contamination results, the intervention
> counts, and "every web call preceded by a charge" come only from the dispatcher (coder) reading the Grok Bot
> transcripts of Arm A (`sand-subagent-2958ea10-2768-7253-0783-bb4cac341fe7`) and Arm B
> (`sand-subagent-d0150782-be41-b2bf-f787-e866e74607c1`). Those transcripts and the per-call lists are **not** in
> this repo, and neither the measuring worker nor the reviewer could read them. The repo holds one cross-check: A's
> ledger has 13 web charges (5 searches and 8 fetches by their notes), consistent with A's 8 recorded sources and 8
> references. Nothing in the repo checks B's 20.

| Measure | Arm A | Arm B |
| --- | --- | --- |
| Web calls (attested) | **13** (5 WebSearch, 8 WebFetch, 0 curl) | **20** (8 WebSearch, 11 WebFetch, 1 curl) |
| Other tool calls (attested) | 17 (6 Read, 11 Shell, which includes all `lab.py` calls) | 15 (2 Read, 13 non-web Shell) |
| Total tool calls | 30 | 35 |
| Elapsed: dispatch window start (02:44:03) → `answer.md` mtime | **4.60 min** | **3.81 min** |
| Elapsed: dispatch window start → final message | ~4.92 min | ~4.27 min |
| Human interventions (attested) | 0 | 0 |
| Stop reason | Stop rule: "no open claims left (5 recorded)" after 2 of 8 cycles, 3.08 min after `init`, 13 of 40 web calls | No loop. A single pass ended by its own judgment; last web call at 02:46:39 |
| Budget (40 web, 60 min; A also 8 cycles) | Within | Within |
| Contamination (transcript grep, attested) | Clean: read only the allowed skill files and its own dirs | Clean: read only `research/SKILL.md` and its own dir |
| Tokens and money | Not measurable with our tools | Not measurable with our tools |
| Model | Not visible in the transcript | Not visible in the transcript |
| Q per web call | 1.15 | 0.70 |
| Q per minute (to `answer.md`) | 3.26 | 3.67 |

- Both arms ran as the same subagent type: a fresh-context knowledgeWork worker dispatched the same way.
- The protocol's "better but costlier" check (more than 1.5× B's web calls or time) does not apply. A's ratios are 0.65× and 1.21×.
- Arm A process checks: `validate` gave `VALID {"claim": 5, "source": 8, "finding": 10}`. `audit --observed-web 13`
  gave AUDIT OK. The 13 comes from the transcript, independent of A's ledger. Per the dispatcher's transcript read
  (attested, see above), every web call is preceded by a matching `charge web`. `knowledge_recalled` was logged at the start (the store was empty), and 5
  knowledge entries were written (2 findings, 1 lesson, 2 questions). The challenge pass was logged as P1/P3/P4 run
  sequentially in one context. An experiment step was logged as not feasible.

## Reuse run (knowledge read-back, outside the comparison)

Protocol line 117 allows this optional follow-up. It has **no control arm**. It shows that the store is read back and
used. It does not show that reuse improves quality.

- Setup: Arm A's store after Arm A had 5 entries
  ([pre-reuse snapshot](artifacts/p1-store/knowledge.pre-reuse.jsonl)). The run used a different but related
  question, which was Arm A's own stored follow-up question K-f32993ff: *On open-ended scientific research tasks, when
  tools and token budgets are matched, does a multi-agent or autonomous research scaffold beat a single tool-using
  frontier model?* Budget: 12 web calls, 4 cycles, 25 min.
- `recall` surfaced all 5 entries. `knowledge_used` was logged for 4 of them, with reasons.
- The run re-fetched the sources cited by K-adcde292 and K-1b720548 (4 distinct URLs) and re-recorded them with
  `via`. There are 6 `via` lines in [sources.jsonl](artifacts/p1-reuse/run/sources.jsonl), so citations stay
  traceable to stored knowledge.
- It applied lesson K-3bf7bfbd ("insist on matched tools and token budgets"). That lesson led it to flag that the
  strongest pro-multi-agent science result, AutoScientists on BioML-Bench, matches GPU compute but not LLM tokens.
- It used 9 of 12 web calls and 4 of 4 cycles, about 3 minutes from `init` to stop and about 4 minutes in total.
  Stop reasons: "cycle budget spent (4/4)" and "no open claims left (5 recorded)". AUDIT OK, VALID
  `{"claim": 5, "source": 15, "finding": 11}`.
- It wrote 7 new entries (2 lessons, 4 questions, 1 finding), so the store now has 12
  ([after](artifacts/p1-store/knowledge.jsonl)). Brief: [p1-reuse/run/brief.md](artifacts/p1-reuse/run/brief.md).
- **Quirk:** it loaded `research` and `adversarial-review` only after `check` had stopped the run. The challenge
  pass (logged at 02:55:31, after the stop at 02:54:59) was therefore a post-hoc review of the brief and made no web
  calls. The contract allows writing after a stop, but a challenge that cannot trigger more research is weaker than
  the one research-lab intends.

## Deviations from the protocol

1. **Worker type.** Both arms ran as fresh-context knowledgeWork subagents, not "fresh executor workers"
   (protocol step 3). A new executor would have inherited the dispatcher's conversation, which contains the protocol,
   rubric, and both prompts. Both arms were dispatched identically.
2. **One manual redaction outside the regex scan.** The protocol regex had 24 hits (15 in A, 9 in B). All were
   topic vocabulary such as "token budget" and "baseline", plus one URL fragment, so none was redacted. Separately,
   A's persona ids `P1/P3/P4` were replaced with `[redacted]`, because the scorer can read protocol.md at the freeze
   SHA and it names them as Arm A's challenge pass. See [key.txt](artifacts/key.txt).
3. **The blinding question was asked only after the scores were recorded.** The question hints that one arm is more
   elaborate, so it was held back until scoring was done. The pre-question scores are kept at
   [blind/scores.pre-blinding-check.md](artifacts/blind/scores.pre-blinding-check.md), and no score changed.
4. **B's self-tally is unreliable.** `calls.log` lists 22 calls plus 2 correction notes, while the transcript shows
   20. B logged two fetches before making them and then never made them (`cdn.openai.com/deep-research-faq.pdf`,
   `github.com/huggingface/blog/blob/...`), and it logged PDF URLs where it actually fetched the HTML versions.
5. **Who measured.** The measuring worker had no way to read transcripts, so its counts came from logs. The
   transcript-based counts above come from the dispatcher reading both transcripts.
6. **Blinding partly failed.** Sol correctly guessed that X was the more elaborate workflow (Arm A), with medium
   confidence. The tells were the leftover stage description "Challenge review of this synthesis (sequential
   [redacted] in one context, not independent reviewers)" and the visible redaction itself. A's
   "not feasible here" line was a weaker tell. Without that sentence Sol would say "can't tell". Scores were written
   before the question, but Sol may have inferred the arm while scoring. The root cause was in the skill, not the
   prompt. research-lab/SKILL.md at the freeze told the agent to state the sequential challenge "in the brief".
   arm-a-prompt.md said not to mention process, and A followed the skill. This was fixed after evaluation (`38fb8e2`).
7. **Conductor role and conflict of interest (implementer).** protocol.md "Setup and run (conductor)" assigns setup
   and dispatch to a conductor, and `key.txt` is headed "Conductor-only". In fact one agent, **coder**, did all of
   it: it built the system under test (the autonomy contract and research-lab), dispatched both arms, held the key,
   made the redaction, and produced the only transcript-based counts, contamination results, and intervention counts.
   No independent party checked those. The implementer acting as conductor and measurer is a conflict of interest.
8. **Conflict of interest (scorer).** Sol was both the blind scorer of T15 and the reviewer of the PR that reports
   T15, which includes Sol's own scores and blinding guess. Sol disclosed this in the review and did not recuse.
9. **Measurement modified the live Arm A run.** The measuring worker ran `lab.py validate` on the live
   `p1/run` directory. That appended one `validation` event at 02:49:39 to `log.jsonl`, after A's own at
   02:48:16. A pre-measurement snapshot exists outside the repo (`/workspace/lab-runs/t15/p1-run-snapshot-pre-measurement.tar`,
   sha256 `079cd0d7…a1ed`). The ledger was not touched, and audit results are unaffected.

## Tradeoffs

- **Cost vs structure.** A used 0.65× the web calls (13 vs 20) but took 1.21× the time (4.60 vs 3.81 min to the answer).
  The extra time goes into structure: claims, ledger, findings, validation, and a knowledge store. That structure is
  what makes A auditable and makes its knowledge reusable, but it was not worth 2 rubric points on this question.
- **Where each arm scored.** A was more cautious and cited more primary sources, which won it source quality and
  usefulness. Its one overreaching synthesis line cost it factual correctness. B was broader and stayed exactly
  right, but it leaned on comparisons against baselines without tools.
- **Enforcement is cooperative.** `lab.py` refuses charges once a limit is hit, but only if the agent calls it.
  Nothing stops an agent from fetching without charging. The protection is a post-run `audit` that checks the
  hash-chained ledger against counts taken from the transcript. Here that matched (13 = 13). Without a transcript,
  the audit can only check the ledger against itself. The chain is unkeyed, so a deliberate rewrite that re-chains the
  ledger passes everything except an outside count.
- **Cost is proxied.** Dollar and token cost was not measured. "Quality per dollar" is proxied only by web calls
  (Q per web call 1.15 vs 0.70) and minutes (Q per minute 3.26 vs 3.67), and those two point in opposite directions.

## Failed approaches

While building the slice (phase 1; details in
[design-notes.md](../../../autonomy-contract/references/design-notes.md)):

- **The hash chain alone missed an edit to the last ledger entry.** The fix: each charge logs the new chain head, and `audit` compares it.
- **Stored knowledge had duplicate sources and unresolvable relative `file:` URLs.** The fix: de-duplicate, and rewrite the URLs relative to the store.
- **The stop message said "all N claims resolved" when one claim was `unresolved`.** It was reworded.
- **The interactive first smoke pass stopped matching the code after the fixes.** It was replaced by the replayable `examples/smoke/smoke.sh`.
- **OpenAI's Harness Engineering page could not be fetched** (403, then a JS challenge). Its lessons come from search excerpts and are labeled that way.

During the experiment:

- **Token-level redaction does not work as a blinding method.** Removing `P1/P3/P4` left the sentence that describes
  the stage, and the `[redacted]` marker was itself a tell. Stage descriptions need to be scrubbed or prevented, not
  just tokens.
- **B's self-kept call log** (see deviation 4). Logging a call before making it records intent, not what happened.
- **Arm A's ad-hoc ledger-count script printed `web_charges 0`.** It filtered ledger lines on a field that does not
  hold the resource. Charges are `{"kind": "charge", "what": "web", "n": 1}`, and the field names were not documented in
  the skill. A's own `audit` and `check` reported the right totals. **Doc fix:** one line in
  [autonomy-contract/SKILL.md](../../../autonomy-contract/SKILL.md) (Budget) now names the ledger fields and points to
  `audit`'s `used` totals.
- **Log-based measurement without transcripts** produced a wrong web count for B (22 instead of 20) and could not
  check contamination. Transcript access was required.
- **Re-verifying with `validate` changes the run.** It appends a `validation` event to `log.jsonl`. The measuring
  worker ran it on the live Arm A run (deviation 9). Re-check on a copy.

## Limitations

- n = 1 per arm and one question. The 1-point gap is within noise: a second run or a second scorer could flip any
  single criterion.
- One scorer (Sol), whose blinding partly failed (medium-confidence correct guess).
- Tokens and money were not measured, so "cheaper" here means web calls and wall-clock time only.
- The model is unpinned and not visible. Both arms used the same worker type, but sameness of the model is assumed,
  not verified.
- Budget enforcement is cooperative, with a post-run audit. It is not a sandbox. At the freeze, `charge --n` also
  accepted refunds (n < 1), and marking claims `unresolved` could end a run or defeat the stall stop. Neither
  happened in these runs (all charges have n = 1). Both were fixed after evaluation.
- The transcript-based numbers are attested by one party with a conflict of interest (deviations 7–8) and cannot be
  reproduced from this repo.
- The reuse run has no control. It shows read-back and use of stored knowledge, not a quality gain.
- Both arms finished in under 5 minutes against a 60-minute budget. This question did not stress the cycle loop or
  the stop rule's stall and time branches.

## Next steps

1. **Blinding:** fix the source, which is the skill. research-lab/SKILL.md no longer puts the challenge-pass
   description in the brief (`38fb8e2`). Next time, also check every skill an arm loads for instructions to describe
   the process in the output. Prefer whole-sentence scrubbing to token redaction, and avoid visible `[redacted]` markers.
2. **Multiple runs per arm** (and more than one question) so that a gap can be told apart from run-to-run variance.
3. **A second, independent scorer**, with agreement reported.
4. Count web calls from the harness or transcript by default, and drop self-kept tallies like `calls.log`. Commit the
   extracted per-call list, so the counts are checkable, and have someone other than the implementer conduct and measure.
5. Consider making the research-lab challenge pass a gate that runs before `check` can stop the run, so a challenge
   can still trigger more research (the reuse-run quirk).
