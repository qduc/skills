# Comparing Harnesses (Same Model, Different Harness)

Pin the model, vary the harness, and the benchmark measures the harness. That is
a real and useful measurement — but only if you control what you can and report
what you cannot.

## Setup

```bash
./scripts/prepare-benchmark.sh --task c11-d8-approval-grant-kind \
  --candidates "codex:openai/gpt-5.4,term2:openai/gpt-5.4,pi:openai/gpt-5.4"
```

`prepare-benchmark.sh` records `comparison_mode: harness-comparison` in
`meta.json` when exactly one model id appears across more than one harness. The
report surfaces that mode and adds a reading caveat.

## What is controlled

- **Task and prompt**: byte-identical `prompt.txt` for every candidate.
- **Workspace**: same history-free `git archive` baseline, same stripped red
  tests, per-candidate `node_modules` so nothing bleeds across runs.
- **Model**: same canonical `provider/model` id, rendered per harness through
  `model_template`.
- **Time limit**: one `--timeout` for all candidates; overruns are recorded as
  `TIMEOUT`, not silently truncated.
- **Grading**: identical typecheck + hidden test gate, and a blind judge that
  sees anonymized diffs in randomized order.

## What is not controlled — report these

1. **System prompt and tool set.** Each harness ships its own. This *is* the
   thing under test, but it means a harness can lose on a task its prompt never
   asks it to attempt (e.g. it never runs tests).
2. **Reasoning effort / thinking level.** Harnesses default differently. Pin it
   in `start_args`/`args` when the harness exposes a flag, and say what you
   pinned. Unpinned effort is the single most common way a "harness comparison"
   silently becomes a compute comparison.
3. **Approval policy.** The registry runs each harness with its auto-approval
   flag on. A harness that still stops for approval is scored `BLOCKED` — a
   genuine harness result, not a model failure. Never hand-approve for one
   candidate only.
4. **Project config.** `AGENTS.md`/`CLAUDE.md` in the archived baseline are read
   by some harnesses and not others. Note it; do not delete them selectively.
5. **Context window and compaction.** Longer tasks favor harnesses with better
   compaction. Keep tasks small enough that this is not the dominant effect, or
   report it as the finding.
6. **Cost.** Same model, different harnesses can differ several-fold in tokens.
   Duration is recorded; token cost is not. Pull it from each harness's own
   usage reporting if the comparison is about efficiency.

## Statistical honesty

One run per harness on one task is an anecdote. A defensible claim needs several
tasks, and repeats per task, because agent runs are non-deterministic. Report
per-task pass/fail rather than a single averaged number, and state the run count
next to every claim.

## Driving hard-to-automate harnesses

`run-candidates.sh --driver herdr` starts the harness's actual interactive TUI in
a dedicated herdr workspace and submits the prompt through `herdr agent prompt`.
Use it when a harness has no headless mode, or when its headless mode differs
enough from the TUI that measuring it would answer the wrong question. Waiting is
done on herdr's agent lifecycle (`working` → `idle`/`done`), with `blocked`
treated as a terminal outcome for the run.

Lifecycle states are scheduling signals, not proof of completion: the run's real
verdict comes from Stage 1 (typecheck + hidden test) against the candidate
workspace, never from the harness's own claim of success in the transcript.
