# Design notes: autonomy contract and research lab

Written 2026-10-09 (ICT) for task T15. This file seeds the PR's tradeoffs and
failed-approaches section. **Experiment arms must not read it.** It quotes
evidence that bears on the experiment question.

## Lessons taken from the named sources

Only lessons that change this design are listed. "Inspected" means the page
itself was read. "Snippet" means only search-result excerpts were seen.

| Source | Lesson | Where it shows up here |
| --- | --- | --- |
| OpenAI, [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) (snippet: direct fetch and curl returned 403 or a JS challenge) | "From the agent's point of view, anything it can't access in-context while running effectively doesn't exist." The repo is the system of record. AGENTS.md is a short map (~100 lines) with pointers, not an encyclopedia. Rules are enforced mechanically by linters and CI, not by prose. | All state is plain files in the run directory and the store. SKILL.md files stay short. Budget and citation rules are checked by `lab.py`, not just described. |
| OpenAI, [Build an Agent Improvement Loop with Traces, Evals, and Codex](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop) (inspected; May 12, 2026) | Traces plus feedback become reusable evals, then harness changes. The example agent writes citations and an evidence table, and runs a checker that fails claims citing files that don't exist. The suggested start is a reviewed loop, automated later. | `validate` is the evidence-coverage check. `log.jsonl` is the trace. LEARN writes task knowledge only; skill changes go through workflow-evolution with a human-reviewed PR. |
| Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (inspected; Jun 13, 2025) | Orchestrator-worker with parallel subagents. Token use explained 80% of performance variance on BrowseComp; multi-agent used about 15× chat tokens. Embed explicit effort rules, because agents misjudge effort. Start wide, then narrow. Save the plan to durable memory. Have subagents write to files to avoid a game of telephone. Judge outcomes, not paths, with a rubric: factual accuracy, citation accuracy, completeness, source quality, tool efficiency. Human testers caught agents preferring SEO content farms. | The budget is explicit and identical for both experiment arms, and spend is measured, because spend alone can explain a quality difference. The rubric uses those criteria. Source quality is scored separately. Parallel workers are off by default. |
| Anthropic, [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) (inspected via curl; Feb 5, 2026) | A bare loop plus good tests kept agents on track. Avoid context pollution: print a few lines, log details to files, and put `ERROR` and the reason on one line so grep finds it. Agents are time-blind, so the harness must track time. Sixteen agents on one shared bug made no progress until the work was split into independent pieces. Keep progress files so a fresh agent can orient. | `lab.py` prints one-line `OK`/`REFUSED`/`STOP`/`ERROR` results. The wall-clock budget is measured by the script, not by the agent. Parallelism only for independent claims. The run directory doubles as the progress file. |
| Anthropic, [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents) (inspected; Apr 8, 2026) | The session is an append-only event log that lives outside the context window, so a crashed harness can wake and resume from it. Be opinionated about interfaces, not implementations; harness assumptions go stale as models improve. Keep credentials out of reach of generated code. | `log.jsonl` and the append-only, last-write-wins records are the session. A fresh agent resumes by reading the run directory. The contract is an interface (files plus exit codes), not a runner. `lab.py` needs no credentials. |

## What is reused

| Existing piece | Reused for |
| --- | --- |
| `agentic-loop` | Loop semantics, PASS/FAIL/UNCERTAIN verdicts, and escalation. The contract maps onto its phases instead of redefining them. |
| `research` | Sourcing, comparison, and synthesis inside ACT and VERIFY. Not copied. |
| `adversarial-review` | The challenge step: personas P1 (assumptions), P3 (consistency), and P4 (scope and omission), run on the draft findings. |
| `investigation` | The experiment step, when a claim can be checked against a concrete system. |
| `workflow-evolution` | The shape of the experiment protocol: freeze the incumbent, use a fitness vector, decide promote, reject, or inconclusive, and never promote on an inconclusive result. |
| `acceptance-gate`, `task-handoff` (shared workflows, not in this repo) | Human-intervention tags (rescue, correction, investigation, approval) and the review of the resulting PR. |
| The executor agent itself | The runner. No new agent runtime, no API keys. |

## The smallest seam

1. A directory layout of plain files: goal, budget, ledger, log, claims, sources, findings, brief. The knowledge store lives outside it.
2. One stdlib script, eight subcommands, and fixed exit codes. The agent calls it; it never calls the agent.
3. One application skill (research-lab) that says what each phase means for research and which existing skill to load there.

Another domain would add only an application skill. The run directory, ledger, stop rule, and store stay as they are. Claims, sources, and findings are generic enough for a software task (claims become acceptance criteria; sources include test output as `file:` URLs).

## Alternatives considered and rejected

| Alternative | Why rejected |
| --- | --- |
| Add mandatory files and a budget to `agentic-loop` | agentic-loop serves every delegated task and deliberately avoids a second tracking system. Requiring files would tax ordinary tasks. The contract is opt-in for unattended, budgeted runs. |
| Use coordinator task state (`coord_state.py`, 1,548 lines, Unix locking, a worker and assignment model) as the run ledger | It is shaped for multi-worker delivery. Coupling a single research run to coordinator records would import that model for a ledger that takes under 100 lines here. |
| Use the coordinator memory sidecar as the knowledge store | Its operational status keeps it disabled. It captures at session hooks rather than per finding, and nothing queries it per run. |
| A Python orchestrator that calls a model API | Needs paid API keys (not authorized) and duplicates the harness we already run in. The agent is the runner. |
| Orchestrator plus parallel subagents by default, as in Anthropic's research system | About 15× token cost. Useful only for independent, breadth-first work. Our executor cannot reliably spawn subagents, and it would confound the comparison. Kept as an opt-in rule in research-lab. |
| Embeddings or a vector database for the store | A service plus a dependency. Keyword recall over a `.jsonl` file is enough for tens to hundreds of entries. Revisit when recall misses become a recorded lesson. |
| Hard enforcement: a proxy that counts and blocks web tool calls | Needs a service and interception of tools we don't control. Chosen instead: a cooperative check during the run plus an audit afterwards against transcript counts. |
| Markdown-only state, no script | Budgets and citation integrity could not be checked mechanically. "A budget that is never enforced" is a named risk. |
| A model-judged stop rule ("enough evidence") | Self-confirmation. The stop rule is deterministic: budget, no open claims, or stall. |
| Excerpt verification inside `lab.py` against saved page snapshots | Agents using WebFetch don't keep page text on disk, so the check would mostly be skipped. Deferred. The smoke script checks excerpts in shell, and the scorer spot-checks citations. |

## Failed approaches and defects found while building

- **The hash chain alone missed an edit to the last ledger entry.** The tamper test failed. Fix: every charge logs the new chain head in `log.jsonl`, and `audit` compares it. The chain and heads are unkeyed, so this makes accidental edits evident; a deliberate rewrite that re-chains the ledger and log is caught only by an outside count (`--observed-*`).
- **Stored knowledge had duplicate sources and unresolvable `file:` URLs.** Seen when run 2 of the first smoke pass recalled run 1's entry. Fix: de-duplicate, and rewrite relative `file:` URLs to be relative to the store.
- **The stop message said "all 3 claims resolved" when one claim was `unresolved`.** Misleading. Reworded to "no open claims left". After the T15 review it reports resolved and unresolved counts separately, and `unresolved` no longer counts as progress for the stall rule.
- **The first smoke pass was interactive, and its transcript no longer matched the code after the fixes above.** Replaced with `examples/smoke/smoke.sh`, which replays the same decisions against real fetches and fails on any exit-code mismatch.
- **OpenAI's Harness Engineering page could not be fetched** (403 via the fetch tool, and a JS challenge via curl). Its lessons come from search excerpts and are labeled that way.

## Known limitations

- Enforcement is cooperative. An agent can skip `charge`. Only the post-run audit against an independent count catches that.
- `validate` checks that citations are structurally sound and recorded. It cannot tell whether an excerpt really appears on the page or supports the claim. That still needs a reader.
- Recall is keyword overlap. It misses synonyms and paraphrases.
- One writer per store is assumed. Concurrent runs appending to one store are not locked.
- The research-lab challenge step runs reviewer personas sequentially in one context, so they are not independent reviews.
