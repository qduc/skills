# Benchmark Methodology & Evaluation Framework

## Core Evaluation Pillars

Benchmarking coding models on real-world codebases like `term2` tests capabilities across four essential dimensions:

```
                  ┌─────────────────────────────────┐
                  │ 1. Functional Correctness       │
                  │    - Passes hidden deterministic│
                  │      vitest / typecheck tests   │
                  └────────────────┬────────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │ 2. Architectural Invariants     │
                  │    - Respects boundaries, DI,   │
                  │      and layering rules         │
                  └────────────────┬────────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │ 3. Scope Discipline             │
                  │    - Edits only necessary files;│
                  │      avoids drive-by refactoring│
                  └────────────────┬────────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │ 4. Observability & Testing      │
                  │    - Adds durable regression    │
                  │      coverage and typed tests   │
                  └─────────────────────────────────┘
```

---

## 1. Workspaces Preparation & Hermetic Environments

- **Clean Baseline**: Workspaces must be extracted directly via `git archive` from a known baseline commit.
- **Dependency Isolation**: Candidate directories should symlink to a shared read-only `node_modules` at repo root or pre-built caching layer. Avoid running `pnpm install` inside candidates to save time and eliminate non-deterministic network fetches.
- **History Scrubbing**: Delete `.git` directories and any metadata files referencing historical fixes.
- **Red-Test Removal**: If `term2` contains an existing failing test for the issue (e.g. `it.fails`), remove that test file before giving the workspace to the candidate. The evaluation suite will inject the authoritative test during scoring.

---

## 2. Execution Protocol

- **Prompt Integrity**: Use identical, standardized prompt text across all candidate runs.
- **Resource Constraints**:
  - Max time: 600s timeout per candidate run.
  - Approval policy: Unattended auto-approve mode for CLI tool operations (`yolo` or `--auto-approve`).
  - Single run per candidate by default to minimize token expenditures.
- **Telemetry Collection**:
  - `candidate.out`: Final model response / report.
  - `candidate.stderr`: Event stream / tool execution logs.
  - `candidate.seconds`: Wall-clock execution time.
  - `candidate.diff`: Git diff of modified files against baseline.

---

## 3. Evaluation & Scoring

Evaluation proceeds in two stages:

### Stage 1: Deterministic Machine Grading (0 or 1)
1. **Typechecking**: `pnpm tsc --noEmit` must pass with 0 errors.
2. **Hidden Test Suite**: Post-run injection of the hidden Vitest evaluator. Must exit with code 0.
3. **Boundary Invariant Check**: Pattern validation (e.g. `grep` checks ensuring no forbidden cross-package imports).

### Stage 2: Blind Multi-Judge LLM Review (0 to 10 scale)
Anonymized candidate diffs (`candidate-A.diff`, `candidate-B.diff`) are presented to an independent LLM judge without revealing model names or harness identities.

**Judge Scoring Rubric (10 Points Total)**:
- **Correctness (4 pts)**: Does the patch completely and cleanly resolve the reported problem without edge-case regressions?
- **Scope Discipline (2 pts)**: Are modifications strictly bounded to the problem statement? Zero unnecessary churn.
- **Backward/Forward Compatibility (2 pts)**: Does the change preserve wire/schema formats and legacy payload handling?
- **Test Quality & Coverage (2 pts)**: Did the candidate include thorough regression tests at the appropriate public boundary?

---

### Comparison Modes

`prepare-benchmark.sh` classifies a run from its candidate specs:

- `harness-comparison`: one model, several harnesses. Isolates harness quality.
- `model-comparison`: one harness, several models. Isolates model quality.
- `mixed`: anything else — interpret candidate by candidate.

See [harness-comparison.md](./harness-comparison.md) for the controlled and
uncontrolled variables in the first mode.

---

## 4. Metrics & Reporting

Every benchmark run produces a consolidated `BENCH-REPORT.md` / `RESULT.md` summarizing:
- Harness and model per candidate, plus the run's comparison mode
- Time to Completion (seconds), from prompt submission to settled state
- Run outcome (`OK` / `BLOCKED` / `TIMEOUT` / `ERROR`) distinct from the
  deterministic pass/fail
- Deterministic Pass/Fail status
- Lines of code changed (Insertions / Deletions / Files touched)
- Tool call counts and execution steps
- Judge scores and qualitative findings
