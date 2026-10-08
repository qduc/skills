# Autonomy contract

A domain-neutral shape for delegated work with minimal supervision. Research
is the first domain; publishing, business discovery, and software development
should reuse this contract by supplying their own **unit of work**, **evidence
type**, and **verifier** — not a new loop.

```
Observe → Decide → Act → Verify → Learn → Repeat (until verified, blocked, or budget spent)
```

| Phase | Generic obligation | Research instance (`lab.py`) |
|---|---|---|
| Observe | Read durable state and prior knowledge before acting; read the remaining budget. | `status`, `kb-search --lessons` |
| Decide | Decompose the goal into units that can each be checked; pick the next one by value per budget. | key claims (`claim-add --key`) |
| Act | Charge the meter before every costly action; record what actually happened, not what was expected. | `charge`, `snapshot`, `evidence`, `challenge`, `experiment` |
| Verify | A deterministic check over durable state, independent of the actor's self-report. Failures become tasks. | `verify` (quotes, coverage, challenge, primary, contradictions, budget) |
| Learn | Promote only verified results; record lessons as rules; repeated lessons become harness changes. | `learn`, `<kb>/lessons.md` |

## Invariants every domain keeps

1. **Durable state outside context.** The run directory is the system of
   record (append-only `events.jsonl` plus current-state files). A fresh agent
   can resume from it; nothing important exists only in a transcript.
2. **Budget is enforced by the environment.** The actor asks the meter before
   acting. Exhaustion flips the run to `STOPPED`, after which only
   verify/report/learn run. Termination is therefore predictable.
3. **Verification is mechanical where possible.** The verifier reads state,
   not prose. Judgment that cannot be mechanized is surfaced to the human as a
   named judgment call, not hidden in a confidence word.
4. **Uncertainty is a first-class outcome.** `contested` and `unresolved` are
   valid terminal states.
5. **Learning is gated.** Only verified results enter the knowledge base.
   A lesson seen twice should become a change to the skill or verifier.
6. **One writer.** Parallel workers return data to a single writer; they never
   share mutable state.

## Adding a domain later (not built yet)

Copy the generic parts (`init/charge/status/finish`, events, `learn` gate) and
replace the research ledger with the domain's unit and verifier, e.g.

- software: unit = acceptance criterion; evidence = command + exit + output
  excerpt; verifier = rerun the oracle command.
- publishing: unit = factual statement in a draft; evidence = source quote;
  verifier = the existing quote check plus a link check.

Extract a shared module only when a second domain actually exists.

## Hard enforcement hook (optional)

`charge` is cooperative: the agent calls it. Hosts that support pre-tool
hooks (Claude Code `PreToolUse`, term2 public hooks, Pi extensions) can make it
mandatory by running `lab.py charge <run> search` before `WebSearch` and
`... fetch` before `WebFetch`, and blocking the tool on exit code 3.
