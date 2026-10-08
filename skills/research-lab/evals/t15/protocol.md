# T15 experiment protocol (frozen)

Frozen before either arm runs. The commit that adds this directory is the
protocol-freeze commit; its SHA and time are recorded in the PR. Nothing in
this directory changes after that commit. Any deviation during the run is
recorded under "Deviations" in the evaluation, not fixed here.

**Experiment arms must not read this file.** It contains the rubric.

## Question

> What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?

Both arms get exactly this text.

## Arms

| | Arm A: autonomous | Arm B: baseline |
| --- | --- | --- |
| Prompt | [arm-a-prompt.md](arm-a-prompt.md) | [arm-b-prompt.md](arm-b-prompt.md) |
| Method | autonomy-contract + research-lab: claims, budget ledger, cycles, challenge pass (adversarial-review P1/P3/P4), experiment step when feasible, citation validation, knowledge store | One well-prompted pass. The prompt asks for primary sources, reading originals, and counter-evidence, and allows the research skill. No contract loop, no ledger, no knowledge store, no separate challenge pass. |
| Output | `/workspace/lab-runs/t15/p1/answer.md` (copy of `p1/run/brief.md`) | `/workspace/lab-runs/t15/p2/answer.md` |
| Working files | `/workspace/lab-runs/t15/p1/run/`, store `/workspace/lab-runs/t15/p1-store/knowledge.jsonl` (starts empty) | `/workspace/lab-runs/t15/p2/calls.log` |
| Skills checkout | `/workspace/lab-runs/t15/skills`, detached at the freeze SHA | same checkout; reads only `skills/research/SKILL.md` |

The output paths use neutral names (`p1`, `p2`) so the paths do not reveal the arm.

Both prompts require the same answer format (the brief format in
[research-lab](../../SKILL.md)) and the same 1,500-word cap. Neither prompt
mentions the other arm, the comparison, or the rubric.

### Identical conditions

| Condition | Both arms |
| --- | --- |
| Model | "The same executor model": each arm is a fresh Grok Bot executor worker dispatched the same way. We cannot pin or observe the underlying model name. If the platform shows one, record it; otherwise say it is unknown. |
| Tools | WebSearch, WebFetch, and Shell on the box. No browser, no subagents or other agents, no MCP tools, no messages. |
| Web budget | 40 web calls. One WebSearch, one WebFetch, or one shell command that fetches from the internet each count as one. |
| Time budget | 60 minutes wall clock from the arm's first action; both stop researching at 50 minutes to write. |
| Cycle budget | Arm A only: 8 cycles, stall stop after 2 cycles with no claim resolved. Arm B has no loop. |
| Prior knowledge | Arm A's store starts empty. Neither arm may read other files on the box. Both may carry whatever the model already knows. |
| Human input | None after dispatch. |
| Timing | Dispatch both arms in the same window (concurrently, or back to back on the same day). Record which. |

## Setup and run (conductor)

1. Create the frozen checkout once (or confirm it exists at the freeze SHA):
   `git -C /workspace/qduc-skills worktree add --detach /workspace/lab-runs/t15/skills <FREEZE_SHA>`
   and `git -C /workspace/lab-runs/t15/skills rev-parse HEAD` must print the freeze SHA.
2. `mkdir -p /workspace/lab-runs/t15/p1 /workspace/lab-runs/t15/p2`. Do not create the store; Arm A's `init` does.
3. Dispatch each arm as a fresh executor worker whose entire task is the text below the line in its prompt file. Record each dispatch time in ICT.
4. Send no messages to either arm. Any message after dispatch is a human intervention (see below).
5. When each arm finishes, record its end time: its final message time and the mtime of its `answer.md`.

## Measured, not scored

These are counted from artifacts, not judged.

| Measure | How |
| --- | --- |
| Human interventions | Count every message or action by a human or the conductor directed at an arm after dispatch. Tag each one rescue, correction, investigation, or approval (acceptance-gate tags). Target: 0. |
| Web calls | Count WebSearch, WebFetch, and internet-fetching shell commands from each arm's transcript. Report by type. For Arm A, also run `lab.py audit /workspace/lab-runs/t15/p1/run --observed-web <count>`; a mismatch is reported as a ledger failure. For Arm B, compare with `calls.log`. |
| Other tool calls | Count all other tool calls by type from each transcript (Arm A's `lab.py` calls appear here). |
| Elapsed time | Dispatch time to `answer.md` mtime, and to the final message, in minutes. |
| Tokens and money | Not measurable with our tools: no per-worker token usage is exposed, and no API is billed per run. Say exactly that. If the platform does show a usage figure, record it with where it came from. |
| Budget adherence | Over 40 web calls or 60 minutes is a violation. The arm is still scored, and the violation is reported next to its scores. |
| Arm A process checks | `lab.py validate` prints VALID; `audit` prints AUDIT OK with the observed count; the run ended by the stop rule (reason recorded); knowledge entries written; `knowledge_recalled` logged at the start. |
| Contamination | Grep both transcripts for reads outside the allowed paths (for example `/workspace/research`, `/workspace/review-scratch`, `references/design-notes.md`, `evals/t15`). Report any hit. |

## Blind scoring

1. **Relabel.** After both arms finish, flip a coin with
   `python3 -c "import secrets; print(secrets.randbelow(2))"` and record the output and time in `/workspace/lab-runs/t15/key.txt` (outside `blind/`). `0` means Arm A becomes X and Arm B becomes Y; `1` means the reverse.
2. **Leak scan.** Search each answer for words that reveal the workflow:
   `grep -n -i -E 'ledger|cycle|knowledge store|lab\.py|autonomy|contract|budget|run dir|\b[CFS][0-9]+\b|arm [ab]|baseline' answer.md`.
   Replace only a revealing token with `[redacted]`. Record each redaction in `key.txt`. Make no other edits.
3. **Copy** the answers to `/workspace/lab-runs/t15/blind/X.md` and `Y.md`.
4. **Score.** Send the scorer (Sol) [scorer-brief.md](scorer-brief.md) and the freeze SHA, nothing else about the runs. Sol did not produce either answer. Sol writes `blind/scores.md` and records a blinding guess.
5. **Unblind** only after `scores.md` exists. Then attach the measured data.

## Rubric

The full anchors are in [scorer-brief.md](scorer-brief.md). In summary, four
blind criteria, each scored 0–4:

| Criterion | What 4 looks like | Notes |
| --- | --- | --- |
| Factual correctness | No errors found in the spot-check or a careful read | Any Misattributed or Fabricated citation caps it at 1 |
| Source quality | Decisive claims rest on primary sources, with dates | |
| Contradiction detection and uncertainty | Two or more cited conflicts, each explained; unknowns stated | |
| Useful findings | Specific, decision-relevant findings that answer the question; useful follow-ups | |

Plus **citation integrity** from the spot-check: (Supported + 0.5 × Partial) ÷
(checked − Unreachable), with up to 6 pairs per answer (4 random by a seed
derived from the freeze SHA, plus the 2 most decisive).

Human intervention, cost, and elapsed time are the measured rows above. They
are reported next to the scores and are not folded into a single number.

## Decision rule

Let Q = the sum of the four blind scores (0–16).

| Label | Condition |
| --- | --- |
| **Autonomy helped** | Q_A − Q_B ≥ 2, A is not more than 1 point below B on any criterion, and A's citation integrity ≥ B's − 0.10 |
| **Autonomy did worse** | Q_B − Q_A ≥ 2 |
| **Inconclusive** | anything else |

- If the label is "Autonomy helped" but Arm A used more than 1.5× Arm B's web calls or elapsed time, the headline must say "better but costlier". Report Q per web call and Q per minute for both arms either way.
- An arm with a budget violation, contamination hit, or rescue intervention keeps its scores, but the headline names the problem next to the label.
- Whatever the label, the result is **directional at best**: one question, one run per arm, one scorer, and an unpinned model. Say so in the headline, not in a footnote.
- No re-runs to change a result. A re-run is allowed only if an arm crashed before writing `answer.md`, and the crashed attempt is reported.

## What this experiment does not test

- Knowledge reuse. Arm A's store starts empty. Read-back is shown by the smoke test (`skills/autonomy-contract/examples/smoke`). An optional follow-up run that reuses Arm A's store is outside this comparison.
- Parallel workers. Neither arm uses them.
- Variance. With one run per arm, a 1-point difference on a criterion is within what a second run or a second scorer could flip.
