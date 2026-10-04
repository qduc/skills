#!/usr/bin/env bash
# Judge candidates from several benchmark runs of the SAME task as one pool.
#
# Cells added in a later grid must be scored against the earlier ones on one
# scale, not in a separate pass: a judge's 10-point scale is only comparable
# within a single prompt, so two runs produce two scales that cannot be
# joined afterwards. This collects pre-computed named diffs from any number of
# run directories, relabels them together, and samples the judge repeatedly.
set -euo pipefail
POOL_DIR=""; TASK_PROMPT=""; SAMPLES=3; JUDGE_MODEL="opus"
MAX_PROMPT_BYTES="${POOLED_JUDGE_MAX_PROMPT_BYTES:-500000}"
SRC_DIRS=()
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() { echo "Usage: $0 --pool-dir <path> --prompt <file> [--samples N] [--max-prompt-bytes N] <run-dir>..."; exit 1; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pool-dir) POOL_DIR="$2"; shift 2 ;;
    --prompt) TASK_PROMPT="$2"; shift 2 ;;
    --samples) SAMPLES="$2"; shift 2 ;;
    --judge-model) JUDGE_MODEL="$2"; shift 2 ;;
    --max-prompt-bytes) MAX_PROMPT_BYTES="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) SRC_DIRS+=("$1"); shift ;;
  esac
done
[ -n "$POOL_DIR" ] && [ -n "$TASK_PROMPT" ] && [ "${#SRC_DIRS[@]}" -gt 0 ] || usage

mkdir -p "$POOL_DIR"
python3 "$SCRIPT_DIR/prepare-pooled-judge.py" collect \
  --pool-dir "$POOL_DIR" "${SRC_DIRS[@]}"

UNIQUE_COUNT=$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["groups"]))' \
  "$POOL_DIR/pool-manifest.json")
if [ "$UNIQUE_COUNT" -gt 0 ]; then
  for i in $(seq 1 "$SAMPLES"); do
    python3 "$SCRIPT_DIR/prepare-pooled-judge.py" sample \
      --pool-dir "$POOL_DIR" --sample "$i" --prompt "$TASK_PROMPT" \
      --max-prompt-bytes "$MAX_PROMPT_BYTES"

    claude --print --model "$JUDGE_MODEL" --tools "" --disable-slash-commands \
        < "$POOL_DIR/judge-prompt.txt" \
        > "$POOL_DIR/judge-$i.txt" 2>"$POOL_DIR/judge-$i.err" \
      || echo "  (sample $i exited non-zero)"
    echo "  sample $i: $(wc -c < "$POOL_DIR/judge-$i.txt") bytes"
  done
else
  echo "no non-empty candidate diffs; skipped judge calls"
fi

python3 "$SCRIPT_DIR/aggregate-judge.py" --control-dir "$POOL_DIR"
