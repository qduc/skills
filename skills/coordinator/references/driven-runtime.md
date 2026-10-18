# Driven runtime: front-desk commands

`scripts/coord.py` is the whole interface. Every command prints one JSON object;
`result.waiting_on` says what happens next: `judgment`, `user`, `workers`, or
nothing when `done`. Task IDs accept a unique prefix of 6+ characters.

## Configuration

The driver needs worker commands: non-interactive harness invocations that take
the prompt as one argv element `"{prompt}"`, run in the current directory, and
exit when finished. Read them from the host profile's `adapters.driver.workers`
(see [Host profile](host-profile.md)); when that entry is missing, run the
`coordinator-setup` skill first. Write the list to a file:

```json
[{"route": {"harness": "<harness>", "model": "<model>"},
  "argv": ["<harness-cli>", "<non-interactive flag>", "--model", "<model>", "{prompt}"]}]
```

Take the real flags from the harness's installed help. The worker must be able
to edit files and run the checks without approval prompts, since nobody is there
to answer them.

These are the routes that *can* run. Which ones *will* run is the user's
per-task choice, confirmed below.

`adapters.driver.judge`, when present, is the argv for answering judgments
headlessly (prompt as a `"{prompt}"` element, or on stdin when there is none).
Limits are optional: `attempts_per_outcome` (3), `goal_rounds` (3),
`judgment_retries` (2), `stall_seconds` (900), `check_timeout` (300).

## Start

```text
coord.py start --repo <git root> --goal "<outcome the user wants>" \
  --criterion "<observable done condition>" [--criterion ...] \
  [--constraint "..."] [--authority "..."] --workers-file workers.json \
  [--real-use-required] [--limits-file limits.json]
```

Use `--real-use-required` when the task changes a skill or orchestration
workflow. The task starts from the repository's current commit; tell the user if
the result reports uncommitted changes, because those are not included.

## Drive

```text
coord.py run --task <id> --judge-command-file judge.json   # headless judging
coord.py run --task <id>                                   # stops at each judgment
```

`run` advances until done, a user question, or a judgment it cannot answer.
Run it in the background for long tasks and check `coord.py status --task <id>`.

Without a judge command, answer judgments yourself: `coord.py prompt --task <id>
--request <rid>` prints the full request, including its guide from
`references/judgments/`. Read what it points at (the repository, the patch),
decide, and submit only the JSON object: `coord.py answer --task <id> --request
<rid> --file answer.json`. A rejected answer comes back with the error; fix the
answer, not the validator.

## Questions for the user

`coord.py questions --task <id>` lists them. Ask the user in plain words, then
record their reply with their own words as `--user-message`:

| Kind | Record with |
|---|---|
| `confirm_selection` | `confirm-selection --question <qid> --user-message "..."` (add `--pool-file` when they chose different routes) |
| `escalation`, `goal_unmet`, `judgment_failed` | `reply --question <qid> --user-message "..."` |
| `completion_blocked` (real-use) | `real-use --status waived --source 'user: "..."'`, or run the real-use check and `--status passed --evidence <file>` |

## Stop and hand back

`coord.py halt --task <id>` stops all workers and holds; `resume` continues.
When `done`, the result is on the reported branch in the reported integration
worktree; merging it is the user's decision. Task records live under the
coordinator state directory with every attempt's prompt, logs, patch, checks,
and the judgment history in `drive.json`.
