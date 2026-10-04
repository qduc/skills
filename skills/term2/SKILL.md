---
name: term2
description: Run, configure, and orchestrate term2 instances for interactive coding sessions or non-interactive CLI tasks. Use when launching term2 in terminal multiplexers (herdr, tmux), running non-interactive batch tasks via term2, configuring providers (OpenRouter, Codex, OpenAI), or querying term2 CLI flags and settings.
compatibility: Requires term2 binary on PATH or node dist/cli.js in repository root.
---

# term2

`term2` is a terminal-based AI coding assistant. It supports interactive React (Ink) TUI sessions, headless non-interactive execution, JSON event streaming, lite sessions, remote SSH sessions, model discovery, and browser-based OAuth login.

## Invocation Modes

### 1. Non-Interactive / Scripted (Recommended for Agents)
When given one or more prompt arguments, `term2` runs headless and exits on completion:

```bash
# Basic query (read-only tools by default)
term2 "explain this function"

# Allow tools (file edits, shell execution) without interactive prompts
term2 --auto-approve "run tests and fix any lint errors"

# Structured NDJSON event stream on stdout (silent stderr)
term2 --json -q "summarize recent git commits"

# Stream reasoning tokens to stderr
term2 --show-reasoning "design an architecture plan"

# Suppress non-error diagnostics on stderr
term2 --quiet "generate json payload"

# Run with minimal context; the session is not persisted as a normal conversation
term2 --lite "summarize this repository"
```

### 2. Interactive TUI (Multiplexer Panes Only)
Running `term2` with **no prompt** launches the interactive full-screen Ink TUI.

> [!CAUTION]
> Never run bare `term2` directly inside an agent tool-execution subshell. It will block waiting for interactive TTY input. Always launch interactive sessions inside a multiplexer pane (e.g. `herdr`).

```bash
# Interactive launch with specific model and provider
term2 -p codex -m gpt-5.6-luna
```

### 3. Session Resumption
```bash
term2 --resume              # Resume the last conversation in current project
term2 --resume <session-id> # Resume specific session ID
term2 --resume <id> --fork  # Fork conversation into a fresh session
term2 --resume ls           # List recent conversations
```

---

## Providers & Model Slugs

Override defaults with `-p, --provider <provider>` and `-m, --model <model>`. The model accepts a pattern or ID in `provider/id` form and can include an optional `:<thinking>` suffix; `--list-models [search]` lists available models grouped by provider.

### OpenRouter approval gate

Choose a non-OpenRouter provider by default. Use the `openrouter` provider only after the user explicitly approves OpenRouter for that invocation. A request for a model or model family—even one available through OpenRouter—is not provider approval; ask before selecting `-p openrouter`.

| Provider (`-p`) | Model Slug Format (`-m`) | Examples |
|---|---|---|
| `openrouter` | **Must include vendor prefix** (`author/slug`) | `deepseek/deepseek-v4-flash`, `z-ai/glm-5.3-flash`, `qwen/qwen3.7-flash` |
| `codex` | Standard bare slug | `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-5.4` |
| `openai` | Standard bare slug | `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| `opencode` | Bare or contributor slug | `muse-spark-1.2-contributor` |
| Custom OpenAI | Matches custom provider ID from settings | Custom provider names configured in `settings.json` |

### Reasoning Effort (`-r, --reasoning`)
Values: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `default`.
```bash
term2 -p codex -m gpt-5.6-sol -r medium
term2 --list-models gpt-5
```

### Remote SSH sessions

Run a session against a remote host. Non-lite SSH sessions require the remote working directory; the SSH port defaults to 22.

```bash
term2 --ssh user@host --remote-dir /path/to/project
term2 --ssh user@host --remote-dir /path/to/project --ssh-port 2222
```

### Authentication and diagnostics

Authentication commands open a browser for OAuth login and exit afterward:

```bash
term2 --grok-login
term2 --codex-login
```

Inspect the installed CLI without starting a session:

```bash
term2 --version
term2 --help
```

---

## Herdr Multiplexer Integration

To provision interactive `term2` tabs in `herdr` without interrupting the user:

```bash
# 1. Resolve active workspace
ws_id=$(herdr api snapshot | jq -r '.result.snapshot.focused_workspace_id')

# 2. Create tab non-disruptively
tab_json=$(herdr tab create --workspace "$ws_id" --label "term2-luna" --cwd "$PWD" --no-focus)
pane_id=$(printf '%s' "$tab_json" | jq -r '.result.root_pane.pane_id')

# 3. Launch term2 in the pane
herdr pane run "$pane_id" "term2 -p codex -m gpt-5.6-luna"

# 4. Verify TUI readiness (use visible source for alternate-screen apps)
herdr pane read "$pane_id" --source visible
```

---

## Settings & Storage

- **Linux Settings Path**: `~/.local/state/term2-nodejs/settings.json`
- **macOS Settings Path**: `~/Library/Logs/term2-nodejs/settings.json`
- **Conversations / Logs**: `~/.local/share/term2-nodejs/conversations/`

CLI flags (`-p`, `-m`, `-r`, `-l`) override persisted settings for that invocation without mutating `settings.json`. `--quiet`, `--json`, and `--show-reasoning` affect non-interactive output; `--fork` only applies with `--resume`.

---

## Gotchas

- **Bare invocations start TUI**: Omitting a prompt string enters the interactive TUI. For background/scripted use, always pass the prompt as an argument.
- **A positional prompt is non-interactive and CANNOT be steered**: `term2 ... "<prompt>"` takes the non-interactive path (`source/cli.tsx:378`, `:831-841` → `non-interactive.ts`). It never mounts Ink and never reads stdin, so **no mechanism can send it a mid-flight correction** — not `herdr pane send-text`, not `herdr agent prompt`. Changing its instructions requires killing it and relaunching with an updated brief.

  Typing into such a pane is actively harmful: the **tty line discipline echoes** the text, so it shows up in `herdr pane read` and looks delivered, while the process never receives it. The bytes then sit in the tty input buffer and **the shell runs them when the process exits** (observed: `zsh: command not found: CORRECTION`). Quotes in the message open a `>` continuation prompt.

  **Verify, do not assume:** grep the run's tee'd stdout for a distinctive phrase from your message. Present in `herdr pane read` but absent from the tee log = terminal echo only. Non-interactive runs also write **no** conversation transcript under `~/.local/share/term2-nodejs/conversations/`, so there is nothing there to check against.

  **Default to interactive when running under a terminal multiplexer.** Launch the TUI (`term2 -m <model> -p <provider> -r high`). Use `herdr agent prompt` when supported; lifecycle tracking does not imply prompt integration. For `agent_not_ready`, follow the [Herdr verified-idle initial-input fallback](../herdr/SKILL.md#initial-input-fallback-for-an-unintegrated-tui), including pending-draft recovery and worker acknowledgement. Reserve positional prompts for contexts with no tty, such as a shell tool or pipeline.
- **Tool execution requires `--auto-approve`**: In non-interactive mode, tool calls are refused by default unless `--auto-approve` is passed.
- **Lite mode is session-only**: `--lite` starts with minimal context and does not use the normal persisted conversation context.
- **SSH requires a directory for full sessions**: Pass `--remote-dir` with `--ssh` unless using a lite session; use `--ssh-port` for non-default SSH ports.
- **Model discovery is provider-aware**: Use `--list-models` (optionally with a search term) instead of guessing model IDs.
- **Login flags exit after authentication**: `--grok-login` and `--codex-login` are setup commands, not conversation modes.
- **OpenRouter requires vendor prefix**: Passing bare `deepseek-v4-flash` to OpenRouter may fail; always pass `deepseek/deepseek-v4-flash` or `z-ai/glm-5.3-flash`.
- **Alternate screen output**: In terminal multiplexers, `term2` renders to the alternate screen. Standard scrollback reads (`recent-unwrapped`) will appear empty; read with `--source visible` instead.
