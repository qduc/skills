---
name: ultrawork
description: Carry one implementation task to verified completion without the user having to step back in — fix a checkable contract before editing, treat existing tests as the record of intended behavior, prove the result on the real surface, and doubt your own "done". Use when the user says "ulw" or "ultrawork", asks to finish something properly or thoroughly, or hands off an implementation they expect back finished. Use ulw-plan when they want a plan before code, and coordinator when the work splits into lanes for workers or must survive across sessions. Not for questions or one-line edits.
---

# Ultrawork

When the user has to take the wheel back — to finish half-done code, restate a
requirement, or discover that the "working" feature doesn't work — the run has
failed. This skill is the discipline for a single agent doing one piece of work
so that doesn't happen: know what done looks like before starting, prove each
step, and don't report success you haven't observed.

Deliver the outcome that was asked for: not a reduced version, and not a larger
one. If finishing honestly requires cutting something, say so before
delivering less. If you notice worthwhile work beyond the request, report it as
an optional proposal instead of doing it.

## 1. Understand before editing

Restate the outcome as something that will be observably true when you are
finished. Then close the gap between that statement and what you actually know.
Look up anything the system can tell you — current behavior, existing patterns,
what a library supports — instead of asking. Ask only about decisions that
belong to the user: irreversible or destructive actions, public interfaces,
data shape, new dependencies, spend. For reversible internal choices, pick the
simplest option consistent with the existing code and mention it if it matters.

You are ready to edit when you can name the files you will change, explain how
the code behaves today, and describe your plan without "probably". Until then,
keep investigating.

If the outcome is still fuzzy after investigation, or the change involves
several real design decisions, stop and use ulw-plan. If the work splits into
independent lanes, or will span sessions, hand it to coordinator and keep this
skill's evidence standard as its acceptance bar.

## 2. Fix the contract

Before the first edit, write the contract into the todo list or working notes:

- **Goal:** one sentence describing a state, not an activity.
- **Scenarios:** the cases that prove the goal. Always include the ordinary
  path. Add an edge case when the change is risky, and a check that a
  neighbouring caller or feature still works when more than one surface is
  touched. Size this to the change; a small fix needs one or two.
- **For each scenario:** a pass condition that can plainly fail ("exits 0 and
  prints the new column", not "works") and the exact command, request, or
  browser action that checks it.

The scenarios define done. Keep each todo tied to one of them and to how it
will be verified, and mark it complete only when that check has passed.

## 3. Work in proven steps

Read the tests that cover an area before changing it. They are the record of
intended behavior; note whether they express the intent and pass today. A test
that looks wrong is a finding to report, not something to edit until it goes
green. Never delete, skip, or loosen a test to get a clean run.

For a bug, reproduce the failure before fixing it. For a refactor, confirm the
existing tests pass on the unchanged code first. Then make the smallest change
that satisfies the scenario, in the style the codebase already uses, and update
any tests your change makes stale.

Add a new test only when the repository keeps tests for this kind of behavior
and a regression would otherwise go unnoticed. It has to be able to fail. A
test that restates the change — asserts a constant, a string, a rename, or that
a function was called — proves nothing. Prose, prompt, documentation and purely
visual changes get review and a real-surface check, not a test pinning their
wording.

If commits are wanted, commit each verified increment, matching the subject
style and size in `git log`.

## 4. Prove it on the real surface

Passing tests, clean types and a green linter support a claim; they do not
establish it. Each scenario needs the relevant tests green *and* an observation
of what the user will actually experience: run the command and read its output,
call the endpoint and inspect the response, drive the page or terminal
(playwright-cli, herdr, or tmux) and capture what renders, build the package and
look inside it, load the real config and print what was parsed. Name the exact
invocation. "Open the page and check" is not a check.

Confirm the tests you cite actually exist and ran; a selector that matched
nothing proves nothing. Anything started for verification — servers, ports,
browser sessions, temp directories — is torn down before you finish.

## 5. Doubt your own "done"

Before reporting, assume your completion claim is wrong and look for where:

- Read the original request again and compare it with what now exists. Is
  anything missing, or anything present that wasn't asked for?
- Does every scenario have a passing observation made after the last change?
- Revisit each completed todo. Was it finished, or started and moved past?
- Is anything left behind: a stub, mock data, a `TODO`, a skipped test, a
  running process?

Anything that fails goes back on the list. You are done when this pass finds
nothing.

## 6. Independent review when stakes justify it

When the change is consequential — security, data, auth, migrations, broad
refactors, or the user asked for rigor — get one independent review before
reporting. Use a fresh subagent if available; otherwise run adversarial-review
yourself as a separate pass. Give the reviewer the goal, scenarios, evidence and
diff, and let it form its own assessment before it reads your reasoning.

A finding blocks only when it shows a scenario or requirement is not actually
met. Fix blockers and re-check what they touched. Treat other findings as notes
you address or decline with a reason. If the same blocker survives repeated
fixes, change approach or bring it to the user rather than looping.

## When stuck

Try a different approach before giving up on one. Get a second opinion — a
fresh subagent, or simplicity-architect when the knot is in the design. If you
still need the user, ask one specific question that says what you tried and
what you need them to decide. Don't deliver a quietly reduced result.

## Report

```
Done: <goal>
Changed: <files or components>
Evidence:
  <scenario> — pass — <command and what it showed>
Decisions: <material choices made on the user's behalf, or none>
Proposals: <worthwhile work beyond the request, not done, or none>
Open: <anything unfinished or needing the user, or nothing>
```
