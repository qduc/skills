#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR=""
SHUFFLE=1
INCLUDE_HUMAN=""
REPO_DIR="${TERM2_REPO_DIR:-$PWD}"

usage() {
  cat <<USAGE
Usage: $0 --benchmark-dir <path> [--no-shuffle]

  --no-shuffle   Assign labels in candidate order (default: randomized to
                 remove positional bias in the blind judge step)
  --include-human <commit>
                 Add the real merged commit as one more anonymized candidate,
                 so the human fix is scored blind on the same rubric. Without
                 it the judge has no calibrated point on the scale and cannot
                 answer whether any model beat the original.
  --repo-dir <p> Repo to read --include-human from (default: $TERM2_REPO_DIR)
USAGE
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-dir) BENCH_DIR="$2"; shift 2 ;;
    --no-shuffle) SHUFFLE=0; shift ;;
    --include-human) INCLUDE_HUMAN="$2"; shift 2 ;;
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

if [ -z "$BENCH_DIR" ] || [ ! -d "$BENCH_DIR" ]; then
  echo "Error: Valid --benchmark-dir is required."
  exit 1
fi

CONTROL_DIR="$BENCH_DIR/control"
REF_DIR="$BENCH_DIR/reference"

if [ ! -f "$CONTROL_DIR/meta.json" ]; then
  echo "Error: Missing control/meta.json in $BENCH_DIR"
  exit 1
fi

CANDIDATES=$(python3 -c "import json; print(' '.join(json.load(open('$CONTROL_DIR/meta.json'))['candidates']))")

echo "=================================================="
echo " Extracting & Anonymizing Diffs"
echo "=================================================="

# Remove stale labeled diffs from any earlier run so the judge never sees
# a candidate that no longer exists.
rm -f "$CONTROL_DIR"/candidate-*.diff

read -ra CANDIDATE_ARRAY <<< "$CANDIDATES"

# The human fix enters the pool as just another unlabeled candidate.
if [ -n "$INCLUDE_HUMAN" ]; then
  git -C "$REPO_DIR" show --format= --no-color "$INCLUDE_HUMAN" > "$CONTROL_DIR/human.diff"
  CANDIDATE_ARRAY+=("human")
fi

# Generate as many labels as there are candidates: A..Z, then AA, AB, ...
mapfile -t LABELS < <(python3 -c "
import sys, string
n = int(sys.argv[1])
letters = string.ascii_uppercase
out, i = [], 0
while len(out) < n:
    q, r = divmod(i, 26)
    out.append((letters[q-1] if q else '') + letters[r])
    i += 1
print('\n'.join(out))
" "${#CANDIDATE_ARRAY[@]}")

ORDER=("${CANDIDATE_ARRAY[@]}")
if [ "$SHUFFLE" = "1" ] && [ "${#ORDER[@]}" -gt 1 ]; then
  mapfile -t ORDER < <(printf '%s\n' "${CANDIDATE_ARRAY[@]}" | shuf)
fi

MAPPING_ARGS=()
INDEX=0
for CANDIDATE in "${ORDER[@]}"; do
  LABEL="${LABELS[$INDEX]}"
  CANDIDATE_DIR="$BENCH_DIR/$CANDIDATE"
  DIFF_FILE="$CONTROL_DIR/candidate-${LABEL}.diff"
  NAMED_DIFF="$CONTROL_DIR/${CANDIDATE}.diff"

  echo "Diffing candidate: $CANDIDATE -> candidate-$LABEL"

  if [ "$CANDIDATE" = "human" ]; then
    cp "$CONTROL_DIR/human.diff" "$DIFF_FILE"
    # The human diff is the origin commit: its evaluator is green by
    # construction (the hidden tests are that commit's own). Without status
    # files the pooled judge reads UNKNOWN evidence and demotes the one
    # calibrated point on its scale.
    printf 'PASS' > "$CONTROL_DIR/human.evaluator.status"
    printf 'OK' > "$CONTROL_DIR/human.run.status"
    MAPPING_ARGS+=("candidate-${LABEL}=human")
    INDEX=$((INDEX + 1))
    continue
  fi

  # Produce clean diff against reference baseline, with unified-diff a/ b/
  # prefixes so downstream parsers see standard headers.
  diff -ruN \
    --exclude="node_modules" \
    --exclude=".git" \
    --exclude="BENCH-TASK.md" \
    --exclude="*.log" \
    --exclude="*.tsbuildinfo" \
    --exclude=".term2" --exclude=".codex" --exclude=".claude" \
    --exclude=".opencode" --exclude=".pi" --exclude=".cache" \
    --exclude="dist" --exclude="dist.bak" --exclude="coverage" \
    --exclude="*.evaluator.test.ts" \
    "$REF_DIR" "$CANDIDATE_DIR" \
    | sed "s|^\(--- \)$REF_DIR/|\1a/|; s|^\(+++ \)$CANDIDATE_DIR/|\1b/|; s|^\(--- \)$REF_DIR\b|\1a|; s|^\(+++ \)$CANDIDATE_DIR\b|\1b|; s|^\(diff -ruN.*\)$REF_DIR/|\1a/|; s|$CANDIDATE_DIR/|b/|g; s|$REF_DIR/|a/|g" \
    > "$DIFF_FILE" || true

  cp "$DIFF_FILE" "$NAMED_DIFF"

  MAPPING_ARGS+=("candidate-${LABEL}=${CANDIDATE}")
  INDEX=$((INDEX + 1))
done

python3 - "$CONTROL_DIR/mapping.json" "${MAPPING_ARGS[@]}" <<'PY'
import json, sys
out, *pairs = sys.argv[1:]
json.dump(dict(p.split("=", 1) for p in pairs), open(out, "w"), indent=2)
PY

# Generate Judge Prompt
PROMPT_FILE="$CONTROL_DIR/claude-judge-prompt.txt"
TASK_PROMPT=$(cat "$CONTROL_DIR/prompt.txt")

cat <<JUDGE_PROMPT > "$PROMPT_FILE"
Review candidate diffs as anonymized solutions to this task:

<TASK_PROMPT>
$TASK_PROMPT
</TASK_PROMPT>

Candidate diff files in current directory:
$(ls -1 "$CONTROL_DIR"/candidate-*.diff 2>/dev/null | xargs -n1 basename)

Diffs are presented in randomized order; position carries no information.
Do not inspect other directories or attempt to identify harnesses/models.

Score each candidate out of 10 using this weighted rubric:
1. Functional Correctness (4 pts): Does the diff completely and cleanly solve
   the prompt without edge-case regressions?
2. Scope Discipline (2 pts): Are modifications strictly bounded to the problem
   statement, with zero unnecessary churn?
3. Backward/Forward Compatibility (2 pts): Are wire/schema formats, events,
   types, and legacy payload handling preserved?
4. Test Quality & Coverage (2 pts): Are regression tests thorough and placed at
   the appropriate public boundary?

For each candidate:
- Provide a summary of changes.
- Provide itemized strengths and weaknesses.

Finally:
- Provide an overall ranking (e.g. Candidate A > Candidate B).
- Explicitly state if there is a tie.

End your reply with a single fenced JSON block, and nothing after it. Report
only per-dimension points; the aggregator computes totals and ranks from the
ranking you state, so do not include a "total" key or any other extra keys:

\`\`\`json
{"scores": {"candidate-A": {"correctness": 0, "scope": 0, "compatibility": 0, "tests": 0}}, "ranking": ["candidate-A"]}
\`\`\`

Include every candidate in "scores" and every candidate in "ranking", best first.
JUDGE_PROMPT

echo ""
echo "Anonymized diffs created in $CONTROL_DIR:"
ls -lh "$CONTROL_DIR"/candidate-*.diff
echo ""
echo "Judge prompt generated at: $PROMPT_FILE"
echo "Mapping saved securely to: $CONTROL_DIR/mapping.json"
