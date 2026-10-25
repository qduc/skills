# Routing reference

Use this reference when selecting among model groups or harnesses, reusing a
persistent worker, or coordinating work with material acceptance risk.

## Select by capability and risk

Match task size, ambiguity, tools, and verification needs to demonstrated
capability. Record a concrete route within the user's authorization as described
in the main skill; route only through the task's selected pool. Use stronger
judgment or independent review when security, authority, release
acceptance, or ambiguous integration risk is material.

Choose model size from the task's shape and record the classification with the
assignment. Use a small model for a clearly bounded task: a known defect, a
prescribed fix, a mechanical change, or explicit acceptance tests. Use a big
model for open-ended, vague, or high-risk work, such as a fix that needs a design
decision, unclear scope, or a mistake that is hard to see or undo. Model size is
independent of reasoning effort. Reclassify when a bounded task turns out to
need design work. <!-- lesson: model-size-by-task-shape promoted 2026-09-27 -->

## Spread load across pools

Spread independent work across suitable authorized pools when it improves
capacity or latency. Do not rotate a cohesive follow-up away from its owner
merely to balance a counter. A host profile lists capabilities, not permission
to use unselected or paid routes.

`python3 <delegate-dir>/scripts/coord_route.py pick --pool <name> ... --history
<task-dir>/route-history.json --inventory <inventory-path> --dry-run` can suggest
a candidate from supplied pools. It does not verify quota, availability,
authorization, or inventory membership (`--inventory` is optional). Check those
before dispatch; exclude unavailable pools and re-pick when needed. Record a
validated pick without `--dry-run`. Keep exhausted pools unavailable until reset.
A particular model may be warranted by risk, an authorized cross-vendor review,
or demonstrated worker capability. Record the route actually used.

Inspect the live tool inventory before selecting a surface:

| Capability | Evidence needed | Use |
| --- | --- | --- |
| Native bounded worker | Can receive context and return attributable results | Ordinary isolated assignments |
| Task graph | Supports stable task IDs and dependency edges | Multi-stage work |
| Persistent terminal | Owns a trusted workspace and retains state | Durable work or terminal isolation |
| Return path | Completion notification or a reliable lifecycle wake | Long-running assignments |
| Independent verification | Another actor or deterministic check can inspect output | Material acceptance risk |

If a required capability is unknown, run one bounded probe within the selected
pool or present verified alternatives for the user to choose. Keep the task
blocked if no route meets its requirements; missing
optional telemetry is not itself a missing execution capability.

## Reuse persistent workers deliberately

Check the model actually running, current work, context headroom, and any exposed
quota/reset information before reuse. Record the evidence source and time,
missing data as unknown, and enough reserve for handoff. Keep a cohesive
discovery→implementation→verification follow-up with that owner when context is
useful and capacity adequate. A milestone alone is not a
reason to clear it. Before unrelated work, harvest and reconcile the previous
assignment, then `/clear` or start fresh; use a separate reviewer when independence
is required. A read-only assignment needs explicit new scope before modification.
If unknown capacity
jeopardizes completion, narrow the task, start a suitable fresh worker, or
resolve the constraint before assignment. Refresh after material model,
harness, or task changes.

For local external CLI selection, consult the optional
[host profile](../../delegate/references/host-profile.md) only when it describes the intended host.
Its host facts are a dated discovery aid, so verify entries you intend to use
against that host's live tools. Native workers do not require this profile. Choose model
capability first, then provider cost and latency; a running pane does not decide
which model the task deserves.
