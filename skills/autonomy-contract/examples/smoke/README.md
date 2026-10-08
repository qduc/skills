# Smoke test: the contract machinery on a small git question

This is not research output. It shows that the helper does what the contract
says, on a question unrelated to any experiment: "Does `git worktree` share
hooks between worktrees?"

Re-run it with `./smoke.sh` (needs network for 3 fetches of git-scm.com, plus
git and python3). The script replays the research decisions an agent made in an
interactive first pass. The fetches, the excerpt checks against the fetched
pages, and the two local git experiments are real. Every step states the exit
code it expects, so the script fails if the behaviour changes.

| What it shows | Where to look in `transcript.log` |
| --- | --- |
| The budget refuses a 4th web call with exit 3 | `REFUSED web: web limit reached: 3 used + 1 requested > 3` |
| The stop rule ends run 1 (budget spent) and run 2 (no open claims) | the two `STOP …` lines, exit 10 |
| Citation validation catches an injected bad source id and an unrecorded URL | `ERROR finding F9 cites unknown source S99` (run `run1-fault-injection`), exit 4 |
| Each recorded excerpt really occurs in the fetched page | `excerpt found in page` |
| The ledger matches an independent count of fetches | `audit … --observed-web 3` → `AUDIT OK` |
| Run 2 reads run 1's knowledge back and records what it used | `knowledge_recalled` and `knowledge_used` events at the end |

Run 2 answered its question in 1 cycle with 0 web calls, by reusing run 1's
stored finding, open question, sources, and lesson ("run the experiment
before spending web calls").

Files:

- `smoke.sh`: the replay script.
- `experiments/`: the two local git experiments.
- `brief-run1.md`, `brief-run2.md`: the briefs the script installs into each run.
- `runs/run1`, `runs/run2`: run directories as the script left them.
- `runs/run1-fault-injection`: a copy of run 1 with an injected bad citation.
- `store/knowledge.jsonl`: the durable knowledge store shared by both runs.
- `transcript.log`: every command, its output, and its exit code.

Not shown here (covered by `scripts/test_lab.py` instead): the wall-clock
refusal, the stall stop, ledger tampering, and a `via` source that no recall
surfaced.
