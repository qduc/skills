# Coordinator operational status

This file holds mutable integration status and dated authority; process lives
in the skill and its references.

## Memory sidecar

Paused since 2026-09-28. Do not bind sessions, install hooks, or run
`coord_memory.py flush`. Its term2 judge can act on transcript content and
edited live source during testing. Keep decisions in task-state `notes` by hand.
Re-enabling requires an isolated judge that cannot act and explicit authorization.
The read-only `coord_state.py resume` remains available.

## Healing authority

The user granted standing authority on 2026-09-28 for the narrow host-fact,
instruction-defect, and helper-defect lanes in [Healing](healing.md).
Behavior-rule changes remain experiments requiring authorization.
