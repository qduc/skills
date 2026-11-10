# 2026-11-04: An eight-lane team was out-produced by one agent with a goal file

## Summary

A large rewrite (term2) ran for twelve days as a supervised team: a dispatch
coordinator, builders, verifiers and a supervisor in panes, coordinated through a
shared inbox and a job queue, as supervise-panes describes. On its last day the
team's open backlog was growing and the owner was sending hundreds of messages a
day. The owner paused the team and gave one agent a single goal file. That agent,
spawning its own subagents, produced more in twelve hours than the team had in
thirty-two, with no owner input. The skill had no step that asked whether the
work needed a team at all.

## Impact

Measured from git, the job queue and the inbox unless marked.

| | Team, last ~32 h | One agent, first ~12 h |
|---|---|---|
| Commits on the candidate | 125 | 96 in the first ~8 h, 183 by the second candidate |
| P1/P2 jobs | 78 opened, 47 closed | not tracked as jobs |
| Inbox posts | 1,232 in 24 h | 36 in total |
| Idle nudges from the loop | 210 in 24 h | none |
| Coordinator context handoffs | 7 in 24 h | 2 compactions in ~27 h |
| Owner messages | hundreds of turns a day (transcript count, includes relayed text) | zero for 12 h |

The oldest P1 jobs had been open 17–22 hours with nothing landed. One of them
was the parity harness the team's own acceptance gate depended on.

The comparison is not clean. The single agent inherited the team's architecture
and lessons, had the machine to itself, and ran on a stable harness while the
team's lanes ran on the build under test. Two providers were at or near quota on
the team's last day.

## Timeline (UTC)

- **10-23 → 11-03:** team phase. A retrospective on 11-03 adds "lessons from
  running a large team" to supervise-panes (a99e92b).
- **11-04 12:23:** the owner asks for an audit of the last 24 hours.
- **11-04 12:41:** one agent is given the goal file. The team is paused at 12:45.
- **11-04 13:36:** its first fixes land for a P1 the team had open ~20 hours.
- **11-04 20:48:** first candidate passes the gate as it then stood.
- **11-04 23:16:** the agent finds that every CI lane had been testing the old
  CLI by default, and fixes it. The first real run on the new CLI fails 91 tests.
- **11-05 00:38:** the owner pauses the agent, tries the build, relaxes the
  parity rule.
- **11-05 15:25:** the owner ships it.

## Root cause

- **The skill assumed the team.** It says "choose the smallest effective
  ownership structure", but only once you are already supervising panes. Nothing
  at entry compared a team with one agent holding the whole goal.
- **Every question crossed a layer.** A builder's question went to the inbox,
  then the coordinator, often the owner. Under one agent a subagent asked and
  got a ruling in minutes.
- **The loop optimised busyness.** Nudges, a stocked queue and "next job in the
  same turn" kept lanes active while the backlog grew. Nothing reported that the
  team as a whole was losing ground.
- **Lanes ran on the build they were changing.** Its bugs (compaction loops,
  exits to the shell) took lanes down at least five times in the last day.
- **Written lessons did not hold.** "Confirm which binary launched" and "test on
  a realistic store" were in the 11-03 lessons. Both failed again within two
  days and stopped only when a default changed.

## What went well

- The owner noticed the stall and changed the shape in one step, without adding
  process.
- The goal file worked as the only instruction: a goal, where things stand,
  hard rules, and what to report.
- One owner per area worked once the owners were subagents under one head.
- The load rule, the closed accepted-differences list and the durable task
  records all carried over and were useful to the single agent.

## Lessons for skill authors

- **Put the "do you need this skill?" check at the top of an orchestration
  skill.** A good principle in the body is read after the shape is chosen.
  (supervise-panes, delegate)
- **A skill that keeps workers busy needs a signal for when the whole is
  failing.** Backlog growth and nudges per landed commit were available and
  unused. (supervise-panes)
- **A lesson in a skill is weak; a default is strong.** When a lesson recurs,
  change a command, a template or a hook, not the wording. (all)
- **Don't state a rule without its cost.** "The old system decides, bugs
  included" was followed faithfully into copying bugs until the owner asked.
  (parity-rewrite, supervise-panes)
- **Don't put audit estimates in a skill as measurements.** The audit behind
  this change reported idle hours that were nudge counts times a guess. Say
  which numbers were counted. (all)
- **One comparison is one comparison.** Make the cheaper shape the default and
  keep the other, with its entry conditions, instead of deleting it. (all)

## Resolution and follow-ups

- supervise-panes gained "First: does this need a team?", four revised lessons,
  three new ones and a collapse signal; the "keep the queue stocked" lesson was
  removed. The control-plane loop reference points at the collapse signal.
- coordinator-setup gained a goal-file template and says a workspace is only for
  a standing coordinator.
- Open: the collapse signal is advice, not something `supervise.py` reports.
  Add it to the loop only if a team is run again and the advice is missed.
- Open: token and quota cost of the two shapes was not compared.
