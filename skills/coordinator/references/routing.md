# Routing reference

Use this reference when selecting among model groups or harnesses, reusing a
persistent worker, or coordinating work with material acceptance risk.

## Select by capability and risk

Match task size, ambiguity, tools, and verification needs to demonstrated
capability. Apply the per-task harness/model selection gate in the main skill;
recommend options within the user's constraints and route only through their
selected pool. Use
stronger judgment or independent review when security, authority, release
acceptance, or ambiguous integration risk is material.

Choose model size from the task's shape and record the classification with the
assignment. Use a small model for a clearly bounded task: a known defect, a
prescribed fix, a mechanical change, or explicit acceptance tests. Use a big
model for open-ended, vague, or high-risk work, such as a fix that needs a design
decision, unclear scope, or a mistake that is hard to see or undo. Model size is
independent of reasoning effort. Reclassify when a bounded task turns out to
need design work. <!-- lesson: model-size-by-task-shape promoted 2026-09-27 -->

## Spread load across pools

Routine dispatches rotate across the implementation pools the local
[host inventory](host-inventory.md) lists as available; do not stack concurrent
or sequential workers on one pool while another suitable pool has headroom.
Let `python3 <skill-dir>/scripts/coord_route.py pick --pool <name> ... --history
<task-dir>/route-history.json --inventory <inventory-path> --dry-run` choose a
candidate without recording it. The helper only rotates across the supplied
pools; it does not verify quota, availability, or inventory membership, and
`--inventory` is optional. The caller must check quota and availability before
dispatch. If the candidate is exhausted or unavailable, exclude it and re-pick.
Once a candidate passes those checks, run the command again without `--dry-run`
to record that pick. Treat an exhausted pool as unavailable until its reset.
Pick one specific
model only when the task's risk, a vendor boundary such as cross-vendor review,
or an observed worker profile calls for it, and record which pool each
assignment used. <!-- lesson: rotate-pools-check-quota promoted 2026-09-29 -->

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
missing data as unknown, and enough reserve for handoff. Between unrelated
assignments and at each milestone, `/clear` the worker or start a fresh one
instead of steering more work into the same context.
<!-- lesson: fresh-context-per-assignment promoted 2026-09-26 -->
If unknown capacity
jeopardizes completion, narrow the task, start a suitable fresh worker, or
resolve the constraint before assignment. Refresh after material model,
harness, or task changes.

For local external CLI selection, consult the optional
[host inventory](host-inventory.md) only when it describes the intended host.
Its user routing preferences are the user's standing policy for model choice;
its host facts are a dated discovery aid, so verify entries you intend to use
against that host's live tools. Native workers do not require this inventory. Choose model
capability first, then provider cost and latency; a running pane does not decide
which model the task deserves.
