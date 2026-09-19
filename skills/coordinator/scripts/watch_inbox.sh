#!/usr/bin/env bash
# Run as a harness-managed background Bash job. Exit on unread messages or error.
set -uo pipefail
if (( $# < 1 || $# > 3 )); then
    printf 'Usage: bash watch_inbox.sh STATE_PATH [CHECK_WINDOW_SECONDS] [FALLBACK_SECONDS]\n' >&2
    exit 1
fi
watcher_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || exit 1
watcher_state=$1
watcher_window=${2:-60}
watcher_fallback=${3:-300}
if [[ ! "$watcher_fallback" =~ ^[1-9][0-9]*$ ]]; then
    printf 'FALLBACK_SECONDS must be a positive integer\n' >&2
    exit 1
fi
watcher_deadline=$((SECONDS + watcher_fallback))
watcher_pid=
stop_child() {
    if [[ -n "$watcher_pid" ]]; then
        kill "$watcher_pid" 2>/dev/null || true
        wait "$watcher_pid" 2>/dev/null || true
    fi
}
trap stop_child EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
while true; do
    python3 "$watcher_dir/coord_lifecycle.py" watch \
        --state "$watcher_state" --wait "$watcher_window" --quiet-timeout &
    watcher_pid=$!
    watcher_status=0
    wait "$watcher_pid" || watcher_status=$?
    watcher_pid=
    if (( watcher_status != 124 )); then
        exit "$watcher_status"
    fi
    if (( SECONDS >= watcher_deadline )); then
        python3 -c 'import json,sys; print(json.dumps({"result": {"event": "fallback_check_in", "state": sys.argv[1], "messages": []}}))' "$watcher_state"
        exit 0
    fi
    # Quiet until a report or bounded fallback check-in.
done
