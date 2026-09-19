#!/usr/bin/env bash
set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="${TERM2_REPO_DIR:-$PWD}"
OUTPUT_ROOT="${BENCH_OUTPUT_DIR:-${SKILL_ROOT}/../../runtime}"
OUTPUT_DIR=""
TASK_ID="c11-d8-approval-grant-kind"
CANDIDATES="candidate-1,candidate-2"
NODE_MODULES_MODE="shallow"
HARNESS_REGISTRY="${SKILL_ROOT}/harnesses.json"

usage() {
  cat <<USAGE
Usage: $0 [options]
Options:
  --repo-dir <path>       Path to source term2 repository (default: \$TERM2_REPO_DIR or \$PWD)
  --output-dir <path>     Directory to create benchmark run (default: \$BENCH_OUTPUT_DIR/bench-<task>-<ts>)
  --task <task_id>        Task to benchmark (default: c11-d8-approval-grant-kind)
  --candidates <specs>    Comma-separated candidate specs. Each is either
                          <harness>:<provider>/<model>[=<alias>] for a runnable
                          candidate, or a bare name for one you drive by hand.
                          Hold the model constant to compare harnesses:
                            --candidates "codex:openai/gpt-5.4,term2:openai/gpt-5.4"
                          Hold the harness constant to compare models:
                            --candidates "codex:openai/gpt-5.4,codex:openai/gpt-5.3"
  --harnesses <file>      Harness registry (default: <skill>/harnesses.json)
  --node-modules <mode>   shallow (default) | symlink | copy
                          shallow: per-candidate node_modules dir of symlinks to each
                                   top-level package, so writes stay candidate-local
                          symlink: single shared symlink (fast, NOT hermetic)
                          copy:    full copy per candidate (slowest, fully hermetic)
  -h, --help              Show this help
USAGE
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --task) TASK_ID="$2"; shift 2 ;;
    --candidates) CANDIDATES="$2"; shift 2 ;;
    --harnesses) HARNESS_REGISTRY="$2"; shift 2 ;;
    --node-modules) NODE_MODULES_MODE="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

case "$NODE_MODULES_MODE" in
  shallow|symlink|copy) ;;
  *) echo "Error: --node-modules must be shallow, symlink, or copy"; exit 1 ;;
esac

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "Error: --repo-dir '$REPO_DIR' is not a git repository."
  echo "Pass --repo-dir or set TERM2_REPO_DIR."
  exit 1
fi
REPO_DIR="$(cd "$REPO_DIR" && pwd)"

if [ -z "$OUTPUT_DIR" ]; then
  mkdir -p "$OUTPUT_ROOT"
  OUTPUT_ROOT="$(cd "$OUTPUT_ROOT" && pwd)"
  OUTPUT_DIR="${OUTPUT_ROOT}/bench-${TASK_ID}-$(date +%Y%m%d-%H%M%S)"
fi

TASK_DIR="${SKILL_ROOT}/tasks/${TASK_ID}"
if [ ! -d "$TASK_DIR" ]; then
  echo "Error: Task directory not found: $TASK_DIR"
  echo "Available tasks:"
  ls -1 "${SKILL_ROOT}/tasks"
  exit 1
fi
if [ ! -f "$TASK_DIR/task.json" ]; then
  echo "Error: Task manifest missing: $TASK_DIR/task.json"
  exit 1
fi

if [ ! -f "$HARNESS_REGISTRY" ]; then
  echo "Error: Harness registry not found: $HARNESS_REGISTRY"
  exit 1
fi

# Resolve candidate specs into workspace names + harness/model records.
CANDIDATE_JSON=$(python3 "${SKILL_ROOT}/scripts/lib/parse-candidates.py" "$CANDIDATES" "$HARNESS_REGISTRY")
mapfile -t CANDIDATE_ARRAY < <(python3 -c "import json,sys; print('\n'.join(json.loads(sys.argv[1])['candidates']))" "$CANDIDATE_JSON")

# link_node_modules <dest_dir>
link_node_modules() {
  local dest="$1"
  [ -d "$REPO_DIR/node_modules" ] || return 0
  case "$NODE_MODULES_MODE" in
    symlink)
      ln -s "$REPO_DIR/node_modules" "$dest/node_modules"
      ;;
    copy)
      cp -a "$REPO_DIR/node_modules" "$dest/node_modules"
      ;;
    shallow)
      mkdir -p "$dest/node_modules"
      # Symlink each top-level entry (and each scope member) so a candidate's
      # `npm install` mutates only its own node_modules tree.
      local entry name scope_dir member
      for entry in "$REPO_DIR"/node_modules/*; do
        [ -e "$entry" ] || continue
        name="$(basename "$entry")"
        if [[ "$name" == @* ]]; then
          mkdir -p "$dest/node_modules/$name"
          for member in "$entry"/*; do
            [ -e "$member" ] || continue
            ln -sfn "$member" "$dest/node_modules/$name/$(basename "$member")"
          done
        else
          ln -sfn "$entry" "$dest/node_modules/$name"
        fi
      done
      # .bin holds executables that must resolve relative to the real tree
      if [ -d "$REPO_DIR/node_modules/.bin" ]; then
        rm -rf "$dest/node_modules/.bin"
        ln -sfn "$REPO_DIR/node_modules/.bin" "$dest/node_modules/.bin"
      fi
      ;;
  esac
}

echo "=================================================="
echo " Preparing Benchmark Run"
echo " Task:         $TASK_ID"
echo " Repo:         $REPO_DIR"
echo " Output Dir:   $OUTPUT_DIR"
echo " Candidates:   $CANDIDATES"
echo " node_modules: $NODE_MODULES_MODE"
echo "=================================================="

mkdir -p "$OUTPUT_DIR/control"
mkdir -p "$OUTPUT_DIR/reference"

# Copy task artifacts into control
cp "${TASK_DIR}/prompt.txt" "$OUTPUT_DIR/control/prompt.txt"
cp "${TASK_DIR}/task.json" "$OUTPUT_DIR/control/task.json"
if [ -f "${TASK_DIR}/evaluator.test.ts" ]; then
  cp "${TASK_DIR}/evaluator.test.ts" "$OUTPUT_DIR/control/evaluator.test.ts"
fi
if [ -f "${TASK_DIR}/verify.sh" ]; then
  cp "${TASK_DIR}/verify.sh" "$OUTPUT_DIR/control/verify.sh"
fi

# 1. Create clean reference archive
# A task may pin `base_commit` to rewind the repo to the parent of a real fix,
# turning a merged commit into a benchmark task with ground truth attached.
BASE_COMMIT=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('base_commit') or 'HEAD')" "$TASK_DIR/task.json")
echo "[1/4] Archiving clean baseline from $REPO_DIR at $BASE_COMMIT..."
git -C "$REPO_DIR" rev-parse --verify "$BASE_COMMIT^{commit}" >/dev/null || {
  echo "Error: base_commit '$BASE_COMMIT' not found in $REPO_DIR"; exit 1; }
git -C "$REPO_DIR" archive "$BASE_COMMIT" | tar -x -C "$OUTPUT_DIR/reference"
rm -rf "$OUTPUT_DIR/reference/.git"
echo "$(git -C "$REPO_DIR" rev-parse "$BASE_COMMIT")" > "$OUTPUT_DIR/control/base_commit"

# Anti-cheating: strip files the task manifest marks as leaking the answer.
STRIP_FILES=$(python3 -c "import json,sys; print('\n'.join(json.load(open(sys.argv[1])).get('strip_files') or []))" "$TASK_DIR/task.json")
if [ -n "$STRIP_FILES" ]; then
  while IFS= read -r REL; do
    [ -n "$REL" ] || continue
    rm -f "$OUTPUT_DIR/reference/$REL"
    echo "      stripped: $REL"
  done <<< "$STRIP_FILES"
fi

link_node_modules "$OUTPUT_DIR/reference"

# 2. Set up candidates
for CANDIDATE in "${CANDIDATE_ARRAY[@]}"; do
  CANDIDATE_DIR="$OUTPUT_DIR/$CANDIDATE"
  echo "[2/4] Setting up candidate workspace: $CANDIDATE..."
  mkdir -p "$CANDIDATE_DIR"
  # Copy source files from reference (node_modules is linked separately)
  tar -C "$OUTPUT_DIR/reference" --exclude=./node_modules -cf - . | tar -C "$CANDIDATE_DIR" -xf -
  link_node_modules "$CANDIDATE_DIR"

  # Copy prompt for convenience
  cp "${TASK_DIR}/prompt.txt" "$CANDIDATE_DIR/BENCH-TASK.md"
done

# 3. Create metadata file
python3 - "$OUTPUT_DIR/control/meta.json" "$TASK_ID" "$REPO_DIR" "$NODE_MODULES_MODE" "$CANDIDATE_JSON" <<'PY'
import json, sys, datetime
out, task_id, repo_dir, nm_mode, candidate_json = sys.argv[1:]
parsed = json.loads(candidate_json)
specs = parsed["candidate_specs"]
models = {s["model_id"] for s in specs.values() if s["model_id"]}
harnesses = {s["harness"] for s in specs.values() if s["harness"] != "manual"}
if len(models) == 1 and len(harnesses) > 1:
    mode = "harness-comparison"   # model held constant
elif len(harnesses) <= 1 and len(models) > 1:
    mode = "model-comparison"     # harness held constant
else:
    mode = "mixed"
json.dump({
    "task_id": task_id,
    "created_at": datetime.datetime.now().astimezone().isoformat(),
    "repo_dir": repo_dir,
    "node_modules_mode": nm_mode,
    "comparison_mode": mode,
    "candidates": parsed["candidates"],
    "candidate_specs": specs,
}, open(out, "w"), indent=2)
print("      comparison mode: " + mode)
PY

echo "[3/4] Initialized control metadata and runner scripts..."
echo "[4/4] Benchmark workspace prepared at: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "1. Run candidates: ${SKILL_ROOT}/scripts/run-candidates.sh --benchmark-dir $OUTPUT_DIR --go"
echo "   (or drive them by hand in $OUTPUT_DIR/<candidate> using $OUTPUT_DIR/control/prompt.txt)"
echo "2. Evaluate: ${SKILL_ROOT}/scripts/run-evaluator.sh --benchmark-dir $OUTPUT_DIR"
echo "3. Anonymize & Judge: ${SKILL_ROOT}/scripts/anonymize-diffs.sh --benchmark-dir $OUTPUT_DIR"
echo "4. Report: python3 ${SKILL_ROOT}/scripts/generate-report.py --benchmark-dir $OUTPUT_DIR"
