<!-- For the blind scorer (Sol). Paste everything below the line once both
answers have been relabeled X and Y. Send nothing else about the runs. -->

---

Blind scoring task. Two answers to the same research question are at `/workspace/lab-runs/t15/blind/X.md` and `/workspace/lab-runs/t15/blind/Y.md`. They were produced by two different workflows. You are not told which is which, and you did not produce either.

**Question:** "What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?"

**Do not open** anything under `/workspace/lab-runs/t15/` other than the `blind/` directory, any branch or PR about an "autonomy contract" or "research lab", or any transcript of the runs, until you have written your scores. The rubric is in this message; you need nothing else.

## 1. Citation spot-check (do this first)

For each answer separately:

1. Number every (statement, citation) pair in "Key findings" and "Contradictions and counter-evidence", in reading order: 1..N. A statement with two citations is two pairs.
2. Select 4 pairs at random with the seed below, then add the 2 pairs you judge most decisive for the answer's conclusion (if already selected, take the next most decisive). That gives up to 6 per answer. Seeds: X uses `S`, Y uses `S+1`, where `S = int(<first 8 hex chars of the protocol-freeze commit SHA>, 16)`; the conductor gives you the SHA.
   `python3 -c "import random; r=random.Random(SEED); print(sorted(r.sample(range(1, N+1), min(4, N))))"`
3. For each selected pair, fetch the cited URL yourself (WebFetch; if blocked, curl; if still blocked, a browser). Find the quoted excerpt on the page and judge whether the page supports the statement. Label it:
   - **Supported**: the page says it, or clearly implies it.
   - **Partial**: the page supports a weaker, narrower, or differently scoped statement.
   - **Not supported**: the page is reachable and does not support it.
   - **Misattributed**: the page exists but the quoted excerpt is not on it, or the source is not what the reference says it is.
   - **Fabricated**: the page or document does not exist.
   - **Unreachable**: all three fetch methods failed. Not counted as fabricated; reported separately.
4. Citation integrity = (Supported + 0.5 × Partial) ÷ (checked − Unreachable).

## 2. Score each answer, 0–4 per criterion

Score X and Y side by side, criterion by criterion. Use the anchors. Half points are not allowed.

**Factual correctness**
- 4: No factual errors found in the spot-check or a careful read. Numbers, dates, and attributions are right.
- 3: One minor error that does not affect any finding.
- 2: One material error (it changes a key finding), or two or more minor errors.
- 1: Several material errors, or the conclusion rests on a wrong claim.
- 0: The central conclusion is wrong.
- Any Misattributed or Fabricated citation caps this score at 1.

**Source quality**
- 4: Decisive claims rest on primary sources (papers with methods and numbers, benchmark reports, first-party engineering write-ups with data). Secondary sources only for context. Dates given.
- 3: Mostly primary; one decisive claim rests on a secondary source.
- 2: Several decisive claims rest on secondary summaries (news, blogs, vendor marketing) where primaries existed.
- 1: Mostly secondary or low-quality sources (content farms, unattributed pages).
- 0: No usable sources.

**Contradiction detection and uncertainty**
- 4: Surfaces two or more substantive conflicts or pieces of counter-evidence, each cited, with a plausible reason for the disagreement (scope, measurement, setting, cost). States what is unknown and what would change the answer.
- 3: Surfaces at least one substantive, cited conflict and explains it. Uncertainty is explicit.
- 2: Limitations are generic, or a conflict is mentioned without citation or explanation.
- 1: One-sided. Uncertainty is boilerplate.
- 0: Presents contested claims as settled.

**Useful findings**
- 4: Directly answers "what evidence shows…". Findings are specific (task, metric, size of effect, setting, cost), separate evidence from inference, and the follow-up questions would change a decision.
- 3: Answers the question with specific findings; minor gaps.
- 2: Partly answers. Findings are vague or not tied to difficult technical research tasks.
- 1: Mostly generic or off the question.
- 0: Does not answer.

## 3. Write your result

Write `/workspace/lab-runs/t15/blind/scores.md` with:

```markdown
| Criterion | X | Y | One-line reason per answer |
| --- | --- | --- | --- |
| Factual correctness | | | |
| Source quality | | | |
| Contradiction detection and uncertainty | | | |
| Useful findings | | | |
| Total (0–16) | | | |

## Citation spot-check
| Answer | # | Statement (short) | URL | Label | Note |
| --- | --- | --- | --- | --- | --- |

Citation integrity: X = …, Y = …   (Unreachable: X = …, Y = …)

## Blinding check
Which answer do you think came from the more elaborate, multi-step workflow? X / Y / can't tell. Confidence (low/medium/high), and what gave it away.
```

Then report back with the path. Do not edit X.md or Y.md.
