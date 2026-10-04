#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR=""

usage() {
  cat <<USAGE
Usage: $0 --benchmark-dir <path>
USAGE
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-dir) BENCH_DIR="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

if [ -z "$BENCH_DIR" ] || [ ! -d "$BENCH_DIR" ]; then
  echo "Error: Valid --benchmark-dir is required."
  exit 1
fi

CONTROL_DIR="$BENCH_DIR/control"
if [ ! -f "$CONTROL_DIR/meta.json" ]; then
  echo "Error: Missing control/meta.json in $BENCH_DIR"
  exit 1
fi
if [ ! -f "$CONTROL_DIR/task.json" ]; then
  echo "Error: Missing control/task.json in $BENCH_DIR (re-run prepare-benchmark.sh)"
  exit 1
fi

TASK_ID=$(python3 -c "import json; print(json.load(open('$CONTROL_DIR/meta.json'))['task_id'])")
CANDIDATES=$(python3 -c "import json; print(' '.join(json.load(open('$CONTROL_DIR/meta.json'))['candidates']))")
EVALUATOR_TEST_PATH=$(python3 -c "import json; print(json.load(open('$CONTROL_DIR/task.json')).get('evaluator_test_path') or '')")
RUN_TYPECHECK=$(python3 -c "import json; print('1' if json.load(open('$CONTROL_DIR/task.json')).get('typecheck') else '0')")

if [ -f "$CONTROL_DIR/evaluator.test.ts" ] && [ -z "$EVALUATOR_TEST_PATH" ]; then
  echo "Error: task.json for $TASK_ID has no evaluator_test_path but evaluator.test.ts exists."
  exit 1
fi

echo "=================================================="
echo " Running Evaluator for Task: $TASK_ID"
echo " Benchmark Directory:        $BENCH_DIR"
echo " Candidates:                 $CANDIDATES"
echo " Typecheck gate:             $([ "$RUN_TYPECHECK" = 1 ] && echo enabled || echo disabled)"
echo "=================================================="

for CANDIDATE in $CANDIDATES; do
  CANDIDATE_DIR="$BENCH_DIR/$CANDIDATE"
  echo ""
  echo ">>> Evaluating Candidate: $CANDIDATE..."

  if [ ! -d "$CANDIDATE_DIR" ]; then
    echo "Warning: Candidate directory not found: $CANDIDATE_DIR"
    continue
  fi

  OUT_FILE="$CONTROL_DIR/${CANDIDATE}.evaluator.txt"
  STATUS_FILE="$CONTROL_DIR/${CANDIDATE}.evaluator.status"
  : > "$OUT_FILE"
  EXIT_CODE=0

  # Stage 1a: global typecheck (skipped when the task's verify.sh runs its own)
  if [ "$RUN_TYPECHECK" = "1" ]; then
    echo "=== Typecheck (tsc --noEmit) ===" >> "$OUT_FILE"
    (
      cd "$CANDIDATE_DIR"
      ./node_modules/.bin/tsc --noEmit
    ) >> "$OUT_FILE" 2>&1 && EXIT_CODE=0 || EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
      echo "TYPECHECK FAILED (exit $EXIT_CODE) - skipping test stage" >> "$OUT_FILE"
    fi
  fi

  if [ $EXIT_CODE -eq 0 ]; then
    # Case 1: Custom verify.sh script
    if [ -f "$CONTROL_DIR/verify.sh" ]; then
      echo "=== verify.sh ===" >> "$OUT_FILE"
      (
        cd "$CANDIDATE_DIR"
        bash "$CONTROL_DIR/verify.sh"
      ) >> "$OUT_FILE" 2>&1 && EXIT_CODE=0 || EXIT_CODE=$?

    # Case 2: Vitest evaluator test
    elif [ -f "$CONTROL_DIR/evaluator.test.ts" ]; then
      TARGET_TEST_PATH="$CANDIDATE_DIR/$EVALUATOR_TEST_PATH"
      if [ ! -d "$(dirname "$TARGET_TEST_PATH")" ]; then
        echo "Error: evaluator_test_path directory missing in candidate: $EVALUATOR_TEST_PATH"
        exit 1
      fi
      cp "$CONTROL_DIR/evaluator.test.ts" "$TARGET_TEST_PATH"

      echo "=== Hidden evaluator test ($EVALUATOR_TEST_PATH) ===" >> "$OUT_FILE"
      (
        cd "$CANDIDATE_DIR"
        NODE_ENV=test ./node_modules/.bin/vitest run "$EVALUATOR_TEST_PATH" --reporter=verbose
      ) >> "$OUT_FILE" 2>&1 && EXIT_CODE=0 || EXIT_CODE=$?

      # Clean up injected test so it never appears in the candidate diff
      rm -f "$TARGET_TEST_PATH"

    else
      echo "Error: No evaluator.test.ts or verify.sh found in control/"
      exit 1
    fi
  fi

  if [ $EXIT_CODE -eq 0 ]; then
    echo "RESULT: PASS"
    echo "PASS" > "$STATUS_FILE"
  else
    echo "RESULT: FAIL (exit code $EXIT_CODE)"
    echo "FAIL" > "$STATUS_FILE"
  fi
  tail -n 15 "$OUT_FILE"
done

echo ""
echo "Evaluation complete. Statuses saved to $CONTROL_DIR/*.evaluator.status"
