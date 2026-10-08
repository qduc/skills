# Can one git worktree run different hooks from the other worktrees of the same repository?

## Answer
Yes. Enable `extensions.worktreeConfig`, then run `git config --worktree core.hooksPath <dir>` inside the worktree that should differ. Only that worktree uses `<dir>`; the others keep the shared `.git/hooks`. Confidence: high (direct experiment). This run reused run 1's stored finding, open question, and sources, and spent no web calls.

## Key findings
- With the extension on, `git config --worktree core.hooksPath` in worktree `wt-b` made `wt-b` resolve hooks to the alternate directory and run the alternate pre-commit hook [1][2]. (confidence: high)
- The main worktree and `wt-a` kept running the shared pre-commit hook [1]. (confidence: high)

## Contradictions and counter-evidence
- None found. Run 1's ambiguity (`$GIT_DIR/hooks`) does not apply here, because `core.hooksPath` overrides the default directory.

## Uncertainty and gaps
- One git version. The git-worktree docs warn that older Git versions refuse repositories with this extension.
- Without `extensions.worktreeConfig`, `--worktree` behaves like `--local` and would change the shared config [2]. Not exercised.

## Follow-up questions
- Which Git version first honours `core.hooksPath` from `config.worktree`?

## References
[1] Local experiment, runs/run2/experiments/per-worktree-hooks.log
    > "wt-b: --git-path hooks = <tmp>/alt-hooks"
[2] git-config — Git project (reused from the knowledge store). https://git-scm.com/docs/git-config
    > "--worktree Similar to --local except that $GIT_DIR/config.worktree is read from or written to if extensions.worktreeConfig is enabled."
