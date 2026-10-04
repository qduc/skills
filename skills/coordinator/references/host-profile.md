# Host profile

Discover and read the installed `coordinator-setup` skill when the profile is
missing or the selected host capability has changed. A profile configures paths
and records observations; it grants no task authority and does not select models.

Location: `${COORDINATOR_CONFIG_HOME}/host.json` when explicitly set to an absolute
directory; otherwise `${XDG_CONFIG_HOME}/coordinator/host.json` on Unix (absolute
XDG path only, falling back to `~/.config`), or `%LOCALAPPDATA%/coordinator/host.json`
on Windows. Keep it outside published skills and task records.

Schema version 1 contains `verified_at`, `platform`, `python`, `prerequisites`,
`executables`, `adapters`, `catalogs`, and `memory_sidecar: "disabled"`.
Each adapter entry records `status` (`verified`, `unavailable`, or `unknown`),
supported operations, paths where applicable, verification date, and evidence.
`catalogs` contains absolute directories. Recheck paths and required capabilities
before use; saved native tool observations do not survive a harness change.

Pass configured paths explicitly to helpers or their documented environment
variables. Helpers do not automatically execute or import profile content.
Record task selection and authority in task state. When a required capability is
unavailable, report it; missing optional adapters permit native tools or direct work.
The bundled persistence currently requires Unix locking, and the process adapter
is Linux-only. Host-neutral instructions do not imply cross-platform helpers.
