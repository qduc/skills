# Task: Durable Approval Grant Kind (C11-D8)

## Problem Description
In `source/services/conversation/conversation-adapter.ts`, handling an interactive approval decision via `handleApprovalDecision('y')` emits an `approval_resolved` durable log event. Currently, the event records only `{ type: 'approval_resolved', answer: 'y' }`, omitting the grant kind (`grantKind: 'interactive'`). When log readers deserialize historical sessions or when downstream services inspect continuation grants, they cannot distinguish between interactive grants and automated/batch grants.

## Expected Solution
1. Update `approval_resolved` payload types to include optional `grantKind?: 'interactive' | string`.
2. Ensure `ConversationAdapter.handleApprovalDecision` sets `grantKind: 'interactive'`.
3. Preserve backward compatibility when reading or deserializing logs lacking `grantKind`.
4. Add focused unit test verifying the event shape.

## Verification
- Deterministic Vitest test: `evaluator.test.ts`
- Typecheck: `pnpm typecheck`
