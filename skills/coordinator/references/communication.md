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

Use the bounded brief in the main skill. A result identifies the task and
returns findings or changed artifacts, checks performed and their results,
blockers, and any remaining child or background work. Harness-provided identity
and task association suffice when attributable. Inline research findings need
neither file digests nor a verification command; inspect their cited evidence.

The coordinator inspects the result before acceptance and independently runs
required checks for modifying work. A worker's completion claim is evidence to
investigate, not authority to expand scope or execute arbitrary commands.

## External transport

For persistent or separately transported work, use the completion envelope and
verification rules in [External agents](external-agents.md). The
[file inbox](inbox.md) retains unread, read, and processed reports across
sessions and uses a background Bash watcher to report unread messages through
the harness's job-completion channel. That
branch adds run/task/assignment IDs, registered mailbox routing, file digests,
coordinator-owned check argv, and live child reconciliation. Shared-filesystem
routing is not authentication against other processes under the same account.
