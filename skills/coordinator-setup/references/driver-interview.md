# Driver interview

Use this when `coord.py doctor` reports no host profile or no driver workers.
You are setting up which agent commands the coordinator may launch as workers,
and optionally which command answers its judgment requests. Interview the user
briefly, build the commands from what is actually installed, then let the probes
decide what gets saved. Keep it to a few questions; nobody wants a form.

## 1. Look before asking

Run `host_profile.py discover` and note which agent CLIs are on PATH
(`claude`, `codex`, `pi`, `term2`, and anything else the user mentions). Read
each candidate's `--help` for its non-interactive mode, model flag, and
permission or approval flags. Do not ask the user for facts the help text answers.

## 2. Ask, in plain words

Ask only what inspection cannot settle, in one or two messages:

1. **Which agents should do the work?** Offer the installed ones you found. One
   is enough to start; a second gives failed attempts a genuinely different try.
2. **Which model for each?** Suggest a sensible default per tool (a mid-tier model
   for routine edits) and accept their choice. Concrete model identifiers only.
3. **How much autonomy?** Workers run unattended, so they must edit files and run
   tests without approval prompts. Say plainly what that means: each worker gets
   its own git worktree, but the process runs as the user and is not sandboxed.
   If they want a narrower setting, use the tool's most restrictive mode that
   still lets it edit and run commands, and let the probe show whether it works.
4. **Judge (optional).** Should judgments be answered automatically by a CLI (a
   strong model in a read-only or plan mode is a good fit), or should the front
   desk answer them in the conversation? Automatic is faster; in-conversation
   lets the user watch every decision.

Recording a route here only says it *can* run. Each task still asks the user to
confirm which routes it uses, so these answers are not a standing approval.

## 3. Build the commands

Each worker is `{"route": {"harness": ..., "model": ...}, "argv": [...]}`. The
argv must run one whole attempt and exit, with the prompt as a single
`"{prompt}"` element and no shell. The judge argv takes the prompt as a
`"{prompt}"` element, or on stdin when it has none, and must print a JSON object.
Write the worker list to a scratch file outside any repository.

## 4. Probe and save

```text
host_profile.py set-driver --workers-file <workers.json> [--judge '<json argv>']
```

It runs every proposed worker on a throwaway repository (create one file with
exact text, then exit) and the judge on a tiny JSON request, then saves only what
passed into `adapters.driver`, keeping the rest of an existing profile. Probes
call real models, so mention that each one costs a little and takes up to a few
minutes.

When a probe fails, read its `reason` and `output_tail`: a missing flag, a prompt
for approval, a login, or a model name the tool rejects. Fix the command and probe
that one again with `probe-worker --argv '<json>'`; ask the user only if the fix
changes something they chose. Report what was saved, what failed and why, and the
profile path. Then return to the task with `coord.py doctor`.
