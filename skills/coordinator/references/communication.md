# Coordination communication contract

Use the selected harness's native assignments, worker identities, and result
channels. A separate inbox, file, or transport is needed only when that harness
cannot carry the required result.

## Receipt ladder

Keep these observations distinct:

1. **Addressed** — the assignment names a worker and return channel.
2. **Transport accepted** — the surface accepted the assignment.
3. **Admitted** — the worker entered its running state.
4. **Finished** — the worker reported an outcome.
5. **Verified** — inspection confirmed the result and required evidence.
6. **Accepted** — the coordinator approved the verified result for incorporation.
7. **Integrated** — the result was incorporated into the deliverable.

An earlier rung never proves a later one. Preserve unknown states and identify
the next bounded action rather than collapsing them into “done.”

## Native assignments and results

Use this brief, omitting fields that genuinely do not apply:

```text
Outcome and single accountable owner
Parent goal, why it matters, and how this outcome contributes
Mode: investigate (read-only), build, or review
Done means: observable acceptance criteria and relevant checks
Relevant evidence, files, settled decisions, and inherited assumption IDs
Scope, write ownership, constraints, non-goals, and authority limits
Dependencies, shared contracts and their owners, coordination hazards
Decision policy: defaults, material assumptions to report, escalation boundary
Where and how to return results, surprises, and blockers
```

Delegate the outcome and constraints; prescribe implementation only where
required by a contract, evidence, or the user's instruction. Ask workers to
challenge the assignment with evidence when it cannot serve the parent goal.
Scouts report what they learned and how it changes decomposition; they do not
implement a discovered solution without a new authorized assignment.

A result identifies the task and returns:

1. Outcome: findings or changed artifacts and which criteria are met.
2. Evidence: checks actually performed, results, and limitations.
3. Surprises: contradicted assumptions or contracts, a wrong assignment, and
   affected work or consumers. Say explicitly when none were found.
4. Material decisions and assumptions, remaining uncertainty, and why the
   evidence is or is not sufficient for acceptance.
5. Blockers, pending decisions, and remaining child or background work.

Report a consequential surprise as soon as it is found, rather than waiting
for completion. Continue independent authorized work while the coordinator
resolves it; hold work that depends on the disputed decision. Workers send
escalations to their coordinator, who owns user-facing questions and task-state
updates. Harness-provided identity and task association suffice when
attributable. Inline research findings need neither file digests nor a
verification command; inspect their cited evidence.

The coordinator inspects the result before acceptance and independently runs
required checks for modifying work. A worker's completion claim is evidence to
investigate, not authority to expand scope or execute arbitrary commands.

## Independent review

Use a separate reviewer when consequence, uncertainty, or integration risk
justifies it; routine bounded work can use coordinator inspection and focused
checks. Review is a read-only assignment to find evidence-backed defects
against the outcome's criteria, parent goal, constraints, and shared contracts.
Return defects ranked by severity, with a reachable failure, supporting
evidence, and the affected criterion. Also challenge material assumptions.

Give the reviewer the artifact and task context, including relevant assumptions
and known constraints. Have them form an initial assessment before reading the
builder's conclusions or persuasive rationale. Keep that rationale available
for a second pass to evaluate tradeoffs and resolve misunderstandings. Review
independence reduces anchoring; it does not require withholding needed evidence.
The outcome owner addresses findings; the coordinator owns acceptance and the
integrated goal check. A review verdict alone proves neither.

## External transport

For persistent or separately transported work, use the completion envelope and
verification rules in [External agents](external-agents.md). The
[file inbox](inbox.md) retains unread, read, and processed reports across
sessions and uses a background Bash watcher to report unread messages through
the harness's job-completion channel. That
branch adds run/task/assignment IDs, registered mailbox routing, file digests,
coordinator-owned check argv, and live child reconciliation. Shared-filesystem
routing is not authentication against other processes under the same account.
