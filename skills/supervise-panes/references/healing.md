# Bounded recovery, separate rule repair

Recover the authorized task, not the appearance of a clean run. A refusal may
correctly enforce a contract; an error or manual workaround is evidence to
investigate, not proof the guard is wrong. Use existing debugging, implementation,
testing, and bug-retro methods as applicable, not a new healing subsystem.

- **Diagnose:** retain the exact command, exit/output, intended effect, and actual
  effect. Distinguish task/source failure from invalid input, stale context,
  helper/instruction defect, or environment failure. Use the smallest check that
  separates plausible causes; do not label an unexplained failure pre-existing.
- **Reconcile:** inspect receipts, task-owned resources, and partial output before
  retrying. Unknown launch/delivery is not non-delivery. Follow the existing
  [delivery recovery contract](external-agents.md#dispatch-and-supervise); reuse
  a recovered owner rather than creating a duplicate. Do not restore protected
  originals from a late snapshot to erase failure evidence.
- **Recover:** when effects are understood and authority covers the correction,
  repair only owned input/output or task source and rerun the failed check plus
  relevant boundary checks. Correct invalid owned input for the same worker,
  without recreation or guard overrides. An incompatible shell wrapper can use
  the existing explicit-exit-capture recipe. Retry only
  after evidence supports a corrective action; if it fails unchanged, stop that
  path and return the blocker. Continue unaffected work.
- **Contain:** if effects, ownership, authority, or the preservation oracle are
  uncertain, hold dependent work and name the evidence/decision needed. No blind
  resend, unsafe reset, check suppression, or claim that later consistency proves
  entry preservation. Follow the main skill's preservation contract.

Runtime recovery does not authorize changing the rules governing that run.
Route an observed helper/instruction defect as a separately owned, bounded repair
candidate within existing authority; otherwise defer it with a next action. Keep
live consumers and their original CLI/return contracts working. For a helper
repair, reproduce the defect in a failing test, fix it, rerun regression/boundary
checks, and obtain required independent inspection. For behavioral instructions,
use `workflow-evolution` with a separate candidate and comparison. Activation uses
proportionate checks and required independent review under the
[risk-based real-use policy](real-use-verification.md), not a separate exercise
merely because instructions changed. Do not mark an unreviewed edit promoted or
install it in-flow.

At the next existing checkpoint, link the retained failure, diagnosis, correction,
checks, and remaining uncertainty in an [incident note](retro.md); do not put a
new report or retrospective ahead of ready work. After verified recovery,
continue the next authorized action with its owner. Capture the bug-retro
regression/lesson in the owning task or repair candidate; deferred repair is not
healed behavior, and passing local recovery is not skill promotion.
