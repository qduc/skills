# Harness/model choice history

Use `python3 <skill-dir>/scripts/coord_state.py` for recording and retrieving
choices. It uses the [task-state directory](task-state.md), outside the skill
package and repositories. A confirmed selection is saved in the task's JSON
record and exported to `<state-root>/choices.jsonl`.

## Read and reuse

Run `choices` before presenting options; it returns the ten most recent choices.
Filter with `--task <id>` or `--project <path>`; use `--limit` to inspect more.
“Previous,” “last time,” or “same as before” means the latest confirmed choice
across tasks unless the user names a task or project.

Show the resolved pool briefly and verify availability. An unambiguous explicit
reuse request is the user's choice for a new task, without another confirmation.
History alone never chooses automatically. Missing or ambiguous history requires
a selection. If the command reports malformed/missing records that could affect
which choice is latest, disclose the uncertainty and confirm the recovered choice.
If the selected pool is unavailable, present alternatives for the user to choose.

## Record a confirmed choice

Write a pool JSON file with concrete harness/model identifiers, for example:

```json
[{"harness": "term2", "provider": "chosen-provider", "model": "chosen-model", "effort": "high", "role": "implementation"}]
```

`harness` and `model` are required; `provider`, `effort`, and `role` are optional.
Use the actual selected identifiers, not these example placeholders. Multiple
routes represent a mixed pool. Record it with:

```text
select --task <id> --owner <owner-id> --revision <observed-revision>
       --pool-file <absolute-json-path> --confirmed --source <short-selection-source>
```

Use `--confirmed` only after the user's selection or explicit reuse request.
The source identifies that choice, without copying a prompt or secrets. The
helper stores the timestamp, task/project association, and a unique choice ID.
Record replacements and explicit reuse on new tasks as new selections; ordinary
same-task follow-ups need none.

Task JSON is saved first. If history export fails, the command reports that
limitation; `choices` merges task-saved events with the log and deduplicates by
ID, recovering choices without a successful export. Corrupt log lines are
reported. Selection history does not grant execution authority or replace the
current task's confirmed pool.
