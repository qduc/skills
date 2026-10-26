# Coordination communication contract

Use the selected harness's native assignments, worker identities, and result
channels. A separate inbox, file, or transport is needed only when that harness
cannot carry the required result.

## Contents

- [Native assignments and results](#native-assignments-and-results)
- [Independent review](#independent-review)
- [External transport](#external-transport)

## Native assignments and results

A brief says only what this task needs:

- the goal, and why it matters
- where to work (worktree or branch), and whether the work is read-only
- what done looks like, and the checks that show it
- anything non-obvious: relevant files, settled decisions, known traps
- where to write the report

Don't restate standing rules. Workers already get the global and project
AGENTS.md (billing, pushing, preserving others' work, test policy), and an
unattended worker already knows it can't ask the user. Repeating those in every
brief buries the task. Add a limit only when it is specific to this task, such
as "read-only" or "don't touch the live bridge".

The worker writes the report file last; its existence is the completion signal.
A report older than the dispatch or the latest steer doesn't count.

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
updates.

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

Separate substantive uncertainty from report packaging. The coordinator can check
an exact path, cwd, citation, or receipt directly and request a narrow correction.
Do not commission recursive reviews solely to validate a report's packaging. After sufficient
inspection, continue the next authorized action rather than reviewing readiness
again.

## External transport

For persistent or separately transported work, use the completion envelope and
verification rules in [External agents](external-agents.md). The
[file inbox](inbox.md) retains unread, read, and processed reports across
sessions and uses a background Bash watcher to report unread messages through
the harness's job-completion channel.
