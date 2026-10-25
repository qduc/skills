# Tasks

| Task | Status | Record |
|---|---|---|

Each task gets `tasks/<slug>/README.md` with this shape:

```markdown
# <title>
Task ID: <runtime id>   Status: <active | blocked | complete | abandoned>
Goal and authority: <one paragraph>
Outcome: <result, or "pending">
Evidence: <report copies, hashes, commit SHAs, paths>
Next action: <exact step, or "none">
```

Keep curated reports and small evidence only. Raw runtime files stay in the
runtime state directory.
