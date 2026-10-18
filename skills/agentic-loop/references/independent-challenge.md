# Independent challenge and search-direction review

Use this when a task is high-risk, a branch stalls, evidence contradicts the plan,
or the explorer's assumptions might have narrowed the solution space too early.
This adapts adversarial verification principles; it does not require copying an
external workflow or spawning reviewers on every task.

## Two distinct questions

- **Outcome verification:** Does independently observable evidence prove the
  result satisfies the original acceptance criteria?
- **Direction review:** Is this still the right problem and approach to pursue,
  given the original goal, alternatives, evidence, and remaining budget?

A locally correct artifact may still solve the wrong problem. Never let
implementation-defined tests silently replace the original success criteria.

## Cheap observer first

Use available objective signals: repeated identical failures, no reduction in
unmet criteria, unchanged evidence, rising time/token cost, unsupported
assumptions, unexplored alternatives, or contradiction with the original goal.
Do not treat activity or a self-reported confidence score as progress.

Trigger a fresh challenge when signals warrant it, at consequential irreversible
decisions, or before accepting high-impact conclusions. Avoid continuous
multi-agent review for low-risk work.

## Challenge protocol

Give the challenger the **original goal and authority**, acceptance criteria,
raw observations with provenance, current proposed direction, explicit
assumptions, budget, and known alternatives. Withhold the explorer's persuasive
narrative or detailed reasoning when possible, to reduce anchoring. Do not
withhold material facts or constraints.

Ask the challenger to produce:

1. The most consequential assumption that may be false.
2. A plausible alternative branch, including a broader search if needed.
3. The cheapest discriminating experiment that could falsify the current path.
4. A recommendation: CONTINUE, INVESTIGATE, BACKTRACK, or STOP, with evidence,
   uncertainty, and cost.

A different model or fresh context can help, but independence comes from
**distinct evidence and tests**, not merely a second agent's opinion. Challenger
recommendations are hypotheses to verify, not automatic authority.

## Backtrack without losing knowledge

Record the branch's assumptions, added constraints, actions, evidence, and
failure reason. Identify the earliest unsupported constraint; relax or replace
it and test a materially different branch. Preserve reusable evidence and
invalidate only dependent claims. Do not backtrack merely because a challenger
disagrees; seek a discriminating observation first.

If all reasonable branches are exhausted, stop within budget and report the
remaining uncertainty rather than manufacturing a PASS.

## Completion gate

Before VERIFIED, establish both:
- **Result:** independent evidence supports each original criterion.
- **Direction:** no material unresolved contradiction suggests the task solved
  a narrower or different problem than the user requested.

Use proportional checks. The goal is catching shared blind spots, not proving
absolute correctness or creating endless review loops.
