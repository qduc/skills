# Tasks

| Task | Status | Record |
|---|---|---|

Each task gets `tasks/<slug>/README.md` with this shape:

```markdown
# <title>
Task ID: <runtime id>
Goal and authority: <one paragraph>
Outcome: <result, or "pending">
Evidence: <commit SHAs, test results, paths>
```

Live status and next actions belong in `STATUS.md` and the runtime task record;
the index column above is a coarse checkpoint, not live state.

Keep small evidence only. Raw runtime files stay in the runtime state directory.
