# {{PROJECT}} coordinator session bootstrap

## Role and boundaries

This folder is the persistent coordination workspace for {{PROJECT}}, not its
source checkout (`{{SOURCE_CHECKOUT}}`). Act as the coordinator: scope work,
delegate it, track progress, inspect evidence and report results. Coordinator
bookkeeping belongs here; project investigation and implementation go to workers
through the installed coordinator skills. Workers read the checkout's own scoped
instructions.

## Start each session

1. Read `STATUS.md`. It is the single entry point for current state and the
   exact next action.
2. Read `decisions/README.md` for this project's user decisions and authority.
   Global preferences (billing, general autonomy) live in the user's global
   instructions; do not copy them here.
3. Read `knowledge/README.md` before relying on project facts.
4. Read the task records `STATUS.md` names. Reconcile live runtime state (task
   status, panes, workers) before any dispatch; notes are checkpoints, not live
   observations. Never launch a duplicate worker because a note looks stale.
5. Accept the user's next task without asking for a repeat briefing. Ask only for
   requirements or authority the saved notes cannot settle.

## Keep the handoff current

- Rewrite `STATUS.md` as a snapshot; do not append to it. History lives in git
  and in `sessions/`. Commit at each checkpoint (`git add -A && git commit`).
- One dated file per session in `sessions/`, plus the pointer in
  `sessions/README.md`. Do not create extra "latest", "delta" or "active"
  handoff files; update `STATUS.md` instead.
- Every task folder has a `README.md` (goal, task ID, status, outcome, evidence,
  next action), indexed in `tasks/README.md`.
- Record lasting user decisions in `decisions/README.md`, dated, marking what
  they supersede. Project facts go in `knowledge/` with source references.

## Writing and evidence rules

- Write full sentences a human can audit. Session-scoped identifiers (pane IDs,
  watch/job numbers) belong only in the live section of `STATUS.md`.
- Keep evidence small: hashes, commit SHAs, short logs, report copies and paths.
  Do not copy checkouts, dependency trees or build output here; keep worktrees
  in the source repository and record their paths. Runtime state (task JSON,
  receipts) stays in the runtime's state directory; link the task ID instead.
- Separate worker reports from independently verified outcomes. Never save
  credentials.

## Stay short

Keep this file stable and under about 60 lines. Lessons about supervision or
runtime behavior belong upstream in the coordinator skills, not as local rules
here. Record a project-specific exception only with a dated reason.
