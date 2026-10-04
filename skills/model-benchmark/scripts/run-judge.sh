#!/usr/bin/env bash
# Blind-judge a prepared benchmark run, several independent samples deep.
#
# Labels are re-shuffled between samples, so a candidate that happens to land
# in a favourable slot once does not keep that slot. One judge sample is a
# single opinion; three make the spread visible.
set -euo pipefail

BENCH_DIR=""
SAMPLES=3
JUDGE_MODEL="opus"
HUMAN_COMMIT=""
REPO_DIR="${TERM2_REPO_DIR:-$PWD}"
SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<USAGE
Usage: $0 --benchmark-dir <path> [--samples N] [--judge-model M] [--include-human <commit>]
USAGE
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-dir) BENCH_DIR="$2"; shift 2 ;;
    --samples) SAMPLES="$2"; shift 2 ;;
    --judge-model) JUDGE_MODEL="$2"; shift 2 ;;
    --include-human) HUMAN_COMMIT="$2"; shift 2 ;;
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

[ -n "$BENCH_DIR" ] && [ -d "$BENCH_DIR" ] || { echo "Error: --benchmark-dir required"; exit 1; }
CONTROL_DIR="$BENCH_DIR/control"

for i in $(seq 1 "$SAMPLES"); do
  echo ">>> Judge sample $i/$SAMPLES"
  "$SKILL_ROOT/scripts/anonymize-diffs.sh" --benchmark-dir "$BENCH_DIR" \
    --repo-dir "$REPO_DIR" ${HUMAN_COMMIT:+--include-human "$HUMAN_COMMIT"} >/dev/null
  cp "$CONTROL_DIR/mapping.json" "$CONTROL_DIR/mapping-$i.json"

  # The judge reads diffs from disk rather than being handed them inline, so a
  # large diff cannot silently truncate the prompt.
  ( cd "$CONTROL_DIR" && claude --print --model "$JUDGE_MODEL" \
      --dangerously-skip-permissions --allowed-tools Read,Glob,Grep \
      < claude-judge-prompt.txt ) > "$CONTROL_DIR/judge-$i.txt" 2>"$CONTROL_DIR/judge-$i.err" \
    || echo "    (judge sample $i exited non-zero; see judge-$i.err)"
  echo "    wrote judge-$i.txt ($(wc -c < "$CONTROL_DIR/judge-$i.txt") bytes)"
done

python3 "$SKILL_ROOT/scripts/aggregate-judge.py" --benchmark-dir "$BENCH_DIR"
