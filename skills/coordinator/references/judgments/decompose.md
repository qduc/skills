# Judgment: decompose the goal into outcomes and checks

You are turning the user's goal into a small plan the driver can execute. Read
the repository at `repository` before deciding; for `delivery: artifact`, read
the original material at `source` instead. The file list is only a start.
Your answer becomes binding contracts, so everything in it must be true and
runnable.

## Outcomes

Each outcome is one worker's bounded job with one accountable result.

- **Split only at real seams.** Two outcomes are independent when each can be
  built and checked without the other's result, judged against the code's actual
  consumers. Disjoint files alone do not make work independent. When in doubt,
  use fewer outcomes; one outcome is a fine plan for a focused change.
- **Order dependencies.** `needs` lists outcomes that must be integrated first.
  A dependent outcome starts from a base that already contains them. Settle any
  shared interface inside the first outcome's contract so dependents can rely on it.
- **Write the contract for a worker with no other context.** `objective` says the
  observable result, `rationale` says why it matters, `scope` says what to touch and
  what not to, `authority` says what the worker may decide on its own.
- **Checks prove the outcome, not just that something ran.** Each check is argv
  run without a shell from the outcome's worktree root; exit 0 means pass. Prefer
  focused existing tests plus new tests the worker must make pass. A check that
  passes before the work is done proves nothing. Use `python3 -c ...` or
  `sh -c ...` when you need a small inline assertion.
- **Tests come first.** Unless the task turned it off, each outcome gets a
  separate checks phase: a worker writes the tests before anyone implements, at
  least one of your checks must fail once they exist, and the tests are reviewed
  for missing cases. So a check may run a test file that does not exist yet
  (`python3 -m unittest test_feature.py`); say in the `scope` what that file must
  cover. The implementing worker cannot modify those approved tests.

For `delivery: artifact`, each outcome also needs `artifact`: one relative file
path such as `report.md`, `data.json`, or `chart.png`. The worker starts in an
empty workspace and reads original material at `source` without editing it.
Already accepted dependencies are at `inputs/<outcome-id>/<artifact>`; an
outcome's checks run beside its output. No test-writing phase is added. Goal
checks run from `repository`, where accepted files appear at
`artifacts/<outcome-id>/<artifact>`. Plan meaningful content/format checks and
state which claims need semantic source inspection. Do not require reports or
binary files to be Git patches. Omit `artifact` for patch delivery.

## Goal checks

Goal checks run from the repository root after every outcome is integrated.
They are the definition of done for the whole task, so derive them from the
`acceptance_criteria`: every criterion should be covered by at least one goal
check, and goal checks should exercise the combined behavior, not repeat a
single outcome's check. Name the cases a too-eager or too-narrow solution would
get wrong, not only the main behavior. At least one goal check must fail on the
current code; the plan is refused otherwise, because a goal that already passes
its checks cannot show the work was done.

## Replanning

When `mode` is `replan`, the previous plan's outcomes are already integrated on
the branch; `failure` says what went wrong and `user_guidance` (if present) is
the user's direction. Plan only the additional work needed. You must keep every
check in `required_goal_checks` exactly as it is; you may add goal checks but
never drop or weaken one, because replanning never lowers the bar for done.

`rationale` should explain the split (or why one outcome is enough) in a sentence.
