# Task: Approval Batch Denial Polarity (C11-D5)

## Problem Description
In `source/services/approval/tool-approval-batch-coordinator.ts`, when looping over sibling interruptions during batch staging, the coordinator checks:
```typescript
if (isToolApproved?.({ toolName, callId }) !== undefined) {
  pendingNow?.decisionsByCallId?.set(callId, 'approved');
  continue;
}
```
If `isToolApproved` returns `false` (meaning the tool was explicitly denied / rejected in the ledger or parent context), it still records `'approved'`.

## Expected Solution
Fix the polarity check so that:
- `true` maps to `'approved'`
- `false` maps to `'rejected'`
- `undefined` continues to subsequent evaluation

## Verification
- Deterministic Vitest test: `evaluator.test.ts`
- Vitest suite: `source/services/approval/*.test.ts`
