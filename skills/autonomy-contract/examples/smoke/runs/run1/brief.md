# Does git worktree share hooks between worktrees?

## Answer
Yes, by default. A hook installed in the main repository's `.git/hooks` fires for commits made in any linked worktree, because hook lookup resolves through the shared (common) git directory, not the worktree's private one. Confidence: high (direct experiment; the docs are ambiguous on this point).

## Key findings
- In a linked worktree, `git rev-parse --git-path hooks` returns the main `.git/hooks`, and a pre-commit hook placed there fired for a commit made in the linked worktree [1]. (confidence: high)
- The githooks page says the default hooks directory is `$GIT_DIR/hooks` [2], and a linked worktree has a private `$GIT_DIR` [3]. Read literally, that suggests per-worktree hooks; the experiment shows otherwise [1]. (confidence: high)
- The docs suggest one worktree could opt out by enabling `extensions.worktreeConfig` and setting `core.hooksPath` with `git config --worktree` [4][5]. Not tested in this run. (confidence: low)

## Contradictions and counter-evidence
- githooks' `$GIT_DIR/hooks` [2] versus the observed behaviour [1]. Likely cause: the page uses `$GIT_DIR` loosely, and `--git-path` maps `hooks` to the common directory [3].

## Uncertainty and gaps
- Observed on one git version (recorded in the experiment log).
- The per-worktree opt-out is an inference from two doc passages, not an observation.

## Follow-up questions
- Can one worktree use different hooks via `extensions.worktreeConfig` plus `git config --worktree core.hooksPath`?

## References
[1] Local experiment, runs/run1/experiments/shared-hooks.log
    > "linked --git-path hooks: <tmp>/main/.git/hooks"
[2] githooks — Git project. https://git-scm.com/docs/githooks
    > "By default the hooks directory is $GIT_DIR/hooks , but that can be changed via the core.hooksPath configuration variable"
[3] git-worktree — Git project. https://git-scm.com/docs/git-worktree
    > "Path resolution via git rev-parse --git-path uses either $GIT_DIR or $GIT_COMMON_DIR depending on the path."
[4] git-worktree, CONFIGURATION FILE — Git project. https://git-scm.com/docs/git-worktree
    > "In order to have worktree-specific configuration, you can turn on the worktreeConfig extension"
[5] git-config — Git project. https://git-scm.com/docs/git-config
    > "--worktree Similar to --local except that $GIT_DIR/config.worktree is read from or written to if extensions.worktreeConfig is enabled."
