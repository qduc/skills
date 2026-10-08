---
name: autonomy-contract
description: >-
  Run a bounded Observe→Decide→Act→Verify→Learn→Repeat loop over plain files
  with a checkable budget and a durable knowledge store. Use when a human
  hands over a goal plus a budget and wants unattended work that terminates
  predictably. Domain-neutral: research, delivery, or discovery plug in as
  application skills. Do not use for a one-shot lookup or a single edit.
---

# Autonomy contract

A small, reusable seam for unattended work. The agent owns judgment. This
skill owns the filesystem shape, the budget ledger, the stop rule, and the
citation check. Research is the first application
([research-lab](../research-lab/SKILL.md)); do not invent other applications
here.

## Contract

| Phase | Decide and do | Carry forward |
| --- | --- | --- |
| OBSERVE | Read the goal, the budget, and the knowledge store. Log which store entries you surface. | Working picture and reused knowledge ids |
| DECIDE | Choose the cheapest next step that moves an unmet claim or acceptance criterion. Name the expected observation. | Chosen action and expected result |
| ACT | Do that step with the tools and authority you have. Charge the budget first. Prefer reversible progress. | What actually ran |
| VERIFY | Check evidence against the claim or criterion. PASS, FAIL, or UNCERTAIN. | Verdicts and unresolved gaps |
| LEARN | Write durable knowledge only when it will help a later run. Record failed approaches so they are not repeated. | Store entries and lessons |
| REPEAT | Run `lab.py check`. Stop when it says stop. Otherwise return to OBSERVE with the updated state. | Stop decision or next cycle |

These are seams, not five agents and not a required function interface. Combine
small steps; never skip OBSERVE or VERIFY. A successful action is not a
successful run.

## Run directory

Plain files only. One run, one directory:

```text
runs/<id>/
  goal.md            frozen goal
  budget.json        limits, start time, path to the knowledge store
  ledger.jsonl       hash-chained budget charges and refusals
  log.jsonl          structured events (one JSON object per line)
  claims.jsonl       investigable claims (last write for an id wins)
  sources.jsonl      inspected sources with URL and quoted excerpt
  findings.jsonl     findings that cite claim ids and source ids
  brief.md           short human-facing conclusions (not a transcript)
```

The knowledge store sits **outside** the run directory (for example
`knowledge/store.jsonl`) so later runs can read it. Temporary model context
stays in the chat; durable knowledge stays in the store.

## Helper

`scripts/lab.py` is a deterministic Python-stdlib helper. No services, no
network of its own.

```sh
LAB=skills/autonomy-contract/scripts/lab.py

python3 $LAB init RUN --goal "..." --store knowledge/store.jsonl \
  --max-cycles N --max-web N --max-minutes N

python3 $LAB recall RUN                 # OBSERVE: read the store, log what was used
python3 $LAB charge RUN cycle --note "..."   # before each cycle; exit 3 = refuse
python3 $LAB charge RUN web --note "..."     # before each search or fetch; exit 3 = refuse
python3 $LAB log RUN PHASE EVENT [--data '{...}']
python3 $LAB add RUN claim|source|finding|knowledge '{...}'   # or '-' for stdin
python3 $LAB check RUN                  # exit 10 = stop
python3 $LAB validate RUN               # exit 4 = bad citations
python3 $LAB audit RUN [--observed-web N] [--observed-cycles N]
```

Exit codes: `0` ok/continue, `2` usage, `3` budget refused, `4` validation
failed, `5` audit failed, `10` stop.

### Budget

Concrete, checkable limits, frozen at `init`:

| Limit | Meaning |
| --- | --- |
| `max_cycles` | How many DECIDE→ACT→VERIFY cycles the run may start |
| `max_web` | How many web search or fetch calls the run may make |
| `max_minutes` | Wall clock from `init` |
| `max_stall` | Stop after this many consecutive cycles that newly support or contradict no claim (default 2; `0` disables) |
| `reserve_minutes` | Stop this early so there is time to write the brief (default 0) |

`charge` refuses with exit 3 once any limit is hit, and appends a `refused`
ledger entry. `--n` must be at least 1; `audit` flags any charge with `n < 1`. The ledger is hash-chained back to `budget.json`, and every
charge also logs the new chain head in `log.jsonl`. `audit` re-checks the
chain and the head, and compares ledger totals with counts observed outside
the run (for example, tool calls counted from the transcript). The chain and
heads are unkeyed: they make accidental edits evident, but a deliberate rewrite
(re-chaining the ledger and log) is caught only by an outside count
(`--observed-web`, `--observed-cycles`).
Ledger lines carry `kind` (`init`, `charge`, `refused`); charge and refused lines also carry `what` (`cycle` or `web`) and `n`. Read totals from `audit`'s `used` instead of counting lines by hand.

### Stop rule

`check` returns stop when any of these hold:

1. The cycle, web, or (minutes − reserve) budget is spent.
2. No recorded claim is `open`. The reason reports resolved (`supported` or
   `contradicted`) and `unresolved` counts separately.
3. The last `max_stall` cycles moved no additional claim to `supported` or
   `contradicted`. Marking a claim `unresolved` is not progress.

`check` prints the claims summary as `open`, `resolved`, and `unresolved`.

### Citations

`validate` requires:

- Every finding cites at least one claim id and one source id that exist.
- Every source has an `http(s)` or `file:` URL and a quoted excerpt (≥ 8 chars).
  Relative `file:` URLs are relative to the run directory (or, inside the
  store, to the store's directory).
- Every claim marked `supported` or `contradicted` is cited by at least one finding.
- A source that claims to come from the knowledge store (`via`) was actually
  surfaced by a `recall` in this run.
- Every URL that appears in `brief.md` is a recorded source.

### Honesty about enforcement

An LLM agent can ignore this script. Enforcement is a **cooperative check
during the run** plus an **audit after the run**. Treat a run that never called
`charge` or that exceeds the observed tool-call counts as a failed run, not as
a soft warning.

## How to run (any application)

1. `lab.py init` with the goal and the budget.
2. OBSERVE: `lab.py recall`. Record which store entries you will use.
3. Decompose the goal into claims (`lab.py add … claim`).
4. Loop: `charge cycle` → DECIDE → `charge web` as needed → ACT → record
   sources and findings → VERIFY → LEARN (`add … knowledge` when warranted) →
   `check`. Exit the loop when `check` returns 10.
5. Write `brief.md` for the human. Run `validate`, then `audit`.

The brief leads with conclusions that need judgment. Cite material claims
with numbered references whose URLs are recorded sources (`validate` checks
this). State contradictions and unresolved uncertainty in the open. Do not
paste the transcript or narrate the process.

## Relationship to existing skills

| Skill | Role relative to this contract |
| --- | --- |
| [agentic-loop](../agentic-loop/SKILL.md) | Same loop semantics (PLAN/ACT/OBSERVE/VERIFY/ADAPT). This skill adds filesystem state, a checkable budget, and a durable store. Prefer this skill when those are required; otherwise prefer agentic-loop. |
| [research](../research/SKILL.md), [investigation](../investigation/SKILL.md), [adversarial-review](../adversarial-review/SKILL.md) | Methodology adapters loaded by an application skill such as research-lab. |
| [workflow-evolution](../workflow-evolution/SKILL.md) | Improves skills across runs. LEARN here writes task knowledge; workflow-evolution mutates skills under a separate experiment protocol. |
| [coordinator](../coordinator/SKILL.md) | Multi-worker orchestration. Out of scope for a single-agent contract run. |
