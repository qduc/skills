# Runtime contracts

Read this before dispatching an outcome-plan assignment through native worker tools
or a non-interactive command. The shared interface is `discover`, `start`, `observe`,
`control`, and `reconcile`. Runtime facts are evidence for Coordinator, never acceptance.
The existing [external lifecycle](external-agents.md) remains the terminal/Herdr
implementation for established tasks; do not restart an existing task in a new
runtime merely to use this interface.

## Selection and dispatch

`coord_runtime.py discover --runtime native|process` returns explicit capabilities.
Select engineering method separately with `--protocol` and supplied `--catalog`
paths. Missing optional methods fall back to the bounded-worker workflow; a missing
supplied catalog is an error. Selected skill text is snapshotted into the attempt.

Create a route JSON matching one entry in the task's confirmed selection pool:
`{"harness":"term2","model":"<confirmed-model>","provider":"<confirmed-provider>"}`.
Start with:

```text
coord_runtime.py start --task-dir <task-dir> --owner <owner> --revision <revision>
  --outcome <id> --runtime native|process --route-file <route.json>
  --protocol <method> --catalog <installed-catalog>
```

Only process runs require `--command-file <argv.json>`. Exact argv elements
`{prompt}`, `{assignment}`, and `{cwd}` are substituted. The command is executed
without a shell in the contract's working directory. Supply explicit harness flags
matching the confirmed route; discover CLI syntax from its installed help. This
runtime does not infer models or providers from argv or rotate the selected pool.

For Term2's non-interactive branch, use its selected provider/model, `--auto-approve`
when authorized local tool execution is required, and a positional `{prompt}`.
This branch cannot accept corrections. Read the Term2 skill before using it.

## Native host

`start` saves intent and returns a host `spawn` request. Execute it through the
host's native worker tool only while still owning the task, then immediately bind
the returned handle:

```text
coord_runtime.py bind-native ... --outcome <id> --attempt-id <attempt-id> --handle <host-handle>
```

No Python adapter pretends to invoke a host tool. If a host call's result is lost,
inspect the host before binding or replacing the attempt. A second `start` is
refused while any attempt is recorded. Native delivery uncertainty requires human
or host reconciliation; absence of a handle does not establish non-delivery.

Use native wait/inspection tools to obtain current observations, then supply a JSON
file to `observe --observation-file`: `{"handle":"<bound-handle>","status":"finished"}`.
Supported statuses are `working`, `finished`, `stopped`, and `unknown`. This is
Coordinator's record of a host observation, not a worker-provided completion claim.
Without an observation, `observe` returns an inspection request and claims no live
status. `control --action stop|correct` returns a host request for the same handle;
execute only supported host operations and observe their result before proceeding.
Native host actions rely on the host's ownership discipline at the tool-call seam.

## Non-interactive process

`start` persists launch intent before starting a separate receipt-writing launcher.
The launcher inherits the ownership lock through process creation and receipt
publication, so Coordinator interruption does not permit a competing owner to
launch against that in-flight operation. It releases the lock once the durable
process identity is saved; the worker can then finish while Coordinator is offline.
Terminal receipts require settlement of the owned process group, including
ordinary subprocesses. Commands must not detach or move jobs outside that group.
Remaining group members are stopped when the command leader exits.

`observe` reads the receipt and checks Linux process identity using PID plus process
start time. A disappeared process without a terminal receipt stays unknown. Logs
and reports are retained under `<task-dir>/attempts/<attempt-id>/`. Start never
repeats a recorded attempt. A busy record during launch means reread and retry
observation, not restart. Observation is bounded and does not wait for task completion.

`control --action correct` explicitly fails. For a correction, reconcile the worker,
request a stop, verify settlement, then revise the assignment and start a new attempt.
`control --action stop` signals only a matching owned process group; signalling does
not itself establish settlement. Record the eventual receipt with `observe`.
All mutation commands require task directory, owner, revision, and outcome ID.

Observation and stopping an existing attempt remain available after a goal or
authority change, so old execution can settle before replanning. New dispatch,
correction, verification, and acceptance require the current authorized goal.

If a launcher dies before its terminal receipt, or native host inspection proves
a saved request was never delivered, record the actual inspection in a JSON file:
`{"attempt_id":"<current-attempt>","status":"stopped","basis":"<observed resource facts>"}`.
Statuses `finished`, `stopped`, and `not_started` are allowed. Run
`coord_runtime.py reconcile ... --attempt-id <id> --evidence-file <inspection.json>
--decision <coordinator judgment>`. Known live process/launcher identities and
process-group members prevent settlement. Missing files alone are not evidence
of non-delivery; inspect the host and owned resources first. The owner-fenced
operation retains hashed evidence and the prior receipt. Only then verify a
finished result, or explicitly revise and dispatch another assignment.

The process runtime currently requires Linux `/proc`; native host observations are
host-dependent. Unknown launch/delivery windows are preserved, not advertised as
exactly-once execution. Retain workspaces until checks, integration, and archival
have finished, or preserve the required evidence before retiring them.
