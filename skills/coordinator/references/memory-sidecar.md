# Memory sidecar

Read [Operational status](operational-status.md) before using this integration.
Keep it disabled unless that status explicitly authorizes use. The watcher,
binding, and flush instructions below apply only when enabled; otherwise write
task-state `notes` by hand. Read-only `coord_state.py resume` is independent.

The sidecar watches a bound session's transcript and captures semantic decisions
and findings with a judge model. It is not operational state: keep next action,
blockers, work items, workers, and pending decisions in the task record.

Collection is a transcript watcher, not a harness hook. It tails complete
transcript records continuously, keeps only conversational text (user and
assistant natural-language text), and drops tool input, tool output, thinking,
and images before the judge runs:

```sh
python3 <skill-dir>/scripts/coord_memory_watch.py --root <root>   # run until stopped
python3 <skill-dir>/scripts/coord_memory_watch.py --once          # one pass
```

One watcher per coordinator root owns collection. Each pass it binds new session
markers and judges every bound session once; one session's failure is logged and
does not stop the watcher.

Binding is launcher-mediated. The launch side records a session marker
`{session_id, task_id, owner, harness, transcript_path}` at
`<root>/sessions/<session_id>.json` using `coord_memory_watch.write_launch_marker`;
the watcher reads the marker and creates the binding, never guessing among
transcripts. The `harness` names the transcript source and selects its filter
profile; Claude Code and Term2 ship profiles (`coord_memory_filter.py`), and an
unseen harness needs a profile before its records can be filtered. A session with
no marker can be bound explicitly:

```sh
python3 <skill-dir>/scripts/coord_state.py bind-session --task <id> --owner <owner> --revision <revision> --session-id <session-id> --harness <name> --transcript <path>
```

On entry, run `coord_state.py resume --task <id>` first. Before release or a
handoff, judge the records accumulated so far:

```sh
python3 <skill-dir>/scripts/coord_memory.py flush --task <id> --session-id <session-id>
```

`coord_memory.py --judge --session-id <session-id>` judges one session directly
for debugging. Judge metadata is logged at
`~/.local/state/coordinator/memory-hook.log`.

Known limits: duplicate decisions can be captured. A complete non-JSON transcript
line stops collection at that point until the file is rewritten; a torn trailing
line is held until it is complete, and the offset resets if the file is truncated
or replaced. Without a running watcher or a live binding, use `notes` by hand as
the degraded fallback.
