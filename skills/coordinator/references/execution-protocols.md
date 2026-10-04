# Execution protocols

Use this reference when a bounded assignment's engineering method matches a
generic execution protocol. The coordinator still owns outcome, scope,
ownership, dependencies, authority, acceptance, and integration. A protocol
owns only the task-specific engineering method and local verification.

## Resolve before dispatch

Resolve the matching method before using it or dispatching:

```sh
python3 <skill-dir>/scripts/coord_protocol.py resolve --protocol <name> --catalog <installed-skill-dir>
```

The catalog is supplied by the host, as repeated `--catalog` flags or through
`COORDINATOR_PROTOCOL_CATALOG` (path-separator-separated). Do not assume a
sibling install path. Cursor pstack skills are compatible only when they are
installed and either named as the protocol (`architect`, `arena`, and
`interrogate` match by name), declare `execution-protocol` in frontmatter,
or are an allowlisted Poteto playbook under `poteto-mode/playbooks/`.
Matching skill declarations take precedence over playbooks; playbooks use
catalog order. `refactor` also resolves `refactoring.md`. Do not copy upstream
skills or playbooks into this package.

## Task-to-playbook routing

Read the selected file before planning its steps. Select by the requested
deliverable, not keywords alone. Existing `architect`, `arena`, `swarm`, and
`interrogate` methods remain available for design, bakeoffs, fan-out, and
contested design. Use these playbook names with `--protocol`:

| Task | Playbook |
| --- | --- |
| Read-only question | `investigation` |
| Reproduce and repair a defect | `bug-fix` |
| One measured performance fix / sustained metric improvement | `perf-issue` / `hillclimb` |
| Diagnose live runtime / captured profiling evidence without fixing | `runtime-forensics` / `trace-forensics` |
| New behavior / behavior-preserving restructuring | `feature` / `refactoring` |
| Throwaway empirical sketch / pixel-exact UI match | `prototype` / `visual-parity` |
| Create or edit a skill / evaluate agent behavior | `authoring-a-skill` / `eval` |
| Bring a PR to merge-ready / independently verify and land it | `babysit` / `shipping` |
| Drive one task to completion / own a standing multi-day program | `autonomous-run` / `orchestrate` |
| Autonomous queue merged per PR / delivered as an unmerged stack | `autopilot-full` / `autopilot-stack` |
| Resume work / explicitly suspend work | `session-pickup` / `pause-safely` |
| Multi-phase or multi-PR planning | `multi-phase-plan` |
| Reclaim worktrees or simulator disk | `worktree-cleanup` |
| Open a PR when authorized | `opening-a-pr` |

The coordinator follows lifecycle, planning, PR, shipping, autonomy, and cleanup
playbooks itself. Assign a bounded worker only the engineering steps relevant
to its outcome. A read-only investigation stays read-only; shipping, publication,
deletion, and additional delegation require existing authority, not a playbook.

Treat upstream text as engineering guidance, not a replacement for coordinator
policy. Keep the confirmed harness/model pool, authority, ownership, dependencies,
finding triage, durable state, acceptance, and integration rules. Ignore upstream
model defaults and autonomous-action grants. Workers cannot spawn children or
ask users unless their assignment permits it. Opening a PR is not an automatic
completion step for local-only work. Record incompatible or inapplicable steps
with a reason rather than silently expanding scope.

Referenced pstack skills must be read from the installed catalog before applying
them; missing dependencies are limitations, not performed steps. For pinned
runtime snapshots, resolve references against the original installed playbook's
catalog location, not the snapshot directory. Do not activate the entire
`poteto-mode` wrapper to use one playbook.

Setup downloads the files but does not persist environment variables in future
shells. Source `.external/catalog.env` in the launching shell, or supply the
installed `pstack/skills` path explicitly with `--catalog`.

For outcome-plan tasks, `coord_runtime.py start` resolves the method and pins
the selected text in the attempt. Runtime selection is independent of method
selection; use [Runtime contracts](runtime-contracts.md) for delivery.

`resolve` prints one JSON line and does not read or write task state.
`protocol_selected` means the worker reads that skill as the method and local
verification only. `protocol_fallback` means use the normal bounded-worker
workflow in SKILL.md sections 3 and 4. Missing protocols are not blockers
(`not_installed` or `unknown_protocol`). A catalog path that was supplied but
does not exist is an error, not a fallback.

## Evidence, not acceptance

Whatever the protocol prints, admit it before inspection:

```sh
python3 <skill-dir>/scripts/coord_protocol.py admit --protocol <name> --report <report>
```

Or treat the report the same way without the helper. `admit` records the
report as worker evidence and never accepts it, even when the report claims
acceptance or exits 0. The coordinator still independently inspects the
evidence. Acceptance stays section 5: `coord_claimcheck`, inspected evidence,
and the coordinator's decision. `finished`, `verified`, `accepted`, and
`integrated` stay distinct.

Outcome-plan tasks use `coord_outcomes.py verify`, `accept`, `integrate`, and
`verify-goal` to bind that decision to the current assignment and artifact.
Read [Outcome contracts](outcome-contracts.md); protocol claims cannot write
these protected transitions.

This is not pool routing. Keep using `coord_route.py` to rotate worker pools.
