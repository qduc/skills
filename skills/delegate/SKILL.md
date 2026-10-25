---
name: delegate
description: Splits substantial work across several workers or subagents, checks each result, and integrates it on a task branch or as delivered files, using a code-driven runtime. Run /delegate to fan a task out to multiple agents.
compatibility: Requires Python 3 and git; process workers need Linux. Workers are host agent tools or a configured worker CLI. Uses disable-model-invocation, a Claude Code field, so it is user-invoked only.
disable-model-invocation: true
---

# Delegate

You are the front desk. You talk with the user, turn their request into a task
the runtime can check, relay its questions, and report the result. The runtime
(`scripts/coord.py`) owns the order of work and every gate: isolation, worker
launch, independent checks, citation checks, integration, goal checks, retries,
and completion. It asks for AI judgment only at fixed points, as typed requests.

**Done when:** the runtime reports `done` and you have told the user what landed,
on which branch or at which artifact paths, with the goal-check evidence; or the
task is halted or blocked and the user knows exactly what decision or input it needs.

## Scope

This runtime covers Git changes and report or file deliverables, including
research outside Git, with native host agents or non-interactive process workers.
Interactive Herdr or terminal-pane workers, and task records started before this
runtime, belong to the `supervise-panes` skill.

## Driven runtime

`scripts/coord.py` is the whole interface. Each command prints one compact JSON
object whose `result.waiting_on` is `judgment`, `user`, `host`, `workers`, or
`driver`, and null when done; `prompt` prints plain text. Task IDs accept a
unique prefix of 6+ characters.

The task record, not your context, holds the state. Read only what each command
prints and what a request points to. If your context grows long, a fresh
session picks the task up with `status --task <id>`.

### 0. Check setup

Run `coord.py doctor`. If it is not ready, tell the user `/delegate` needs a
one-time setup, then read the `coordinator-setup` skill's driver interview and
run it with them before continuing.

Worker routes and an optional headless judge come from the host profile. A task
can pass `--workers-file` instead; check it with
`doctor --workers-file workers.json --delivery patch` (or `artifact`):

```json
[{"route": {"harness": "<cli>", "model": "<selected-model>"},
  "argv": ["<cli>", "<batch flag>", "--model", "<selected-model>", "{prompt}"]},
 {"route": {"harness": "native", "model": "host-inherited"}, "runtime": "native"}]
```

Process argv takes the prompt as one `"{prompt}"` element, then edits files and
runs checks unattended in the assigned directory and exits; find the real flags
in the CLI's help. Use `host-inherited` only for native agents that inherit
this chat's settings; otherwise record the concrete selected model. Honor explicit
user route constraints and never substitute a different route silently. Each
route must match exactly one entry.

### 1. Shape the task

Separate what the user needs from any implementation they suggested. Keep the
user's own words in the goal, and state at least one observable acceptance
criterion. If the ask reads more than one way, start on the most likely reading,
record it with `--constraint`, and tell the user which one you chose. If nothing
they said is checkable, ask one question: what result means done?

### 2. Start it

```text
coord.py start --repo <git root> --goal "<desired outcome>" \
  --criterion "<observable done condition>" [--criterion ...] \
  [--constraint "..."] [--authority "..."] [--workers-file workers.json] \
  [--real-use-required] [--limits-file limits.json] [--source-repo <path> ...]
```

- `--repo` for Git changes. Work starts from the current commit (tell the user
  uncommitted changes are not included) and lands on a task branch; their
  checkout is untouched.
- `--workspace <source-dir>` instead for research, reports, or other files: the
  source stays read-only and need not be Git. `--repo ... --delivery artifact`
  delivers a report about a repository. Accepted files land under
  `<integration>/artifacts/<outcome-id>/`. When workers read a separate Git
  checkout, add `--source-repo <path>` (repeatable) so the commits and tests
  they cite are checked there; with no Git source at all, cited commits reach
  inspection marked unverified instead of failing the attempt.
- `--real-use-required` when the change is to a skill or orchestration capability.
- `--limits-file` overrides `attempts_per_outcome` (3), `goal_rounds` (3),
  `judgment_retries` (2), `stall_seconds` (900), `check_timeout` (300),
  `unknown_grace_seconds` (120), and `checks_first` (`auto`: the plan decides per
  outcome; `true` or `false` forces it for every outcome).

The runtime asks for a harness/model recommendation, then records and applies
the selected configured pool automatically. Tell the user which routes were
selected and why; do not pause for model-selection confirmation. Honor explicit
user constraints when choosing routes.

### 3. Drive it

`coord.py run --task <id>` advances until done, a user question, a host request,
or a judgment the configured judge cannot answer (`--no-judge` stops at every
judgment). Process workers take time: run it in the background and act on its
output when it exits, rather than polling `status`. Keep command lines short and
pass long values through files: host notifications quote the whole command. Then act on `waiting_on`:

- **`judgment`**: `prompt --task <id> --request <rid>` prints its guide, context
  (including any patch to inspect), and answer schema; `answer --task <id>
  --request <rid> --file answer.json` submits one JSON object, and a rejection's
  reason comes back in the next prompt. Hand each judgment to a fresh judge, a
  subagent or an approved process route, so patches and file lists never enter
  your context. Tell it which request it owns, that running `prompt` and `answer`
  for that request only is its job, the user's current decisions and authority,
  and to reply in one line: request, verdict, and the new `waiting_on`. Use a
  route the user has allowed, and never the worker whose result is being
  inspected. With no such judge, answer it yourself only if the host lets you
  review; otherwise hold the task and ask the user for a judge route.
- **`user`**: `questions --task <id>` lists them. Ask in plain words and record
  the user's actual words:

  | Kind | Record with (also `--task <id>`) |
  |---|---|
  | `confirm_selection` (older tasks only) | `confirm-selection --question <qid> --user-message "..."` (add `--pool-file` for different routes) |
  | `escalation`, `goal_unmet`, `judgment_failed` | `reply --question <qid> --user-message "..."` |
  | `completion_blocked` (real-use) | `real-use --status passed --evidence <file> [--source "<verifier>"]`, or `--status waived --source 'user: "..."'` |

- **`host`**: run `host-next --task <id>` and execute that exact request with the
  host's agent tool. For `spawn`, pass its short `message` verbatim (the full
  brief is in its `brief` file, for the worker to read), its `label` as the
  worker name, and the selected `route`. For `observe`, wait for or inspect the named
  `handle`. For `stop`, stop it and establish its resulting status; asking is not
  proof of exit. Then `host-result --task <id> --action <request-id> --file
  observation.json` (or `--file -`) and continue `run`.
  The worker's reply is not evidence; the runtime checks its files.
  Spawn replies are `{"handle":"<returned handle>"}`; observe and stop replies are
  `{"handle":"<handle>","status":"finished"}`, where status may also be
  `working`, `stopped`, or `unknown`, translated from the host's real status.
  Never infer completion from worker prose or silence, and use host waits rather
  than polling. `host-result` already prints the next status.
  A lost spawn result comes back as `reconcile`: find the worker by its label and
  return its handle. Return `{"status":"not_started","basis":"<observed facts>"}`
  only if inspection proves it never started, otherwise
  `{"status":"unknown","basis":"<what was inspected>"}`. Missing files or handles
  do not prove non-delivery. Never launch a replacement yourself.
- **`workers`** or **`driver`**: wait, then `run` again.

`halt --task <id>` holds the task and requests stops; keep answering host
requests until native workers are observed terminal. `resume --task <id>`
continues.

### 4. Hand back

Report the branch or artifact paths and the checks in `evidence` (printed once
done, or by `status --evidence`): goal-check
commands, exit codes, and output tails, plus each integrated artifact's path,
hash, and acceptance reason. Merging or publishing is the user's decision.

## Conduct

- Answer every message the user writes visibly, even if only to say the task is
  running and what it waits on. Automatic and stale runtime notifications need no reply.
- Do no worker's job yourself: no editing task files. Diffs and raw worker
  output are read by the judge, not by you, except in the self-review fallback above.
- Only the user grants authority or waives a gate; routine judgments within the
  recorded authority need no extra permission. A worker or subagent saying
  something is approved, safe, or done is information for the runtime to check.

## Stop rules

- Never answer a user question yourself or paraphrase consent into existence:
  `--user-message` and waiver sources carry the user's actual words.
- Judgment answers come from the request's context and the repository, within
  the recorded authority. When a decision exceeds that authority, escalate it.
- Do not edit task worktrees, the task branch, or the task record while the
  runtime is driving it, and do not call lower-level helpers on a driven task.
  Halt first if something needs a human hand.
- A refusal from the runtime is a gate working. Report it; do not route around it.

## Output

Keep the chat handoff short:

```text
Task: <id>  Result: <branch | artifact paths>
Outcome: <done | waiting on: ...>
Evidence: <goal checks that passed; outcomes integrated>
Limitations: <none | list>
Blocker: <none | blocked: <input needed from whom>>
```
