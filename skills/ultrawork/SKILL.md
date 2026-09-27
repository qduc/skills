---
name: ultrawork
description: Take a non-trivial task all the way to verified completion without needing the user to babysit it — understand first, fix a checkable contract, work in small proven steps, and refuse to call anything done without real-surface evidence. Use when the user says "ulw", "ultrawork", "just get it done", "finish this properly", or hands off an implementation they expect to come back to finished. Use ulw-plan instead when they want a plan before any code, and coordinator when the work splits into several independent lanes for workers. Not for quick questions or one-line edits.
---

# Ultrawork

Every time the user has to step back in — to fix half-finished code, repeat a requirement, or point out that the "working" feature doesn't work — the run has failed. The job is to make that unnecessary: the user states the outcome, you deliver it verified, and you stop.

Two rules hold for the whole run:

- **Deliver exactly what was asked.** Not a demo, a skeleton, a "simplified version", or "a starting point you can extend". If something genuinely has to be cut, say so and get agreement *before* delivering less — never silently.
- **Add nothing that wasn't asked.** No adjacent refactors, speculative abstractions, extra config knobs, or bonus features. Exactly X means neither a subset nor a superset.

## 1. Understand before touching anything

Restate the outcome in one or two sentences: what will be true when you are done, for whom. Then close the gap between that sentence and what you actually know.

- **Facts the system can answer, look up.** Existing patterns, conventions, how the code currently behaves, what a library supports: read the code, run it, check the docs. Never ask the user something the repository could tell you.
- **Decisions only the owner can make, ask.** Irreversible or destructive actions, public interface or config shape, data/schema shape, new dependencies, spending money, scale or audience targets. Ask once, briefly, with your recommended option first. Reversible internal choices you make yourself and note in the notepad.
- **Readiness check.** You are not ready to change code while your plan contains "probably" or "maybe", you can't name the files you'll touch, or you don't understand how the code you're changing works today. Investigate until you can.

Route bigger work out: if the outcome is fuzzy or the change spans many surfaces with real design choices, run **ulw-plan** first. If the work splits into independent lanes that benefit from parallel workers, hand execution to **coordinator** and keep this skill's contract and evidence rules as the bar.

## 2. Write the contract

Before the first edit, write down:

- **Goal** — one outcome sentence (a state, not an activity like "investigate X").
- **Scenarios** — sized to the change: 1–2 for a small single-surface change, 3+ for multi-surface or risky work. Draw from:
  - *Happy path* — always.
  - *Edge* — empty, boundary, malformed, concurrent — when the change is risky.
  - *Adjacent regression* — a neighbouring caller or sibling feature still works — when more than one surface is touched.
- For each scenario: a **binary pass condition** ("exits 0 and prints the new column", not "works") and the **exact check** that proves it — the literal command, request, or browser action with concrete inputs.
- **Stop condition** — the observable state that ends the run.

The scenarios are the contract. You are done when every one passes with evidence, not before and not "mostly".

## 3. Keep a notepad

Create one markdown file at the start (outside the repo unless the project already keeps agent notes somewhere) and tell the user its path. Append; don't rewrite.

```
# Notepad — <goal>
## Contract        goal, scenarios, stop condition
## Now             the single step in progress
## Todo            remaining steps, in order
## Findings        non-obvious facts, with file:line
## Evidence        scenario → PASS/FAIL → how it was proven
## Decisions       reversible choices you made and why
```

If context is compacted or the session restarts, re-read the notepad and resume from `Now`. It is the only memory that survives.

Write todos so each one says where, what, which scenario it serves, and how it will be verified — `src/auth/login.ts: add per-IP limit for S1 — verify by 6th curl returning 429`. "Implement feature" is not a todo. Keep exactly one in progress; mark each done the moment its check passes.

## 4. Work in small, proven steps

For each step:

1. **Read the tests that cover the area first.** They are the record of intended behaviour. Note whether they encode the intent, cover this path, and pass today. A test that looks wrong is a finding to report — never edit a test just to turn it green, and never delete or skip one to get a clean run.
2. **Bugs: reproduce before fixing.** Capture the failure. Refactors: confirm the tests are green on the unchanged code first.
3. **Make the smallest change that satisfies the scenario**, following the patterns already in the codebase. Update tests your change makes stale.
4. **Add a test only when it earns its place** — the repository keeps tests for this kind of behaviour *and* a regression would otherwise slip through unnoticed. It must be able to fail. A test that restates the change (asserts a constant, a string, a rename, that a function was called) proves nothing; the run is the proof. Prose, prompt, docs and purely visual changes get review plus a real-surface check, not a test pinning their text.
5. **Run the step's check**, record the result in the notepad, and only then move on.

Commit in small verified increments if the user allows commits. Before writing a message, read `git log --oneline -20` and match the repository's subject style, scope names and size.

## 5. Prove it on the real surface

"It should work", "types check", "lint is clean" and "tests pass" are supporting signals, never the proof. Every scenario needs:

- **The tests of record** for the area, green.
- **A real-surface artifact** — what the user would actually see:

| If the change touches... | Prove it by... |
|---|---|
| A CLI command or script | Running it; capture the output and exit code |
| An API | Calling the endpoint; capture status and body |
| A web UI | Driving the real page (e.g. playwright-cli); capture a screenshot and the assertions |
| A TUI or terminal layout | Driving it in a multiplexer (e.g. herdr or tmux); capture the rendered screen |
| Build output or packaging | Building it and inspecting the produced files |
| Config handling | Loading the real config and showing the parsed result |
| A hook, plugin, or integration | Triggering it end-to-end and showing it fired |

Name the exact invocation for every scenario. "Open the page and check" is not a check.

Anything you start for QA — servers, ports, browser contexts, temp dirs, multiplexer sessions — gets a teardown todo the moment it is created. A leftover process is unfinished work.

## 6. Doubt your own "done"

Before reporting completion, assume the claim is wrong and look for where:

1. Re-read the user's original request, word by word. Compare it with what exists now — anything missing? anything added that wasn't asked for?
2. For each scenario: is there a recorded PASS with its artifact, from *after* the last code change?
3. For each todo marked done: re-examine it skeptically. Was it actually finished, or just started and moved past?
4. Any test deleted, skipped, or loosened? Any `TODO`, stub, mock data, or placeholder left in shipped code?
5. Any QA resource still running?

Anything that fails goes back on the todo list. Only an all-clear pass ends the run.

## 7. Gate review when the stakes justify it

Get one independent review before declaring done when any of these hold: the user asked for rigour; three or more files changed; the run was long; or the work is a refactor, migration, performance, auth, security, or data change.

- Use **one** reviewer — a fresh subagent where available, otherwise a deliberate adversarial pass of your own using **adversarial-review**. A panel produces noise; one accountable gate produces a verdict.
- Give it the goal, the scenarios, the evidence, the diff, and the notepad path. Ask it to check the delivered behaviour against the contract, look for missed context (callers, sibling code, docs, config that reference the change), and flag quality or security problems.
- Verify each concern yourself. A concern **blocks** only when it shows a scenario or requirement is not actually met; anything else is a note you fix or decline with a one-line reason.
- Fix blockers, re-run only the affected checks, and resubmit just the delta. At most two resubmissions; if blockers remain after that, stop and put them in front of the user rather than looping.

## When you hit a wall

Don't give up and don't quietly deliver less. In order: try a different approach; take a step back and get a second opinion (a fresh subagent, or **simplicity-architect** for a design knot); then ask the user one specific question that names what you tried and what decision you need. If a cut really is unavoidable, propose it explicitly and wait.

## Report

Keep it short and evidential:

```
Done: <goal, one line>
Changed: <files or components, one line each>
Evidence:
  S1 <scenario> — PASS — <command/artifact>
  S2 ...
Decisions I made: <reversible choices worth knowing, or "none">
Not done / needs you: <anything outstanding, or "nothing">
```

## Anti-patterns

- Starting to edit before you can name the files and explain the current behaviour
- Asking the user something the codebase could have answered
- Declaring done on "tests pass" or "types check" with no real-surface run
- Editing, skipping or deleting a test to make the suite green
- Tests that restate the change and can't fail
- "Here's a simplified version" or "you can extend this later" without prior agreement
- Bonus refactors, abstractions or features nobody asked for
- Batching todo completion at the end instead of marking each as it's verified
- Leaving servers, ports, or temp files behind after QA
- Looping on reviewer feedback that doesn't cite an unmet requirement
