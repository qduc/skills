<!-- Arm B (baseline: one well-prompted pass). Paste everything below the
line, verbatim, as the whole task for a fresh executor worker. Do not add
context. -->

---

Research task. Work alone and unattended. Nobody will answer questions, so do not ask any; if something blocks you, say so under "Uncertainty and gaps" and finish.

**Question:** "What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?"

**Budget (hard limits):**

- At most 40 web calls. Each WebSearch call, each WebFetch call, and each shell command that fetches from the internet (for example curl) counts as one.
- At most 60 minutes of wall-clock time from your first action. Stop searching at 50 minutes so you have 10 minutes to write.
- Keep a tally so you stay within budget. Run `date -Iseconds` as your first action and write it to `/workspace/lab-runs/t15/p2/calls.log`. Before each web call, append one line to that file: `<time> <tool> <query or URL>`. Stop searching when the file has 40 call lines or 50 minutes have passed.

**Tools.** WebSearch, WebFetch, and Shell only. Shell may be used for notes, local checks, and curl for public pages (each fetch counts as a web call). Do not use a browser, other agents or subagents, MCP tools (X, GitHub, or others), or messages to anyone.

**Files.** You may read `/workspace/lab-runs/t15/skills/skills/research/SKILL.md` (a research method you may follow) and your own directory `/workspace/lab-runs/t15/p2/`. Do not open any other file under `/workspace` or `/home/box`: some of them contain material about this question and would contaminate the result.

**How to research (one careful pass):**

1. Pin down the question. Define "autonomous research agent", "a single well-prompted model", "difficult technical research tasks", and what would count as evidence that one outperforms the other.
2. Search broadly first, then narrow. Prefer primary sources for anything decisive: papers with methods and numbers, benchmark reports, first-party engineering write-ups with data. Use secondary sources (news, blogs, summaries) to find primaries, not as proof.
3. Open and read the original for every claim you rely on. A search snippet is not evidence. Copy the passage you rely on verbatim.
4. Look actively for counter-evidence: cases where a single model matches or beats agents, cost and token trade-offs, flawed or unfair comparisons, results that did not replicate.
5. Compare like with like: tasks, metrics, models, and budgets. Do not count mentions as votes; several articles repeating one study are one piece of evidence.
6. Separate what sources report from your own inference, and set each confidence by the strength of the evidence, not by how many sources agree.

**Output.** Write `/workspace/lab-runs/t15/p2/answer.md` in exactly this format. Keep the body under 1,500 words, excluding references. Every URL in it must be a page you opened. Do not mention your process, tools, or budget.

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

**Final message:** the path of `answer.md` and how many web calls you made.
