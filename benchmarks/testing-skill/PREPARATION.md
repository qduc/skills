# Preparation evidence — 2026-10-15

Scope: prepare the PR #7 pilot and validate offline, without model calls, paid
judging, integration installation, account changes, merge or branch protection.

## Source inspection

- Fresh checkout of `qduc/skills`, main `e56afe155ef3eae172269bf5a83f42ccb456d252`.
  The unrelated `/workspace/term2` checkout was not modified.
- `gh pr view 7 --repo qduc/skills`: OPEN, draft, head
  `9e5f2219a3035135dd8632aed47f4daa3add0948`, base branch main. Head was
  rechecked before publication. The PR's requested baseline remains
  `9c75d00ea3167d67afcec4ec2882f5ededa55141`; do not substitute today's main.
- PR body supplies the eight scenarios, three repetitions, 48 runs and soft
  pre-merge agreement. No reviews or comments supplied additional trial evidence.
  Its existing PyYAML validation and scenario walkthrough are structural evidence,
  not model trials. The candidate changes only `skills/testing/SKILL.md`.
- Inspected current remote branches and all PR listings: no existing benchmark
  support branch/PR to reuse. Reused the PR design rather than creating a second
  candidate treatment PR. This support branch is based on main.
- Repository has no applicable `AGENTS.md` (searched checkout and mounted
  instruction directories). Read README, `.gitignore`, testing eval placeholders,
  candidate skill and testing isolation checklist; inspected benchmark tooling
  and existing stdlib unittest conventions in `scripts/test_setup_protocols.py`.
- `skills/testing/evals/evals.json` explicitly labels its two author-drafted evals
  placeholders. These remain untouched; the independent pack is separate.
- Read `skills/model-benchmark/SKILL.md` and its methodology; inspected preparation,
  evaluator and candidate runner code. Its Term2-specific fixtures, live launch
  and paid judge are unsuitable for this scoped testing-skill experiment. Reused
  history-free isolation, revision binding, negative controls, budget, cost and
  evidence-separation principles, without executing that runner.
- Personal-context skill/tool was attempted for prior work; tool returned
  “Personal context is unavailable for this conversation.” No unseen past results
  are assumed. Inspection is limited to accessible repository/PR material.

## Methodology actually loaded

Read the available cloud `SKILL.md` for personal-context, agentic-loop,
investigation, testing, implementation and code-review. Also read the repository
model-benchmark skill as noted above. No subagents, skill installations or skill
creator were used. No repository instructions required additional gates.

## Observed verification

Environment: Python 3.12.14, Linux, Python standard library, existing Git.

- `python3 -B -m unittest discover -s benchmarks/testing-skill -p 'test_*.py' -v`:
  **13 tests passed**. Covers fixture assertions/negative controls, pair identity,
  independent storage, complete skill/reference injection, deterministic ledger,
  overwrite refusal, setting/content drift, frozen oracles, unknown/missing
  evidence, serious failures, unauthorized edits, placeholder configs, invalid
  numeric measurements, ties and wins using explicitly synthetic reviews. Added
  regressions verify the exact ten-file skill allowlist excludes tracked eval
  answers and agent/asset metadata; write checks cover dotfiles, bytecode caches,
  empty directories, symlinks, permission changes, deletion, special files, exact
  per-case regular-file allowances and reverted writes in the event audit.
  Timeout and every measured budget override ordinary criterion failures while
  preserving independently observed serious failures.
- `python3 -B benchmarks/testing-skill/bench.py preflight --out /tmp/testing-pr9-fixes-preflight.json`:
  all eight expected fixture outcomes confirmed, including real failure at the
  removed guard, exit-0 zero discovery, and first-fail/second-pass retry. Raw
  smoke observations retained in `evidence/preflight.json`. Its pack hash binds
  source/config/docs/tests, excluding this preparation report and evidence
  subdirectory to avoid a recursive evidence hash.
- Prepared `/tmp/testing-pr9-fixes-pilot` with the example config and default
  3 repetitions: **48 workspaces**, exact old/new skill injection, prompt and
  fixture hashes, shuffled paired order, frozen oracles and review templates.
- Graded untouched preparation to `/tmp/testing-pr9-fixes-not-run.json`:
  **48 NOT RUN; 24 inconclusive pairs; 0 wins; 0 ties**. No model output exists.
- `git diff --check`: passed before publication. Reviewed all added handwritten
  files; fixed missing common agentic-loop references and validation edge cases
  in the original preparation, then applied the approved offline review fixes
  below. No new methodology skill was needed; the previously loaded testing,
  implementation and code-review skills were reused.
  No candidate skill file or unrelated repository file changed.

The temporary preparation directories are reproducible examples, not portable
real trial results. The checked-in preflight is deterministic smoke evidence;
variable elapsed times and temporary paths in raw observations are not quality
measurements. No paid API call or model inference was performed.

## Approved offline follow-up on support PR #9

Starting support revision: `1255736657097f868c5880f9e4f28e9d1b6eac9c`.
The parent authorized these three fixes; the existing branch/PR was reused.

1. Trial bundles now contain only a reviewed explicit ten-file allowlist of
   SKILL.md and needed transitive Markdown references. All 48 regenerated bundles
   were checked for exact file membership; no eval answers, assets or agent
   metadata are exposed. Both pinned Git trees still contain the excluded eval
   answer sources, which the regression test checks before testing exclusion.
2. No global `.attempt`/`__pycache__` exclusions or broad `checks/` write permission
   remain. Snapshot checks cover every retained filesystem entry and its kind,
   contents/target and permission mode. Only retry may create/modify the regular
   file `.attempt`; only hidden-bug may modify `checks/test_app.py` or
   create/modify `checks/test_regression.py`. All other paths/operations are
   denied, including directory/symlink substitutions at an allowed filename.
   Because snapshots cannot see reverted writes, review now requires a complete
   tool/subprocess write-event audit; absent audit coverage cannot produce PASS.
   Synthetic tests verify an unauthorized create/delete remains a serious failure
   even with an empty final diff. This is an evidence requirement, not a newly
   implemented live sandbox or process audit collector.
3. With valid infrastructure/isolation, serious failures remain FAIL even on a
   timeout/budget overrun. Otherwise exhaustion is INCONCLUSIVE before ordinary
   failed criteria can imply a correctness regression. Regression tests cover
   explicit timeout, wall-clock overrun, tool-call overrun and output-token
   overrun, both with and without a serious failure.

Run/fixture schema is now version 2; old preparations must be regenerated, and
old-format grading fails explicitly. The new offline preparation reports 48
NOT RUN, 24 inconclusive pairs and zero model calls. Current pack hash recorded
in the regenerated preflight:
`08627a0cbde05c14db2520c8a91aeb70e5c068b50ba1cdb10ae94cf7e6eb5be2`.

## Remaining step

Obtain separate approval for live model trials, choose and pin the real harness,
model, system prompt and sandbox environment, then follow README's manual trial
procedure with a new filled-config preparation. No live adapter or sandbox has
been selected or validated here. If the chosen harness cannot enforce isolation
or budgets, classify that as infrastructure unavailable and resolve it before
claiming a comparison. Actual behavioral quality and PR #7's merge agreement
remain unverified; nothing in this pack authorizes merging.
