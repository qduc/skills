# Optional integration policy

The memory sidecar is disabled by default and must remain disabled with the
shipped implementation: its judge can act on transcript content. Write task-state
`notes` by hand. Read-only `coord_state.py resume` remains available.

Keep mutable host status in the external [Host profile](host-profile.md).
Healing requires authority from the current task or an explicitly applicable
user preference; the shipped skill grants none.
