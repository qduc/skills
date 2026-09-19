#!/usr/bin/env bash
set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_DIR=""
HARNESS_REGISTRY="${SKILL_ROOT}/harnesses.json"
TIMEOUT_SECS=600
PARALLEL=0
GO=0
DRIVER="auto"
KEEP_PANES=0
HERDR_WS=""

usage() {
  cat <<USAGE
Usage: $0 --benchmark-dir <path> [--go] [options]

Runs each candidate's harness inside its own workspace on the task prompt,
recording wall-clock duration, exit code, and transcript.

Options:
  --benchmark-dir <path>  Prepared benchmark run directory (required)
  --go                    Actually launch the harnesses. Without it, prints the
                          plan and exits (cost/approval discipline).
  --timeout <seconds>     Per-candidate wall-clock limit (default: 600)
  --parallel              Run candidates concurrently (default: sequential, which
                          is fairer for latency comparisons)
  --harnesses <file>      Harness registry (default: <skill>/harnesses.json)
  --only <names>          Comma-separated subset of candidates to run
  --driver <mode>         auto (default) | herdr | cli
                          auto: use herdr for harnesses that declare a herdr
                          kind (real TUI, lifecycle-aware waiting), cli for the
                          rest. herdr: require a herdr pane for every candidate.
                          cli: force non-interactive invocation.
  --keep-panes            Leave herdr tabs/workspace open after the run (debugging)
  --herdr-workspace <id>  Run herdr candidates in this existing workspace instead
                          of a throwaway one created for the benchmark
USAGE
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-dir) BENCH_DIR="$2"; shift 2 ;;
    --timeout) TIMEOUT_SECS="$2"; shift 2 ;;
    --harnesses) HARNESS_REGISTRY="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --driver) DRIVER="$2"; shift 2 ;;
    --keep-panes) KEEP_PANES=1; shift ;;
    --herdr-workspace) HERDR_WS="$2"; shift 2 ;;
    --parallel) PARALLEL=1; shift ;;
    --go) GO=1; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done
ONLY="${ONLY:-}"

case "$DRIVER" in
  auto|herdr|cli) ;;
  *) echo "Error: --driver must be auto, herdr, or cli"; exit 1 ;;
esac
if [ "$DRIVER" != "cli" ] && ! command -v herdr >/dev/null 2>&1; then
  if [ "$DRIVER" = "herdr" ]; then
    echo "Error: --driver herdr requested but the herdr CLI is not on PATH."
    exit 1
  fi
  echo "Note: herdr CLI not found; falling back to --driver cli."
  DRIVER="cli"
fi

if [ -z "$BENCH_DIR" ] || [ ! -d "$BENCH_DIR" ]; then
  echo "Error: Valid --benchmark-dir is required."
  exit 1
fi
CONTROL_DIR="$BENCH_DIR/control"
if [ ! -f "$CONTROL_DIR/meta.json" ]; then
  echo "Error: Missing control/meta.json in $BENCH_DIR"
  exit 1
fi

TASK_ID=$(python3 -c "import json; print(json.load(open('$CONTROL_DIR/meta.json'))['task_id'])")
MODE=$(python3 -c "import json; print(json.load(open('$CONTROL_DIR/meta.json')).get('comparison_mode','mixed'))")
mapfile -t CANDIDATES < <(python3 -c "import json; print('\n'.join(json.load(open('$CONTROL_DIR/meta.json'))['candidates']))")

if [ -n "$ONLY" ]; then
  mapfile -t CANDIDATES < <(python3 -c "
import json, sys
keep = [s.strip() for s in sys.argv[1].split(',') if s.strip()]
all_c = json.load(open('$CONTROL_DIR/meta.json'))['candidates']
missing = [k for k in keep if k not in all_c]
if missing:
    sys.exit('Error: --only names not in this run: ' + ', '.join(missing))
print('\n'.join(c for c in all_c if c in keep))
" "$ONLY")
fi

echo "=================================================="
echo " Candidate Runs"
echo " Task:            $TASK_ID"
echo " Comparison mode: $MODE"
echo " Timeout:         ${TIMEOUT_SECS}s per candidate"
echo " Execution:       $([ "$PARALLEL" = 1 ] && echo parallel || echo sequential)"
echo " Driver:          $DRIVER"
echo "=================================================="

# Build the plan first so the user can approve it before anything is spent.
declare -A PLAN_CWD PLAN_ARGV PLAN_DRIVER
RUNNABLE=()

# has_herdr_support <candidate> -> 0 if its harness declares a herdr kind
has_herdr_support() {
  python3 -c "
import json, sys
bench, registry_path, cand = sys.argv[1:4]
meta = json.load(open(bench + '/control/meta.json'))
registry = json.load(open(registry_path))['harnesses']
spec = meta.get('candidate_specs', {}).get(cand) or {}
sys.exit(0 if registry.get(spec.get('harness'), {}).get('herdr') else 1)
" "$BENCH_DIR" "$HARNESS_REGISTRY" "$1"
}

for CANDIDATE in "${CANDIDATES[@]}"; do
  CAND_DRIVER="cli"
  if [ "$DRIVER" != "cli" ] && has_herdr_support "$CANDIDATE"; then
    CAND_DRIVER="herdr"
  fi

  if [ "$CAND_DRIVER" = "herdr" ]; then
    PLAN_DRIVER["$CANDIDATE"]="herdr"
    RUNNABLE+=("$CANDIDATE")
    printf '  %-24s herdr pane (interactive TUI)\n' "$CANDIDATE"
    continue
  fi

  # NUL-separated argv must go through a file; command substitution drops NULs.
  RENDER_FILE="$(mktemp)"
  if python3 "${SKILL_ROOT}/scripts/lib/harness-cmd.py" "$HARNESS_REGISTRY" "$BENCH_DIR" "$CANDIDATE" > "$RENDER_FILE" 2>/dev/null; then
    mapfile -d '' -t PARTS < "$RENDER_FILE"
    rm -f "$RENDER_FILE"
    PLAN_CWD["$CANDIDATE"]="${PARTS[0]}"
    PLAN_ARGV["$CANDIDATE"]=$(printf '%q ' "${PARTS[@]:1}")
    PLAN_DRIVER["$CANDIDATE"]="cli"
    RUNNABLE+=("$CANDIDATE")
    printf '  %-24s cli: %.160s...\n' "$CANDIDATE" "${PLAN_ARGV[$CANDIDATE]}"
  else
    RC=$?
    rm -f "$RENDER_FILE"
    if [ $RC -eq 2 ]; then
      if [ "$DRIVER" = "herdr" ]; then
        echo "Error: candidate '$CANDIDATE' has no herdr kind and no CLI invocation."
        exit 1
      fi
      printf '  %-24s (manual — skipped)\n' "$CANDIDATE"
    else
      python3 "${SKILL_ROOT}/scripts/lib/harness-cmd.py" "$HARNESS_REGISTRY" "$BENCH_DIR" "$CANDIDATE" >/dev/null
      exit 1
    fi
  fi
done

if [ "${#RUNNABLE[@]}" -eq 0 ]; then
  echo ""
  echo "No runnable candidates (all manual). Drive them by hand, then run run-evaluator.sh."
  exit 0
fi

if [ "$GO" != "1" ]; then
  echo ""
  echo "Dry run. Re-run with --go to launch these ${#RUNNABLE[@]} candidate(s)."
  exit 0
fi

# run_one <candidate>
run_one() {
  local candidate="$1"

  if [ "${PLAN_DRIVER[$candidate]}" = "herdr" ]; then
    local keep=()
    [ "$KEEP_PANES" = "1" ] && keep=(--keep-pane)
    echo ">>> Running $candidate in a herdr pane ..."
    python3 "${SKILL_ROOT}/scripts/lib/herdr-run.py" \
      --benchmark-dir "$BENCH_DIR" --candidate "$candidate" \
      --registry "$HARNESS_REGISTRY" --timeout "$TIMEOUT_SECS" \
      ${HERDR_WS:+--workspace "$HERDR_WS"} "${keep[@]}" || true
    return 0
  fi

  local cwd="${PLAN_CWD[$candidate]}"
  local log="$CONTROL_DIR/${candidate}.run.log"
  local start end rc
  local render_file
  render_file="$(mktemp)"
  python3 "${SKILL_ROOT}/scripts/lib/harness-cmd.py" "$HARNESS_REGISTRY" "$BENCH_DIR" "$candidate" > "$render_file"
  local -a argv
  mapfile -d '' -t argv < "$render_file"
  rm -f "$render_file"
  argv=("${argv[@]:1}")

  echo ">>> Running $candidate ..."
  start=$(date +%s)
  # stdin must be closed: a harness that keeps reading it can finish its work,
  # print a final answer, and still never exit, which the runner would then
  # record as a TIMEOUT that never happened.
  ( cd "$cwd" && timeout --signal=TERM --kill-after=30 "$TIMEOUT_SECS" "${argv[@]}" < /dev/null ) > "$log" 2>&1 && rc=0 || rc=$?
  end=$(date +%s)

  echo "$((end - start))" > "$CONTROL_DIR/${candidate}.seconds"
  # Window boundaries let out-of-band telemetry (e.g. term2's provider-traffic
  # log, which never reaches stdout) be attributed back to this candidate.
  echo "$start" > "$CONTROL_DIR/${candidate}.start_epoch"
  echo "$end" > "$CONTROL_DIR/${candidate}.end_epoch"
  echo "$rc" > "$CONTROL_DIR/${candidate}.exitcode"
  if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    echo "TIMEOUT" > "$CONTROL_DIR/${candidate}.run.status"
    echo "<<< $candidate TIMED OUT after ${TIMEOUT_SECS}s"
  elif [ "$rc" -eq 0 ]; then
    echo "OK" > "$CONTROL_DIR/${candidate}.run.status"
    echo "<<< $candidate finished in $((end - start))s"
  else
    echo "ERROR" > "$CONTROL_DIR/${candidate}.run.status"
    echo "<<< $candidate exited $rc after $((end - start))s (see $log)"
  fi
}

# Herdr candidates run in a workspace of their own so benchmark panes never
# land in the user's working layout.
OWNS_WS=0
if [ -z "$HERDR_WS" ]; then
  for CANDIDATE in "${RUNNABLE[@]}"; do
    if [ "${PLAN_DRIVER[$CANDIDATE]}" = "herdr" ]; then
      HERDR_WS=$(herdr workspace create --label "bench-${TASK_ID}" --no-focus \
        | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['workspace']['workspace_id'])")
      OWNS_WS=1
      echo "Created herdr workspace $HERDR_WS for benchmark panes."
      break
    fi
  done
fi

cleanup_ws() {
  if [ "$OWNS_WS" = "1" ] && [ "$KEEP_PANES" != "1" ] && [ -n "$HERDR_WS" ]; then
    herdr workspace close "$HERDR_WS" >/dev/null 2>&1 || true
  fi
}
trap cleanup_ws EXIT

echo ""
if [ "$PARALLEL" = "1" ]; then
  for CANDIDATE in "${RUNNABLE[@]}"; do run_one "$CANDIDATE" & done
  wait
else
  for CANDIDATE in "${RUNNABLE[@]}"; do run_one "$CANDIDATE"; done
fi

echo ""
echo "Runs complete. Durations in $CONTROL_DIR/*.seconds, transcripts in *.run.log"
echo "Next: ${SKILL_ROOT}/scripts/run-evaluator.sh --benchmark-dir $BENCH_DIR"
