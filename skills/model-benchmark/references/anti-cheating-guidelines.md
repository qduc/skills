# Anti-Cheating & Workspace Isolation Guidelines

When benchmarking capable LLMs on engineering tasks from a real codebase like `term2`, modern models will proactively look for shortcuts (e.g. reading git logs, diffing commits, looking for existing bug reproduction test files, or reading files outside their workspace).

To ensure a valid, unpolluted benchmark, apply these isolation rules:

---

## 1. Eliminate Git History
- **Rule**: Never leave a `.git` folder or `.git` file pointing to parent repos inside the candidate workspace.
- **Implementation**:
  ```bash
  # Generate clean history-free snapshot
  git -C "$REPO_DIR" archive HEAD | tar -x -C "$CANDIDATE_DIR"
  rm -rf "$CANDIDATE_DIR/.git"
  ```
- **Why**: Models frequently run `git log`, `git show`, or `git status` to find recent commits that fixed the issue or similar bugs.

---

## 2. Strip Pre-existing Defect & Audit Markers
- **Rule**: If a reproduction test or failing test exists in the repository (e.g., `source/services/approval/c11-d5-batch-denial-boundary.test.ts` or files with `it.fails`), remove it from the candidate directory before starting the benchmark.
- **Rule**: Remove or redact audit report files if the benchmark prompt directly references an audit finding ID.
- **Why**: An agent encountering an `it.fails` test file with comments describing the exact bug and expected fix can simply copy the test's requirements without diagnosing the root cause.

---

## 3. Sandboxing Workspace Bounds
- **Rule**: Add an explicit instruction to the prompt: `Do not inspect paths outside this workspace.`
- **Rule**: Place candidate workspaces in a dedicated isolated runtime directory (`~/.agents/runtime/bench-<timestamp>/`).
- **Why**: Some agent harnesses will search parent directories or scan `~/.codex/` / `~/.agents/` for prior run artifacts.

---

## 4. Post-Run External Evaluator Injection
- **Rule**: Keep the deterministic evaluator test files exclusively inside the benchmark `control/` directory until the candidate completes its run.
- **Rule**: Copy the evaluator into the workspace only during the evaluation phase, run Vitest, and record the results externally.
