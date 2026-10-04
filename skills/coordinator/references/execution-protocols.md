# Execution protocols

Use this reference when a bounded assignment's engineering method matches a
generic execution protocol. The coordinator still owns outcome, scope,
ownership, dependencies, authority, acceptance, and integration. A protocol
owns only the task-specific engineering method and local verification.

## Resolve before dispatch

When the method is one of `bug-fix`, `architect`, `refactor`, `arena`,
`swarm`, or `interrogate`, resolve it before dispatch:

```sh
python3 <skill-dir>/scripts/coord_protocol.py resolve --protocol <name> --catalog <installed-skill-dir>
```

The catalog is supplied by the host, as repeated `--catalog` flags or through
`COORDINATOR_PROTOCOL_CATALOG` (path-separator-separated). Do not assume a
sibling install path. Cursor pstack skills are compatible only when they are
installed and either named as the protocol (`architect`, `arena`, and
`interrogate` match by name) or they declare `execution-protocol` in
frontmatter. Do not copy those skills into this package.

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
