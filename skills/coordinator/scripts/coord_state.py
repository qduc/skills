#!/usr/bin/env python3
"""Durable coordinator task records, ownership fencing, and recent choices."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid


class StateError(RuntimeError):
    pass


STATUSES = {'pending', 'active', 'blocked', 'paused', 'completed'}
DETAIL_DEFAULTS = {
    'objective': '', 'authority': '', 'next_action': '', 'constraints': [],
    'deliverables': [], 'acceptance_criteria': [], 'pending_decisions': [],
    'work_items': [], 'workers': [], 'artifacts': [], 'verification': [],
    'blockers': [], 'background_work': [], 'notes': [],
}


def now():
    return datetime.now(timezone.utc).isoformat()


def root_path(override=None):
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get('XDG_STATE_HOME', '')
    return (Path(base) if base and Path(base).is_absolute() else Path.home() / '.local/state') / 'coordinator'


def task_path(root, task_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', task_id):
        raise StateError('invalid task ID')
    path = root / 'tasks' / task_id
    if path.is_symlink():
        raise StateError('task directory must not be a symlink')
    return path


@contextmanager
def locked(path):
    # Keep the lock inode: unlinking it would let concurrent processes lock different files.
    with path.open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise StateError('record is busy; reread and retry') from error
        # Close releases the lock when its last inherited descriptor closes.
        # Explicit LOCK_UN would also unlock children still using this description.
        yield stream


def atomic_write(path, text):
    fd, temporary = tempfile.mkstemp(prefix='.checkpoint-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load(path):
    source = path / 'state.json'
    if not source.exists() and (path / 'state.md').exists():
        raise StateError('legacy Markdown record: preserve it and explicitly reconstruct a JSON task; no automatic interpretation')
    state = json.loads(source.read_text())
    if not isinstance(state, dict) or state.get('schema_version') != 1 or state.get('id') != path.name:
        raise StateError(f'unsupported task record: {source}')
    if type(state.get('revision')) is not int or not isinstance(state.get('details'), dict):
        raise StateError(f'invalid task record: {source}')
    required = {'title', 'project', 'conversation', 'created_at', 'updated_at', 'owner',
                'status', 'archived_at', 'selection', 'choice_events', 'ownership_events'}
    if not required.issubset(state) or not isinstance(state['status'], str) or state['status'] not in STATUSES:
        raise StateError(f'incomplete task record: {source}')
    if not set(DETAIL_DEFAULTS).issubset(state['details']):
        raise StateError(f'incomplete task details: {source}')
    if not isinstance(state['choice_events'], list) or not isinstance(state['ownership_events'], list):
        raise StateError(f'invalid task history: {source}')
    for event in state['choice_events']:
        if not isinstance(event, dict) or not all(isinstance(event.get(k), str) for k in ('id', 'at', 'task_id')):
            raise StateError(f'invalid choice event: {source}')
        validate_pool(event.get('pool'))
    validate_details(state['details'])
    return state


def markdown(state):
    lines = [f"# {state['title']}", '',
             '<!-- Generated from state.json; use coord_state.py to update. -->', '',
             f"Task: {state['id']} | Status: {state['status']} | Revision: {state['revision']}",
             f"Project: {state['project']}", f"Updated: {state['updated_at']}",
             f"Owner: {state['owner'] or 'unclaimed'}", '', '## Harness/model selection', '',
             json.dumps(state['selection'], ensure_ascii=False, indent=2), '']
    for name, value in state['details'].items():
        lines.extend([f"## {name.replace('_', ' ').title()}", '',
                      value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2), ''])
    return '\n'.join(lines)


def save(path, state):
    atomic_write(path / 'state.json', json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    warnings = []
    try:
        atomic_write(path / 'state.md', markdown(state))
    except OSError as error:
        warnings.append(f'JSON checkpoint saved; Markdown view needs regeneration: {error}')
    return warnings


def response(path, state, warnings=None):
    return {'state_path': str(path / 'state.json'), 'markdown_path': str(path / 'state.md'),
            'state': state, 'warnings': warnings or []}


def create(args, root):
    if not args.title.strip() or not args.objective.strip():
        raise StateError('title and objective must be non-empty')
    task_id = uuid.uuid4().hex
    path = task_path(root, task_id)
    path.mkdir(parents=True, mode=0o700)
    stamp = now()
    state = {'schema_version': 1, 'id': task_id, 'title': args.title,
             'project': str(Path(args.project).expanduser().resolve()), 'conversation': args.conversation,
             'created_at': stamp, 'updated_at': stamp, 'revision': 1,
             'owner': args.owner or uuid.uuid4().hex, 'status': 'pending', 'archived_at': None,
             'selection': None, 'choice_events': [], 'ownership_events': [],
             'details': dict(DETAIL_DEFAULTS, objective=args.objective)}
    return response(path, state, save(path, state))


def check_revision(state, revision):
    if state['revision'] != revision:
        raise StateError(f"stale revision: expected {revision}, current {state['revision']}; reread before retrying")


def check_owner(state, owner):
    if not owner or state['owner'] != owner:
        raise StateError('task is not owned by this coordinator; claim it before writing')


def validate_details(details):
    if set(details) - set(DETAIL_DEFAULTS):
        raise StateError('unknown detail fields: ' + ', '.join(sorted(set(details) - set(DETAIL_DEFAULTS))))
    for key, value in details.items():
        if not isinstance(value, type(DETAIL_DEFAULTS[key])):
            raise StateError(f'incorrect type for details.{key}')
    items = details.get('work_items', [])
    ids = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or not isinstance(item.get('status'), str):
            raise StateError('each work item requires string id and status')
        if item['id'] in ids:
            raise StateError('duplicate work item ID')
        ids.add(item['id'])
    edges = {}
    for item in items:
        needs = item.get('needs', [])
        if not isinstance(needs, list) or any(not isinstance(n, str) or n not in ids for n in needs):
            raise StateError('work-item dependencies must name existing IDs')
        edges[item['id']] = needs
    visiting, visited = set(), set()
    def visit(node):
        if node in visiting:
            raise StateError('cyclic work-item dependencies')
        if node in visited:
            return
        visiting.add(node)
        for dependency in edges[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)
    for node in edges:
        visit(node)


def apply_patch(state, patch):
    if not isinstance(patch, dict) or set(patch) - {'title', 'status', 'details'}:
        raise StateError('checkpoint accepts only title, status, and details')
    if 'title' in patch and (not isinstance(patch['title'], str) or not patch['title'].strip()):
        raise StateError('title must be non-empty text')
    if 'status' in patch and (not isinstance(patch['status'], str) or patch['status'] not in STATUSES):
        raise StateError('invalid task status')
    details = patch.get('details', {})
    if not isinstance(details, dict):
        raise StateError('details must be an object')
    merged = dict(state['details'], **details)
    validate_details(merged)
    state.update({k: v for k, v in patch.items() if k != 'details'})
    state['details'] = merged
    if state['status'] == 'completed':
        if merged['blockers'] or merged['pending_decisions'] or merged['background_work']:
            raise StateError('resolve blockers, decisions, and background work before completion')
        if any(item['status'] not in {'completed', 'cancelled'} for item in merged['work_items']):
            raise StateError('settle all work items before completion')


def validate_pool(pool):
    if not isinstance(pool, list) or not pool:
        raise StateError('pool must be a non-empty array')
    for route in pool:
        if not isinstance(route, dict) or set(route) - {'harness', 'model', 'provider', 'effort', 'role'}:
            raise StateError('each route accepts harness, model, provider, effort, role')
        if any(not isinstance(route.get(k), str) or not route[k].strip() for k in ('harness', 'model')):
            raise StateError('each route requires explicit harness and model')
        if any(not isinstance(value, str) or not value.strip() for value in route.values()):
            raise StateError('route fields must be non-empty strings')
        if any(route[k].lower() in {'default', 'previous', 'same as previous'} for k in ('harness', 'model')):
            raise StateError('resolve previous/default to concrete identifiers first')


def export_choice(root, event):
    root.mkdir(parents=True, exist_ok=True)
    with locked(root / '.choices.lock'):
        path = root / 'choices.jsonl'
        # A leading newline after an interrupted append keeps the next entry parseable.
        prefix = ''
        if path.exists() and path.stat().st_size:
            with path.open('rb') as stream:
                stream.seek(-1, os.SEEK_END)
                if stream.read(1) != b'\n':
                    prefix = '\n'
        with path.open('a') as stream:
            stream.write(prefix + json.dumps(event, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())


def mutate(args, root):
    if not args.owner.strip():
        raise StateError('owner must be a non-empty coordinator-session identifier')
    path = task_path(root, args.task)
    if not path.is_dir():
        raise StateError('task does not exist')
    event = None
    with locked(path / '.write.lock'):
        state = load(path)
        if args.revision == 'latest':
            if args.command == 'claim':
                raise StateError('claim requires a numeric revision after reconciliation')
            check_owner(state, args.owner)
            check_revision(state, state['revision'])
        else:
            check_revision(state, args.revision)
        if state['archived_at']:
            raise StateError('task is archived; it cannot be mutated')
        if args.command == 'claim':
            if state['owner'] and state['owner'] != args.owner:
                if not args.takeover or not args.reason or not args.reason.strip():
                    raise StateError('task has an owner; takeover requires --takeover and --reason after reconciliation')
            state['ownership_events'].append({'at': now(), 'from': state['owner'], 'to': args.owner,
                                              'reason': args.reason})
            state['owner'] = args.owner
        else:
            check_owner(state, args.owner)
            if args.command == 'checkpoint':
                apply_patch(state, json.loads(Path(args.patch_file).read_text()))
            elif args.command == 'select':
                if not args.confirmed or not args.source.strip():
                    raise StateError('record only a user-confirmed selection with its source')
                pool = json.loads(Path(args.pool_file).read_text())
                validate_pool(pool)
                event = {'id': uuid.uuid4().hex, 'at': now(), 'task_id': state['id'],
                         'project': state['project'], 'pool': pool, 'source': args.source}
                state['selection'] = pool
                state['choice_events'].append(event)
            elif args.command == 'release':
                state['ownership_events'].append({'at': now(), 'from': state['owner'], 'to': None, 'reason': 'release'})
                state['owner'] = None
            elif args.command == 'archive':
                if state['status'] != 'completed':
                    raise StateError('only completed tasks may be archived')
                state['archived_at'] = now()
                state['owner'] = None
        state['revision'] += 1
        state['updated_at'] = now()
        warnings = save(path, state)
    if event:
        try:
            export_choice(root, event)
        except (OSError, StateError) as error:
            warnings.append(f'selection saved in task; history export failed (choices can recover it): {error}')
    return response(path, state, warnings)


def scan(root):
    records, warnings = [], []
    for path in sorted((root / 'tasks').glob('*')):
        if not path.is_dir():
            continue
        try:
            records.append(load(task_path(root, path.name)))
        except (OSError, ValueError, StateError) as error:
            warnings.append(f'{path}: {error}')
    return records, warnings


def list_tasks(args, root):
    records, warnings = scan(root)
    selected = []
    for state in records:
        if not args.all and (state['status'] == 'completed' or state['archived_at']):
            continue
        if args.project and state['project'] != str(Path(args.project).expanduser().resolve()):
            continue
        if args.conversation and state['conversation'] != args.conversation:
            continue
        selected.append({key: state[key] for key in ('id', 'title', 'project', 'status', 'updated_at', 'revision', 'owner', 'archived_at')}
                        | {'next_action': state['details']['next_action'], 'blockers': state['details']['blockers']})
    selected.sort(key=lambda item: item['updated_at'], reverse=True)
    return {'tasks': selected, 'warnings': warnings}


def choices(args, root):
    entries, warnings = {}, []
    history = root / 'choices.jsonl'
    if history.exists():
        for number, line in enumerate(history.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict) or not isinstance(entry.get('at'), str):
                    raise ValueError('missing timestamp')
                validate_pool(entry.get('pool'))
                entries[entry.get('id') or hashlib.sha256(line.encode()).hexdigest()] = entry
            except (ValueError, StateError) as error:
                warnings.append(f'history line {number}: {error}')
    records, scan_warnings = scan(root)
    warnings.extend(scan_warnings)
    for state in records:
        for entry in state['choice_events']:
            entries[entry['id']] = entry  # Recover selections saved before an export failure.
    result = [entry for entry in entries.values()
              if (not args.task or entry.get('task_id') == args.task)
              and (not args.project or entry.get('project') == str(Path(args.project).expanduser().resolve()))]
    result.sort(key=lambda entry: (entry['at'], entry.get('id', '')), reverse=True)
    return {'choices': result[:args.limit], 'warnings': warnings}


def inspect_resume(state):
    findings = []
    for artifact in state['details']['artifacts']:
        if not isinstance(artifact, dict) or not isinstance(artifact.get('path'), str):
            findings.append({'kind': 'invalid_artifact_reference', 'artifact': artifact})
            continue
        path = Path(artifact['path'])
        if not path.is_absolute():
            findings.append({'kind': 'nonabsolute_artifact_path', 'path': str(path)})
        elif not path.exists():
            findings.append({'kind': 'missing_artifact', 'path': str(path)})
        elif artifact.get('sha256') and path.is_file():
            hasher = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    hasher.update(chunk)
            if hasher.hexdigest() != artifact['sha256']:
                findings.append({'kind': 'artifact_changed', 'path': str(path)})
    for worker in state['details']['workers']:
        if isinstance(worker, dict):
            for key in ('cwd', 'worktree'):
                if worker.get(key) and (not Path(worker[key]).is_absolute() or not Path(worker[key]).is_dir()):
                    findings.append({'kind': 'missing_worker_directory', 'worker': worker.get('id'), 'path': worker[key]})
    return {'findings': findings, 'unfinished': [i for i in state['details']['work_items']
             if i['status'] not in {'completed', 'cancelled'}],
            'live_worker_reconciliation_required': bool(state['details']['workers'])}


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument('--root', help='override the coordinator state directory')
    sub = root.add_subparsers(dest='command', required=True)
    command = sub.add_parser('create')
    for key in ('title', 'objective', 'project'):
        command.add_argument('--' + key, required=True)
    command.add_argument('--conversation')
    command.add_argument('--owner', help='unique coordinator-session ID; generated if omitted')
    command = sub.add_parser('list')
    command.add_argument('--all', action='store_true')
    command.add_argument('--project')
    command.add_argument('--conversation')
    for name in ('show', 'render', 'check-resume'):
        command = sub.add_parser(name)
        command.add_argument('--task', required=True)
    for name in ('claim', 'checkpoint', 'select', 'release', 'archive'):
        command = sub.add_parser(name)
        command.add_argument('--task', required=True)
        command.add_argument('--owner', required=True)
        command.add_argument('--revision', required=True, type=lambda value: value if value == 'latest' else int(value))
        if name == 'claim':
            command.add_argument('--takeover', action='store_true')
            command.add_argument('--reason')
        elif name == 'checkpoint':
            command.add_argument('--patch-file', required=True)
        elif name == 'select':
            command.add_argument('--pool-file', required=True)
            command.add_argument('--confirmed', action='store_true')
            command.add_argument('--source', required=True)
    command = sub.add_parser('choices')
    command.add_argument('--task')
    command.add_argument('--project')
    command.add_argument('--limit', type=int, default=10)
    return root


def main():
    args = parser().parse_args()
    root = root_path(args.root)
    try:
        if args.command == 'create':
            result = create(args, root)
        elif args.command == 'list':
            result = list_tasks(args, root)
        elif args.command == 'choices':
            if args.limit < 1:
                raise StateError('limit must be positive')
            result = choices(args, root)
        elif args.command in {'show', 'render', 'check-resume'}:
            path = task_path(root, args.task)
            if args.command == 'render':
                with locked(path / '.write.lock'):
                    state = load(path)
                    atomic_write(path / 'state.md', markdown(state))
            else:
                state = load(path)
            result = inspect_resume(state) if args.command == 'check-resume' else response(path, state)
        else:
            result = mutate(args, root)
    except (StateError, OSError, ValueError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
