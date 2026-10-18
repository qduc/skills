# Judgment: recommend the worker harness and model

You are recommending which configured worker routes should run this task's
outcomes. Your answer is a recommendation only: the user confirms it before any
worker starts, so explain the choice in a sentence they can judge quickly.

Choose only from `routes`; those are the routes with a working command on this
host. Recent choices for the same project are in `recent_choices`. Reusing a
choice the user made before is a good default when the work is similar; say so.

Weigh:

- **Difficulty and size of the goal.** Small, well-specified changes do not need
  the strongest model. Unfamiliar codebases, subtle invariants, or wide changes do.
- **Independent retries.** The driver rotates through the pool on retries, so a
  second route in the pool gives a failed outcome a genuinely different attempt.
  Add one when the work is risky; keep a single route when it is routine.
- **Cost of a wrong attempt.** Every attempt is checked independently, so a
  cheaper route that sometimes fails is fine when checks are strong.

The rationale should name the deciding factor ("parser work in one module,
moderate size"), not restate the routes.
