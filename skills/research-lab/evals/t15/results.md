# T15 results: autonomy contract vs a single well-prompted model

**Headline: INCONCLUSIVE.** Arm A (autonomy contract) scored 15/16 and Arm B (single well-prompted pass) scored 14/16.
Under the frozen decision rule a difference of at least 2 points is needed, so a 1-point gap does not count.
A used 0.65× B's web calls and took 1.21× B's time. This is directional at best: one question, one run per arm,
one scorer, an unpinned model, and a blinding check that partly failed.

Protocol: [protocol.md](protocol.md), frozen at `54d86025aa213040592cd082b5b07146451e0dd6`. The run happened on
2026-10-09, starting 02:44 ICT. The arms ran concurrently. Raw records are in [artifacts/](artifacts/README.md).

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

### Decision rule (frozen)

- Q_A − Q_B = 1, which is less than 2, so the label cannot be "Autonomy helped". Q_B − Q_A = −1, so it cannot be "Autonomy did worse".
  The label is **Inconclusive**.
- The other conditions for "helped" did hold. A is never more than 1 point below B on any criterion, and A's citation
  integrity of 0.92 is at least B's 1.00 minus 0.10. Only the margin failed.
- Neither arm has a budget violation, contamination hit, or rescue intervention.

## Measured (not scored)

Counts come from each arm's transcript, which the dispatcher read
([measurements.md addendum](artifacts/measurements.md)). They replace the log-based counts in the body of that file.

| Measure | Arm A | Arm B |
| --- | --- | --- |
| Web calls | **13** (5 WebSearch, 8 WebFetch, 0 curl) | **20** (8 WebSearch, 11 WebFetch, 1 curl) |
| Other tool calls | 17 (6 Read, 11 Shell, which includes all `lab.py` calls) | 15 (2 Read, 13 non-web Shell) |
| Total tool calls | 30 | 35 |
| Elapsed: dispatch window start (02:44:03) → `answer.md` mtime | **4.60 min** | **3.81 min** |
| Elapsed: dispatch window start → final message | ~4.92 min | ~4.27 min |
| Human interventions | 0 | 0 |
| Stop reason | Stop rule: "no open claims left (5 recorded)" after 2 of 8 cycles, 3.08 min after `init`, 13 of 40 web calls | No loop. A single pass ended by its own judgment; last web call at 02:46:39 |
| Budget (40 web, 60 min; A also 8 cycles) | Within | Within |
| Contamination (transcript grep) | Clean: read only the allowed skill files and its own dirs | Clean: read only `research/SKILL.md` and its own dir |
| Tokens and money | Not measurable with our tools | Not measurable with our tools |
| Model | Not visible in the transcript | Not visible in the transcript |
| Q per web call | 1.15 | 0.70 |
| Q per minute (to `answer.md`) | 3.26 | 3.67 |

- Both arms ran as the same subagent type: a fresh-context knowledgeWork worker dispatched the same way.
- The protocol's "better but costlier" check (more than 1.5× B's web calls or time) does not apply. A's ratios are 0.65× and 1.21×.
- Arm A process checks: `validate` gave `VALID {"claim": 5, "source": 8, "finding": 10}`. `audit --observed-web 13`
  gave AUDIT OK, and the 13 comes from the transcript, independent of A's ledger. Every web call in the transcript is
  preceded by a matching `charge web`. `knowledge_recalled` was logged at the start (the store was empty), and 5
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
   before the question, but Sol may have inferred the arm while scoring.

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
  the audit can only check the ledger against itself.

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
- **Re-verifying with `validate` changes the run.** It appends a `validation` event to `log.jsonl`. Re-check on a copy.

## Limitations

- n = 1 per arm and one question. The 1-point gap is within noise: a second run or a second scorer could flip any
  single criterion.
- One scorer (Sol), whose blinding partly failed (medium-confidence correct guess).
- Tokens and money were not measured, so "cheaper" here means web calls and wall-clock time only.
- The model is unpinned and not visible. Both arms used the same worker type, but sameness of the model is assumed,
  not verified.
- Budget enforcement is cooperative, with a post-run audit. It is not a sandbox.
- The reuse run has no control. It shows read-back and use of stored knowledge, not a quality gain.
- Both arms finished in under 5 minutes against a 60-minute budget. This question did not stress the cycle loop or
  the stop rule's stall and time branches.

## Next steps

1. **Blinding:** forbid stage and process descriptions in arm prompts, or scrub whole sentences that describe stages
   (not just tokens), before scoring. Avoid visible `[redacted]` markers.
2. **Multiple runs per arm** (and more than one question) so that a gap can be told apart from run-to-run variance.
3. **A second, independent scorer**, with agreement reported.
4. Count web calls from the harness or transcript by default, and drop self-kept tallies like `calls.log`.
5. Consider making the research-lab challenge pass a gate that runs before `check` can stop the run, so a challenge
   can still trigger more research (the reuse-run quirk).
