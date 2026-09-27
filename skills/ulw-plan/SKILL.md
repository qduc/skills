---
name: ulw-plan
description: Turn a large or fuzzy request into one decision-complete plan that someone without this conversation can execute — explore before asking, bring the user only the decisions that are theirs, get approval, then write a plan whose goal, criteria, assumptions, contracts and work items coordinator or ultrawork can take as-is. Use when the user says "ulw-plan", asks for a plan before any code, says "plan this out" or "interview me", or when a task is too big or vague to start safely. Plans only; never implements.
---

# ULW Plan

Produce one plan complete enough that whoever executes it — another session,
coordinator's workers, or ultrawork — has no judgment calls left that belong to
the user. Read, search, and run read-only analysis; write only the draft and the
plan. Don't edit product code or start implementation, directly or through a
subagent, even when the work looks small. While this skill is active, "do X"
means "plan X". Approval of the brief authorizes writing the plan, not
executing it.

Explore a lot, ask little, and stop when the plan is done. Scale the effort to
the request: an obvious single-file change gets a short plan after a confirmation
or two; system design gets deep exploration and an independent check of the
plan.

## 1. Explore before asking

Investigate the code the change touches, the patterns and conventions it should
follow, the test setup, and — when the repository can't answer — external docs
or contracts. Run independent read-only investigations in parallel where the
harness allows. Treat what a scout reports as a claim until you have looked at
the evidence yourself. Stop investigating a question once the evidence answers
it.

Then describe who the result is for — end users, other programmers, a program
or agent that consumes it — how they deal with this area today, and what a good
result looks like for them. Use this to judge decisions and to write acceptance
criteria. It will sometimes show gaps beyond the literal request. Put those in
front of the user as proposals at the approval gate; plan them only if the user
takes them. Don't silently widen the scope, and don't silently shrink it into a
"first phase" nobody asked for.

## 2. Decide what to ask

First judge whether the desired *outcome* is clear — not whether the request is
long — and tell the user your read in one line.

- **Clear outcome:** the user knows what they want and only preferences remain.
  Ask the questions that survive the filter below.
- **Fuzzy outcome** ("make auth better"): don't interrogate. Research further,
  choose defaults that serve the people affected, and present them as
  assumptions the user can overturn at the gate. Say that you read the request
  as open-ended, so a user with a specific outcome in mind can correct you.
- **Can't tell:** treat it as clear and ask one question.
- **The user asks to be interviewed:** ask every real fork instead of
  defaulting.

Filter each candidate question. If evidence can answer it, investigate instead.
If the goal plus a reasonable reversible default settles it, decide, and record
it as an assumption when being wrong would matter. Always ask about decisions
the user owns, even when you have a default: irreversible or destructive
actions, public interfaces and configuration, packaging, new external
dependencies, data or schema shape, spend, scale targets, and audience or
compliance limits. Budget, mandated technology, scale and audience leave no
trace in the code, so raise them explicitly when they could change the plan.

When you ask, say what you investigated, why it didn't settle the question, and
what in the plan depends on the answer. Keep questions few and narrow, offer
concrete options with your recommendation first, and treat a skipped question as
accepting the recommendation. Confirm how the work will be tested.

## 3. Check for gaps

Before the brief, look at the request through the lens that fits it:

| Kind of work | Pin down |
|---|---|
| Refactor | The behavior that must be preserved, the commands that prove it, and verification after each step rather than only at the end |
| New feature | The existing pattern to follow, with a path, and what will explicitly not be built |
| Scoped change | The exact deliverables, the boundaries, and how done is observed |
| Architecture | Expected lifespan, scale, fixed constraints, and integrations — without designing for hypothetical futures |
| Investigation | The question, what ends the investigation, and what it produces |

Also look for work creeping in that nobody asked for: tests or cleanup beyond
the target, an abstraction without a second use, validation out of proportion to
the inputs, documentation no one requested. Each becomes a non-goal. For a
design-heavy plan, proportionality-review can check the direction before you
commit to it.

## 4. Approval gate

Keep a draft beside where the plan will go, recording your read of the intent,
decisions, assumptions, open questions, and that you are waiting for approval,
so a later session can resume without re-exploring.

Present the brief once: who is affected and what good looks like for them; the
key findings, with paths; the approach; decisions you made and why; decisions
that need the user, with your recommendation; and any proposals beyond the
request. Keep it short enough to read in a minute; supporting detail belongs in
the draft. Then treat the reply as a decision. Acceptance, or answers to the open
questions, authorizes writing the plan. A change of scope gets folded in and
the brief presented again. If the reply doesn't settle it, say in one line what
you still need.

## 5. Write the plan

Write it using [the plan format](references/plan-format.md), which uses the same
concepts coordinator records — goal, acceptance criteria, non-goals, authority,
decision defaults, assumptions, contracts, pending decisions, and work items
with dependencies — so it can be loaded directly. Store it outside the
repository by default, in `${XDG_STATE_HOME:-~/.local/state}/ulw-plan/<project>/<slug>.md`,
unless the user or the repository already has a place for plans. Tell the user
the path. Write the summary at the top last, so it describes the plan you
actually wrote.

Don't choose workers, harnesses or models; coordinator asks the user for those
at dispatch.

## 6. Check that it can be executed

Before handing over, check whether someone with no access to this conversation
could carry out the plan without getting stuck. Use a fresh reviewer when the
intent was fuzzy, the work is large, or the user asked for rigor; otherwise do
it yourself as a separate pass.

This check exists to unblock execution, not to perfect the plan, so it should
approve by default. It fails only on blockers: a referenced file or line that
doesn't exist or doesn't say what the plan claims; a work item with no starting
point; items that contradict each other; or a done condition nobody can check.
Style, missing minor edge cases, and approaches the reviewer would have chosen
differently are not blockers. Report only the blockers that matter, each
specific enough to fix. Fix them and recheck what changed. If the same blocker
keeps coming back, bring it to the user.

Also confirm that every acceptance criterion is covered by at least one work
item and one check.

## 7. Hand off

Summarize from the finished plan: what it achieves and for whom; how many
milestones and work items; anything added beyond the literal request and why;
how completion will be proven; and how to run it — coordinator for work with
independent lanes or that will span sessions, ultrawork for a single agent
working straight through. Then stop.
