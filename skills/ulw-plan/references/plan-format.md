# Plan format

The plan is Markdown for people and uses the concepts coordinator keeps in its
task state, so a coordinator session can load it without re-planning. The
comment after each heading names the coordinator field it maps to. Omit a
section that genuinely does not apply rather than filling it with "none".

```markdown
# <title>

## Summary
What will be true when this is done, for whom, the approach in a sentence or
two, the main exclusions, rough size (quick / short / medium / large /
multi-session), the main risk, and the decisions made on the user's behalf.
Written last.

## Goal
<!-- objective; rationale and non-goals as intent notes -->
One observable outcome, why it matters, and who it is for.

Non-goals:
- Explicit exclusions, including the scope creep flagged during planning.

## Acceptance criteria
<!-- acceptance_criteria -->
- AC-1: A checkable statement about the delivered result, with the command,
  request, or action that proves it.

## Authority and constraints
<!-- authority, constraints -->
What the executor may do without asking (branches, local runs, dependency
changes, commits) and what it may not (deploys, data migration, publishing),
plus technical constraints discovered during exploration.

## Decision defaults
<!-- notes, kind: decision_policy -->
How the executor should resolve choices the plan doesn't settle: which
reversible defaults to apply and record, and which kinds of choice to bring
back to the user.

## Assumptions
<!-- notes, kind: assumption -->
- A-1: The assumption. Evidence. If wrong: consequence. Reversibility and how
  to undo it. Affects: work item IDs. Depends on: assumption IDs.

## Pending decisions
<!-- pending_decisions -->
Decisions the user still has to make, with the recommended option and the work
each one blocks. Empty when the plan was approved with everything settled.

## Contracts
<!-- notes, kind: contract -->
- C-1: A shared interface, schema, or behavior more than one work item relies
  on: the agreement, the consumers, and the check that exercises it. Settle it
  before dependent items start.

## Milestones
<!-- work_items.milestone -->
- M1: The smallest end-to-end slice that exercises the important boundaries,
  and the check that shows it works.
- M2: ...

## Work items
<!-- work_items: id, status, needs, write_scope, milestone -->
### <id> — <outcome>
- Mode: investigate, build, or review
- Milestone: M1
- Needs: <ids of real prerequisites only>
- Write scope: <exact files or directories; "every X in Y" for sweeps>
- Follow: <existing pattern to copy, with path:line>
- Must not: <what this item must not touch or add>
- Done means: <observable criteria and the ACs this item serves>
- Check: <exact command or action, and the expected result — including a
  failure case when the item handles bad input>
```

## Guidance

- Work items are outcomes, not steps. Size each so one owner can deliver and
  verify it; keep a single hard problem whole rather than splitting its
  reasoning across owners.
- Implementation and its test belong to the same work item.
- Record only real prerequisites in `Needs`. Disjoint files do not make items
  independent when they share a contract, and a shared contract does not
  make items sequential once it is settled.
- Leave owners, workers, harnesses and models out. Coordinator assigns them.
- Every acceptance criterion should be served by at least one work item and
  proven by at least one check.
