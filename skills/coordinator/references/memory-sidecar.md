# Memory sidecar

**Paused (2026-09-28). Don't install the hooks, bind sessions, or run `flush`.**
The judge runs as a non-interactive term2 agent. With the user's
`shell.autoApproveMode: always`, transcript content hijacked it into editing
live source during testing. It stays off until the judge can't act: isolated
judge settings without auto-approve, or a term2 no-tools mode. Use
hand-written `notes` meanwhile. The read-only `coord_state.py resume` is
unaffected.

The sidecar captures semantic decisions and findings at `PreCompact` and
`SessionEnd` boundaries (or an explicit flush). It is not operational state:
keep next action, blockers, work items, workers, and pending decisions in the
task record.

Install once, and uninstall when the integration is no longer wanted:

```sh
python3 <skill-dir>/scripts/install_memory_hooks.py install --settings ~/.claude/settings.json
python3 <skill-dir>/scripts/install_memory_hooks.py uninstall --settings ~/.claude/settings.json
```

Bind a session with two steps. First run `coord_state.py session-nonce` and
retain its output. Then bind with the nonce; `auto` searches the newest Claude
transcripts without guessing:

```sh
python3 <skill-dir>/scripts/coord_state.py session-nonce
python3 <skill-dir>/scripts/coord_state.py bind-session --task <id> --owner <owner> --revision <revision> --session-id auto --nonce <nonce>
```

On entry, run `coord_state.py resume --task <id>` first. Before release or a
handoff, run `python3 <skill-dir>/scripts/coord_memory.py flush --task <id> --session-id <session-id>`.
Hook metadata is logged at `~/.local/state/coordinator/memory-hook.log`.

Known limits: duplicate decisions can be captured, and a non-JSON transcript
line stops capture until the session is rebound. A capture failure stops at
that point and retries from the saved offset at the next boundary. Without
hooks or a live binding, use `notes` by hand as the degraded fallback.
