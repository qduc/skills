---
name: model-benchmark
description: Benchmark AI models and coding harnesses on real-world engineering tasks from the term2 repository. Use when evaluating coding models, comparing agent harnesses (Codex, Pi, Term2, OpenCode), running controlled coding benchmarks, measuring solve rates, testing for regressions, grading candidate diffs with blind LLM judges, or verifying model capabilities against deterministic real-world tasks.
---

# Model Benchmark (term2 Tasks)

A skill for executing rigorous, reproducible, low-cost coding benchmarks on AI models and agent harnesses using real-world bug fixes, refactors, and architectural invariant tasks extracted from the `term2` repository.

## Overview & Principles

1. **Real-World Fidelity**: Uses actual production tasks from `term2` (approval flows, invariant enforcement, security boundary validations, provider decoupling) rather than synthetic puzzles.
2. **Leakage & Anti-Cheating Protection**:
   - Workspaces are created from history-free git archives (`git archive HEAD`) with `.git` and candidate-visible red tests removed.
   - Models cannot inspect past commits or commit messages to cheat.
   - Hidden deterministic evaluators reside outside candidate workspaces and are injected only post-run.
3. **Deterministic & Blinded Evaluation**:
   - **Stage 1: Deterministic Test**: Candidate must pass `tsc --noEmit` and then the hidden vitest test suite (or the task's `verify.sh`).
   - **Stage 2: Blind Multi-Judge LLM Review**: Candidate diffs are anonymized (`candidate-A.diff`, `candidate-B.diff`) and graded on correctness, backward compatibility, scope discipline, and code quality.
4. **Cost & Approval Discipline**:
   - Controlled execution limits (e.g. 1 paired run, 600s timeout per harness).
   - No costly model calls or benchmark executions begin before explicit user `go`.

---

## What You Can Compare

The candidate spec decides which variable moves; hold everything else constant.

| Question | Candidates | Mode recorded in `meta.json` |
| :--- | :--- | :--- |
| Which harness is better? | `codex:openai/gpt-5.4,term2:openai/gpt-5.4,pi:openai/gpt-5.4` | `harness-comparison` |
| Which model is better? | `codex:openai/gpt-5.4,codex:openai/gpt-5.3` | `model-comparison` |
| Anything else | mixed specs | `mixed` |

In `harness-comparison` mode the model is pinned, so the remaining differences
are the harness itself: system prompt, tool set, context management, approval
policy, and how it recovers from a failed edit. Read
[harness-comparison.md](./references/harness-comparison.md) before drawing
conclusions — several confounds are not controllable and must be reported.

---

## Benchmark Workflow

```
1. Select / Define Task
   └── Choose from tasks/ (or create from audit finding)
2. Prepare Isolated Workspaces
   └── Run scripts/prepare-benchmark.sh
3. User Confirmation ("go")
   └── Dry-run scripts/run-candidates.sh, verify setups and cost limits
4. Execute Candidate Runs
   └── Run scripts/run-candidates.sh --go (herdr panes or headless CLI)
5. Deterministic Evaluation
   └── Run scripts/run-evaluator.sh
6. Anonymize Diffs & Judge
   └── Run scripts/anonymize-diffs.sh -> Blind LLM Judge
7. Generate Benchmark Report
   └── Run scripts/generate-report.py -> RESULT.md / BENCH-REPORT.md
```

---

## Curated Real-World Benchmark Tasks

The skill includes pre-packaged, validated tasks in `tasks/`:

| Task ID | Name | Category | Primary Seam / File | Verification Criteria |
| :--- | :--- | :--- | :--- | :--- |
| `c11-d8-approval-grant-kind` | Durable Approval Grant Kind | Schema / Events | `source/services/conversation/conversation-adapter.ts` | Vitest: `grantKind: 'interactive'` emitted on `approval_resolved` |
| `c11-d5-batch-denial-tristate` | Batch Denial Polarity | State Logic | `source/services/approval/tool-approval-batch-coordinator.ts` | Vitest: Denied calls recorded as `'rejected'`, never `'approved'` |
| `f-correctness-002-null-session-context` | Provider DI Boundary | Invariant / Refactor | `source/providers/*.provider.ts` | Grep: No cross-boundary imports; Typecheck & provider tests pass |
| `f-security-002-symlink-traversal` | Workspace Path Traversal Guard | Security / Sandbox | `source/tools/utils.ts` | Vitest: Realpath resolution blocks symlinks pointing outside CWD |
| `r-retry-abort-backoff` | Interrupt during retry backoff | Rewound bug fix | `source/providers/retrying-model.ts` | Vitest: abort during backoff rejects immediately, model not re-invoked |
| `r-ws-session-lifetime` | WebSocket session lifetime cap | Rewound bug fix | `source/providers/responses-websocket-sessions.ts` | Vitest: error listener attached; idle socket retired before 60 min |
| `r-concise-toolrun-collapse` | Collapse tool runs in concise mode | Rewound feature | `source/components/message/MessageList.tsx` | verify.sh only; quality settled by blind judge |

### Rewound tasks (`base_commit`)

A task may set `"base_commit"` in `task.json` to the parent of a real merged
commit. `prepare-benchmark.sh` archives *that* commit instead of `HEAD`, so a
shipped fix becomes a benchmark task with ground truth already attached: the
commit's own tests become the hidden evaluator, and the commit's diff can be
entered as an extra blind candidate (see below).

Two rules keep a rewound task honest:

- **Prove red before green.** The evaluator must fail at `base_commit` and pass
  at the origin commit. An evaluator that is green at the baseline measures
  nothing, and you will not notice from the results alone.
- **The evaluator must be solution-agnostic.** Tests that call a helper the
  original author happened to name are a naming lottery, not a correctness
  gate. Reject a commit as a task source if its tests only exercise new private
  names; prefer ones that assert through an API the baseline already exposes.

Each task directory carries a `task.json` manifest that drives the scripts:

```json
{
  "task_id": "c11-d8-approval-grant-kind",
  "evaluator_test_path": "source/services/conversation/grant-kind.evaluator.test.ts",
  "typecheck": true,
  "strip_files": []
}
```

- `evaluator_test_path`: where `evaluator.test.ts` is injected post-run (`null` for `verify.sh` tasks).
- `typecheck`: run `tsc --noEmit` as a Stage 1 gate before the test stage.
- `strip_files`: candidate-visible red tests removed from the baseline.

Adding a task means adding a directory with `task.json` — no script edits.

See [methodology.md](./references/methodology.md) for full task specifications and scoring guidelines.

---

## Step-by-Step Procedure

### 0. Reasoning effort

Effort is part of the candidate spec, appended with `#`:

```
codex:openai-codex/gpt-5.6-terra#high=codex-terra
```

It renders into whichever flag the harness uses (`-c
model_reasoning_effort=`, `--thinking`, `-r`). Holding effort flat across
models isolates the model variable; setting each model to the effort you would
actually deploy measures the configuration instead. Both are valid — decide
which question you are asking before you spend anything, and say which one the
numbers answer.

### 1. Preparation
Run the preparation script to spin up isolated candidate workspaces:

```bash
./scripts/prepare-benchmark.sh \
  --repo-dir "$TERM2_REPO_DIR" \
  --task c11-d8-approval-grant-kind \
  --candidates "term2-luna,pi-luna,codex-luna"
```

Paths come from the environment: `TERM2_REPO_DIR` (default `$PWD`, must be a git
repo) and `BENCH_OUTPUT_DIR` (default `<skill>/../../runtime`). `--repo-dir` and
`--output-dir` override them.

This creates:
- `control/`: Contains `prompt.txt`, `task.json`, `evaluator.test.ts`, and metadata.
- `candidate-*/`: Independent clean workspace with no git history and a
  per-candidate `node_modules` of symlinks (`--node-modules shallow`, the
  default) so one candidate running `npm install` cannot contaminate another.
  Use `--node-modules copy` for full hermeticity, `symlink` for the old shared
  behavior.

### 2. Confirm Plan with User
Before launching model invocations, present the benchmark configuration:
- Models / harnesses under test
- Target task & prompt
- Timeout limits & estimated costs
- Wait for explicit user `go`.

### 3. Run Benchmark Candidates

```bash
# Dry run: prints the exact invocation per candidate, spends nothing
./scripts/run-candidates.sh --benchmark-dir "$BENCH_DIR"

# After the user says go
./scripts/run-candidates.sh --benchmark-dir "$BENCH_DIR" --go --timeout 600
```

Each candidate is driven by one of two drivers, chosen per harness (`--driver
auto` by default):

- **herdr** — for harnesses that are hard or unrepresentative to run headless.
  The harness's real TUI is started in a throwaway herdr workspace (one tab per
  candidate, `--cwd` set to the candidate workspace), the prompt is submitted
  with `herdr agent prompt`, and the run is waited out on herdr's agent
  lifecycle. A `blocked` state (approval prompt) is recorded as a harness
  outcome, never auto-accepted. Transcript is harvested via the herdr skill's
  `extract-agent-response.py`.
- **cli** — for harnesses with a faithful non-interactive mode (`codex exec`,
  `term2 --auto-approve`, `pi --print`).

Force one with `--driver herdr` or `--driver cli`; `--keep-panes` leaves the
herdr workspace up for inspection; `--only <names>` re-runs a subset.

Each run records `control/<candidate>.seconds`, `.run.status`
(`OK`/`BLOCKED`/`TIMEOUT`/`ERROR`), and `.run.log`. Candidates declared with a
bare name (no `harness:`) are skipped — drive those by hand in their workspace.

Harnesses are declared in [harnesses.json](./harnesses.json); add one there
rather than editing scripts. Each entry supplies a `cli` invocation (`bin` +
`args`), an optional `herdr` block (`kind` + `start_args`), and a
`model_template` that renders the canonical `provider/model` id into that
harness's syntax.

### 4. Run Deterministic Evaluator
Execute the typecheck gate and hidden test against all candidate workspaces
(`BENCH_DIR` is the run directory printed by `prepare-benchmark.sh`):

```bash
./scripts/run-evaluator.sh --benchmark-dir "$BENCH_DIR"
```

### 4b. Collect Cost

```bash
python3 scripts/collect-cost.py --benchmark-dir "$BENCH_DIR"
```

Writes `control/<candidate>.cost.json` with normalised token counts and a
dollar figure. Each harness reports usage differently and one does not report
it at all, so read [cost-capture.md](./references/cost-capture.md) before
trusting or extending the numbers — especially the term2 prerequisite
(`logging.debugLogging = true`) and the serial-execution requirement.

### 5. Blind Judge Review
Extract anonymized diffs and evaluate via a high-capability judge model (e.g. Claude Opus or Gemini Pro). Label assignment is randomized per run to remove positional bias (`--no-shuffle` disables):

```bash
./scripts/anonymize-diffs.sh --benchmark-dir "$BENCH_DIR"
```

Prompt the judge using the standard template in [judge-prompt-guide.md](./references/judge-prompt-guide.md), or run several samples end to end:

```bash
./scripts/run-judge.sh --benchmark-dir "$BENCH_DIR" --samples 3 \
  --include-human <origin_commit> --repo-dir "$TERM2_REPO_DIR"
```

`--include-human` enters the real merged commit as one more unlabeled
candidate. Without it the judge's 10-point scale has no calibrated point on it
and the run cannot answer whether any candidate beat the original fix. Labels
are re-shuffled between samples; `aggregate-judge.py` joins scores back through
each sample's mapping and reports the spread next to the mean.

When later grid runs add candidates for the same task, score the combined set on
one scale with `scripts/pooled-judge.sh`. Its preflight removes empty submissions,
hash-deduplicates byte-identical diffs, and carries existing run/evaluator statuses
into an anonymized dossier. The judge is tool-free and returns dimension scores
only; Python owns totals, ranking, validation, and expansion back to duplicate
candidate names. Run `scripts/run-evaluator.sh` on every source run first so the
pooled judge receives deterministic evidence instead of trying to recreate it.
Preflight rejects prompts above 500,000 bytes before spending judge tokens;
override that reviewed admission limit with `--max-prompt-bytes`. Because this
tool-free rubric uses frozen evaluator evidence, do not trend its scores against
older pooled runs whose judges explored repositories and ran their own tests.

```bash
./scripts/pooled-judge.sh --pool-dir "$POOL_DIR/control" \
  --prompt "$FIRST_RUN/control/prompt.txt" --samples 3 \
  "$FIRST_RUN" "$LATER_RUN"
```

### 6b. Fold several runs into one grid

```bash
python3 scripts/grid-report.py <run-dir> <run-dir> <run-dir> --out GRID.md
```

One task is one data point. Ranking harnesses or models on a single task
measures that task, so run the same candidate set across several tasks of
different shape and read the grid, not any one column.

### 6. Generate Comparative Report
Compile all metrics into a unified summary:

```bash
python3 scripts/generate-report.py --benchmark-dir "$BENCH_DIR"
```

---

## Additional References

- [Methodology & Metric Definitions](./references/methodology.md)
- [Anti-Cheating & Workspaces Isolation Guide](./references/anti-cheating-guidelines.md)
- [Blind Judge Rubrics & Prompts](./references/judge-prompt-guide.md)
