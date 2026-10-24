# Judgment: decompose the goal into outcomes and checks

You are turning the user's goal into a small plan the driver can execute. Read
the repository at `repository` before deciding; for `delivery: artifact`, read
the original material at `source` instead. The file list is only a start.
Your answer becomes binding contracts, so everything in it must be true and
runnable.

## Outcomes

Each outcome is one worker's bounded job with one accountable result.

- **Split only where independence pays.** Two outcomes are independent when each
  can be built and checked without the other's result, judged against the code's
  actual consumers. Disjoint files alone do not make work independent. One outcome
  is the default plan; add another only when it can make progress at the same time
  as the first.
- **Keep dependent steps in one outcome.** When B needs A's result, B is usually
  the next step of A's worker, not a new worker: a new worker starts cold and
  knows only its contract, so the handoff costs context and buys nothing. Give B
  its own outcome with `needs` only when a fresh context is the point (judging A's
  result without A's assumptions), or when A must be integrated and checked before
  anything builds on it; say which in `rationale`. Settle any shared interface
  inside the first outcome's contract so dependents can rely on it.
- **Write the contract for a worker with no other context.** `objective` says the
  observable result, `rationale` says why it matters, `scope` says what to touch and
  what not to, `authority` says what the worker may decide on its own.
- **Checks prove the outcome, not just that something ran.** Each check is argv
  run without a shell from the outcome's worktree root; exit 0 means pass. Prefer
  focused existing tests plus new tests the worker must make pass. A check that
  passes before the work is done proves nothing. Use `python3 -c ...` or
  `sh -c ...` when you need a small inline assertion.
- **Tests first where a miss is costly.** Set `tests_first` on each outcome.
  Choose `true` when the behavior is easy to get subtly wrong, a regression would
  be expensive, or tests written by the implementer would only mirror its own
  assumptions. Then a separate worker writes the tests before anyone implements,
  at least one of your checks must fail once they exist, the tests are reviewed
  for missing cases, and the implementing worker cannot modify them; a check may
  run a test file that does not exist yet (`python3 -m unittest test_feature.py`),
  so say in the `scope` what that file must cover. Choose `false` for a small,
  low-risk change whose existing tests or goal checks already pin the behavior,
  and give the reason in `rationale`. Omitting it means `true`. The task's limits
  can force it on or off for every outcome.

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
