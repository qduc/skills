---
name: coordinator
description: Coordinate work through bounded delegation, dependency management, verification, and integration. Use when the user asks to orchestrate workers or subagents, or when substantial independent work benefits from supervised delegation.
disable-model-invocation: true
---

# Coordinator

You are the front desk. You talk with the user, turn their request into a task
the runtime can check, relay its questions, and report the result. The runtime
(`scripts/coord.py`) owns the order of work and every gate: isolation, worker
launch, independent checks, citation checks, integration, goal checks, retries,
and completion. It asks for AI judgment only at fixed points, as typed requests.

**Done when:** the runtime reports `done` and you have told the user what landed,
on which branch or at which artifact paths, with the goal-check evidence; or the task is halted or blocked
and the user knows exactly what decision or input it needs.

## Choose the path

Use the **driven runtime** for Git changes and report/file-artifact delivery,
including research and work outside Git. Workers may be native host agents or
non-interactive processes. That is the default. Read
[Driven runtime](references/driven-runtime.md) before the first command.

Use [Manual coordination](references/manual-coordination.md) for provisioning,
task records started before the driven runtime, and interactive Herdr workers.
Native agents and report/artifact tasks do not need that path.

## Driven runtime

0. **Check setup.** Run `scripts/coord.py doctor` (with `--workers-file` for
   task-specific native routes; see the guide). If it is not ready, tell the
   user the coordinator needs a one-time setup, then read the `coordinator-setup`
   skill's driver interview and run it with them before continuing.
1. **Shape the task.** Separate what the user needs from any implementation they
   suggested. State the goal and at least one observable acceptance criterion.
   If nothing they said is checkable, ask one question: what result means done?
   Mark `--real-use-required` when the change is to a skill or workflow.
2. **Start it.** Use `--repo` for Git changes or `--workspace` for read-only
   source material and file deliverables. Worker routes and the judge come from
   the host profile or the task's worker configuration. The
   runtime asks for a harness recommendation and then a user confirmation;
   nothing runs before it.
3. **Drive it** with `coord.py run`. Answer judgment requests through the
   configured judge or yourself, following the guide each prompt carries.
   When it waits on `host`, use `host-next`, execute that exact native-tool
   request, and return the observation with `host-result`. The guide covers
   this small bridge; do not use lower-level lifecycle helpers.
4. **Relay questions.** Put each one to the user in plain words and record their
   reply with their own words. Read [Driven runtime](references/driven-runtime.md)
   for which command records which kind.
5. **Hand back** the branch or delivered artifact paths and the checks in
   `status.evidence`. Merging or publishing is the user's decision.

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
