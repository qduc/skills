# Compact working state

Use the host's task record or an existing project checkpoint when suitable.
Keep simple tasks in context. Persist a compact checkpoint for long work,
interruptions, or handoffs using the host's authorized storage workflow.
Do not create a second project tracking system or record private chain of thought.
Store concise decisions, observations, and evidence pointers instead.

Use this shape as needed; omit empty fields:

```yaml
goal: observable delegated outcome
constraints: []
authority: {granted: [], reserved: []}
status: ACTIVE
phase: PLAN
criteria:
  - id: C1
    requirement: observable acceptance condition
    verdict: UNCERTAIN
    evidence: []
plan: []
facts: []
assumptions: []
actions: []
failures: []
questions: []
skills: []
risks: []
budget: {}
next_step: smallest useful action
blocker: null
```

For evidence, retain the observed result, source or artifact location, relevant
version/environment/time when needed, criterion supported, and limitations.
For actions, retain the important change and any pending external effects.
For failures, retain the attempted approach and what was learned so a resumed
agent does not repeat it blindly. For skills, retain names/locations, purpose,
and provisional status when applicable.

Update at material changes: revised contract or plan, decisive observations,
failed approaches, changed skill selection, blockers, and handoffs. Avoid writing
a transcript after every tool call. Keep stable knowledge separate from transient
task state; preserve pointers to large logs instead of copying them into the record.

Never store credentials or unnecessary personal data. Do not treat a stored
assumption as a fact after resumption. Recheck evidence only when its dependencies
could have changed, and preserve unaffected evidence.
