# Incidents

Post-mortems of failures caused by the skills in this repository. Each one
records what happened, why, what changed, and lessons for anyone writing skills.

**Before creating or changing a skill,** scan the index below for incidents that
list that skill or touch the kind of rule you are adding (gates, checks, retained
state, delegation). Read the relevant post-mortem's lessons and make sure your
change doesn't repeat them.

These are for skill authors, not for agents running a skill. Don't copy them
into runtime workspaces or briefs. Fixes that came out of an incident live in the
skills themselves, and the post-mortem links to the commits.

## Writing one

Name the file `YYYY-MM-DD-short-slug.md` and add a row to the index below, listing the skills involved.
Keep it blameless and factual. Cover:

- **Summary:** what went wrong, in two or three sentences.
- **Impact:** time lost, work blocked, disk used.
- **Timeline:** in UTC, from durable records (commits, file times, reports)
  rather than recollection.
- **Root cause:** the mechanism, not just the symptom list.
- **What went well.**
- **Lessons for skill authors:** transferable, one line each, with the skills
  affected.
- **Resolution and follow-ups:** what changed, with commit links, and what is
  still open.

Say which numbers were measured and which come from an agent's summary.

## Index

| Date | Incident | Skills | Summary |
|---|---|---|---|
| 2026-10-25 | [Coordinator ceremony](2026-10-25-coordinator-ceremony.md) | supervise-panes, delegate, coordinator-setup | Accumulated verification gates turned small fixes into multi-hour pipelines; removing the rules and the state that carried them cleared five merges in about 30 minutes. Lessons: price every gate, let owners fix environment failures, clean derived state when removing rules. |
