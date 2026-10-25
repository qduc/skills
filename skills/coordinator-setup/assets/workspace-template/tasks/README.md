# Tasks

| Task | Status | Record |
|---|---|---|

Each task gets `tasks/<slug>/README.md` with this shape:

```markdown
# <title>
Task ID: <runtime id>
Goal and authority: <one paragraph>
Outcome: <result, or "pending">
Evidence: <report copies, hashes, commit SHAs, paths>
```

Live status and next actions belong in `STATUS.md` and the runtime task record;
the index column above is a coarse checkpoint, not live state.

Keep curated reports and small evidence only. Raw runtime files stay in the
runtime state directory.
