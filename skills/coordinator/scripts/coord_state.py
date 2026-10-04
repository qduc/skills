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
import subprocess
import sys
import tempfile
import uuid


class StateError(RuntimeError):
    pass


STATUSES = {'pending', 'active', 'blocked', 'paused', 'completed'}
MEMORY_CATEGORIES = {'intent', 'decisions', 'state', 'discoveries'}
JOURNAL_STATUSES = {'pending', 'consolidated', 'discarded'}
COLD_STATUSES = {'current', 'superseded', 'withdrawn'}
HOT_FIELDS = {'focus', 'model', 'files', 'source_ids'}
DETAIL_DEFAULTS = {
    'objective': '', 'authority': '', 'next_action': '', 'phase': '', 'constraints': [],
    'deliverables': [], 'acceptance_criteria': [], 'pending_decisions': [],
    'work_items': [], 'workers': [], 'artifacts': [], 'verification': [],
    'blockers': [], 'background_work': [], 'notes': [],
}


LESSON_SCOPES = {'host', 'general', 'one-off'}


def now():
    return datetime.now(timezone.utc).isoformat()


def _memory_default():
    return {'hot': {'focus': '', 'model': '', 'files': [], 'source_ids': [], 'updated_at': now()},
            'journal': [], 'cold': [], 'audit': []}


def _json_bytes(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def _authored_bytes(item):
    return _json_bytes({'text': item['text'], 'provenance': item.get('provenance', [])})


def _utc_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _validate_provenance(value, required=False):
    if not required and value in (None, []):
        return
    if not isinstance(value, list) or not value or len(value) > 3:
        raise StateError('durable memory claims require one to three provenance references; consolidation required')
    for ref in value:
        if not isinstance(ref, dict) or set(ref) != {'kind', 'ref'} or not all(isinstance(ref[k], str) and ref[k].strip() for k in ref):
            raise StateError('provenance must contain non-empty kind and ref')
        if not re.search(r'[A-Za-z0-9]', ref['ref']):
            raise StateError('provenance references must contain useful text')
        if any(token in ref['ref'].lower() for token in ('password=', 'token=', 'secret=')):
            raise StateError('provenance reference contains a secret-like value')


def validate_memory(memory, legacy_ids=None):
    if not isinstance(memory, dict) or set(memory) != {'hot', 'journal', 'cold', 'audit'}:
        raise StateError('invalid v2 memory shape')
    hot = memory['hot']
    if not isinstance(hot, dict) or set(hot) - (HOT_FIELDS | {'updated_at'}):
        raise StateError('invalid hot memory fields')
    for key in ('focus', 'model'):
        if key in hot and not isinstance(hot[key], str):
            raise StateError(f'hot.{key} must be text')
    for key in ('files', 'source_ids'):
        if key in hot and (not isinstance(hot[key], list) or any(not isinstance(x, str) for x in hot[key])):
            raise StateError(f'hot.{key} must be an array of strings')
    if not isinstance(hot.get('updated_at'), str):
        raise StateError('hot.updated_at must be a host timestamp')
    if _json_bytes(hot) > 4096:
        raise StateError('hot memory exceeds 4096 bytes; consolidation required')
    ids = set()
    if not isinstance(memory['journal'], list) or not isinstance(memory['cold'], list):
        raise StateError('memory journal and cold must be arrays')
    legacy_ids = set(legacy_ids or [])
    for collection, statuses, label in ((memory['journal'], JOURNAL_STATUSES, 'journal'), (memory['cold'], COLD_STATUSES, 'cold')):
        if not isinstance(collection, list):
            raise StateError(f'memory.{label} must be an array')
        for item in collection:
            if not isinstance(item, dict):
                raise StateError(f'{label} entries must be objects')
            required = {'id', 'category', 'text', 'status', 'scope', 'created_at', 'updated_at', 'provenance', 'supersedes', 'superseded_by'}
            if not required.issubset(item) or not isinstance(item['id'], str) or not item['id']:
                raise StateError(f'{label} entry is incomplete')
            if item['id'] in ids:
                raise StateError('duplicate memory ID')
            ids.add(item['id'])
            if not isinstance(item.get('category'), str) or item['category'] not in MEMORY_CATEGORIES:
                raise StateError(f'invalid {label} category or status')
            if not isinstance(item.get('status'), str) or item['status'] not in statuses:
                raise StateError(f'invalid {label} category or status')
            if not isinstance(item['text'], str) or not item['text'].strip():
                raise StateError('memory claim text must be non-empty')
            if _authored_bytes(item) > (600 if label == 'journal' else 1024):
                raise StateError(f'{label} entry exceeds its byte budget; consolidation required')
            if not isinstance(item.get('scope'), str) or item['scope'] not in {'task', 'workspace'}:
                raise StateError('memory scope must be task or workspace')
            if item['scope'] == 'workspace':
                raise StateError('workspace memory is a milestone 2 feature')
            if not all(_utc_timestamp(item.get(k)) for k in ('created_at', 'updated_at')):
                raise StateError('memory timestamps must be host strings')
            if not isinstance(item['supersedes'], list) or not all(isinstance(x, str) for x in item['supersedes']):
                raise StateError('supersedes must be an array of IDs')
            if item['superseded_by'] is not None and not isinstance(item['superseded_by'], str):
                raise StateError('superseded_by must be an ID or null')
            if label == 'journal' and item['supersedes']:
                raise StateError('journal entries cannot supersede claims')
            if item['category'] in {'decisions', 'discoveries'} and label == 'journal' and not item['provenance'] and item.get('unverified') is not True:
                raise StateError('unverified journal decisions/discoveries must be marked unverified')
            _validate_provenance(item['provenance'], item['category'] in {'decisions', 'discoveries'} and label == 'cold')
    if sum(1 for item in memory['journal'] if item['status'] == 'pending') > 30:
        raise StateError('more than 30 pending journal entries; consolidation required')
    if not isinstance(memory['audit'], list):
        raise StateError('memory.audit must be an array')
    cold_by_id = {item['id']: item for item in memory['cold']}
    for item in memory['cold']:
        for target_id in item['supersedes']:
            if isinstance(target_id, str) and target_id.startswith('legacy:'):
                if target_id[7:] not in legacy_ids:
                    raise StateError('legacy supersession target does not exist')
                continue
            target = cold_by_id.get(target_id)
            if not target or target['scope'] != item['scope']:
                raise StateError('supersession target must exist in the same scope')
            if target['superseded_by'] != item['id']:
                raise StateError('supersession links must be symmetric')
        if item['superseded_by'] is not None:
            replacement = cold_by_id.get(item['superseded_by'])
            if not replacement or item['id'] not in replacement['supersedes'] or replacement['scope'] != item['scope']:
                raise StateError('supersession links must be symmetric')
    visiting, visited = set(), set()
    def visit(item_id):
        if item_id in visiting:
            raise StateError('cyclic memory supersession')
        if item_id in visited:
            return
        visiting.add(item_id)
        for parent_id in cold_by_id[item_id]['supersedes']:
            if not parent_id.startswith('legacy:'):
                visit(parent_id)
        visiting.remove(item_id); visited.add(item_id)
    for item_id in cold_by_id:
        visit(item_id)
    event_ids = set()
    for event in memory['audit']:
        if not isinstance(event, dict) or not isinstance(event.get('id'), str) or not isinstance(event.get('event_id'), str) or not _utc_timestamp(event.get('at')):
            raise StateError('invalid memory audit event')
        if event['event_id'] in event_ids:
            raise StateError('duplicate memory event ID')
        event_ids.add(event['event_id'])


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


def resolve_task_id(root, task_id):
    """Expand an unambiguous prefix (6+ chars) of an existing task ID to the full ID."""
    if not task_id or (root / 'tasks' / task_id).exists() or len(task_id) < 6:
        return task_id
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', task_id):
        return task_id
    matches = sorted(p.name for p in (root / 'tasks').glob(task_id + '*') if p.is_dir())
    if len(matches) > 1:
        raise StateError(f'ambiguous task ID prefix {task_id}: ' + ', '.join(matches))
    return matches[0] if matches else task_id


def canonical_project(project):
    """Return the identity used for workspace memory (including symlink resolution)."""
    return str(Path(project).expanduser().resolve())


def workspace_path(root, project):
    canonical = canonical_project(project)
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return root / 'workspaces' / digest


def _workspace_default(project):
    return {'schema_version': 1, 'project': canonical_project(project), 'revision': 1,
            'items': [], 'audit': []}


def validate_workspace(record, project=None):
    if not isinstance(record, dict) or set(record) != {'schema_version', 'project', 'revision', 'items', 'audit'}:
        raise StateError('invalid workspace memory shape')
    if record.get('schema_version') != 1 or not isinstance(record.get('project'), str):
        raise StateError('invalid workspace memory header')
    if project is not None and record['project'] != canonical_project(project):
        raise StateError('workspace project identity mismatch')
    if type(record.get('revision')) is not int or record['revision'] < 1:
        raise StateError('workspace revision must be a positive integer')
    ids = set()
    for item in record['items']:
        if not isinstance(item, dict):
            raise StateError('workspace entries must be objects')
        required = {'id', 'category', 'text', 'status', 'scope', 'project', 'task_id', 'origin',
                    'created_at', 'updated_at', 'provenance', 'supersedes', 'superseded_by'}
        if not required.issubset(item) or not isinstance(item['id'], str) or not item['id']:
            raise StateError('workspace entry is incomplete')
        if item['id'] in ids:
            raise StateError('duplicate workspace memory ID')
        ids.add(item['id'])
        if not isinstance(item.get('scope'), str) or item['scope'] != 'workspace' or not isinstance(item.get('project'), str) or item['project'] != record['project']:
            raise StateError('workspace entry has the wrong scope or project')
        if not isinstance(item.get('category'), str) or not isinstance(item.get('status'), str):
            raise StateError('workspace category and status must be strings')
        if item['category'] not in MEMORY_CATEGORIES or item['status'] not in COLD_STATUSES:
            raise StateError('invalid workspace category or status')
        if not isinstance(item['text'], str) or not item['text'].strip():
            raise StateError('memory claim text must be non-empty')
        if _authored_bytes(item) > 1024:
            raise StateError('workspace entry exceeds its byte budget; consolidation required')
        if not isinstance(item['task_id'], str) or not isinstance(item['origin'], dict) or set(item['origin']) != {'task_id', 'item_id'}:
            raise StateError('workspace entries require task provenance origin')
        if item['origin']['task_id'] != item['task_id'] or not all(isinstance(item['origin'].get(k), str) and item['origin'][k] for k in ('task_id', 'item_id')):
            raise StateError('workspace origin must identify its source task item')
        if not all(_utc_timestamp(item.get(k)) for k in ('created_at', 'updated_at')):
            raise StateError('workspace timestamps must be host strings')
        if not isinstance(item['supersedes'], list) or not all(isinstance(x, str) for x in item['supersedes']):
            raise StateError('supersedes must be an array of IDs')
        if item['superseded_by'] is not None and not isinstance(item['superseded_by'], str):
            raise StateError('superseded_by must be an ID or null')
        _validate_provenance(item['provenance'], item['category'] in {'decisions', 'discoveries'})
    origins = set()
    by_id = {item['id']: item for item in record['items']}
    for item in record['items']:
        origin = (item['origin']['task_id'], item['origin']['item_id'])
        if origin in origins:
            raise StateError('duplicate workspace origin')
        origins.add(origin)
        for old_id in item['supersedes']:
            old = by_id.get(old_id)
            if not old or old['scope'] != item['scope'] or old['category'] != item['category']:
                raise StateError('workspace supersession links must be symmetric and same-scope')
            if old['status'] != 'withdrawn' and old['superseded_by'] != item['id']:
                raise StateError('workspace supersession links must be symmetric and same-scope')
        if item['superseded_by'] is not None:
            new = by_id.get(item['superseded_by'])
            if not new or item['id'] not in new['supersedes']:
                raise StateError('workspace supersession links must be symmetric')
    if not isinstance(record['audit'], list):
        raise StateError('workspace audit must be an array')
    event_ids = set()
    for event in record['audit']:
        if not isinstance(event, dict) or not isinstance(event.get('id'), str) or not isinstance(event.get('event_id'), str) or not _utc_timestamp(event.get('at')):
            raise StateError('invalid workspace audit event')
        if event['event_id'] in event_ids:
            raise StateError('duplicate workspace event ID')
        event_ids.add(event['event_id'])


def load_workspace(path, project=None):
    if path.is_symlink():
        raise StateError('workspace directory must not be a symlink')
    source = path / 'memory.json'
    if not source.exists():
        raise StateError('workspace memory does not exist')
    record = json.loads(source.read_text())
    validate_workspace(record, project)
    return record


def workspace_current(root, project):
    """Return only current claims for this canonical project."""
    path = workspace_path(root, project)
    if not (path / 'memory.json').exists():
        return []
    record = load_workspace(path, project)
    return [item for item in record['items'] if item['status'] == 'current']


def save_workspace(path, record):
    if path.is_symlink():
        raise StateError('workspace directory must not be a symlink')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    validate_workspace(record)
    atomic_write(path / 'memory.json', json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


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
    if not isinstance(state, dict) or state.get('schema_version') not in {1, 2} or state.get('id') != path.name:
        raise StateError(f'unsupported task record: {source}')
    if type(state.get('revision')) is not int or not isinstance(state.get('details'), dict):
        raise StateError(f'invalid task record: {source}')
    required = {'title', 'project', 'conversation', 'created_at', 'updated_at', 'owner',
                'status', 'archived_at', 'selection', 'choice_events', 'ownership_events'}
    if not required.issubset(state) or not isinstance(state['status'], str) or state['status'] not in STATUSES:
        raise StateError(f'incomplete task record: {source}')
    missing_details = set(DETAIL_DEFAULTS) - set(state['details'])
    if missing_details - {'phase'}:  # phase is optional for records written before it existed
        raise StateError(f'incomplete task details: {source}')
    if not isinstance(state['choice_events'], list) or not isinstance(state['ownership_events'], list):
        raise StateError(f'invalid task history: {source}')
    for event in state['choice_events']:
        if not isinstance(event, dict) or not all(isinstance(event.get(k), str) for k in ('id', 'at', 'task_id')):
            raise StateError(f'invalid choice event: {source}')
        validate_pool(event.get('pool'))
    validate_details(state['details'])
    if state['schema_version'] == 2:
        legacy_ids = []
        for note in state['details'].get('notes', []):
            if isinstance(note, dict):
                for key in ('id', 'key'):
                    if isinstance(note.get(key), str):
                        legacy_ids.append(note[key])
        validate_memory(state.get('memory'), legacy_ids)
        for item in state['memory']['journal'] + state['memory']['cold']:
            if item.get('task_id') != state['id']:
                raise StateError('task memory entry names the wrong parent task')
    return state


def markdown(state):
    lines = [f"# {state['title']}", '',
             '<!-- Generated from state.json; use coord_state.py to update. -->', '',
             f"Task: {state['id']} | Status: {state['status']} | Revision: {state['revision']}",
             f"Project: {state['project']}", f"Updated: {state['updated_at']}",
             f"Owner: {state['owner'] or 'unclaimed'}", '', '## Harness/model selection', '',
             json.dumps(state['selection'], ensure_ascii=False, indent=2), '']
    for name, value in state['details'].items():
        heading = 'Legacy unclassified history' if name == 'notes' else name.replace('_', ' ').title()
        lines.extend([f"## {heading}", '',
                      value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2), ''])
    if state.get('schema_version') == 2:
        lines.extend(['## Memory hot projection', '', json.dumps(state['memory']['hot'], ensure_ascii=False, indent=2), ''])
        if state['memory']['journal']:
            lines.extend(['## Pending journal', '',
                          json.dumps(state['memory']['journal'], ensure_ascii=False, indent=2), ''])
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


def bindings_path(root):
    return root / 'session-bindings.json'


def _load_bindings(root):
    path = bindings_path(root)
    if not path.exists():
        return {'schema_version': 1, 'bindings': {}}
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or value.get('schema_version') != 1 or not isinstance(value.get('bindings'), dict):
        raise StateError('invalid session bindings record')
    return value


def _save_bindings(root, value):
    root.mkdir(parents=True, exist_ok=True)
    atomic_write(bindings_path(root), json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def session_nonce():
    return 'coord-nonce-' + uuid.uuid4().hex[:16]


def _find_transcript(projects_dir, nonce):
    candidates = sorted(projects_dir.glob('*/*.jsonl'), key=lambda path: path.stat().st_mtime_ns, reverse=True)[:50]
    matches = []
    needle = nonce.encode('utf-8')
    for candidate in candidates:
        try:
            size = candidate.stat().st_size
            with candidate.open('rb') as stream:
                stream.seek(max(0, size - 256 * 1024))
                if needle in stream.read():
                    matches.append((candidate, size))
        except OSError:
            continue
    if not matches:
        raise StateError(f'no Claude transcript contains nonce {nonce}')
    if len(matches) > 1:
        raise StateError(f'multiple Claude transcripts contain nonce {nonce}; refusing to guess')
    return matches[0]


def bind_session(args, root):
    session_id = args.session_id
    transcript = None
    if session_id == 'auto':
        if not getattr(args, 'nonce', None):
            raise StateError('--nonce is required with --session-id auto')
        transcript, size = _find_transcript(Path(getattr(args, 'projects_dir', None) or Path.home() / '.claude/projects'), args.nonce)
        session_id = transcript.stem
    path = task_path(root, args.task)
    with locked(path / '.write.lock'):
        task = load(path); check_owner(task, args.owner); check_revision(task, args.revision)
        with locked(root / '.bindings.lock'):
            bindings = _load_bindings(root)
            key = f'claude:{session_id}'
            prior = bindings['bindings'].get(key)
            if prior and (prior.get('task_id') != args.task or prior.get('owner') != args.owner):
                raise StateError('session binding is owned by another coordinator')
            bindings['bindings'][key] = {'task_id': args.task, 'owner': args.owner,
                'revision': args.revision + 1, 'harness': 'claude', 'session_id': session_id,
                'transcript_offset': prior.get('transcript_offset', 0) if prior else (size if transcript else 0),
                'transcript_path': prior.get('transcript_path') if prior else (str(transcript) if transcript else None)}
            _save_bindings(root, bindings)
        task['revision'] += 1; task['updated_at'] = now(); warnings = save(path, task)
    return response(path, task, warnings)


def unbind_session(args, root):
    path = task_path(root, args.task)
    with locked(path / '.write.lock'):
        task = load(path); check_owner(task, args.owner); check_revision(task, args.revision)
        with locked(root / '.bindings.lock'):
            bindings = _load_bindings(root)
            key = f'claude:{args.session_id}'
            prior = bindings['bindings'].get(key)
            if prior and (prior.get('task_id') != args.task or prior.get('owner') != args.owner):
                raise StateError('binding is owned by another coordinator')
            bindings['bindings'].pop(key, None); _save_bindings(root, bindings)
        task['revision'] += 1; task['updated_at'] = now(); warnings = save(path, task)
    return response(path, task, warnings)


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


def validate_lessons(notes):
    # Checked on write only, so older free-form incident notes stay loadable.
    for note in notes if isinstance(notes, list) else []:
        if not isinstance(note, dict) or note.get('kind') != 'incident':
            continue
        if 'key' in note and not (isinstance(note['key'], str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', note['key'])):
            raise StateError('incident key must be a lowercase slug')
        if 'scope' in note and note['scope'] not in LESSON_SCOPES:
            raise StateError('incident scope must be host, general, or one-off')


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
    if state.get('schema_version') == 2 and 'notes' in details:
        old_notes = state['details'].get('notes', [])
        new_notes = details['notes']
        if not isinstance(new_notes, list) or new_notes[:len(old_notes)] != old_notes:
            raise StateError('legacy notes are append-only after v2 import')
    merged = dict(state['details'], **details)
    validate_details(merged)
    validate_lessons(details.get('notes', []))
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


def upgrade_memory(state):
    if state['schema_version'] == 2:
        return
    state['schema_version'] = 2
    state['memory'] = _memory_default()
    notes = state['details'].get('notes', [])
    state['memory']['audit'].append({'id': uuid.uuid4().hex, 'at': now(),
        'event_id': 'legacy-import:' + uuid.uuid4().hex, 'action': 'legacy-import',
        'item_id': None, 'actor': 'host', 'before': {'schema_version': 1,
        'details_ref': 'state.json#details', 'notes_ref': 'state.json#details.notes'},
        'after': {'notes_count': len(notes), 'notes_sha256': hashlib.sha256(json.dumps(notes, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}})


def _action_fingerprint(action):
    return json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _prepare_actions(actions, audit):
    groups = {}
    order = []
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get('event_id'), str) or not action['event_id'].strip():
            raise StateError('every memory action requires an event_id')
        event_id = action['event_id']
        if event_id not in groups:
            groups[event_id] = []
            order.append(event_id)
        groups[event_id].append(action)
    existing = {event['event_id']: event for event in audit}
    normalized, payloads, skipped = [], {}, set()
    for event_id in order:
        group = groups[event_id]
        payload = _action_fingerprint(group if len(group) > 1 else group[0])
        payloads[event_id] = payload
        prior = existing.get(event_id)
        if prior:
            if prior.get('payload') != payload:
                raise StateError('event ID was previously used with a different payload')
            skipped.add(event_id)
            continue
        for number, action in enumerate(group):
            copy = dict(action)
            if number:
                copy['_part'] = number
            normalized.append(copy)
    return normalized, payloads, skipped


def _new_memory_item(action, state, kind):
    category = action.get('category')
    if not isinstance(category, str) or category not in MEMORY_CATEGORIES:
        raise StateError('invalid memory category')
    scope = action.get('scope', 'task')
    if not isinstance(scope, str):
        raise StateError('memory scope must be task or workspace')
    if scope == 'workspace':
        raise StateError('workspace memory is a milestone 2 feature')
    if scope != 'task':
        raise StateError('memory scope must be task or workspace')
    text = action.get('text')
    if not isinstance(text, str) or not text.strip():
        raise StateError('memory claim text must be non-empty')
    provenance = action.get('provenance')
    _validate_provenance(provenance, category in {'decisions', 'discoveries'} and kind == 'cold-add')
    supersedes = action.get('supersedes', [])
    if not isinstance(supersedes, list) or not all(isinstance(x, str) for x in supersedes):
        raise StateError('supersedes must be an array of IDs')
    if kind == 'journal' and supersedes:
        raise StateError('journal entries cannot supersede claims')
    if kind == 'journal' and category in {'decisions', 'discoveries'} and not provenance and action.get('unverified') is not True:
        raise StateError('unverified journal decisions/discoveries must be marked unverified')
    item = {'id': uuid.uuid4().hex, 'category': category, 'text': text, 'status': 'pending' if kind == 'journal' else 'current',
            'scope': scope, 'task_id': state['id'], 'created_at': now(), 'updated_at': now(),
            'provenance': provenance or [], 'supersedes': supersedes, 'superseded_by': None}
    if kind == 'journal' and category in {'decisions', 'discoveries'} and not provenance:
        item['unverified'] = True
    if _authored_bytes(item) > (600 if kind == 'journal' else 1024):
        raise StateError(f'{kind} entry exceeds its byte budget; consolidation required')
    return item


def _memory_audit(memory, event_id, action, before, after):
    memory['audit'].append({'id': uuid.uuid4().hex, 'at': now(), 'event_id': event_id,
                            'action': action.get('action'), 'item_id': after.get('id') if isinstance(after, dict) else None,
                            'actor': 'sidecar', 'before': before, 'after': after,
                            'payload': _action_fingerprint(action)})


def apply_memory_actions(state, proposal, owner):
    if not isinstance(proposal, dict) or not isinstance(proposal.get('actions'), list):
        raise StateError('actions file must contain an actions array')
    if proposal.get('task_id') not in (None, state['id']):
        raise StateError('actions task ID does not match record')
    memory = json.loads(json.dumps(state['memory']))
    actions, payloads, skipped = _prepare_actions(proposal['actions'], memory['audit'])
    seen = set()
    event_effects = {}
    batch_audit_start = len(memory['audit'])
    for action in actions:
        event_id = action['event_id']
        seen.add(event_id)
        base_event_id = event_id
        event_effects.setdefault(base_event_id, False)
        audit_count = len(memory['audit'])
        operation = action.get('action')
        if operation == 'ignore':
            if not isinstance(action.get('reason'), str) or not action['reason'].strip():
                raise StateError('ignore requires a reason')
            _memory_audit(memory, event_id, action, None, {'reason': action['reason']})
        elif operation == 'hot-update':
            if set(action) - {'action', 'event_id', '_part', 'focus', 'model', 'files', 'source_ids'}:
                raise StateError('hot-update cannot modify operational task fields')
            hot_changes = {key: action[key] for key in HOT_FIELDS if key in action}
            if not hot_changes or any(not isinstance(value, (str, list)) or (isinstance(value, list) and any(not isinstance(x, str) for x in value)) for value in hot_changes.values()) or ('focus' in hot_changes and not hot_changes['focus'].strip()):
                raise StateError('hot-update fields must be non-empty strings or string arrays')
            before = {key: memory['hot'].get(key) for key in hot_changes}
            memory['hot'].update(hot_changes)
            memory['hot']['updated_at'] = now()
            if any(source_id not in {item['id'] for item in memory['journal'] + memory['cold']} for source_id in memory['hot'].get('source_ids', [])):
                raise StateError('hot source_ids must reference memory items')
            _memory_audit(memory, event_id, action, before, {key: memory['hot'][key] for key in hot_changes})
        elif operation == 'journal' and 'journal_ids' in action:
            if set(action) - {'action', 'event_id', '_part', 'journal_ids', 'disposition', 'destination'}:
                raise StateError('journal disposition has invalid fields')
            ids = action.get('journal_ids')
            if not isinstance(ids, list) or not ids or not isinstance(action.get('disposition'), str) or action.get('disposition') not in {'consolidated', 'discarded'}:
                raise StateError('journal disposition requires journal_ids and a disposition')
            if len(ids) != len(set(ids)):
                raise StateError('journal_ids must not contain duplicates')
            for item_id in ids:
                item = next((x for x in memory['journal'] if x['id'] == item_id and x['status'] == 'pending'), None)
                if not item:
                    raise StateError('journal disposition target must be pending')
                item['status'] = action['disposition']; item['updated_at'] = now()
            _memory_audit(memory, event_id, action, {'journal_ids': ids}, {'disposition': action['disposition'], 'destination': action.get('destination')})
        elif operation in {'journal', 'cold-add'}:
            if set(action) - {'action', 'event_id', '_part', 'category', 'scope', 'text', 'provenance', 'supersedes', 'unverified', 'id', 'created_at', 'updated_at'}:
                raise StateError(f'{operation} has invalid fields')
            item = _new_memory_item(action, state, operation)
            target = memory['journal'] if operation == 'journal' else memory['cold']
            if operation == 'cold-add' and item['supersedes']:
                for old_id in item['supersedes']:
                    if old_id.startswith('legacy:'):
                        continue
                    old = next((x for x in memory['cold'] if x['id'] == old_id), None)
                    if not old or old['scope'] != item['scope'] or old['category'] != item['category'] or old['status'] != 'current':
                        raise StateError('supersession target must be a current same-scope cold item')
                    old['status'] = 'superseded'; old['superseded_by'] = item['id']; old['updated_at'] = now()
            target.append(item)
            _memory_audit(memory, event_id, action, None, item)
        elif operation == 'cold-update':
            if set(action) - {'action', 'event_id', '_part', 'id', 'disposition', 'reason', 'provenance'}:
                raise StateError('cold-update cannot modify immutable claim fields')
            item = next((x for x in memory['cold'] if x['id'] == action.get('id')), None)
            if not item:
                raise StateError('cold-update target does not exist')
            if item['status'] == 'superseded':
                raise StateError('superseded claims are immutable; create a new replacement')
            if not isinstance(action.get('disposition'), str) or action.get('disposition') not in {'current', 'withdrawn'}:
                raise StateError('cold-update disposition must be current or withdrawn')
            if item['status'] == 'withdrawn' and action.get('disposition') == 'current':
                raise StateError('withdrawn claims are terminal')
            if action.get('provenance') is not None:
                _validate_provenance(action['provenance'], item['category'] in {'decisions', 'discoveries'})
            if item['status'] == action['disposition']:
                continue
            if action.get('disposition') == 'withdrawn' and (not isinstance(action.get('reason'), str) or not action['reason'].strip()):
                raise StateError('withdrawing a claim requires a reason')
            before = {'status': item['status']}
            item['status'] = action['disposition']; item['updated_at'] = now()
            _memory_audit(memory, event_id, action, before, {'status': item['status'], 'reason': action.get('reason'), 'provenance': action.get('provenance')})
        elif operation == 'supersede':
            old = next((x for x in memory['cold'] if x['id'] == action.get('old_id')), None)
            replacement = action.get('replacement')
            if not old or old['status'] != 'current' or not isinstance(replacement, dict):
                raise StateError('supersede requires a current cold item and replacement')
            if replacement.get('scope', 'task') != old['scope'] or replacement.get('category') != old['category']:
                raise StateError('supersession must stay in the same scope and category')
            new_action = dict(replacement, action='cold-add')
            new_item = _new_memory_item(new_action, state, 'cold-add')
            new_item['supersedes'] = [old['id']]
            old['status'] = 'superseded'; old['superseded_by'] = new_item['id']; old['updated_at'] = now()
            memory['cold'].append(new_item)
            _memory_audit(memory, event_id, action, {'id': old['id'], 'status': 'current'}, {'id': new_item['id'], 'category': new_item['category'], 'text': new_item['text'], 'provenance': new_item['provenance'], 'supersedes': [old['id']]})
        else:
            raise StateError('unknown memory action')
        if len(memory['audit']) > audit_count:
            event_effects[base_event_id] = True
    grouped_ids = {event_id for event_id in payloads
                   if len([a for a in proposal['actions'] if a['event_id'] == event_id]) > 1}
    if grouped_ids:
        created = memory['audit'][batch_audit_start:]
        memory['audit'] = memory['audit'][:batch_audit_start]
        memory['audit'].extend(event for event in created if event['event_id'] not in grouped_ids)
        for event_id, payload in payloads.items():
            if event_id not in grouped_ids or event_id in skipped or not event_effects.get(event_id):
                continue
            memory['audit'].append({'id': uuid.uuid4().hex, 'at': now(), 'event_id': event_id,
                'action': 'batch', 'item_id': None, 'actor': 'sidecar', 'before': None,
                'after': {'parts': len([a for a in proposal['actions'] if a['event_id'] == event_id])},
                'payload': payload})
    validate_memory(memory, [note.get(key) for note in state['details'].get('notes', []) if isinstance(note, dict) for key in ('id', 'key') if isinstance(note.get(key), str)])
    state['memory'] = memory
    return any(event_effects.values())


def _memory_replay(state, proposal):
    if state.get('schema_version') != 2 or not isinstance(proposal, dict) or not isinstance(proposal.get('actions'), list):
        return False
    try:
        _, payloads, skipped = _prepare_actions(proposal['actions'], state['memory']['audit'])
    except StateError:
        return False
    return len(payloads) > 0 and len(skipped) == len(payloads)


def _workspace_actions(proposal):
    if not isinstance(proposal, dict) or not isinstance(proposal.get('actions'), list):
        return []
    return [action for action in proposal['actions']
            if isinstance(action, dict) and ((action.get('action') == 'cold-add' and action.get('scope') == 'workspace')
                                             or (action.get('action') == 'supersede' and isinstance(action.get('replacement'), dict)
                                                 and action['replacement'].get('scope') == 'workspace'))]


def _workspace_delivery_state(root, project, intents):
    path = workspace_path(root, project)
    if not (path / 'memory.json').exists():
        return 'missing'
    workspace = load_workspace(path, project)
    for intent in intents:
        existing = next((item for item in workspace['items'] if item['origin'] == intent['origin']), None)
        if not existing:
            return 'missing'
        if existing['text'] != intent['text'] or existing['category'] != intent['category']:
            return 'collision'
    return 'intact'


def _missing_workspace_origin(root, project, intents):
    path = workspace_path(root, project)
    if not (path / 'memory.json').exists():
        return intents[0]['origin'] if intents else None
    workspace = load_workspace(path, project)
    for intent in intents:
        if not any(item['origin'] == intent['origin'] for item in workspace['items']):
            return intent['origin']
    return None


def _validate_promotion_targets(root, project, actions, state=None):
    targets = []
    for action in actions:
        source = action.get('replacement', action)
        supersedes = source.get('supersedes', []) if isinstance(source, dict) else []
        if action.get('action') == 'supersede':
            supersedes = [action.get('old_id')]
        if not isinstance(supersedes, list) or len(supersedes) > 8:
            raise StateError('workspace supersedes accepts at most 8 IDs')
        targets.extend(supersedes)
    if not targets:
        return
    path = workspace_path(root, project)
    if not (path / 'memory.json').exists():
        raise StateError('workspace supersession target does not exist')
    workspace = load_workspace(path, project)
    by_id = {item['id']: item for item in workspace['items']}
    intents = {}
    if state is not None:
        intents = {event.get('source_event_id'): event.get('after')
                   for event in state['memory']['audit'] if event.get('action') == 'promotion-intent'}
    for action in actions:
        source = action.get('replacement', action)
        action_targets = source.get('supersedes', []) if isinstance(source, dict) else []
        if action.get('action') == 'supersede':
            action_targets = [action.get('old_id')]
        intent = intents.get(action.get('event_id'))
        origin = intent.get('origin') if isinstance(intent, dict) else None
        for target in action_targets:
            item = by_id.get(target)
            if not item:
                raise StateError('workspace supersession target does not exist')
            if item['status'] in {'current', 'withdrawn'}:
                continue
            successor = by_id.get(item.get('superseded_by'))
            if (item['status'] == 'superseded' and successor and origin
                    and successor.get('origin') == origin):
                continue
            raise StateError('workspace supersession target does not exist')


def _promotion_intents(state, actions):
    """Return persisted intents, creating host IDs but never trusting model IDs."""
    intents = []
    for action in actions:
        if set(action) - {'action', 'event_id', 'category', 'scope', 'text', 'provenance', 'supersedes', 'unverified', 'id', 'created_at', 'updated_at', 'old_id', 'replacement'}:
            raise StateError('workspace cold-add has invalid fields')
        if not isinstance(action.get('event_id'), str) or not action['event_id'].strip():
            raise StateError('every memory action requires an event_id')
        source = action.get('replacement', action)
        if not isinstance(source, dict) or source.get('category') not in MEMORY_CATEGORIES or not isinstance(source.get('text'), str) or not source['text'].strip():
            raise StateError('invalid workspace memory claim')
        _validate_provenance(source.get('provenance'), True)
        payload = _action_fingerprint(action)
        existing = next((event for event in state['memory']['audit']
                         if event.get('action') == 'promotion-intent' and event.get('source_event_id') == action['event_id']), None)
        if existing:
            if existing.get('source_payload') != payload:
                raise StateError('event ID was previously used with a different payload')
            intents.append(existing['after'])
            continue
        origin = {'task_id': state['id'], 'item_id': uuid.uuid4().hex}
        after = {'origin': origin, 'category': source['category'], 'text': source['text'],
                 'provenance': source.get('provenance') or [], 'supersedes': source.get('supersedes', [])}
        if action.get('action') == 'supersede':
            if not isinstance(action.get('old_id'), str) or action['old_id'] in after['supersedes']:
                raise StateError('workspace supersede requires a distinct old_id')
            after['supersedes'] = [action['old_id']]
            after['operation'] = 'supersede'
        if _authored_bytes(after) > 1024:
            raise StateError('workspace entry exceeds its byte budget; consolidation required')
        state['memory']['audit'].append({'id': uuid.uuid4().hex, 'at': now(),
            'event_id': 'promotion-intent:' + action['event_id'], 'action': 'promotion-intent',
            'item_id': origin['item_id'], 'actor': 'sidecar', 'before': None, 'after': after,
            'source_event_id': action['event_id'], 'source_payload': payload})
        intents.append(after)
    return intents


def _promote_workspace(root, state, actions, actor):
    """Apply workspace writes after the task lock has been released."""
    path = workspace_path(root, state['project'])
    if path.is_symlink():
        raise StateError('workspace directory must not be a symlink')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    with locked(path / '.write.lock'):
        if (path / 'memory.json').exists():
            workspace = load_workspace(path, state['project'])
        else:
            workspace = _workspace_default(state['project'])
        changed = False
        for action in actions:
            intent = next(event['after'] for event in state['memory']['audit']
                          if event.get('action') == 'promotion-intent' and event.get('source_event_id') == action['event_id'])
            origin = intent['origin']
            existing = next((item for item in workspace['items']
                             if item['origin'] == origin), None)
            if existing:
                if existing['text'] != intent['text'] or existing['category'] != intent['category']:
                    raise StateError('workspace origin already has a different claim')
                continue
            item = {'id': uuid.uuid4().hex, 'category': intent['category'], 'text': intent['text'],
                    'status': 'current', 'scope': 'workspace', 'project': workspace['project'],
                    'task_id': state['id'], 'origin': origin, 'created_at': now(), 'updated_at': now(),
                    'provenance': intent['provenance'], 'supersedes': intent['supersedes'], 'superseded_by': None}
            if item['supersedes']:
                for old_id in item['supersedes']:
                    old = next((candidate for candidate in workspace['items'] if candidate['id'] == old_id), None)
                    if not old or old['scope'] != 'workspace' or old['category'] != item['category'] or old['status'] not in {'current', 'withdrawn'}:
                        raise StateError('supersession target must be a current or withdrawn same-scope workspace item')
                    if old['status'] == 'current':
                        old['status'] = 'superseded'; old['superseded_by'] = item['id']; old['updated_at'] = now()
            workspace['items'].append(item)
            event_id = 'promotion:' + origin['task_id'] + ':' + origin['item_id']
            if any(event.get('event_id') == event_id for event in workspace['audit']):
                event_id = 'promotion-reconcile:' + origin['task_id'] + ':' + origin['item_id'] + ':' + uuid.uuid4().hex
            workspace['audit'].append({'id': uuid.uuid4().hex, 'at': now(),
                'event_id': event_id,
                'action': 'cold-add', 'item_id': item['id'], 'actor': actor,
                'before': None, 'after': item})
            changed = True
        if changed:
            workspace['revision'] += 1
            validate_workspace(workspace)
            save_workspace(path, workspace)
        return workspace


def _record_promotion_delivery(root, state, actions, workspace):
    path = task_path(root, state['id'])
    with locked(path / '.write.lock'):
        current = load(path)
        check_owner(current, state['owner'])
        for action in actions:
            intent = next(event for event in current['memory']['audit']
                          if event.get('action') == 'promotion-intent' and event.get('source_event_id') == action['event_id'])
            delivery_id = 'promotion-delivery:' + intent['after']['origin']['item_id']
            if any(event.get('event_id') == delivery_id for event in current['memory']['audit']):
                continue
            item = next((candidate for candidate in workspace['items'] if candidate['origin'] == intent['after']['origin'] and candidate['status'] == 'current'), None)
            if not item:
                raise StateError('workspace promotion was not delivered; retry reconciliation')
            current['memory']['audit'].append({'id': uuid.uuid4().hex, 'at': now(),
                'event_id': delivery_id, 'action': 'promotion-delivered', 'item_id': item['id'],
                'actor': 'host', 'before': None, 'after': {'workspace_revision': workspace['revision'], 'workspace_id': item['id']}})
        current['revision'] += 1
        current['updated_at'] = now()
        validate_memory(current['memory'], [note.get(key) for note in current['details'].get('notes', []) if isinstance(note, dict) for key in ('id', 'key') if isinstance(note.get(key), str)])
        save(path, current)
        return current


def promote_memory(root, args, proposal):
    path = task_path(root, args.task)
    promotions = _workspace_actions(proposal)
    with locked(path / '.write.lock'):
        current = load(path)
        replay_local = dict(proposal, actions=[a for a in proposal.get('actions', []) if a not in promotions])
        local_replayed = not replay_local['actions'] or _memory_replay(current, replay_local)
        if args.revision != 'latest' and args.revision != current['revision'] and promotions and local_replayed:
            delivered = True
            for action in promotions:
                intent = next((event for event in current.get('memory', {}).get('audit', [])
                               if event.get('action') == 'promotion-intent' and event.get('source_event_id') == action.get('event_id')),
                               None)
                if not intent or intent.get('source_payload') != _action_fingerprint(action):
                    delivered = False; break
                origin_id = intent.get('after', {}).get('origin', {}).get('item_id')
                if not any(event.get('action') == 'promotion-delivered' and event.get('event_id') == 'promotion-delivery:' + origin_id
                           for event in current.get('memory', {}).get('audit', [])):
                    delivered = False; break
                delivery_state = _workspace_delivery_state(root, current['project'], [intent['after']])
                if delivery_state == 'collision':
                    raise StateError('workspace origin already has a different claim')
                if delivery_state == 'missing':
                    raise StateError('stale revision: delivered workspace memory is missing; reread before retrying')
            if delivered:
                check_owner(current, args.owner)
                return response(path, current)
        if args.revision == 'latest':
            check_owner(current, args.owner)
            revision = current['revision']
        else:
            check_revision(current, args.revision)
            check_owner(current, args.owner)
            revision = args.revision
        if current['archived_at']:
            raise StateError('task is archived; it cannot be mutated')
        upgrade_memory(current)
        existing_delivery_ids = {
            event.get('event_id', '').removeprefix('promotion-delivery:')
            for event in current['memory']['audit'] if event.get('action') == 'promotion-delivered'
        }
        existing_intent_ids = {
            event.get('source_event_id'): event.get('after', {}).get('origin', {}).get('item_id')
            for event in current['memory']['audit'] if event.get('action') == 'promotion-intent'
        }
        if not all(existing_intent_ids.get(action.get('event_id')) in existing_delivery_ids for action in promotions):
            _validate_promotion_targets(root, current['project'], promotions, current)
        audit_before_intents = len(current['memory']['audit'])
        intents = _promotion_intents(current, promotions)
        delivered_origins = {
            event.get('event_id', '').removeprefix('promotion-delivery:')
            for event in current['memory']['audit']
            if event.get('action') == 'promotion-delivered'
        }
        if (not any(a for a in proposal['actions'] if a not in promotions)
                and all(intent['origin']['item_id'] in delivered_origins for intent in intents)):
            delivery_state = _workspace_delivery_state(root, current['project'], intents)
            if delivery_state == 'collision':
                raise StateError('workspace origin already has a different claim')
            if delivery_state == 'intact':
                return response(path, current)
            origin = _missing_workspace_origin(root, current['project'], intents)
            raise StateError(f'workspace memory lost for origin {origin["task_id"]}/{origin["item_id"]}; not delivered')
        if promotions and all(intent['origin']['item_id'] in delivered_origins for intent in intents):
            delivery_state = _workspace_delivery_state(root, current['project'], intents)
            if delivery_state == 'collision':
                raise StateError('workspace origin already has a different claim')
            if delivery_state == 'missing':
                origin = _missing_workspace_origin(root, current['project'], intents)
                raise StateError(f'workspace memory lost for origin {origin["task_id"]}/{origin["item_id"]}; not delivered')
            if local_replayed:
                return response(path, current)
            promotions = []
        # Apply non-workspace actions in this same task transaction.
        local = dict(proposal, actions=[a for a in proposal['actions'] if a not in promotions])
        changed = len(current['memory']['audit']) != audit_before_intents
        if local['actions']:
            changed = apply_memory_actions(current, local, args.owner) or changed
        if changed:
            current['revision'] += 1
            current['updated_at'] = now()
            save(path, current)
        elif not promotions:
            return response(path, current)
    workspace = _promote_workspace(root, current, promotions, args.owner)
    delivered = _record_promotion_delivery(root, current, promotions, workspace)
    return response(path, delivered)


def demote_memory(root, args):
    path = task_path(root, args.task)
    with locked(path / '.write.lock'):
        task = load(path)
        check_revision(task, args.task_revision)
        check_owner(task, args.owner)
        if task['archived_at']:
            raise StateError('task is archived; it cannot authorize demotion')
        workspace_dir = workspace_path(root, task['project'])
        if workspace_dir.is_symlink():
            raise StateError('workspace directory must not be a symlink')
        if not (workspace_dir / 'memory.json').exists():
            raise StateError('workspace memory does not exist')
        # This is a lock-free preflight: the workspace lock is acquired only
        # after the task lock is released, preserving lock ordering.
        workspace_preflight = load_workspace(workspace_dir, task['project'])
        if not any(item.get('id') == args.item_id for item in workspace_preflight['items']):
            raise StateError('workspace item does not exist')
    with locked(workspace_dir / '.write.lock'):
        workspace = load_workspace(workspace_dir, task['project'])
        if workspace['project'] != canonical_project(task['project']):
            raise StateError('workspace project does not match caller project')
        if workspace['revision'] != args.workspace_revision:
            raise StateError(f"stale workspace revision: expected {args.workspace_revision}, current {workspace['revision']}; reread before retrying")
        item = next((candidate for candidate in workspace['items'] if candidate['id'] == args.item_id), None)
        if not item:
            raise StateError('workspace item does not exist')
        event_id = 'demote:' + args.item_id
        prior = next((event for event in workspace['audit'] if event.get('event_id') == event_id), None)
        actor = {'task_id': task['id'], 'owner': args.owner}
        if item['status'] == 'withdrawn':
            if not prior or prior.get('after', {}).get('reason') != args.reason:
                raise StateError('workspace item is already withdrawn')
        elif item['status'] == 'current':
            item['status'] = 'withdrawn'; item['updated_at'] = now()
            workspace['revision'] += 1
            workspace['audit'].append({'id': uuid.uuid4().hex, 'at': now(),
                'event_id': event_id, 'action': 'demote', 'item_id': args.item_id,
                'actor': actor, 'before': {'status': 'current'},
                'after': {'status': 'withdrawn', 'reason': args.reason,
                          'origin': item['origin'], 'demoter': actor}})
            validate_workspace(workspace)
            save_workspace(workspace_dir, workspace)
        else:
            raise StateError('workspace item is not current')
    with locked(path / '.write.lock'):
        task = load(path)
        if task['schema_version'] == 1:
            upgrade_memory(task)
        if task['schema_version'] != 2:
            raise StateError('demotion caller was not upgraded to v2')
        delivery_id = 'demotion-delivery:' + args.item_id
        if not any(event.get('event_id') == delivery_id for event in task['memory']['audit']):
            task['memory']['audit'].append({'id': uuid.uuid4().hex, 'at': now(),
                'event_id': delivery_id, 'action': 'demote-delivered',
                'item_id': args.item_id, 'actor': {'task_id': args.task, 'owner': args.owner}, 'before': None,
                'after': {'reason': args.reason, 'workspace_revision': workspace['revision'],
                          'origin': item['origin'], 'demoter': {'task_id': args.task, 'owner': args.owner}}})
            task['revision'] += 1; task['updated_at'] = now(); save(path, task)
    return response(path, task)


def mutate(args, root):
    if not args.owner.strip():
        raise StateError('owner must be a non-empty coordinator-session identifier')
    path = task_path(root, args.task)
    if not path.is_dir():
        raise StateError('task does not exist')
    if args.command == 'memory-apply':
        proposal = json.loads(Path(args.actions_file).read_text())
        if _workspace_actions(proposal):
            return promote_memory(root, args, proposal)
    event = None
    with locked(path / '.write.lock'):
        state = load(path)
        replay = False
        replay_proposal = None
        if args.command == 'memory-apply' and args.revision != 'latest' and args.revision != state['revision']:
            try:
                replay_proposal = json.loads(Path(args.actions_file).read_text())
            except (OSError, ValueError):
                replay_proposal = None
            replay = _memory_replay(state, replay_proposal)
        if args.revision == 'latest':
            if args.command == 'claim':
                raise StateError('claim requires a numeric revision after reconciliation')
            check_owner(state, args.owner)
            check_revision(state, state['revision'])
        else:
            if not replay:
                check_revision(state, args.revision)
        if state['archived_at']:
            raise StateError('task is archived; it cannot be mutated')
        was_v1 = state['schema_version'] == 1
        upgrade_memory(state)
        if args.command == 'claim':
            if state['owner'] and state['owner'] != args.owner:
                if not args.takeover or not args.reason or not args.reason.strip():
                    raise StateError('task has an owner; takeover requires --takeover and --reason after reconciliation')
            state['ownership_events'].append({'at': now(), 'from': state['owner'], 'to': args.owner,
                                              'reason': args.reason})
            state['owner'] = args.owner
        else:
            check_owner(state, args.owner)
            if args.command == 'memory-apply':
                proposal = json.loads(Path(args.actions_file).read_text())
                changed = apply_memory_actions(state, proposal, args.owner) or was_v1
            elif args.command == 'checkpoint':
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
        if args.command == 'memory-apply' and not changed:
            warnings = []
        else:
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
        except (OSError, ValueError, TypeError, KeyError, StateError) as error:
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
            except (ValueError, TypeError, KeyError, StateError) as error:
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


def _git_snapshot(path, updated_at):
    result = {'path': str(path)}
    if not path.exists():
        return result | {'error': 'missing directory'}
    def git(*args):
        return subprocess.run(['git', *args], cwd=path, text=True,
                              capture_output=True, timeout=5, check=True)
    try:
        branch = git('branch', '--show-current').stdout.strip()
        head = git('rev-parse', '--short', 'HEAD').stdout.strip()
        dirty = len(git('status', '--porcelain').stdout.splitlines())
        commits = git('log', '--since', updated_at, '--format=%h %s').stdout.splitlines()
        return result | {'exists': True, 'branch': branch, 'HEAD': head, 'dirty': dirty,
                         'commits_since_update': commits[:10],
                         'commits_since_update_count': len(commits)}
    except subprocess.TimeoutExpired:
        return result | {'error': 'git command timed out'}
    except (OSError, subprocess.CalledProcessError):
        return result | {'error': 'git error'}


def _resume_budget(result, budget):
    omitted = {'cold_items': 0, 'commits': 0, 'work_item_notes': 0}
    while _json_bytes(result | {'omitted': omitted}) > budget and result['memory']['cold']:
        result['memory']['cold'].pop()
        omitted['cold_items'] += 1
    while _json_bytes(result | {'omitted': omitted}) > budget:
        candidate = next((repo for repo in result['git']
                          if len(repo.get('commits_since_update', [])) > 3), None)
        if not candidate:
            break
        omitted['commits'] += len(candidate['commits_since_update'][3:])
        candidate['commits_since_update'] = candidate['commits_since_update'][:3]
    while _json_bytes(result | {'omitted': omitted}) > budget:
        item = next((item for item in result['task']['work_items'] if len(item) > 2), None)
        if not item:
            break
        result['task']['work_items'][result['task']['work_items'].index(item)] = {
            'id': item.get('id'), 'status': item.get('status')}
        omitted['work_item_notes'] += 1
    return omitted


def resume_task(root, args):
    path = task_path(root, args.task)
    state = load(path)
    details = state['details']
    task = {'title': state['title'], 'objective': details['objective'], 'status': state['status'],
            'acceptance_criteria': details['acceptance_criteria'],
            'work_items': [item for item in details['work_items']
                           if item['status'] not in {'completed', 'cancelled'}],
            'blockers': details['blockers'], 'pending_decisions': details['pending_decisions'],
            'next_action': details['next_action'], 'updated_at': state['updated_at'],
            'owner': state['owner']}
    if state['schema_version'] == 1:
        memory = {'legacy': True}
    else:
        cold = [item for item in state['memory']['cold'] if item['status'] == 'current']
        cold.sort(key=lambda item: item['updated_at'], reverse=True)
        memory = {'hot': state['memory']['hot'],
                  'cold': [{key: item[key] for key in ('id', 'category', 'text', 'provenance')}
                           for item in cold]}
    directories = [state['project']]
    for group in (details['work_items'], details['workers']):
        for item in group:
            if isinstance(item, dict):
                directories.extend(item[key] for key in ('worktree', 'cwd')
                                   if isinstance(item.get(key), str))
    git = [_git_snapshot(Path(directory), state['updated_at'])
           for directory in dict.fromkeys(directories)]
    checks = inspect_resume(state)
    if details['workers']:
        checks['reminders'] = ['git status and file existence do not prove worker liveness; inspect live panes/processes']
    result = {'task': task, 'memory': memory, 'git': git, 'checks': checks}
    omitted = _resume_budget(result, args.budget_bytes)
    result['omitted'] = omitted
    return result


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
    command = sub.add_parser('resume')
    command.add_argument('--task', required=True)
    command.add_argument('--budget-bytes', type=int, default=16 * 1024)
    sub.add_parser('session-nonce')
    for name in ('claim', 'checkpoint', 'select', 'release', 'archive', 'memory-apply'):
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
        elif name == 'memory-apply':
            command.add_argument('--actions-file', required=True)
    command = sub.add_parser('memory-demote')
    command.add_argument('--task', required=True)
    command.add_argument('--owner', required=True)
    command.add_argument('--task-revision', required=True, type=int)
    command.add_argument('--id', dest='item_id', required=True)
    command.add_argument('--workspace-revision', required=True, type=int)
    command.add_argument('--reason', required=True)
    for name in ('bind-session', 'unbind-session'):
        command = sub.add_parser(name)
        command.add_argument('--task', required=True)
        command.add_argument('--owner', required=True)
        command.add_argument('--revision', required=True, type=int)
        command.add_argument('--session-id', required=True)
        if name == 'bind-session':
            command.add_argument('--nonce')
            command.add_argument('--projects-dir')
    command = sub.add_parser('choices')
    command.add_argument('--task')
    command.add_argument('--project')
    command.add_argument('--limit', type=int, default=10)
    return root


def main():
    args = parser().parse_args()
    root = root_path(args.root)
    try:
        if getattr(args, 'task', None):
            args.task = resolve_task_id(root, args.task)
        if args.command == 'create':
            result = create(args, root)
        elif args.command == 'session-nonce':
            result = {'nonce': session_nonce()}
        elif args.command == 'list':
            result = list_tasks(args, root)
        elif args.command == 'choices':
            if args.limit < 1:
                raise StateError('limit must be positive')
            result = choices(args, root)
        elif args.command == 'resume':
            if args.budget_bytes < 1:
                raise StateError('budget must be positive')
            result = resume_task(root, args)
        elif args.command in {'show', 'render', 'check-resume'}:
            path = task_path(root, args.task)
            if args.command == 'render':
                with locked(path / '.write.lock'):
                    state = load(path)
                    atomic_write(path / 'state.md', markdown(state))
            else:
                state = load(path)
            result = inspect_resume(state) if args.command == 'check-resume' else response(path, state)
        elif args.command == 'memory-demote':
            if not args.reason.strip():
                raise StateError('demotion reason must be non-empty')
            result = demote_memory(root, args)
        elif args.command == 'bind-session':
            result = bind_session(args, root)
        elif args.command == 'unbind-session':
            result = unbind_session(args, root)
        else:
            result = mutate(args, root)
    except (StateError, OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
