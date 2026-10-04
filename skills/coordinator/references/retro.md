# Retro: capture, harvest, route, prune

Lessons reach the next coordinator only through the task record and the
destinations below; handoff files and conversation memory are read once and lost.

## Capture

When a coordination step costs time, work, or trust, add a `notes` entry to the
task record at the next checkpoint:

```json
{
  "kind": "incident",
  "key": "worktree-removed-under-worker",
  "at": "2026-09-26",
  "what": "Removed a worktree while its term2 worker was alive; the worker's shell failed with spawn git ENOENT",
  "cost": "T1 worker relaunched; about 30 minutes lost",
  "rule": "Close a worker's tab before removing its worktree",
  "scope": "general"
}
```

- `key`: a lowercase slug naming the lesson, not the event. Reuse an existing
  key when the same lesson recurs; the harvest groups recurrences by key.
- `scope`: `host` (true of this machine, account, or tool version), `general`
  (true of coordination anywhere), or `one-off`.
- `cost`: what was lost. A recorded cost is how a single occurrence reaches
  the promotion bar.

The helper validates `key` and `scope` when present. When a promoted rule
applies again, record an incident with its key and `outcome: prevented` or
`outcome: recurred`; that is the evidence that keeps it from being pruned.

## Resuming work

Routine resumption uses the task snapshot and any worker lifecycle receipts.
Record a missing worker locator or other fact that those sources cannot recover
in the task state. A separate resume diary is unnecessary.

## Harvest

```bash
python3 <skill-dir>/scripts/coord_retro.py [--memory-dir <feedback-memory-dir>] > <task-dir>/artifacts/retro.md
```

It reads task notes (kinds `incident`, `lesson`, `coordination_failure`,
`tooling`), `friction-log.md`, "Hard-won rules" in `handoff-*.md`, and
feedback memories, and writes nothing. Keyed lessons group exactly; unkeyed
ones group by word overlap, which is a hint. Count occurrences from the
citations: one event retold in a note, a handoff, and a memory is one
occurrence.

## Route

Promote a lesson only when it recurred in at least two independent events or
caused real damage once (lost work, a wrong merge, an unsafe action, or hours of
idle workers). Everything else stays in its task record.

| Lesson | Destination |
| --- | --- |
| Host fact: a tool's quirk, a model's profile, a path, a quota | The local host inventory (see [Host inventory](host-inventory.md)) or a memory; correct stale entries in place |
| General coordination rule that fixes an unclear or missing instruction | The instruction-defect lane in "Heal as you drive" (`SKILL.md`) |
| Rule that changes planning, delegation, routing, verification, or stop behavior | A candidate for a `workflow-evolution` experiment against `evals/evals.json`; record it in [Candidate experiments](experiments.md) and leave it unapplied unless an experiment is authorized |
| Tool or helper defect | The helper-defect lane in "Heal as you drive"; for a tool outside the skills, a bug report, with the rule as a workaround until it is fixed |
| One-off | Stays in the task record |

Mark each promoted rule with `<!-- lesson: <key> promoted <YYYY-MM-DD> -->`
beside it, then record the disposition in the task notes with the destination.

## Prune

The digest lists every marked rule with the incidents cited since its promotion.
Remove or merge a rule with no citations for 90 days unless it guards against
damage that would be rare but severe; record the removal like a promotion.
Remove a host fact when the tool changes and a recheck disproves it.
