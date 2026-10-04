# Outcome contracts

Coordinator owns the authorized goal, decomposition, decisions, acceptance, and
integration. A protocol owns engineering method and local checks. A runtime owns
delivery, observation, recovery, and cleanup. A worker returns claims and artifacts.

## Initialize new delivery work

Create the task with `coord_state.py`; record authority, constraints, observable
acceptance criteria, and the confirmed harness/model pool before dispatch. Write
a plan JSON containing `outcomes` and `goal_checks`:

```json
{
  "outcomes": [{
    "id": "configuration",
    "objective": "Produce configuration usable by existing and new consumers",
    "rationale": "The migration must preserve existing behavior",
    "scope": "Configuration artifact inside the assigned workspace",
    "authority": "Write local files; escalate publication or additional scope",
    "cwd": "/absolute/isolated/workspace",
    "needs": [],
    "checks": [{"id": "configuration-behavior", "argv": ["python3", "check_config.py"]}]
  }],
  "goal_checks": [{"id": "integrated-compatibility", "argv": ["python3", "check_product.py"]}]
}
```

Use `python3 <skill-dir>/scripts/coord_outcomes.py plan --task-dir <task-dir>
--owner <owner> --revision <revision> --spec-file <plan.json>`. The plan has one
current assignment per outcome; dependencies must name existing IDs and be acyclic.
Existing incompatible work items require explicit reconciliation before adoption.
Old task records remain loadable and retain their established workflow.

V1 verifies file artifacts by content hash. Represent multi-file results as a
reviewable file bundle or manifest and make the checks exercise its actual
contents; an artifact path alone cannot establish repository behavior. Keep
artifact sources and evidence durable through completion and archive.

## Execute and inspect

Use [Runtime contracts](runtime-contracts.md) to dispatch. A generated assignment
identifies task, outcome, assignment, and attempt, with goal rationale, scope,
authority, dependencies, checks, and the selected engineering method. Worker
publication uses `coord_outcomes.py report --assignment-file <descriptor>
--artifact <file>` and never changes task state. Workers cannot authorize extra
scope, ask the user directly, or spawn children in this first contract version.
They return a `blocker.json` naming the missing decision when they cannot proceed.

After runtime observation establishes settlement, inspect the report and run:

```text
coord_outcomes.py verify      --outcome <id> --report <report.json>
coord_outcomes.py accept      --outcome <id> --decision <inspection decision>
coord_outcomes.py integrate   --outcome <id> --artifact <actual integrated file>
coord_outcomes.py verify-goal
```

Every command also requires `--task-dir`, `--owner`, and `--revision`.
`verify` and `verify-goal` accept a positive `--timeout` for each check.
The verification argv is supplied by Coordinator, never taken from a report.
Check output and numeric exit status are saved in the protected plan; a failed
check stays failed evidence. Inspection must evaluate the actual deliverables,
authority, surprises, and relevant changed behavior before `accept`.
`--decision` records judgment; it does not automate semantic inspection.

Incorporate the inspected artifact within existing authority, then `integrate`
records its actual target and requires the accepted bytes. After a crash between
incorporation and checkpoint, inspect that target and run `integrate`; never assume
the incorporation failed because its receipt is missing. For transformations,
produce and verify a new candidate representing the resulting deliverable.

Completion through `coord_state.py checkpoint` requires current integrated
artifacts, successful independent goal checks, settled attempts, and the existing
no-blockers/no-pending-decisions/no-background-work gate. Archival rechecks the
evidence. `finished`, `verified`, `accepted`, and `integrated` remain separate.

## Replan without losing the goal

Use `revise --outcome <id> --spec-file <contract.json>` after reconciling and settling
affected attempts. It preserves history, issues new assignment IDs, and invalidates
transitive dependents, including previously accepted/integrated results. Independent
outcomes remain valid. Inspect all resulting pending work before continuing.

A material change to task objective, authority, constraints, or acceptance criteria
blocks execution against the old plan. Only adopt such changes within the user's
authorization. Use `replan --spec-file <plan.json> --decision <authority source and
reason>` after all attempts are settled. History remains in the same task record.
Routine checkpoints do not alter assignment identity or invalidate acceptance.

## Ownership and trust

The authoritative plan is a protected top-level extension of `state.json`;
generic checkpoints cannot write its acceptance fields. All Coordinator mutations
check the current owner and revision under the existing task lock. Workers only
publish report files. State, runtime receipts, reports, and artifacts have separate
roles; none substitutes for another.

These checks govern cooperative agents. They do not isolate processes running as
the same OS user. Scope and authority are reviewed against observed actions; actual
tool permissions and filesystem isolation belong to the host. Do not describe a
brief, route selection, or file hash as a sandbox. Memory remains advisory and its
paused sidecar is not involved in execution or acceptance.
