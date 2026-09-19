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
missing data as unknown, and enough reserve for handoff. If unknown capacity
jeopardizes completion, narrow the task, start a suitable fresh worker, or
resolve the constraint before assignment. Refresh after material model,
harness, or task changes.

For local external CLI selection, consult the optional
[host inventory](host-inventory.md) only when it describes the intended host.
It is a dated discovery aid; verify entries you intend to use against that
host's live tools. Native workers do not require this inventory. Choose model
capability first, then provider cost and latency; a running pane does not decide
which model the task deserves.
