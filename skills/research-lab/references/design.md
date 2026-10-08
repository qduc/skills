# Design notes: why research-lab looks like this

## What was surveyed

- **OpenAI, Harness Engineering.** The repository is the system of record;
  give agents a map and make the environment legible; enforce rules
  mechanically with remediation-bearing errors; when an agent fails, add the
  missing tool or guardrail rather than retrying.
  → `lab.py` is the environment; `ISSUE` lines are remediation tasks.
- **OpenAI cookbook, Agent Improvement Loop.** Traces plus feedback become
  evals, evals gate harness changes, and humans review diffs at first.
  → `events.jsonl` is the trace, `lessons.md` the feedback, `verify` the gate.
  The v1→v2 breadth check in experiment 001 went through this loop once.
- **Anthropic, building a C compiler with parallel Claudes.** The verifier must
  be near-perfect; parallelism helps only on independent units; keep tool
  output to a few greppable lines; agents can't tell time, so the harness
  must; fresh agents need progress files.
  → single writer, short output, a time budget in the meter, a resumable run directory.
- **Anthropic, Managed Agents.** Keep the durable session log outside the
  context window; the harness is stateless and resumable; disposable hands.
  → the run directory, not the transcript, holds state.
- **Anthropic, multi-agent research system.** Multi-agent beat single-agent by
  90.2% on an internal eval, but token usage explained 80% of variance and
  multi-agent runs used ~15x chat tokens. → **budget-match the baseline**, and
  default to one worker.
- **Existing assets.** `agentic-loop` (ownership and stop rules) and `research`
  (sourcing method) already existed in this repo, so research-lab composes
  them. `coordinator` (~9k lines, git- and code-centric) was not reused.
  Earlier `qduc/research_agent` (LangGraph) was not revived because it would
  add a framework dependency for no measured gain.

## Decisions and tradeoffs

| Decision | Chosen | Alternative rejected | Tradeoff accepted |
|---|---|---|---|
| Where the loop lives | A skill run by whatever host agent is present | A new Python orchestrator calling a model API | Budget is cooperative unless a host hook enforces it (see autonomy-contract.md). In exchange: no paid API, no new runtime, and it works in Claude Code, term2, Pi and Codex. |
| State | Plain JSON/JSONL in a run directory | SQLite / vector DB | Keyword-only KB search, one writer. Fine at the current scale. |
| Verification | Deterministic checks over the ledger | LLM-judge self-review | Cannot judge whether a quote really supports a claim; it only checks that the quote exists, coverage, challenge, primary-source use and contradiction handling. Semantic support is left to an independent grader at eval time. |
| Challenge | Mandatory recorded counter-search per key claim | A separate adversarial agent | Same-context bias remains; cheaper, and no nested agents. |
| Parallelism | Off by default; workers return data to a single writer | Fan-out per claim | Slower on very broad questions. Experiment 001 finished in under 10 minutes without it. |
| Generality | One file, with a domain-neutral contract documented | A shared `autonomy` package now | Some code will be copied when a second domain arrives; extract then. |

## Failed approaches and dead ends

- **Fetching raw pages from the shell** for byte-exact snapshots: the sandbox
  allowlist blocks arXiv, vendor sites and readers. Fell back to WebFetch
  "verbatim passage" requests; this limitation is documented in RESULTS.md.
- **Claims-first decomposition (v1).** Writing key claims before any search
  produced a narrow report that ranked last in round 2. Replaced by
  scan-first plus a gap check, enforced by the verifier.
- **Timestamp ordering for the breadth check.** Second-resolution timestamps
  tie, so a scan logged in the same second as a claim counted as "before".
  Switched to position in the append-only log, and added a test.
- **A `log(kind=...)` signature clash** crashed `charge` on first use; a unit
  test caught it before any run.
- **`report` before `finish`** made the report show `ACTIVE` with a still-running
  clock. The order is now finish then report, and elapsed time freezes at `ended`.

## Remaining limitations

- Budget enforcement is cooperative without a host pre-tool hook.
- Snapshots are model-processed text, not original bytes.
- No dollar metering; tokens come from the host.
- The KB is append-only with keyword search; there is no staleness handling
  beyond the advice to re-check time-sensitive claims.
- Evidence of quality improvement rests on n=1 per arm.
