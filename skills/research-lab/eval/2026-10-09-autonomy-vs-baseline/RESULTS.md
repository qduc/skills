# Experiment 001 — research-lab vs single well-prompted model

**Question:** "What evidence shows that autonomous research agents outperform a
single well-prompted model on difficult technical research tasks?"
**Date:** 2026-10-09. **Model:** same model (Claude Opus 5.5) in every arm, each
started cold as an isolated subagent. **Budget:** 20 searches, 20 fetches,
45 minutes per tool-using arm. No paid APIs.

## Bottom line

On this one question, the autonomy harness **did not beat** a single
well-prompted, tool-using agent on research quality. After one improvement
iteration it **tied** it on every rubric score (5/5/5) but was still ranked
second by a blind grader, because the baseline covered slightly more ground.
The harness's measurable wins are elsewhere: every quote is mechanically
traceable to a saved snapshot, termination is predictable and recorded,
wall-clock time was lower, findings are reusable, and failures turn into
verifier checks. Factual correctness was ~90%+ for every tool-using arm, so it
did not separate them. With n=1 per arm none of these differences are
statistically meaningful; this is a working vertical slice plus a first
measurement, not proof.

## Arms

| Arm | What it is |
|---|---|
| **A** lab v1 | `research-lab` skill + `lab.py` harness (ledger, budget meter, verifier, KB) |
| **A2** lab v2 | Same after one improvement-loop change: breadth scan before decomposition + final gap check, both enforced by the verifier |
| **B** single agent | One strong prompt: decompose, prefer primary sources, seek counter-evidence, quote, state uncertainty. Same tools and budget. No harness. |
| **C** no tools | Same strong prompt, answered from model knowledge, no browsing |

## Results

Blind grading: a separate grader agent received anonymized, shuffled reports
(lab ledgers stripped so formats matched), picked the ~8 most decision-relevant
claims per report and re-fetched the original sources to check them. Round 1
graded A/B/C; round 2 (a fresh grader) graded A/A2/B. Raw grades:
`blind/round*/grades.json`; label keys: `blind/round*/key.txt`.

| Metric | A lab v1 | A2 lab v2 | B single agent | C no tools |
|---|---|---|---|---|
| Claims checked: correct / minor error / wrong | R1 8/1/0 · R2 8/0/0 | 7/1/0 | R1 10/1/0 · R2 8/2/0 | 10/1/0 |
| Bad citations (wrong/nonexistent) | 0 | 0 | 0 | 2 |
| Source quality (1–5) | 5 · 4 | 5 | 5 · 5 | 3 |
| Contradiction detection (1–5) | 4 · 4 | 5 | 5 · 5 | 4 |
| Useful findings (1–5) | 3 · 3 | 5 | 5 · 5 | 4 |
| Blind rank | 2nd of 3 · 3rd of 3 | 2nd of 3 | 1st · 1st | 3rd of 3 |
| Quotes mechanically matched to snapshots | 31/31 | 39/39 | n/a (self-reported "near-verbatim") | n/a |
| Key claims marked contested/unresolved | 0 of 6 | 1 of 7 | (prose) | (prose) |
| Searches / fetches used | 11 / 13 | 14 / 16 | 12 / 18 | 0 / 0 |
| Subagent tokens | 99.8k | 114.1k | 88.6k | 69.2k |
| Wall-clock | 10.2 min | 7.9 min | 13.1 min | 1.5 min |
| Human interventions during run | 0 | 0 | 0 | 0 |
| Terminated by | goal answered, budget left | goal answered, gap check empty | self-judged | n/a |

"R1 · R2" = round 1 grade · round 2 grade for the arms graded twice.
Dollar cost was not metered (runs used this session's model; no paid API keys);
tokens are the cost proxy. Grading cost an extra ~100k tokens per round.

## What we learned

1. **Correctness did not separate the arms.** All tool-using arms were ~90%+
   correct on independently re-checked claims, with no wrong claims. Even the
   no-tools arm scored well on correctness but produced 2 bad citations, which
   is where browsing pays off.
2. **The v1 lab was narrow, and the event log showed why.** It wrote all 6 key
   claims at 19:47:35, before its first search, and stopped once those settled,
   at 10 of 45 minutes with half the budget unused. Pre-committing claims from
   model priors made the run thorough on what it already believed and blind to
   other evidence lines (DeepResearch Bench, scaffold ablations, AI-scientist
   evaluations). All 6 claims ended "supported".
3. **One improvement-loop change fixed most of it.** Requiring a recorded
   breadth scan before decomposition and a gap check after it raised usefulness
   from 3 to 5 and contradiction detection from 4 to 5. It also produced the
   first honestly `contested` claim, with fewer minutes and modestly more
   tokens. The new verifier check fails the v1 run, so the fix guards against
   regression.
4. **The verifier caught a real fabrication pattern.** A2 rebuilt a source
   passage from memory once, the quote check failed it, and the agent re-did
   the snapshot (lesson recorded in `arms/A2-lab-v2/lessons.md`). Both lab runs
   independently wrote this lesson, so it was promoted into `SKILL.md`. The
   baseline openly says its quotes came through a summarizing fetch tool and
   are only "near-verbatim"; nothing checks them.
5. **The baseline is strong.** A single agent with a good prompt and the same
   tools already does decomposition, counter-search and uncertainty well. The
   harness adds auditability and predictability more than raw quality. This
   matches the content of the research itself: at matched budgets,
   architecture gains are small or contested.

## Success criteria

| Criterion | Status | Evidence |
|---|---|---|
| Complete task with minimal supervision | Met | 0 interventions in A and A2; both ran init→learn→finish unattended |
| Traceable evidence for important claims | Met for lab | 39/39 quotes matched snapshots; claim ledger in `findings.md` |
| Contradictions and uncertainty visible | Met | A2: 1 contested claim plus a contradictions section; grader CD 5/5 |
| Respects budget, terminates predictably | Met | Meter + `STOPPED`/`FINISHED` status; unit test proves exit 3 and refusal after exhaustion |
| Findings reusable | Met (mechanism) | `kb/claims.jsonl` (verified claims with quotes), `questions.jsonl`, `lessons.md`; `kb-search` returns them. A later run reusing the KB has **not** been measured yet |
| Measure whether autonomy improves outcomes | Met (measured; answer: not on quality, n=1) | This file |

## Threats to validity

- **n=1 per arm, one question, two graders** (one per round). Rankings could
  flip on rerun. Round 1 and round 2 graders disagreed on A's source quality
  (5 vs 4).
- **The question favors the baseline's strengths**: a well-known literature
  where the model's priors are good. Harness value should grow on less familiar
  topics and longer budgets; that is untested.
- **The same model family wrote, ran and graded everything.** Blinding was
  imperfect: C's text marks memory-based details, and report length differs.
- **Snapshots come through WebFetch**, which is model-processed (the shell
  cannot reach the web). The quote check therefore proves consistency with
  what was fetched, not with the original bytes. The grader's independent
  re-fetch is what checks source fidelity.
- **A2 is the v1 skill plus a change chosen after seeing v1's grades.** Its
  improvement over A is partly in-sample.
