#!/usr/bin/env python3
"""Transcript watcher for the coordinator memory sidecar.

Tails the transcripts of bound sessions and runs the memory judge on new
complete records. This replaces the Claude Code hook trigger: collection no
longer depends on harness lifecycle events.

Ownership: one watcher per coordinator root (per host). The launcher records a
*session marker* when it launches a session (``write_launch_marker``); the
watcher only reads markers and bindings and never scans for a session by
guessing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import coord_memory
import coord_state as state

MARKER_DIR = 'sessions'


def marker_path(root, session_id):
    return Path(root) / MARKER_DIR / (session_id + '.json')


def write_launch_marker(root, session_id, task_id, owner, transcript_path, harness='claude'):
    """Record a launcher-mediated binding for a session the coordinator launched."""
    path = marker_path(root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state.atomic_write(path, json.dumps({'session_id': session_id, 'task_id': task_id, 'owner': owner,
                                         'harness': harness, 'transcript_path': str(transcript_path)},
                                        indent=2) + '\n')
    return path


def read_markers(root):
    """Return session markers by session id; unreadable markers are skipped."""
    directory = Path(root) / MARKER_DIR
    if not directory.is_dir():
        return {}
    markers = {}
    for path in sorted(directory.glob('*.json')):
        try:
            marker = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(marker, dict) and isinstance(marker.get('session_id'), str):
            markers[marker['session_id']] = marker
    return markers


def _binding_key(session_id, harness):
    return f'{harness}:{session_id}'


def _has_binding(root, session_id, harness):
    return _binding_key(session_id, harness) in state._load_bindings(root)['bindings']


def _ensure_binding(root, marker):
    session_id = marker['session_id']
    harness = marker.get('harness') or 'claude'
    if _has_binding(root, session_id, harness):
        return False
    task = state.load(state.task_path(root, marker['task_id']))
    args = argparse.Namespace(task=marker['task_id'], owner=marker['owner'],
                              revision=task['revision'], session_id=session_id, harness=harness,
                              transcript=marker['transcript_path'])
    state.bind_session(args, root)
    return True


def bind_markers(root):
    """Create a binding for each launcher marker that lacks one. Idempotent."""
    created = []
    for session_id, marker in read_markers(root).items():
        transcript = marker.get('transcript_path')
        if not isinstance(transcript, str) or not transcript:
            continue
        try:
            if _ensure_binding(root, marker):
                created.append(session_id)
        except (state.StateError, OSError, ValueError, KeyError, TypeError):
            continue
    return created


def bound_sessions(root):
    """Session ids whose binding has a transcript path to tail, across harnesses."""
    bindings = state._load_bindings(root)['bindings']
    sessions = []
    for key, value in bindings.items():
        if not isinstance(value, dict) or not value.get('transcript_path'):
            continue
        session_id = value.get('session_id')
        sessions.append(session_id if isinstance(session_id, str) else key.split(':', 1)[1])
    return sessions


def watch(root, poll_seconds=5.0, iterations=None, runner=None, sleep=time.sleep, logger=None):
    """Tail bound transcripts, judging new records each pass.

    ``iterations=None`` runs until stopped; a number bounds the passes (tests use
    ``iterations=1``). Each pass binds new markers, then judges every bound
    session once. One session's failure is logged and does not stop the watcher.
    """
    root = Path(root)
    passes = 0
    while iterations is None or passes < iterations:
        bind_markers(root)
        for session_id in bound_sessions(root):
            try:
                result = coord_memory.judge(root, session_id, runner)
            except Exception as error:  # one bad session must not stop the watcher
                result = {'status': 'deferred', 'reason': type(error).__name__}
            if logger:
                logger(session_id, result)
        passes += 1
        if iterations is not None and passes >= iterations:
            break
        sleep(poll_seconds)


def main():
    parser = argparse.ArgumentParser(description='Tail bound transcripts and judge new memory.')
    parser.add_argument('--root')
    parser.add_argument('--poll', type=float, default=5.0)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    root = Path(args.root) if args.root else state.root_path()
    watch(root, poll_seconds=args.poll, iterations=1 if args.once else None)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
