<!-- Arm A (autonomous). Paste everything below the line, verbatim, as the
whole task for a fresh executor worker. Do not add context. -->

---

Research task. Work alone and unattended. Nobody will answer questions, so do not ask any; if something blocks you, say so under "Uncertainty and gaps" and finish.

**Question:** "What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?"

**Method.** Follow the autonomy contract and its research application, from the frozen skills checkout at `/workspace/lab-runs/t15/skills`:

1. Read `skills/autonomy-contract/SKILL.md` and `skills/research-lab/SKILL.md` first.
2. Load `skills/research/SKILL.md`, `skills/adversarial-review/SKILL.md` (plus the one reference file it names for your artifact type), and `skills/investigation/SKILL.md` only when research-lab tells you to.
3. Use `LAB="python3 /workspace/lab-runs/t15/skills/skills/autonomy-contract/scripts/lab.py"`. Start with exactly:

```sh
$LAB init /workspace/lab-runs/t15/p1/run --goal "What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?" --store /workspace/lab-runs/t15/p1-store/knowledge.jsonl --max-cycles 8 --max-web 40 --max-minutes 60 --max-stall 2 --reserve-minutes 10
```

**Budget (hard limits, set by the init command above; never raise them):**

- At most 40 web calls. Each WebSearch call, each WebFetch call, and each shell command that fetches from the internet (for example curl) counts as one. Run `$LAB charge ... web` before every one of them.
- At most 60 minutes of wall-clock time from `init`. The stop rule stops you at 50 minutes so you have 10 minutes to write the brief.
- At most 8 cycles. Run `$LAB charge ... cycle` at the start of each.
- Stop researching as soon as `charge` exits 3 or `check` exits 10. After that, only finish: write the brief, validate, audit.

**Tools.** WebSearch, WebFetch, and Shell only. Shell may run `lab.py`, local experiments, and curl for public pages (each fetch counts as a web call). Do not use a browser, other agents or subagents, MCP tools (X, GitHub, or others), or messages to anyone.

**Files.** Read only the skill files named above and your own directories `/workspace/lab-runs/t15/p1/` and `/workspace/lab-runs/t15/p1-store/`. Do not open any other file under `/workspace` or `/home/box`, including other files in the skills checkout: some of them contain material about this question and would contaminate the result.

**Output.**

1. Write the brief described in research-lab to `/workspace/lab-runs/t15/p1/run/brief.md`. Write it for a reader who wants conclusions: do not mention your process, tools, budget, ledger, cycles, or internal claim, finding, or source ids. Cite with the numbered references the format specifies.
2. Run `$LAB validate /workspace/lab-runs/t15/p1/run` and fix every ERROR line. Then run `$LAB audit /workspace/lab-runs/t15/p1/run`.
3. Copy the brief to `/workspace/lab-runs/t15/p1/answer.md`.

**Final message:** the path of `answer.md`, the output of the `audit` command, and how many web calls you made.
