---
name: herdr
description: >
  Use whenever the user mentions Herdr or asks to inspect, control, automate,
  or coordinate Herdr workspaces, tabs, panes, terminals, or agents. Covers
  safe CLI usage, workspace targeting, pane operations, agent lifecycle, and
  non-disruptive coordination.
---

# Herdr

Herdr is a terminal multiplexer organized as:

workspace → tab → pane → optional recognized agent

Use the installed CLI as the syntax authority:

```bash
herdr --help
herdr <command> --help
```

Never run bare `herdr`; it may open or attach to the UI.

## Targeting

Prefer explicit IDs from the caller environment:

```bash
printf 'workspace=%s\ntab=%s\npane=%s\nsocket=%s\n' \
  "${HERDR_WORKSPACE_ID:-}" "${HERDR_TAB_ID:-}" \
  "${HERDR_PANE_ID:-}" "${HERDR_SOCKET_PATH:-}"
```

For caller-scoped work, use `HERDR_WORKSPACE_ID` and `HERDR_PANE_ID`.
Do not silently fall back to the visually focused workspace or pane.

If caller IDs are unavailable:

- For read-only inspection explicitly requested by the user, use an explicit
  workspace or pane ID supplied by the user, or discover IDs with:
  ```bash
  herdr workspace list
  herdr tab list
  herdr pane list --workspace <workspace-id>
  herdr agent list
  ```
- For mutating operations, stop and request an explicit target.

IDs are opaque. Read IDs from command JSON; never predict them.

## Safe inspection

Start with the narrowest relevant command:

```bash
herdr workspace list
herdr tab list --workspace <workspace-id>
herdr pane list --workspace <workspace-id>
herdr agent list
herdr api snapshot
```

Do not change focus, zoom, attachment, layout, or lifecycle state unless the
user asks. In particular, do not use these speculatively:

- `workspace focus`
- `tab focus`
- `pane focus`
- `pane zoom`
- `agent attach`

Use `--no-focus` on creation or layout commands unless focus was requested.

## Panes and agents

Use pane commands for ordinary shells, tests, servers, and processes.

Use agent commands only when Herdr recognizes an agent and the target is an
explicit pane ID or registered agent name. A kind such as `codex`, `grok`, or
`claude` is not necessarily a registered agent name.

Lifecycle states are scheduling signals:

- `working`: active work
- `idle`: ready and observed
- `blocked`: approval or question UI detected
- `done`: quiescent background work
- `unknown`: classification is uncertain

`idle` and `done` do not prove that a task completed. Verify the requested
artifact, receipt, or output.

## Reading output

For ordinary processes:

```bash
herdr pane run <pane-id> "<command>"
herdr pane wait-output <pane-id> --regex "<anchored-marker>" --timeout 120000
herdr pane read <pane-id> --source recent-unwrapped --lines 80
```

Avoid blind sleeps. `pane wait-output` can match stale or echoed text, so use
unique anchored markers where possible.

For recognized agents:

```bash
herdr agent wait <agent-or-pane> --until done --timeout 120000
herdr agent read <agent-or-pane> --source recent-unwrapped --lines 120
```

Full-screen agents may use an alternate screen whose history is not available
through scrollback. If reads are empty, inspect the visible screen or ask the
agent to write its result to a Markdown file.

## Layout and helper panes

**One pane per tab.** When you create a new pane, give it its own tab. Do not
`pane split` an existing tab to add another of your panes — a tab you work in
holds its original pane and nothing you add. This keeps agents, servers, and
logs separable: each tab closes independently and the layout stays predictable
for the user.

Before creating, inspect the workspace and reuse an existing non-caller pane
when possible:

```bash
herdr pane list --workspace <workspace-id>
```

When creating a new pane, create a tab and use its root pane:

```bash
created=$(herdr tab create --workspace <workspace-id> \
  --label <short-label> --cwd <path> --no-focus)
pane_id=$(printf '%s' "$created" | jq -r '.result.root_pane.pane_id')
```

Read the pane ID from the JSON response; never predict it. Do not create
repeated helper panes or close panes unless the user explicitly asks.

## Start and prompt Term2 with the helper

For coordinated workers, use [the worker helper](scripts/herdr_worker.py).
Its `--help` lists `inventory`, `start`, `submit`, `steer`, `inspect`, `read`,
`wait`, `stop`, and `close`. It emits JSON receipts, creates nonfocused tabs,
and accepts opaque targets. `start` requires an explicit harness (`--kind`),
model, workspace, name, and cwd. Term2/Pi also require a provider; Codex accepts
an optional configured provider ID; Claude uses its provider environment.
All four accept effort. Unsupported routes fail before creating resources.

```bash
python3 <herdr-skill-dir>/scripts/herdr_worker.py start \
  --name worker --kind term2 --provider <chosen-provider> --model <chosen-model> \
  --effort high --workspace <workspace-id> --cwd <absolute-workdir>
python3 <herdr-skill-dir>/scripts/herdr_worker.py submit <returned-pane-id> \
  --message-file <absolute-brief-or-dispatch-file>
```

Global `--timeout-ms` precedes the subcommand. `submit` performs a bounded
admission wait; `steer` preserves the running context. Term2 steering checks
acknowledgement after echo; other harnesses return delivery with acknowledgement
unverified. Inspect output/inbox before retrying an uncertain submission.
`close <pane-id> --owned-tab <recorded-tab-id>` checks settlement and membership
and refuses tabs containing additional panes. Only supply task-owned resources
whose cleanup is authorized. Failed starts preserve any returned IDs for recovery.

Coordinator integrations discover this skill through the catalog and set
`COORDINATOR_HERDR_HELPER` to this helper's absolute path. The helper uses
`COORDINATOR_HERDR` or `--herdr` to override the underlying CLI. Runtime state
belongs to the coordinator's state directory, outside this skill. Coordinated
launches supply `--operation-id` and `--receipt-file`; the helper saves intent
before creation and resource IDs before launch. An existing receipt is refused
instead of launching again. Recover through the coordinator's lifecycle helper.
A missing creation response remains uncertain and requires inspection.

The older `scripts/start_term2.py` launch/recovery interface remains compatible.
The worker helper reuses its guarded Term2 steering transport. Use the older
interface when recovering a launch made through it:
It creates one non-focused tab, launches an explicit route, waits for the idle
prompt, submits the brief, and returns a JSON admission receipt:

```bash
python3 <herdr-skill-dir>/scripts/start_term2.py \
  --workspace <workspace-id> --cwd <worker-worktree> \
  --brief <absolute-brief-path> --label <worker-label> \
  --provider <provider> --model <model> --effort high
```

`--workspace` defaults only to `HERDR_WORKSPACE_ID`; provider/model are required.
Add `--auto-approve` explicitly when the assignment permits it. The helper does
not create worktrees, install dependencies, choose authorized models, or wait
for task completion. Its `--timeout-ms` applies to each admission step, not
worker runtime. It handles structured Herdr errors on stdout or stderr.

On failure, inspect the returned pane before retrying: it is preserved, never
closed automatically. If it is still the intended idle, empty TUI, repeat the
command with `--pane <returned-pane-id>` to skip creation and launch. Recovery
checks the visible route; requested effort/approval flags are not reapplied.
A pending draft or unknown state requires the manual procedure below instead.

On `status: admitted`, verify worker-authored acknowledgement and attach one
bounded background `herdr agent wait` with your harness completion monitor.
The receipt explicitly leaves acknowledgement unverified. Tests:
`python3 -m unittest discover -s <herdr-skill-dir>/scripts -p test_start_term2.py`.

### Steer a running Term2 worker

`start_term2.py steer` delivers a mid-flight correction to a Term2 worker that is
already running, and verifies the worker acknowledged it:

```bash
python3 <herdr-skill-dir>/scripts/start_term2.py steer <pane-id> \
  --message "<correction>" --ack-timeout-ms 180000
```

Use `--message-file <path>` for anything long. It refuses a non-Term2 pane, a
`blocked` or `unknown` worker, and a pane with no empty input line; it withholds
Enter until it has seen the text in the draft. It does **not** require an idle
worker — Term2 accepts input while generating, and Enter steers at the next
request boundary.

The receipt distinguishes `acknowledged` (marker seen), `delivered`
(`--no-ack` only), and `failed`; a `timed_out` acknowledgement exits non-zero.
It appends a random `STEER_ACK_<hex>` marker request and looks for that marker
only in output **after** the echoed message, because the echo of your own text
contains the marker and matching it anywhere reports a false success. Do not use
`pane wait-output` on an ack marker for this reason.

## Sending text to a running agent

**Launch agents interactively by default**, so they stay correctable for the whole
task. Start the TUI, then use `herdr agent prompt` when its integration supports
prompt delivery:

```bash
herdr pane run <pane-id> 'claude'
herdr agent prompt <pane-id> "<task>"
```

**`agent prompt` never works for `term2`**, which has no Herdr integration and so
no named agent session; it always fails `agent_not_ready`. That is structural, not
a busy worker — do not retry it. Use `scripts/start_term2.py` to launch and
`start_term2.py steer` to correct (above), or the manual pane path below.

Reserve a batch/positional-prompt launch for contexts with no tty at all — running
the agent straight from a shell tool or a pipeline. The convenience of one-shot
dispatch costs you every mid-flight correction for the rest of the task.

`herdr agent prompt <target> <text>` reports `agent_blocked` and, under
`--wait`, `agent_prompt_stalled`. Lifecycle recognition alone does not prove
prompt support: a tracked TUI can lack the named session this command requires.

### Initial-input fallback for an unintegrated TUI

If `agent prompt` returns `agent_not_ready`, inspect the explicit pane with
`pane read --source visible`. Only when it shows the intended interactive agent
at an idle input prompt may you deliver the initial brief through the pane:

```bash
herdr pane run <pane-id> "Read <absolute-brief-path> and execute that assignment."
herdr pane send-keys <pane-id> enter
herdr agent wait <pane-id> --until working --timeout 10000
```

If admission times out, inspect the visible screen once. If the exact brief is
still in the idle draft, send Enter once without resending the text, then check
admission. If it is working, leave it alone; if the shell, a blocked UI, or an
unknown foreground process is visible, stop input and diagnose that state.
Require a worker-authored acknowledgement or transcript evidence before treating
the brief as received. Input echo is not acknowledgement.

This fallback is for verified idle interactive input, not batch processes or
unverified mid-flight steering. Interactivity preserves the possibility of
correction; actual correction delivery still needs evidence.

**`herdr pane send-text` + `send-keys Enter` is not a steering mechanism.** It types
into the tty. Whether anything receives those bytes depends entirely on what the
foreground process is doing with stdin.

**A batch/headless agent run cannot be steered by any mechanism.** It does not read
stdin. Changing its instructions means killing it and relaunching with an updated
brief. For term2 specifically, a positional prompt (`term2 ... "<prompt>"`) selects
that path — see the `term2` skill.

Typing into such a pane is worse than a no-op:

- The **tty line discipline echoes** the text, so it appears in `herdr pane read` and
  looks delivered. **Terminal echo is not evidence of delivery.**
- The bytes stay in the tty input buffer and the **shell executes them when the run
  exits** (observed: `zsh: command not found: CORRECTION`). Quotes open a `>`
  continuation prompt; any command inside your message becomes an argument on that
  line.

**Verify delivery, never assume it.** Grep the run's own stdout (a tee'd log, or the
agent's transcript) for a distinctive phrase from your message. Present in
`herdr pane read` but absent from the process's own output means echo only — the
agent never saw it.

Decide at launch: if a run may need mid-flight correction, start it interactively.
Otherwise put everything in the brief file. Never conclude that an agent "ignored"
an instruction without first confirming the instruction reached it.

## Coordination

For long-running agent work:

1. Dispatch one complete prompt.
2. Confirm admission with one bounded lifecycle check.
3. Do not poll repeatedly.
4. Collect the artifact or receipt at a turn boundary.
5. Reconcile child work before claiming completion.

When a command fails, consult the installed command help and report the exact
failure rather than changing focus or trying an unrelated target.

### Helper response and supervision contract

The worker helper supports explicit model routes for Term2, Pi, Codex, Claude,
and agy. agy accepts `--model` and optional `--effort`; it uses its provider
environment and rejects an unmapped `--provider`.

Herdr's CLI rendering differs from its socket protocol: successful `pane run`,
`pane send-text`, `pane send-keys`, and `agent send-keys` may print no stdout.
The helper normalizes only these acknowledgements. Resource creation, reads,
waits, and `tab close` retain their own response validation. Failed launch
receipts include bounded stdout/stderr diagnostics and known resource IDs;
inspect those resources before any retry.

Use `python3 <skill-dir>/scripts/herdr_worker.py observe <pane-id>` for a bounded,
read-only supervision snapshot. It preserves lifecycle status and flags a
visible Term2 approval menu as `approval_suspected`, even under `working`.
Treat this as a reason to inspect the request, never as approval. It does not
scan historical scrollback markers or promise detection for every harness.
