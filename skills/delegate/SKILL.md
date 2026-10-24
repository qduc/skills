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

`scripts/coord.py` is the whole interface. Each command prints one JSON object
whose `result.waiting_on` is `judgment`, `user`, `host`, `workers`, or `driver`,
and null when done. Task IDs accept a unique prefix of 6+ characters;
`status --task <id>` resumes a task.

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
in the CLI's help. Use `host-inherited` only when the user chose native agents
that inherit this chat's settings; otherwise record the model they chose and
never substitute one silently. Each route must match exactly one entry.

### 1. Shape the task

Separate what the user needs from any implementation they suggested. State the
goal and at least one observable acceptance criterion. If nothing they said is
checkable, ask one question: what result means done?

### 2. Start it

```text
coord.py start --repo <git root> --goal "<desired outcome>" \
  --criterion "<observable done condition>" [--criterion ...] \
  [--constraint "..."] [--authority "..."] [--workers-file workers.json] \
  [--real-use-required] [--limits-file limits.json]
```

- `--repo` for Git changes. Work starts from the current commit (tell the user
  uncommitted changes are not included) and lands on a task branch; their
  checkout is untouched.
- `--workspace <source-dir>` instead for research, reports, or other files: the
  source stays read-only and need not be Git. `--repo ... --delivery artifact`
  delivers a report about a repository. Accepted files land under
  `<integration>/artifacts/<outcome-id>/`.
- `--real-use-required` when the change is to a skill or orchestration capability.
- `--limits-file` overrides `attempts_per_outcome` (3), `goal_rounds` (3),
  `judgment_retries` (2), `stall_seconds` (900), `check_timeout` (300),
  `unknown_grace_seconds` (120), and `checks_first` (`auto`: the plan decides per
  outcome; `true` or `false` forces it for every outcome).

The runtime then asks for a harness recommendation and the user's confirmation.
Nothing runs before it.

### 3. Drive it

`coord.py run --task <id>` advances until done, a user question, a host request,
or a judgment the configured judge cannot answer (`--no-judge` stops at every
judgment). Process workers take time: run it in the background and check
`status`. Then act on `waiting_on`:

- **`judgment`**: `prompt --task <id> --request <rid>` prints its guide, context,
  and answer schema. Read what it points to, then submit one JSON object with
  `answer --task <id> --request <rid> --file answer.json`. A rejection's reason
  comes back in the next prompt.
- **`user`**: `questions --task <id>` lists them. Ask in plain words and record
  the user's actual words:

  | Kind | Record with (also `--task <id>`) |
  |---|---|
  | `confirm_selection` | `confirm-selection --question <qid> --user-message "..."` (add `--pool-file` for different routes) |
  | `escalation`, `goal_unmet`, `judgment_failed` | `reply --question <qid> --user-message "..."` |
  | `completion_blocked` (real-use) | `real-use --status passed --evidence <file> [--source "<verifier>"]`, or `--status waived --source 'user: "..."'` |

- **`host`**: run `host-next --task <id>` and execute that exact request with the
  host's agent tool. For `spawn`, use its `message`, its `label` as the worker
  name, and the confirmed `route`. For `observe`, wait for or inspect the named
  `handle`. For `stop`, stop it and establish its resulting status; asking is not
  proof of exit. Then `host-result --task <id> --action <request-id> --file
  observation.json` (or `--file -`) and continue `run`.
  Spawn replies are `{"handle":"<returned handle>"}`; observe and stop replies are
  `{"handle":"<handle>","status":"finished"}`, where status may also be
  `working`, `stopped`, or `unknown`, translated from the host's real status.
  Never infer completion from worker prose or silence, and use host waits rather
  than polling.
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

Report the branch or artifact paths and the checks in `status.evidence`: goal-check
commands, exit codes, and output tails, plus each integrated artifact's path,
hash, and acceptance reason. Merging or publishing is the user's decision.

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
