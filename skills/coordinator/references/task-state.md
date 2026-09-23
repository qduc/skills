# Durable task state

The main agent owns the task record. Use the bundled `scripts/coord_state.py`
for persistence, ownership, and discovery. Workers return evidence and reports;
they do not edit task state. Keep the snapshot concise and link detailed evidence.

## Storage

The helper resolves `${XDG_STATE_HOME}/coordinator` when `XDG_STATE_HOME` is
absolute, otherwise `~/.local/state/coordinator`. An explicit `--root <directory>`
before the subcommand overrides it; retain that root when resuming.

Each task gets `tasks/<task-id>/state.json` as its authoritative record and a
**generated** `state.md` view. Never edit the view as state. A Markdown-view write
failure leaves the JSON checkpoint saved and produces a warning; use `render`
to regenerate it. Runtime data stays outside skill packages and repositories.
Local persistence does not transfer tasks to another machine automatically.

## Create, discover, and own

Invoke `python3 <skill-dir>/scripts/coord_state.py` with:

- `create --title <title> --objective <objective> --project <absolute-path>`:
  creates a task, unique ID, revision, and unique owner ID. Add `--conversation`
  when the conversation identifier is known. Save the returned IDs and paths.
- `list`: shows unfinished tasks, latest update, owner, blocker, and next action.
  Filter with `--project` or `--conversation`; `--all` includes completed/archived
  tasks. Unreadable records produce warnings rather than silently disappearing.
- `show --task <id>`: reads the complete authoritative state.
- `claim --task <id> --owner <session-id> --revision <observed-revision>`:
  claims a released task. To replace another owner, first reconcile that session
  and its workers, then add `--takeover --reason <explanation>`. A new session
  uses a new owner ID; it does not impersonate the previous session.
- `release --task <id> --owner <owner-id> --revision <observed-revision>`:
  releases ownership at an intentional handoff without stopping workers.

Ownership persists across days and does not expire automatically. A filesystem
lock serializes task writes and bound lifecycle operations; a persistent owner ID and increasing revision
reject stale writers after a takeover. These checks coordinate cooperative
agents, not hostile processes with filesystem access. If a lock is busy or a
revision is stale, reread and reconcile before retrying. Every mutation returns
its new revision. Read-only discovery does not require ownership.

## Bind lifecycle actions to ownership

For external workers, prepare the lifecycle with `--task-dir <task-directory>`
(the directory containing the authoritative `state.json`), the matching
`--task-id`, and `--owner <owner-id> --revision <current-task-revision>`.
Pass owner and revision to each lifecycle mutation, including dispatch,
reconciliation, verification, read acknowledgement, and recovery. These commands
check the task's current owner while holding its lock across the operation.
They update lifecycle state without incrementing the task revision. Use the
revision returned by the latest task checkpoint or claim.

Use `bind --state <lifecycle-path> --task-dir <task-directory> --owner <id>
--revision <revision>` for older unbound lifecycle files. Task IDs must match;
a binding cannot be replaced. Unbound files support inbox-only operations but
cannot launch, dispatch, or control external workers. Worker report publication
and read-only monitoring remain available while the coordinator is offline.

The task lock remains held by an in-flight adapter if its coordinator dies.
A busy lock means reconcile that process before takeover; never delete lock
files. The synchronous `run-task` convenience holds the lock for its bounded
run. Prefer the lower-level commands for work that spans sessions.

## Recover interrupted operations

Launch intent is saved before invoking Herdr. The helper writes an operation
receipt under `operations/<run-id>/` beside lifecycle state, saving tab/pane IDs
as soon as they arrive. Resume with `recover-worker --state <path> --worker <name>
--owner <id> --revision <revision>`. It validates receipt identity and inspects
the recorded pane; it never launches another worker or resends a prompt.

A crash between Herdr creating a tab and the receipt reaching disk can still
leave no durable pane ID. Recovery reports that uncertainty. Inspect the recorded
workspace and retain the unresolved intent; repeating start with the same worker
name is refused. There is no claim of exactly-once creation across the socket.

Dispatch intent is also saved first. Any recorded dispatch blocks automatic
resubmission. Inspect worker output and inbox reports, then use
`resolve-dispatch --state <path> --worker <name> --outcome delivered|not-delivered
--evidence <inspection-evidence> --owner <id> --revision <revision>`.
Only affirmative evidence of non-delivery permits another dispatch; a timeout
or missing output alone is insufficient. Unresolved operations are preserved
through failure cleanup and block tab reconciliation.

## Checkpoint decisions

Use `checkpoint --task <id> --owner <owner-id> --revision <observed-revision>
--patch-file <absolute-json-path>`. It accepts only `title`, `status`, and
`details`; protected identity, ownership, and selection fields have dedicated
commands. Status is `pending`, `active`, `blocked`, `paused`, or `completed`.
Use `paused` only when the user asks to pause.

A patch merges supplied detail fields; each supplied list replaces that list.
Preserve prior evidence and completed work when constructing updates. Example:

```json
{
  "status": "active",
  "details": {
    "next_action": "Inspect the worker's artifact and run the focused check",
    "work_items": [
      {"id": "implementation", "status": "pending", "needs": []}
    ]
  }
}
```

String details: `objective`, `authority`, `next_action`.
List details: `constraints`, `deliverables`, `acceptance_criteria`,
`pending_decisions`, `work_items`, `workers`, `artifacts`, `verification`,
`blockers`, `background_work`, and `notes`.

Work items need unique `id` and `status`; optional `needs` lists existing IDs
without cycles. Add ownership and write scope to work-item objects. Worker
objects can hold harness identity, pane/job IDs, absolute `cwd`/`worktree`, return
channel, and last observation. Artifact objects hold absolute `path` and an
optional `sha256`. Verification entries describe checks, results, and evidence.
Store no credentials. Use [Choice history](choice-history.md) to save selection.

### Store planning context in existing fields

Use the current schema for the goal-driven workflow; these are object
conventions inside existing lists, not new top-level detail fields:

| Information | Location |
| --- | --- |
| Observable goal | `objective`; preserve the rationale and non-goals in `notes` entries with `kind: intent` |
| Success and milestone checks | `acceptance_criteria` and `verification`, with criterion and milestone IDs where useful |
| Authority and decision defaults | `authority`, `constraints`, and a `notes` entry with `kind: decision_policy` |
| Owned outcomes and milestone grouping | `work_items`, with `owner`, `write_scope`, `milestone`, and actual prerequisite IDs in `needs` |
| Shared agreements and their owners | `notes` entries with `kind: contract`, stable `id`, `owner`, agreement, affected work-item IDs, and check or evidence link |
| Material assumptions and their dependencies | `notes` entries with `kind: assumption` and the fields in [Decision policy](decision-policy.md#record-material-assumptions) |
| Decisions still requiring resolution | `pending_decisions`, referencing the assumption or contract ID and blocked work |
| Replanning and goal changes | `notes` entries with `kind: replan` or `kind: goal_change`, evidence, affected IDs, and authorization when required |

For example, an assumption note can be:

```json
{
  "kind": "assumption",
  "id": "A-2",
  "decision": "Treat the stable account ID as the export join key",
  "status": "provisional",
  "evidence": "The schema and sampled export both expose account_id",
  "alternatives": ["Use the legacy external reference"],
  "uncertainty": "Historical imports have not yet been sampled",
  "if_wrong": "Historical export rows could be joined to the wrong account",
  "reversibility": "effort",
  "undo": "Revise the mapping and regenerate the unshipped export",
  "work_items": ["export-mapping", "export-check"],
  "depends_on": ["A-1"]
}
```

Record referenced assumptions and work items in the same task. The helper
validates `work_items.needs`; the coordinator checks note IDs, assumption
dependencies, contract consumers, and milestone coverage itself. Material
unresolved decisions required for the authorized goal belong in
`pending_decisions` as well as any explanatory note, so the completion gate can
see them. Keep optional out-of-scope proposals in deferred notes as described in
the decision policy. Resolve a pending entry by recording
its disposition in `notes` and removing it from the pending list. Preserve
prior notes when checkpointing because supplied lists replace existing lists.
Workers and lane owners report changes; only the main coordinator checkpoints
this authoritative record.

Checkpoint before dispatch or consequential actions, recording intent and work
item IDs, then record actual outcomes and worker/resource identities. Also save
user decisions, blockers, verification, integration, and cleanup; checkpoint
before waiting for input or ending a session. An intended action does not prove
it ran. Writes use atomic replacement and fsync. If JSON persistence fails,
restore it before additional delegated or consequential work.

## Resume and archive

Resolve “continue” by explicit task ID, conversation association, or a unique
unfinished task matching the project. Ask if multiple tasks match. Load the
record before the new-task selection gate: a resumed task keeps its own confirmed
pool; an unresolved selection still requires the user. Recent-choice history
never overrides the task's selection.

Run `check-resume --task <id>` to flag missing or changed artifacts and worker
directories, and list unfinished work. This is a filesystem check, not proof of
live worker activity. Inspect the inbox's unread and read-but-unprocessed reports,
reconcile live workers and incomplete operations, then claim/take over as needed
and checkpoint the next action. Inspect partial output before recreating missing
workers with the recorded pool. Ask for a replacement only if it must change.

Keep external-worker lifecycle state (`lifecycle.json`) and inboxes alongside
the task record; link their paths from task details. Lifecycle receipts do not
replace task checkpoints. Each lifecycle's `--task-id` equals the parent task ID;
multiple named lifecycle files may represent milestones within that task.
Bound lifecycle mutations require an explicit session owner and a numeric
revision, or explicit `--revision latest` checked under the ownership lock.
Use lifecycle `preserve` before removing worker workspaces; it records durable
copies of reported artifacts and retires workspace delivery. For old manually written `state.md` records, preserve
the original, explicitly reconstruct a new JSON task from evidence, and record
the old path. The helper refuses to guess a schema from prose.

Mark completed only after the acceptance criteria are met. The helper also
requires work items to be `completed` or `cancelled`, with no unresolved blockers,
pending decisions, or background work. Then `archive --task <id> --owner <id>
--revision <revision>` records archival, releases ownership, and preserves all
files in place. It does not delete artifacts, stop processes, or prove tests
passed. Keep required evidence in durable locations (for example the task's
`artifacts/` directory) before removing temporary workspaces. Include the task
ID and record path in the handoff.

For consecutive `select`/`checkpoint` operations by the current owner,
`coord_state.py` also accepts `--revision latest` under the task lock. This avoids
manual revision chaining while retaining owner fencing. Keep numeric revisions
when an edit depends on an exact snapshot. `claim`/takeover always requires a
numeric revision after reconciliation.
