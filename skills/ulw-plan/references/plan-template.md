# Plan template

Keep these headings in this order. The TL;DR comes first so a human can read the top and stop; write it last.

```markdown
# <slug> — Work Plan

## TL;DR
- **You'll get:** <the outcome, 1–2 sentences>
- **Approach:** <the chosen approach and why, 1–2 sentences>
- **Won't do:** <the main exclusions>
- **Effort:** Quick | Short | Medium | Large | XL
- **Risk:** <the main risk and its mitigation>
- **Decisions I made for you:** <reversible defaults, each with a one-line reason — or "none">

## Scope
### Affected user and ideal state
<who, how they use it today and after>
- IS-1: <property> — <why>
- GAP-1: <difference from today> — <why>
### Must have
### Must NOT have
<explicit exclusions: guardrails against additions nobody asked for, never a reduction of the request>

## Verification strategy
<test approach (test-first / tests-after / none), the test commands of record, and the real surfaces each scenario is checked on>

## Execution strategy
<waves; what runs in parallel inside each wave; the dependencies between waves>

## Tasks
- [ ] 1. <title>
  - **Where:** <exact files, and "every X in Y" when it's a sweep>
  - **Follow:** <existing pattern to copy, with path:line>
  - **Do:** <the change, with no judgment calls left>
  - **Don't:** <what this task must not touch>
  - **Accept when:** <binary, agent-checkable conditions>
  - **Check (happy):** <exact command/action> → <expected observable>
  - **Check (failure):** <exact command/action> → <expected observable>
  - **Closes:** GAP-n
  - **Difficulty:** small | medium | hard — <one-line reason>
  - **Commit:** <message in the repository's style>

## Final verification
- [ ] F1. Plan compliance — every task done as written, nothing extra
- [ ] F2. Code quality — the diff reviewed against repo conventions
- [ ] F3. Real-surface QA — every check re-run after the last change
- [ ] F4. Ideal-state fidelity — delivered behaviour checked against each IS row; any shortfall becomes a new task, not a note

## Success criteria
| IS row | Delivered by | Proven by | Evidence |
|---|---|---|---|
| IS-1 | 1, 3 | <check> | <where the artifact will be> |
```

## Sizing guidance

- **Effort bands**, never hours or days: Quick (a single edit), Short (one focused change across a few files), Medium (a multi-file feature in one session), Large (several waves), XL (multi-session or architectural).
- Implementation and its test are one task, not two.
- Aim for 3–8 tasks per wave. Split work into small, independently checkable tasks when you can — but keep a single hard task whole when splitting would separate the parts of one piece of reasoning.
- Difficulty tells the executor how capable a worker the task needs: *small* is mechanical or single-file, *medium* is a standard multi-file change, *hard* is where the key decision can't be read off the evidence (a trade-off, a cross-module contract, correctness argued from invariants).
