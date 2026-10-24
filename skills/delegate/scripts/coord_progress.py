#!/usr/bin/env python3
"""Render a machine-readable coordinator progress snapshot from task state."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def snapshot(path):
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f'invalid task state {path}: {error}') from error
    if not isinstance(state, dict) or not isinstance(state.get('details'), dict):
        raise ValueError(f'invalid task state shape: {path}')
    details = state['details']
    def parse_timestamp(value):
        if not isinstance(value, str):
            return None
        try:
            moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment

    def duration_between(start_value, end_value):
        start, end = parse_timestamp(start_value), parse_timestamp(end_value)
        if start is None or end is None:
            return None
        return round((end - start).total_seconds(), 1)

    workers = []
    for worker in details.get('workers', []):
        if not isinstance(worker, dict):
            continue
        status = str(worker.get('status', 'unknown')).lower()
        last_progress = worker.get('last_progress_at') or worker.get('updated_at')
        report = worker.get('report')
        if not last_progress and isinstance(report, str):
            try:
                last_progress = datetime.fromtimestamp(Path(report).stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                pass
        reported_at = worker.get('reported_at')
        entry = {
            'id': worker.get('id') or worker.get('pane') or worker.get('pane_id'),
            'pane': worker.get('pane') or worker.get('pane_id') or worker.get('id'),
            'worktree': worker.get('worktree'), 'report': report, 'status': status,
            'last_progress_at': last_progress, 'blocked': status in {'blocked', 'unknown'},
        }
        if worker.get('merge_commit'):
            entry['merge_commit'] = worker['merge_commit']
        dispatch_to_report = duration_between(worker.get('dispatched_at'), reported_at)
        if dispatch_to_report is not None:
            entry['dispatch_to_report_s'] = dispatch_to_report
        report_to_merge = duration_between(reported_at, worker.get('merged_at'))
        if report_to_merge is not None:
            entry['report_to_merge_s'] = report_to_merge
        workers.append(entry)
    items = details.get('work_items', [])
    done = sum(1 for item in items if isinstance(item, dict) and item.get('status') in {'completed', 'cancelled'})
    checks = details.get('verification', [])
    merges = details.get('merges')
    if not isinstance(merges, list):
        merges = [item for item in checks if isinstance(item, dict) and 'merge' in str(item.get('check', '')).lower()]
    return {
        'task_id': state.get('id'),
        'phase': details.get('phase') or details.get('current_phase'),
        'next_action': details.get('next_action'),
        'status': state.get('status'), 'updated_at': state.get('updated_at'),
        'workers': workers, 'merges': merges, 'done': done, 'total': len(items),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, help='task state.json path')
    args = parser.parse_args()
    try:
        print(json.dumps(snapshot(Path(args.state)), ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError) as error:
        print(f'coord_progress: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
