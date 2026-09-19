# Task: Provider Boundary DI Violation (F-correctness-002)

## Problem Description
Multiple provider files directly value-import `NULL_SESSION_CONTEXT_SERVICE` from `../services/session/session-context-service.js`.
Per architectural invariants in `audit/invariants.md`, provider packages must never directly value-import concrete implementations from `services/` to maintain clean separation of concerns and avoid dependency cycles.

## Expected Solution
1. Remove `import { NULL_SESSION_CONTEXT_SERVICE }` value imports from provider files in `source/providers/`.
2. Define a typed local null object in each provider or import type-only `ISessionContextService`.
3. Preserve identical fallback behavior `sessionContextService ?? NULL_SESSION_CONTEXT_SERVICE`.

## Verification
- Run `verify.sh`
