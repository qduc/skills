# Reporting Formats

## 1. Lens report format (every lens pass uses this)

File: `audit/reports/<lens>.md`

```markdown
# Lens report: <lens>
Codebase: <path>  |  Scope: <scope>  |  Date: <date>

## Summary
2–4 sentences. Overall assessment through this lens only.

## Findings

### F-<lens>-001: <one-line claim>
- **Severity**: critical | high | medium | low
- **Confidence**: high | medium | low
- **Location**: file:line (all relevant spots)
- **Claim**: One falsifiable sentence. ("X is unused because no import exists outside its own test", not "X seems unnecessary")
- **Evidence**: What in the code supports the claim. Quote sparingly; cite precisely.
- **Verify by**: Concrete check the synthesis pass can run to confirm/refute (a grep, a test to run, a trace to follow).
- **Invariant impact**: which entry in invariants.md this touches, or "none".

(repeat per finding; sequential IDs)

## Non-findings
Things this lens checked and found healthy. Prevents synthesis from assuming unchecked = unproblematic.

## Blocked
Anything this lens could not evaluate (missing access, needed a tool, out of scope) — so gaps are visible.
```

For the null-hypothesis pass, replace "Findings" with "Defenses" (same structure: D-null-001, the pattern being defended, the justification, and evidence) and add a required final section "## Concessions" listing what could not be defended.

## 2. Synthesis format

File: `audit/synthesis.md`

```markdown
# Synthesis report
Inputs: <list of lens reports>

## Verification ledger
Table: finding ID | status (verified / refuted / unverifiable) | re-check performed | evidence (file:line)
Every finding from every lens appears here. "Two lenses agreed" is not a verification.

## Contradictions resolved
For each conflict between lenses: the conflict, the code evidence consulted, the resolution.

## Null-hypothesis outcomes
Which findings the defense pass rebutted (downgraded/dropped, with the rebuttal), which survived it (upgraded: load-bearing).

## Root-cause groups  ⚠ HYPOTHESIS — requires human confirmation
### RC-1: <hypothesized root cause>
- Symptoms: F-arch-002, F-dup-004, ...
- Causal story: <explicitly labeled as hypothesis>
- Alternative explanation: <at least one>

## Dropped findings
Refuted or rebutted findings, with reasons — kept for transparency.
```

## 3. Repair plan format

File: `audit/repair-plan.md` — written ONLY after the human checkpoint.

```markdown
# Repair plan

## Priority order
Ranked by severity × confidence × blast-radius. Hot modules (most-changed in git) first within a tier.

### R-001: <fix title>  [addresses RC-1: F-..., F-...]
- **Change**: concrete, scoped to one reviewable PR-sized chunk
- **Risk**: what could break; which invariants to watch
- **Test impact**: assertions strengthened / added / changed — and why (never silently weakened)
- **Verify done by**: observable outcome
- **Depends on**: prior R-items, or none

## Explicitly deferred
Findings acknowledged but not scheduled, with reasons.

## Process rule
Each R-item is executed and human-reviewed before the next begins. No batch merges of unreviewed fixes.
```
