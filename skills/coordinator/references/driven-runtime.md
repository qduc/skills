# Driven runtime: front-desk commands

`scripts/coord.py` is the whole interface. Each command prints one JSON object;
`result.waiting_on` is `judgment`, `user`, `host`, `workers`, or `driver` (run
again to advance), and is null when `done`. Task IDs accept a unique prefix
of 6+ characters. Use `status` to resume a task; no task-record editing is needed.

## Worker routes and setup

Process workers and an optional headless judge normally come from the host
profile. `coord.py doctor` checks that configuration. If it is missing, use the
`coordinator-setup` driver interview. A task can instead supply `--workers-file`:

```json
[{"route": {"harness": "<cli>", "model": "<selected-model>"},
  "argv": ["<cli>", "<batch flag>", "--model", "<selected-model>", "{prompt}"]}]
```

A native worker uses the host's agent tools, so it needs no CLI or process probe:

```json
[{"route": {"harness": "native", "model": "host-inherited"}, "runtime": "native"}]
```

Use `host-inherited` only when the user selected native agents inheriting this
chat's settings. Otherwise record the actual selected model/settings and use a
host tool that can honor them. Do not silently substitute a model. Native and
process entries may share a pool; each route must identify one entry uniquely.
Check an override with `doctor --workers-file workers.json --delivery artifact`
(or `patch`). This does not require creating or editing a host profile. Supply
the same override to `start`. It describes available routes; the runtime still
asks for the user's per-task selection before a worker can run. An existing
explicit user selection can be recorded using their actual words.

Process argv must accept the prompt as one `"{prompt}"` element, run in the
assigned directory, edit files and run checks unattended, then exit. Discover
real flags from installed help. The profile's `adapters.driver.judge` or an
explicit `--judge-command-file` can answer judgments headlessly. `--no-judge`
keeps those decisions in the conversation.

## Start and drive

For code delivery:

```text
coord.py start --repo <git root> --goal "<desired outcome>" \
  --criterion "<observable done condition>" [--criterion ...] \
  [--constraint "..."] [--authority "..."] [--workers-file workers.json] \
  [--real-use-required] [--limits-file limits.json]
```

The task starts from the repository's current commit. If it reports uncommitted
changes, tell the user they are not included. Changes are made in isolated
worktrees and integrated on the reported task branch; the user's checkout stays
in place. Merging is a separate human decision.

For research, reports, or other file artifacts, use `--workspace <source-dir>`
instead of `--repo`. The source need not be a Git repository and remains
read-only under the default authority. The runtime creates empty isolated worker
workspaces. Each planned outcome names one relative `artifact`, such as
`report.md`, `data/results.json`, or `chart.png`. Several files can be separate
outcomes or one archive. Workers produce the file; the runtime checks, requests
semantic inspection, and publishes the exact accepted bytes under
`<integration>/artifacts/<outcome-id>/<artifact>`. Dependencies are copied into
`inputs/<outcome-id>/<artifact>` in the dependent worker's workspace. Reports
need evidence and semantic review, not merely a file-existence check. No patch,
commit or checks-first phase is imposed on artifact delivery. `--repo ...
--delivery artifact` also supports reports about a Git repository.

Use `--real-use-required` when delivering a changed skill or orchestration
capability; a report about existing code does not itself change that capability.

```text
coord.py run --task <id>                    # uses a configured judge, if present
coord.py run --task <id> --no-judge         # stops at each judgment
coord.py status --task <id>                # progress and verification evidence
```

`run` advances until done, a user question, a native host request, or a judgment
it cannot answer. Process workers may take time: run the command in the background
and check `status`. To answer a judgment, `prompt --task <id> --request <rid>`
prints its guide, context and answer schema. Read the indicated source/artifact,
then submit one JSON object with `answer --task <id> --request <rid> --file
answer.json`. Rejections include the reason in the next prompt. No internal
state fields, helper commands or lifecycle transitions are needed.

## Native host bridge

When `waiting_on` is `host`:

1. Run `host-next --task <id>`. It durably issues one request with an `id`,
   `action`, required tool inputs, and `reply_with` shape.
2. Execute the matching host tool. For `spawn`, use the supplied `message`,
   `label` as the worker name, and confirmed `route`. For `observe`, wait for or
   inspect the named `handle`. For `stop`, stop that handle and establish its
   resulting status; requesting a stop is not proof of exit.
3. Write the actual observation to JSON and call `host-result --task <id>
   --action <request-id> --file observation.json` (or `--file -` for stdin).
   Then continue `run`.

Spawn replies are `{"handle":"<actual returned worker handle>"}`. Observation
and stop replies are `{"handle":"<requested handle>","status":"finished"}`,
where status may also be `working`, `stopped`, or `unknown`. Translate the host's
actual status vocabulary; never infer completion from worker prose or silence.
Use host waits for ongoing workers; do not spin on status requests. The driver
packages the settled worker's output and owns verification and retries.

If a spawn result is lost, `host-next` returns `reconcile`, not another spawn.
Inspect the host for the worker with the supplied label and return its handle.
Only if inspection proves it never started, return
`{"status":"not_started","basis":"<observed facts>"}`. If uncertain, return
`{"status":"unknown","basis":"<what was inspected>"}`; the request stays
unresolved. Missing files or missing handles do not prove non-delivery. Never
launch a replacement yourself. The runtime decides whether to retry.

## User questions and stopping

`questions --task <id>` lists open human decisions. Ask them in plain words and
record the user's actual words:

| Kind | Record with (also supply `--task <id>`) |
|---|---|
| `confirm_selection` | `confirm-selection --question <qid> --user-message "..."` (add `--pool-file` for different routes) |
| `escalation`, `goal_unmet`, `judgment_failed` | `reply --question <qid> --user-message "..."` |
| `completion_blocked` (real-use) | `real-use --status passed --evidence <file> [--source "<verifier>"]`, or `--status waived --source 'user: "..."'` |

`halt --task <id>` holds the task and requests stops. Native workers may still
need host actions: complete the `host-next` / `host-result` bridge until their
observed status is terminal. `resume --task <id>` continues. Pending, unissued
native spawns are cancelled before any host worker starts.

## Completion evidence and optional limits

`status.evidence` contains goal-check commands, exit codes, working directories
and output tails, plus each integrated artifact's path/hash, acceptance reason,
and outcome checks. Use that evidence for the final handoff; no internal record
inspection is required. Artifact paths are deliverables; patch-task artifacts
are evidence accompanying the reported branch. Do not publish either implicitly.

Optional `--limits-file` fields: `attempts_per_outcome` (3), `goal_rounds` (3),
`judgment_retries` (2), `stall_seconds` (900), `check_timeout` (300),
`unknown_grace_seconds` (120), and `checks_first` (true for patch delivery).
Checks-first creates and reviews failing tests before implementation; approved
tests are then frozen. Disable it for patch work with complete existing checks.
Artifact delivery always uses its contracted checks and semantic inspection.
