#!/usr/bin/env bash
set -euo pipefail

echo "=== Checking for cross-boundary value imports ==="
# Check if any provider value-imports NULL_SESSION_CONTEXT_SERVICE from services/
BAD_IMPORTS=$(grep -rn "import.*NULL_SESSION_CONTEXT_SERVICE.*from.*services/session" source/providers/ || true)
if [ -n "$BAD_IMPORTS" ]; then
  echo "FAIL: Found illegal cross-boundary imports:"
  echo "$BAD_IMPORTS"
  exit 1
fi
echo "PASS: No illegal cross-boundary value imports found in source/providers/"

echo "=== Running Typecheck ==="
./node_modules/.bin/tsc --noEmit

echo "=== Running Provider Tests ==="
NODE_ENV=test ./node_modules/.bin/vitest run --reporter=minimal \
  source/providers/openai.provider.test.ts \
  source/providers/codex.provider.test.ts \
  source/providers/openrouter.provider.test.ts \
  source/providers/openai-compatible.provider.test.ts

echo "ALL CHECKS PASSED"
