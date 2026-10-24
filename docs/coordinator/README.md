# Coordinator design notes

Maintainer material for the [delegate skill](../../skills/delegate/SKILL.md) and the [supervise-panes skill](../../skills/supervise-panes/SKILL.md). None of it is loaded while the skill runs.

- [experiments.md](experiments.md): candidate behavior changes, unapplied until a `workflow-evolution` experiment promotes them. Healing and retros add entries here.
- [architecture.md](architecture.md): the outcome-centered design behind the coordinator runtime; read it when changing coordination boundaries or adding a runtime.
- [management-principles.md](management-principles.md): the systems principles behind the coordination rules.
- [memory-sidecar.md](memory-sidecar.md) and [memory-sidecar-redesign.md](memory-sidecar-redesign.md): the memory sidecar, which stays disabled per the skill's `references/operational-status.md`.
