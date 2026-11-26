# Run ledger — plan: <plan path or stable plan ID>

Base: <branch> @ <sha> · Workspace: <worktree path>

## Preflight

| Check | Tasks | Finding | Resolution |
| --- | --- | --- | --- |
| Overlap | T1 × T2 | <shared files / interfaces / state> | <serialize, converge contract, or none> |
| Internal consistency | T1 | <description vs tests vs files> | <ok / fix brief> |
| Global constraints | all | <conflicts with spec or conventions> | <ruling or none> |
| Write ownership | all | <any file with two owners> | <owner> |
| Git/index contention | <pairs> | <concurrent commits?> | <serialize / separate worktrees> |
| Test interference | <pairs> | <shared services, fixtures> | <serialize / isolate> |

## Tasks

### T1 — <objective>
- Status: queued | working | reported | reviewing | fixing | accepted | blocked | deferred
- Depends on: —
- Owner / session: <worker id>
- Brief: briefs/T1.yaml · Report: reports/T1.md · Review: reviews/T1-r0.md
- Commits: <sha range>
- Verification: <command → outcome>
- Verdicts: <criterion/entry point → verified | failed | verified-unreachable (prereq) | skipped (reason)>
- Assumption check: <ok | sent back: what context was missing>
- Review verdict: <APPROVED | NEEDS_FIXES>
- Fix rounds: <n> · Open findings: <list>
- Deferred minor findings: <list>

## Verify layer

- Skill: <path | created in T0 (scoped to …) | dead end: reason (recorded in wiki)>
- Isolate: <instances can run side by side? → parallel or serial live verification>
- Features added (extend): <list>
- Gotchas added: <feature → trap>
- Regression steps added: <feature → bug ref, failed before / passed after>
- Drift logged: <feature · step · observed>
- Scoped maintenance: <clean | changed: … | blocked: …>

## Rulings

Ruling: <decision> — <why> — <what it costs if wrong>
