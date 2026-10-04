# Optional adapters

## Native host

Inspect current tool definitions. Record dispatch, observation, return, correction,
and stop operations actually exposed. The Python runtime returns host requests;
the coordinator executes them through these tools. No CLI pretends to invoke them.

## Linux process

Require Linux `/proc`, Unix locking, and Python. Read the base coordinator's
`references/runtime-contracts.md`. Discover the chosen harness CLI syntax from
installed help. Process commands cannot accept mid-flight corrections. Keep
provider/model selection in the task's confirmed route, not this profile.

## Herdr terminal

Discover and read the installed Herdr skill. Locate its `scripts/herdr_worker.py`
adapter or `herdr-worker` on PATH. Configure `COORDINATOR_HERDR_HELPER` and optionally
`COORDINATOR_HERDR` in the launching environment. Read the base coordinator's
external-agent and worker-observation references before use. Their watcher is
Herdr-specific and recognizes Term2 UI patterns; verify compatibility with the
chosen harness rather than applying those patterns universally.

## Method catalogs

Pass verified directories with `--catalog`, or set
`COORDINATOR_PROTOCOL_CATALOG` in the launching environment. The base does not
automatically execute configuration values. Resolve one installed method as a
smoke check. Poteto methods remain optional guidance under coordinator policy.
