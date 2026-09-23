# Milestones, contracts, and rolling integration

Use this reference when several dependent outcomes need staged delivery,
milestone checks, or ongoing supervision. Keep a single coordinator and direct
workers when that is sufficient. The size of a task alone does not justify
additional management levels.

## Plan milestones and waves

Define milestones as observable progress toward the parent goal, each with
success criteria and an integration check. Begin with the smallest useful
end-to-end slice that exercises the important boundaries. It may use explicit
stubs where necessary, but distinguish scaffold evidence from verified behavior.

Order work by dependencies. Start a wave once the decisions and contracts it
requires are settled, even if unrelated work from an earlier wave continues.
Use work-item edges for actual prerequisites; avoid artificial barriers between
independent lanes. Record milestone membership, owners, and checks in task
state so another session can resume the plan.

## Own contracts at the seams

For each shared interface, schema, or cross-lane behavior, record its current
agreement, one accountable owner, affected consumers, and a check that exercises
the agreement. The default owner is the coordinator common to those consumers;
delegate ownership explicitly if that coordinator becomes a bottleneck.

Lanes propose changes with evidence and affected consumers. The owner decides
within existing authority, coordinates transition ordering, updates the record,
and confirms affected assignments received the change before dependent work
resumes. Preserve old agreements as superseded when needed to explain existing
artifacts. A lane cannot silently change a contract that siblings rely on.

## Add lane owners only when useful

A lane owner owns a sub-goal and runs the same understand, plan, assign, inspect,
and integrate loop within its authority and selected harness/model pool. Give
it a bounded resource budget and a supported return channel. Confirm that the
surface supports child delegation before assigning a role that requires it;
otherwise keep the topology flat.

The parent assigns and steers lane owners; lane owners manage their children.
Escalate evidence that affects a shared contract, sibling lane, parent goal,
acceptance criteria, or authority boundary. Resolve purely local execution
choices locally. Outcome ownership and durable record ownership are distinct:
the main coordinator remains the sole writer of the authoritative task record.
Lane owners return proposals and evidence for it to checkpoint; subsidiary
artifacts are linked supporting material, not competing sources of truth.

## Integrate throughout delivery

Choose integration points around available end-to-end slices and contract
changes, and assign who performs integration. Incorporate accepted compatible
results as they become available; exercise the real seams before many consumers
accumulate. Isolate incompatible partial work and serialize integration that
shares mutable state. Record what is actually integrated and which checks ran.

At each milestone, verify the integrated slice against its own criteria and
its contribution to the parent goal. Passing component checks does not establish
that contribution. If it misses, revisit understanding, identify the faulty
assumption or missing outcome, and revise affected waves before expanding the
implementation. Continue independent work when its basis remains valid.

Use milestone handoffs for the decision policy's batch review. Surface evidence
that the goal or its rationale has changed to the user; keep working within the
current authorized goal until a change is agreed. Close the overall task only
after goal-level verification and the main skill's acceptance, decision, and
resource cleanup requirements are satisfied.
