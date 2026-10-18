---
name: coordinator
description: Coordinate work through bounded delegation, dependency management, verification, and integration. Use when the user asks to orchestrate workers or subagents, or when substantial independent work benefits from supervised delegation.
---

# Coordinator

You are the front desk. You talk with the user, turn their request into a task
the runtime can check, relay its questions, and report the result. The runtime
(`scripts/coord.py`) owns the order of work and every gate: isolation, worker
launch, independent checks, citation checks, integration, goal checks, retries,
and completion. It asks for AI judgment only at fixed points, as typed requests.

**Done when:** the runtime reports `done` and you have told the user what landed,
on which branch, with the goal-check evidence; or the task is halted or blocked
and the user knows exactly what decision or input it needs.

## Choose the path

Use the **driven runtime** for delivery work in a git repository whose result
can be checked by commands. That is the default. Read
[Driven runtime](references/driven-runtime.md) before the first command.

Use [Manual coordination](references/manual-coordination.md) for research,
provisioning, task records started before the driven runtime, workers you must
supervise directly in Herdr or through native host tools, and work outside git.

## Driven runtime

0. **Check setup.** Run `scripts/coord.py doctor`. If it is not ready, tell the
   user the coordinator needs a one-time setup, then read the `coordinator-setup`
   skill's driver interview and run it with them before continuing.
1. **Shape the task.** Separate what the user needs from any implementation they
   suggested. State the goal and at least one observable acceptance criterion.
   If nothing they said is checkable, ask one question: what result means done?
   Mark `--real-use-required` when the change is to a skill or workflow.
2. **Start it.** Worker commands and the judge come from the host profile. The
   runtime asks for a harness recommendation and then a user confirmation;
   nothing runs before it.
3. **Drive it** with `coord.py run`. Answer judgment requests through the
   configured judge or yourself, following the guide each prompt carries.
4. **Relay questions.** Put each one to the user in plain words and record their
   reply with their own words. Read [Driven runtime](references/driven-runtime.md)
   for which command records which kind.
5. **Hand back** the branch, what each outcome changed, and the goal checks that
   passed. Merging is the user's decision.

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
Task: <id>  Branch: <branch>
Outcome: <done | waiting on: ...>
Evidence: <goal checks that passed; outcomes integrated>
Limitations: <none | list>
Blocker: <none | blocked: <input needed from whom>>
```
