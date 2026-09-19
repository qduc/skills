# File inbox and coordinator wakeups

Use a local filesystem inbox for external workers that share this machine.
There is no messaging service or database. Native workers retain their native
result channel. Source scripts live in this skill. Durable inboxes live alongside the task record,
outside skill packages and worker workspaces. New assignments also receive a
workspace-local delivery bundle so sandboxed workers can publish.

## Layout and ownership

Prepare a lifecycle run at `<task-dir>/lifecycle.json`. Its default inbox root is
`<task-dir>/inbox/<run-id>/`. An explicit `--inbox <directory>` overrides the root.
Each registered worker assignment gets an opaque subdirectory:

```text
<task-dir>/inbox/<run-id>/<assignment-id>/
  unread/<message-id>.json
  read/<message-id>.json
  processed/<message-id>.json
```

For each new dispatch, the helper stages `.coord/<run-id>/<assignment-id>/`
inside the worker's assigned directory. It contains the brief, assignment,
pinned reporting scripts, and delivery directories. Keep `.coord/` out of commits.
The generated reporting command uses this copy, insulating in-flight workers
from skill updates. The worker should send an initial progress report to confirm
it can publish under its actual sandbox. Do not assume arbitrary `/tmp` paths
are writable: a harness may grant only its private temporary directory.

`receive` and `watch` copy immutable delivery messages to the durable inbox,
preserving message IDs. Only the durable inbox tracks read/processed state.
Repeated harvesting cannot resurrect an acknowledged report. A missing delivery
directory is an error until explicitly retired, not evidence of no reports.

The helper persists the assignment-to-worker mapping and generates an
`assignment.json` descriptor before sending the brief. Workers receive their
assignment descriptor and reporting command. The coordinator is the sole
reader-state writer; workers publish separate immutable files. This is routing
attribution among cooperative workers sharing a user account, not authentication
against malicious processes with access to that account. Keep acceptance checks
independent of report claims. Remote hosts require a shared supported transport;
this design does not promise network-filesystem semantics.

## Publish, inspect, process

Run commands through `python3 <skill-dir>/scripts/coord_lifecycle.py`.
All bound mutations, including `mark-read`, `ack`, and `preserve`, require
`--owner <session-token> --revision <number|latest>`. Supply your session's owner
token explicitly. `latest` checks the current revision under the task lock and
still rejects stale owners; a numeric revision additionally rejects intervening
checkpoints. Reads, watches, and worker reports need neither flag.

- `prepare --state <task-dir>/lifecycle.json --task-dir <task-dir> --task-id <id> --owner <session-token> --revision latest --verify-command '<JSON argv>'`
  creates the run. The ID must equal the durable task ID; use different lifecycle
  filenames for separate runs or milestones under that task. Use the existing run when resuming; prepare refuses overwrite.
- `report --assignment-file <path> --kind <progress|blocked|complete>`
  builds and publishes a worker report from the generated assignment descriptor.
  It uses a unique filename, fsync, and atomic rename on the same filesystem.
  Incomplete temporary files are invisible to readers.
- `receive --state <path>` returns all unread and read-but-unprocessed reports,
  each with message ID, mapped worker, assignment ID, and read status. It harvests delivery files and leaves
  read/processed status unchanged. Add `--unread-only` to filter or `--wait <seconds>` to wait.
- `mark-read --state <path> --worker <name> --message-id <id> --owner <session-token> --revision latest` marks a report read
  after the main agent inspects it. Seeing a wake notification is not reading.
- `ack --state <path> --worker <name> --message-id <id> --outcome <summary> --owner <session-token> --revision latest`
  records the handling outcome in lifecycle state, then archives the report as
  processed. First checkpoint the corresponding decision in durable task state.
  Acknowledgement means handled; an outcome can be blocked or rejected, not just
  successful completion. Retries preserve processed status.

The dispatch script embeds the reporting instructions in the worker brief.
Workers append only the outcome-specific arguments to the supplied command:

```text
report --assignment-file <path> --kind progress --summary "<update>"
report --assignment-file <path> --kind blocked --summary "<blocker>"
report --assignment-file <path> --kind complete --artifact <path>
```

For completion, add `--children-file <path>` if children were started. Its JSON
array contains objects with each child's stable `name`. Declare all children;
the coordinator still reconciles them with live state. Artifact paths can be
absolute or relative to the assigned working directory and must resolve inside
it. The helper validates the file and computes its SHA-256.

The generated descriptor supplies `run_id`, `task_id`, `assignment_id`, `worker`,
and the coordinator's verification argv. The report command fills these fields,
adds the outcome, and atomically publishes the result. Workers do not construct
protocol JSON, choose a return address, or copy verification commands manually.
The report command does not run the check or imply that it passed; acceptance
still requires independent verification. Keep the descriptor unchanged.

The low-level `send --inbox <path> --message-file <path>` remains available for
transport recovery/testing with already-built JSON; normal workers use `report`.
Workers never update task state or acknowledge their own messages.

Reading does not imply handling: a crash after mark-read leaves the report in
`read/` for resume. A crash after the handling checkpoint but before ack can
redeliver it; reconcile message IDs with recorded outcomes before repeating side
effects. Publication retries can create another message ID, so also reconcile
assignment outcomes. Delivery is at least once, not exactly once. Malformed
messages are returned with an error and retained for explicit disposition.
`stop` preserves all reports; it has no daemon or inbox directory to delete.

## Preserve before cleanup

After the worker and its declared children/background jobs are settled, run:

```text
preserve --state <path> --worker <name> --owner <session-token> --revision latest
```

This harvests reports, copies artifacts from unread/read/processed completion
reports into the durable inbox's `artifacts/`, verifies their reported hashes,
and records a manifest before retiring workspace delivery. Hash changes or
missing artifacts block preservation. It does not accept the result or remove
files. Only after successful preservation and independent acceptance may you
remove the worker workspace. `reconcile --disposition close-owned` also performs
preservation before closing the pane. External `git worktree remove`/`rm` cannot
be intercepted by this helper; never run them ahead of preservation.

An old inbox inside a worktree needs explicit copying and verification outside
that worktree before cleanup; the helper refuses to certify that layout durable.

## Wake the main agent

Start one background Bash job per lifecycle run through the harness's normal
background shell facility:

```bash
bash <skill-dir>/scripts/watch_inbox.sh <task-dir>/lifecycle.json
```

The script stays quiet while waiting. When unread messages exist, it prints a
JSON `inbox_unread` event and exits successfully, allowing the harness to report
the background job's completion to the main agent. The event includes the state
path, message IDs, mapped workers, assignment IDs, and read status, not report
text. No callback command or custom hook is configured.

Keep the job attached to the harness's background-job tracking; record its job
identifier in task state. A detached `nohup` process or shell `&` alone may only
write to a log, so use the harness facility that reports job completion to the
agent. If the harness requires collecting background output explicitly, collect
that job's result at the next supported check-in; do not claim that starting a
Bash process by itself resumes an idle model.

The Bash script repeats bounded Python watches internally, checks at most one
second apart, and suppresses empty timeout output. Each watch reloads worker
registration, so it can start before dispatch. It exits on an unread report or
an error or a fallback check-in, forwards termination to its active child, and leaves message state
unchanged. An optional second argument sets the positive check window in seconds
(up to 60; default 60). A third positive integer sets the fallback interval
(default 300 seconds). If no report arrives, the script emits `fallback_check_in`
and exits within that interval plus one check window. On this event, inspect
recorded workers with the Herdr helper's `observe`, resolve blockers, and re-arm
the watcher. Quiet workers cannot leave an otherwise healthy watcher waiting
forever. A fallback is a coordinator inspection event, not a request for routine
user-facing status updates.

On job completion, receive and inspect reports, mark them read, handle and
checkpoint outcomes, ack handled reports, then start the watcher again. Keep
only one watcher active per run. Existing unread messages trigger immediately,
including messages published while the watcher or main agent was offline.
Repeated notifications have the same message IDs until marked read. Check that
`mark-read` succeeded before re-arming; a prior `receive` is not a read receipt.

If the watcher fails or disappears, recover the reported error and restart it.
On every resume, inspect both unread and read-but-unprocessed reports before
waiting again. Background output availability and automatic agent continuation
are distinct harness capabilities; durable messages work regardless.

## Retiring the old transport

Keep each in-flight worker's original return contract until it finishes. A
worker given a terminal marker or an older reporting command will not learn a
new protocol merely because installed scripts changed. Recover its result using
the original contract and record that disposition. Do not silently retrofit its
assignment or restart it to migrate the transport.

New runs use file inboxes exclusively. Old named-inbox lifecycle state is not
silently converted: first recover any outstanding reports and reconcile workers,
then prepare a new file run and give any retained worker its new assignment
contract. Old unread transport messages are not imported automatically. The
helper no longer invokes or configures the retired transport.
