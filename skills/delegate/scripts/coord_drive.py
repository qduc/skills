#!/usr/bin/env python3
"""Code-driven coordinator runtime. Code owns order and gates; the AI answers typed judgments.

`advance()` performs every deterministic step it can: isolated workspaces, worker launch,
observation, independent checks and claimcheck, patch or artifact integration, goal checks,
and completion. It stops only to wait for workers, for a typed judgment request
(harness, decompose, assess, inspect), or for a user question. Judgment answers
are validated against their schema before anything acts on them; an invalid
answer is returned with its error, a bounded number of times, then escalated.

Native dispatch uses durable host actions exposed by the front-desk CLI.
Artifact outcomes use separate directories and publish accepted files with checks
and evidence; their source directory is read-only by worker instruction.

Git isolation: each outcome works in its own git worktree under the task directory.
The wrapper (`_work`) packages the worker's changes as a patch and publishes the
report, so workers never handle reporting. Accepted patches are committed onto
the task branch in a separate integration worktree; the user's checkout is not
touched. Merging that branch is the user's decision.

Library for the front-desk CLI `coord.py`; the only direct entry point is `_work`.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid

import coord_outcomes as outcomes
import coord_process
import coord_runtime as runtime
import coord_state as tasks

SELF = Path(__file__).resolve()
JUDGMENT_DOCS = SELF.parents[1] / 'references' / 'judgments'
DRIVE_FILE = 'drive.json'
PACKAGE_DIR = '.coord'
EXCLUDE_PACKAGE = ':(exclude)' + PACKAGE_DIR
DEFAULT_LIMITS = {'attempts_per_outcome': 3, 'goal_rounds': 3, 'judgment_retries': 2,
                  'stall_seconds': 900, 'check_timeout': 300, 'unknown_grace_seconds': 120,
                  'checks_first': 'auto'}  # 'auto': each outcome's tests_first decides; True/False forces it
CHECKS_FIRST_MODES = ('auto', True, False)
OUTCOME_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,31}')
CHECKS_SUFFIX = '-checks'
TAIL = 4000
INLINE_PATCH = 12000  # judgments are often answered in the front desk's own context


class DriveError(tasks.StateError):
    pass


# --------------------------------------------------------------------------- utilities

def now_ts():
    return time.time()


def tail(text, limit=TAIL):
    text = text or ''
    return text if len(text) <= limit else '[...]\n' + text[-limit:]


def read_tail(path, limit=TAIL):
    try:
        return tail(Path(path).read_text(errors='replace'), limit)
    except OSError:
        return ''


def git(cwd, *args, check=True):
    result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True)
    if check and result.returncode:
        raise DriveError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip() if check else result


def drive_path(task_dir):
    return Path(task_dir) / DRIVE_FILE


def load_drive(task_dir):
    path = drive_path(task_dir)
    if not path.is_file():
        raise DriveError('task is not driven by coord_drive; start it with coord.py start')
    return json.loads(path.read_text())


def save_drive(task_dir, drive):
    tasks.atomic_write(drive_path(task_dir), json.dumps(drive, indent=2) + '\n')


@contextmanager
def driving(task_dir):
    """One driver at a time per task; the drive record is saved on every exit path."""
    task_dir = Path(task_dir)
    with tasks.locked(task_dir / '.drive.lock'):
        drive = load_drive(task_dir)
        try:
            yield drive
        finally:
            save_drive(task_dir, drive)


def log(drive, event, **fields):
    drive['log'].append({'at': tasks.now(), 'event': event, **fields})
    del drive['log'][:-300]


def mutate(task_dir, drive, action, attempts=100):
    """Owner-fenced task mutation; a launcher briefly holding the lock means retry, not failure."""
    for _ in range(attempts):
        try:
            return outcomes.mutate(task_dir, drive['owner'], 'latest', action)['result']
        except tasks.StateError as error:
            if 'busy' not in str(error):
                raise
            time.sleep(0.1)
    raise DriveError('task record stayed busy; retry advance')


def state_mutate(task_dir, drive, command, **fields):
    """coord_state commands (select, checkpoint, real-use) with the same busy retry."""
    root = Path(task_dir).parents[1]
    args = argparse.Namespace(command=command, task=Path(task_dir).name, owner=drive['owner'],
                              revision='latest', **fields)
    for _ in range(100):
        try:
            return tasks.mutate(args, root)
        except tasks.StateError as error:
            if 'busy' not in str(error):
                raise
            time.sleep(0.1)
    raise DriveError('task record stayed busy; retry')


def command_for(drive, route):
    for worker in drive['workers']:
        if route_matches(worker['route'], route):
            return worker.get('argv')
    return None


def worker_for(drive, route):
    return next((w for w in drive['workers'] if route_matches(w['route'], route)), None)


def artifact_delivery(drive):
    return drive.get('delivery', 'patch') == 'artifact'


def citation_sources(drive):
    """Read-only repositories an artifact report may cite; a patch's citations stay in its own worktree."""
    return [drive['repo'], *drive.get('sources', [])] if artifact_delivery(drive) else []


def route_matches(configured, route):
    # The selected route includes optional effort and role, and must not silently
    # select another configured command that shares only harness/model/provider.
    return configured == route


def limit(drive, name):
    return drive['limits'][name]


# --------------------------------------------------------------------------- requests and questions

def find(collection, key):
    matches = [entry for entry in collection.values() if entry['key'] == key]
    return matches[-1] if matches else None


def open_request(drive, kind, key, context):
    existing = find(drive['requests'], key)
    if existing and existing['status'] in {'open', 'answered', 'failed'}:
        return existing
    request = {'id': uuid.uuid4().hex[:12], 'kind': kind, 'key': key, 'status': 'open',
               'context': context, 'errors': [], 'created_at': tasks.now()}
    drive['requests'][request['id']] = request
    log(drive, 'judgment_requested', request=request['id'], kind=kind)
    return request


def open_question(drive, kind, key, prompt, payload=None):
    existing = find(drive['questions'], key)
    if existing and existing['status'] in {'open', 'replied'}:
        return existing
    question = {'id': uuid.uuid4().hex[:12], 'kind': kind, 'key': key, 'status': 'open',
                'prompt': prompt, 'payload': payload or {}, 'created_at': tasks.now()}
    drive['questions'][question['id']] = question
    log(drive, 'user_question', question=question['id'], kind=kind)
    return question


def reject_answer(drive, request, error):
    """An answer code could not use goes back to the judge, a bounded number of times."""
    request['errors'].append(str(error))
    request.pop('answer', None)
    if len(request['errors']) > limit(drive, 'judgment_retries'):
        request['status'] = 'failed'
        open_question(drive, 'judgment_failed', 'failed-' + request['id'],
                      f"The {request['kind']} judgment kept returning answers I can't use. "
                      f"Last error: {request['errors'][-1]}. What should it do differently?",
                      {'request': request['id']})
    else:
        request['status'] = 'open'
    log(drive, 'judgment_rejected', request=request['id'], error=str(error))


# --------------------------------------------------------------------------- answer schemas

SCHEMAS = {
    'harness': '{"pool": [{"harness": str, "model": str, "provider"?: str}], "rationale": str}',
    'decompose': ('{"outcomes": [{"id": "lowercase-slug", "objective": str, "rationale": str, "scope": str, '
                  '"authority": str, "needs": [outcome ids], "checks": [{"id": str, "argv": [str]}], '
                  '"tests_first"?: bool, "artifact"?: "relative/file.ext"}], '
                  '"goal_checks": [{"id": str, "argv": [str]}], "rationale": str}'),
    'assess': '{"action": one of context.actions, "reason": str, "guidance"?: str, "question"?: str}',
    'inspect': '{"verdict": "accept" | "reject", "reason": str, "feedback"?: str}',
    'review_checks': '{"verdict": "accept" | "reject", "reason": str, "feedback"?: str}',
}
OUTCOME_FIELDS = {'id', 'objective', 'rationale', 'scope', 'authority', 'needs', 'checks'}


def nonempty(value, name):
    if not outcomes.text(value):
        raise DriveError(f'{name} must be non-empty text')


def validate_answer(drive, request, answer):
    if not isinstance(answer, dict):
        raise DriveError('answer must be a JSON object')
    kind, context = request['kind'], request['context']
    if kind == 'harness':
        if set(answer) != {'pool', 'rationale'}:
            raise DriveError('harness answer needs exactly pool and rationale')
        tasks.validate_pool(answer['pool'])
        nonempty(answer['rationale'], 'rationale')
        missing = [r for r in answer['pool'] if worker_for(drive, r) is None]
        if missing:
            raise DriveError(f'no worker command is configured for {missing}; choose from context.routes')
    elif kind == 'decompose':
        if set(answer) != {'outcomes', 'goal_checks', 'rationale'}:
            raise DriveError('decompose answer needs exactly outcomes, goal_checks, rationale')
        nonempty(answer['rationale'], 'rationale')
        if not isinstance(answer['outcomes'], list) or not answer['outcomes']:
            raise DriveError('outcomes must be a non-empty list')
        for entry in answer['outcomes']:
            expected = OUTCOME_FIELDS | ({'artifact'} if artifact_delivery(drive) else set())
            if not isinstance(entry, dict) or set(entry) - {'tests_first'} != expected:
                raise DriveError('each outcome needs exactly ' + ', '.join(sorted(expected))
                                 + ' (tests_first is optional)')
            if not isinstance(entry.get('tests_first', True), bool):
                raise DriveError(f"outcome {entry['id']!r}: tests_first must be true or false")
            if artifact_delivery(drive):
                outcomes.artifact_name(entry['artifact'])
            if not isinstance(entry['id'], str) or not OUTCOME_ID.fullmatch(entry['id']):
                raise DriveError(f"outcome id {entry['id']!r} must be a lowercase slug of at most 32 characters")
            if entry['id'].endswith(CHECKS_SUFFIX):
                raise DriveError(f"outcome ids ending in {CHECKS_SUFFIX} are reserved for the checks phase")
            outcomes.checks(entry['checks'])
        outcomes.checks(answer['goal_checks'])
        kept = {(c['id'], tuple(c['argv'])) for c in answer['goal_checks']}
        dropped = [c['id'] for c in context.get('required_goal_checks', [])
                   if (c['id'], tuple(c['argv'])) not in kept]
        if dropped:
            raise DriveError(f'a replan may add goal checks but never drop or change them: {dropped}')
    elif kind == 'assess':
        if answer.get('action') not in context['actions']:
            raise DriveError(f"action must be one of {context['actions']}")
        nonempty(answer.get('reason'), 'reason')
        if answer['action'] == 'retry':
            nonempty(answer.get('guidance'), 'guidance for retry')
        if answer['action'] == 'escalate':
            nonempty(answer.get('question'), 'question for escalate')
    elif kind in {'inspect', 'review_checks'}:
        if answer.get('verdict') not in {'accept', 'reject'}:
            raise DriveError('verdict must be accept or reject')
        nonempty(answer.get('reason'), 'reason')
        if answer['verdict'] == 'reject':
            nonempty(answer.get('feedback'), 'feedback for reject')
    else:
        raise DriveError('unknown judgment kind: ' + kind)


def answer(task_dir, request_id, value):
    """Record a judgment answer after structural validation; returns the request."""
    with driving(task_dir) as drive:
        request = drive['requests'].get(request_id)
        if not request or request['status'] != 'open':
            raise DriveError('no open judgment request ' + request_id)
        try:
            validate_answer(drive, request, value)
        except tasks.StateError as error:
            reject_answer(drive, request, error)
            raise DriveError(f'answer rejected: {error}') from error
        request.update(status='answered', answer=value, answered_at=tasks.now())
        log(drive, 'judgment_answered', request=request_id, kind=request['kind'])
        return copy.deepcopy(request)


def request_prompt(task_dir, request_id):
    drive = load_drive(task_dir)
    request = drive['requests'][request_id]
    guide = (JUDGMENT_DOCS / f"{request['kind']}.md").read_text()
    parts = [guide, '## This request', '```json', json.dumps(request['context'], indent=2), '```']
    if request['errors']:
        parts += ['## Your previous answers were rejected', *('- ' + e for e in request['errors'])]
    parts += ['## Answer', 'Reply with only one JSON object of this shape, no prose:', SCHEMAS[request['kind']]]
    return '\n\n'.join(parts)


# --------------------------------------------------------------------------- worktrees and workers

def ensure_worktree(task_dir, drive, oid):
    if artifact_delivery(drive):
        workspace = drive.setdefault('workspaces', {}).get(oid)
        if workspace is None:
            workspace = str(Path(task_dir) / 'workspaces' / oid / uuid.uuid4().hex[:12])
            drive['workspaces'][oid] = workspace
        Path(workspace).mkdir(parents=True, exist_ok=True)
        return Path(workspace)
    path = Path(task_dir) / 'worktrees' / oid
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        git(drive['integration'], 'worktree', 'add', '--detach', str(path), 'HEAD')
    return path


def reset_worktree(path, head):
    git(path, 'checkout', '--detach', '--force', head)
    git(path, 'clean', '-fd', '-e', PACKAGE_DIR)  # previous attempts' patches stay as evidence


def worker_instructions(feedback, frozen=(), drive=None):
    def build(assignment, path):
        contract = assignment['contract']
        cwd = contract['cwd']
        summary = Path(cwd) / PACKAGE_DIR / assignment['attempt_id'] / 'summary.md'
        summary.parent.mkdir(parents=True, exist_ok=True)
        checks = '\n'.join(f"- {c['id']}: {shlex.join(c['argv'])}" for c in contract['checks'])
        lines = [
            'You are working on one bounded outcome of a larger task.',
            f"Objective: {contract['objective']}",
            f"Why it matters: {contract['rationale']}",
            f"Scope: {contract['scope']}",
            f"Authority: {contract['authority']}",
            f'Working directory: {cwd} (an isolated git worktree; change files only here).',
            'These checks will be run independently after you finish, from the working directory:',
            checks,
            'Rules:',
            '- Make the change in place. You do not need to commit; the runtime packages your changes as a patch.',
            f'- Do not modify anything under {PACKAGE_DIR}/ except your summary file.',
            '- Do not ask the user questions, spawn other agents, or start background jobs.',
            f'- When finished, write a short summary to {summary}: what you changed and which tests you ran, '
            'citing real file paths. Cited tests and commits are checked against the repository.',
            f'- If you cannot proceed without a decision outside your authority, write {{"decision": "<exact '
            f'missing decision>"}} to {Path(path).parent / "blocker.json"} and stop.',
            f'The full assignment is at {path} (read-only).',
            'Your final reply is not read: end with one line, done or blocked.',
        ]
        if frozen:
            lines += ['These tests were written and reviewed before you started; make them pass without '
                      'modifying them (write a blocker if one is wrong):', *(f'- {name}' for name in frozen)]
        if drive and artifact_delivery(drive):
            lines[5] = f'Working directory: {cwd} (an isolated artifact workspace; write only here).'
            lines[9] = (f"- Deliver the file {contract['artifact']} inside your working directory. "
                        'The runtime publishes it after independent checks and inspection.')
            lines += [f"Source material: {drive['repo']} (read-only; do not edit the source directory).",
                      *(f'Source repository: {source} (read-only).' for source in drive.get('sources', [])),
                      'Cited commits and tests are checked against your working directory and the source '
                      'material above; cite only revisions that exist there.',
                      'Accepted dependencies are in inputs/<outcome-id>/<artifact-name> (read-only).']
        if feedback:
            lines += ['Earlier attempts at this outcome did not pass. Address this feedback:',
                      *(f"- {entry['text']}" for entry in feedback[-5:])]
        return '\n'.join(lines)
    return build


def outcome_record(drive, oid):
    return drive['outcomes'].setdefault(oid, {'attempts': 0, 'allowance': 0, 'feedback': [],
                                              'blocked': None, 'progress': {}, 'flags': {}})


def is_integrated(state, oid):
    try:
        outcomes.integrated(state, oid)
        return True
    except tasks.StateError:
        return False


def start_attempt(task_dir, drive, state, oid):
    record = outcome_record(drive, oid)
    worktree = ensure_worktree(task_dir, drive, oid)
    head = None if artifact_delivery(drive) else git(drive['integration'], 'rev-parse', 'HEAD')
    if head:
        reset_worktree(worktree, head)
    else:
        for dependency in outcomes.outcome_of(state, oid)['contract']['needs']:
            upstream = outcomes.outcome_of(state, dependency)
            target = worktree / 'inputs' / dependency / upstream['contract']['artifact']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(outcomes.integrated(state, dependency)['artifact']['path'], target)
    pool = state['selection']
    route = pool[record['attempts'] % len(pool)]  # rotate across the selected pool on retries
    command = [sys.executable, str(SELF), '_work', '--assignment', '{assignment}', '--cwd', '{cwd}',
               '--base', head or 'artifact', '--', *(command_for(drive, route) or [])]
    partner = drive.get('checks_for', {}).get(oid)
    receipt = outcomes.outcome_of(state, partner).get('integration') if partner else None
    frozen = sorted(files_in_patch(receipt['artifact']['path'])) if receipt else []
    build = worker_instructions(record['feedback'], frozen, drive)
    def instructions(assignment, path):
        tasks.atomic_write(Path(path).parent / 'packaging.json', json.dumps({'base': head}) + '\n')
        return build(assignment, path)
    kind = worker_for(drive, route).get('runtime', 'process')
    started = mutate(task_dir, drive, lambda s, p: runtime.start(s, p, oid, kind, route, 'bounded_worker',
                                                                  [], command, instructions=instructions))
    if kind == 'native':
        # The front desk relays this message verbatim; the full brief stays on disk, out of its context.
        brief = Path(started['assignment_file']).with_name('prompt.txt')
        enqueue_host(drive, oid, started['attempt_id'], 'spawn', route=route, brief=str(brief),
                     message=f'Read {brief} and follow it exactly. Your files are the result: '
                             'end with a one-line reply saying done or blocked, not a report.')
    record['attempts'] += 1
    record['progress'] = {'signature': None, 'at': now_ts()}
    log(drive, 'attempt_started', outcome=oid, attempt=started['attempt_id'], route=route, base=head)


def progress_signature(attempt, worktree):
    run_dir = Path(attempt['run_dir'])
    sizes = [(run_dir / name).stat().st_size if (run_dir / name).exists() else 0
             for name in ('stdout.log', 'stderr.log')]
    # Never write the index: the worker's own git commands may need it right now. `git diff` refreshes
    # and rewrites it even with --no-optional-locks, so use the plumbing `diff-files` instead.
    if not (Path(worktree) / '.git').exists():
        files = [(str(p.relative_to(worktree)), p.stat().st_size, p.stat().st_mtime_ns)
                 for p in Path(worktree).rglob('*') if p.is_file() and PACKAGE_DIR not in p.parts]
        return hashlib.sha256(json.dumps([sizes, files]).encode()).hexdigest()
    status = git(worktree, '--no-optional-locks', 'status', '--porcelain', '--', '.', EXCLUDE_PACKAGE,
                 check=False).stdout
    diff = git(worktree, '--no-optional-locks', 'diff-files', '-p', '--', '.', EXCLUDE_PACKAGE, check=False).stdout
    return hashlib.sha256(json.dumps([sizes, status, diff]).encode()).hexdigest()


def retry(task_dir, drive, state, oid, text, counted=True):
    """A failed attempt goes back to a worker with feedback until the bound, then to judgment."""
    record = outcome_record(drive, oid)
    record['feedback'].append({'at': tasks.now(), 'text': text})
    if not counted:
        record['allowance'] += 1
    log(drive, 'attempt_failed', outcome=oid, feedback=tail(text, 500), counted=counted)
    if record['attempts'] >= limit(drive, 'attempts_per_outcome') + record['allowance']:
        item = outcomes.outcome_of(state, oid)
        request = open_request(drive, 'assess', f"exhausted-{oid}-{item['assignment_id']}", {
            'event': 'attempts_exhausted', 'outcome': oid, 'contract': item['contract'],
            'attempts': record['attempts'], 'feedback': [f['text'] for f in record['feedback'][-5:]],
            'actions': ['retry', 'escalate', 'replan']})
        record['blocked'] = request['id']
        return
    revise_attempt(task_dir, drive, state, oid)


def revise_attempt(task_dir, drive, state, oid):
    contract = copy.deepcopy(outcomes.outcome_of(state, oid)['contract'])
    if artifact_delivery(drive):
        drive.setdefault('workspaces', {}).pop(oid, None)
        contract['cwd'] = str(ensure_worktree(task_dir, drive, oid))
    mutate(task_dir, drive, lambda s, p: outcomes.revise(s, oid, contract))


def stop_attempt(task_dir, drive, oid, reason, guidance=None):
    record = outcome_record(drive, oid)
    state = tasks.load(task_dir)
    attempt = outcomes.outcome_of(state, oid).get('attempt') or {}
    if attempt.get('status') in {'finished', 'stopped'}:
        record['flags'].setdefault(attempt['id'], {})['stopping'] = {'reason': reason, 'guidance': guidance}
        return
    if attempt.get('runtime') == 'native' and not attempt.get('handle'):
        spawn = next((a for a in drive.get('host_actions', {}).values()
                      if a['attempt'] == attempt['id'] and a['action'] == 'spawn'), None)
        if spawn is None or spawn['status'] == 'pending':
            evidence = Path(attempt['run_dir']) / 'cancelled-before-host.json'
            basis = 'driver cancelled the pending spawn before host-next issued it'
            tasks.atomic_write(evidence, json.dumps({'attempt_id': attempt['id'],
                                                     'status': 'not_started', 'basis': basis}) + '\n')
            mutate(task_dir, drive, lambda s, p: runtime.reconcile(s, oid, attempt['id'], evidence, basis))
            if spawn:
                spawn.update(status='answered', result={'status': 'not_started', 'basis': basis})
            record['flags'].setdefault(attempt['id'], {})['stopping'] = {'reason': reason, 'guidance': guidance}
            return
    try:
        result = mutate(task_dir, drive, lambda s, p: runtime.control(s, oid, 'stop'))
        if attempt.get('runtime') == 'native':
            enqueue_host(drive, oid, attempt['id'], 'stop', handle=result['request']['handle'])
    except tasks.StateError as error:
        # Identity unknown: the unknown-attempt path reconciles it once no process remains.
        log(drive, 'attempt_stop_deferred', outcome=oid, error=str(error))
    record['flags'].setdefault(attempt['id'], {})['stopping'] = {'reason': reason, 'guidance': guidance}
    log(drive, 'attempt_stop_requested', outcome=oid, reason=reason)


# Host tools execute requests; all lifecycle decisions remain inside the driver.
def enqueue_host(drive, oid, attempt_id, action, **payload):
    actions = drive.setdefault('host_actions', {})
    for entry in actions.values():
        if entry['attempt'] == attempt_id and entry['action'] == action and entry['status'] != 'answered':
            return entry
    entry = dict(id=uuid.uuid4().hex[:12], outcome=oid, attempt=attempt_id,
                 action=action, status='pending', **payload)
    if action == 'spawn':
        entry['label'] = 'coord_' + oid.replace('-', '_') + '_' + attempt_id[:8]
    actions[entry['id']] = entry
    return entry


def host_next(task_dir):
    """Issue one host-tool request durably. Re-reading an issued spawn requires inspection, never respawn."""
    advance(task_dir)
    with driving(task_dir) as drive:
        actions = [a for a in drive.get('host_actions', {}).values() if a['status'] != 'answered']
        actions.sort(key=lambda a: (a['status'] != 'issued', a['action'] != 'stop'))
        if not actions:
            return {'action': None, 'next': summary(task_dir, drive)}
        entry = actions[0]
        repeated_spawn = entry['status'] == 'issued' and entry['action'] == 'spawn'
        entry['status'] = 'issued'
        result = {k: v for k, v in entry.items() if k not in {'attempt', 'status'}}
        if repeated_spawn:
            result.update(action='reconcile', instruction=(
                'A spawn request was already issued. Inspect the host for that worker; do not spawn again. '
                'Return its handle, or status not_started with basis only if host inspection proves non-delivery. '
                'If uncertain, return status unknown with basis and keep the request unresolved.'))
        result['reply_with'] = ({'handle': '<returned worker handle>'} if entry['action'] == 'spawn' else
                                {'handle': entry['handle'], 'status': 'working|finished|stopped|unknown'})
        return result


def host_result(task_dir, action_id, value):
    """Record the observed result of a host request; bind identity and package settled work internally."""
    if not isinstance(value, dict):
        raise DriveError('host result must be a JSON object')
    with driving(task_dir) as drive:
        entry = drive.get('host_actions', {}).get(action_id)
        if not entry or entry['status'] != 'issued':
            raise DriveError('no issued host action ' + action_id)
        state = tasks.load(task_dir)
        item = outcomes.outcome_of(state, entry['outcome'])
        attempt = item.get('attempt', {})
        if attempt.get('id') != entry['attempt'] or attempt.get('runtime') != 'native':
            raise DriveError('host result belongs to an obsolete worker request')
        if entry['action'] == 'spawn':
            if outcomes.text(value.get('handle')):
                mutate(task_dir, drive, lambda s, p: runtime.bind_native(
                    s, entry['outcome'], entry['attempt'], value['handle']))
            elif value.get('status') in {'not_started', 'unknown'} and outcomes.text(value.get('basis')):
                if value['status'] == 'unknown':
                    entry['last_observation'] = value
                    return summary(task_dir, drive)
                evidence = Path(attempt['run_dir']) / 'host-non-delivery.json'
                tasks.atomic_write(evidence, json.dumps(dict(value, attempt_id=entry['attempt'])) + '\n')
                mutate(task_dir, drive, lambda s, p: runtime.reconcile(
                    s, entry['outcome'], entry['attempt'], evidence, value['basis']))
            else:
                raise DriveError('spawn result needs a handle, or inspected not_started/unknown status with basis')
        else:
            if value.get('handle') != entry['handle']:
                raise DriveError('host observation must match the requested handle')
            mutate(task_dir, drive, lambda s, p: runtime.observe(s, entry['outcome'], value))
        entry.update(status='answered', result=value)
        if value.get('status') in {'finished', 'stopped', 'not_started'}:
            for other in drive.get('host_actions', {}).values():
                if other['attempt'] == entry['attempt'] and other['status'] != 'answered':
                    other.update(status='answered', result={'superseded_by': action_id})
        log(drive, 'host_result', outcome=entry['outcome'], action=entry['action'], result=value)
    return advance(task_dir)


# --------------------------------------------------------------------------- phases

def selection_phase(task_dir, drive, state):
    request = find(drive['requests'], 'harness')
    if request is None:
        details = state['details']
        open_request(drive, 'harness', 'harness', {
            'goal': details['objective'], 'acceptance_criteria': details['acceptance_criteria'],
            'constraints': details['constraints'], 'authority': details['authority'],
            'routes': [w['route'] for w in drive['workers']],
            'recent_choices': recent_choices(task_dir, drive['repo'])})
    elif request['status'] == 'answered':
        value = request['answer']
        pool_file = Path(task_dir) / '.drive-pool.json'
        tasks.atomic_write(pool_file, json.dumps(value['pool']) + '\n')
        state_mutate(task_dir, drive, 'select', pool_file=str(pool_file), confirmed=False,
                     source='coordinator recommendation: ' + value['rationale'])
        log(drive, 'selection_applied', pool=value['pool'], rationale=value['rationale'])
        request['status'] = 'applied'


def recent_choices(task_dir, repo):
    """Recorded choices for the same repository, whether its tasks were driven or manual."""
    root = Path(task_dir).parents[1]
    try:
        lines = (root / 'choices.jsonl').read_text().splitlines()[-50:]
    except OSError:
        return []
    found = []
    for line in lines:
        try:
            event = json.loads(line)
            other = root / 'tasks' / str(event.get('task_id')) / DRIVE_FILE
            # A driven task's project is its own integration worktree; its repo is in drive.json.
            same = event.get('project') == repo or (other.is_file() and json.loads(other.read_text())['repo'] == repo)
        except (ValueError, OSError, KeyError, TypeError):
            continue
        if same:
            found.append({'pool': event.get('pool'), 'source': event.get('source')})
    return found[-5:]


def plan_context(task_dir, drive, state, mode, evidence=None, guidance=None):
    details = state['details']
    integration = drive['integration']
    files = [] if artifact_delivery(drive) else git(integration, 'ls-files', check=False).stdout.splitlines()
    context = {'mode': mode, 'goal': details['objective'], 'acceptance_criteria': details['acceptance_criteria'],
               'constraints': details['constraints'], 'authority': details['authority'],
               'repository': integration, 'files': files[:100] + ([f'... {len(files) - 100} more; run git ls-files'] if len(files) > 100 else []),
               'delivery': drive.get('delivery', 'patch'), 'source': drive['repo'],
               'rules': ['Outcome checks run from that outcome\'s isolated worktree root.',
                         'Goal checks run from the repository root after every outcome is integrated.',
                         'Each check is argv run without a shell; exit code 0 means pass.',
                         'An outcome may only need outcomes listed earlier.']}
    if artifact_delivery(drive):
        context['rules'] += [
            'Read source for context only; never edit it. Each outcome gets an empty isolated workspace.',
            'Each outcome must name one artifact (relative file path, e.g. report.md or chart.png).',
            'Outcome checks run beside that artifact; dependencies are copied into inputs/<id>/<artifact>.',
            'Accepted artifacts are published at artifacts/<outcome-id>/<artifact> under repository.',
            'Goal checks run there. No Git, patch, commit, or checks-first phase is required.',
            'Report quality and evidence must also be inspected; existence checks alone do not prove claims.']
    if 'outcome_plan' in state:
        plan = state['outcome_plan']
        context['previous_plan'] = [item['contract'] for item in plan['outcomes'].values()]
        context['required_goal_checks'] = plan['goal_checks']
        for contract in context['previous_plan']:
            contract.pop('cwd', None)
    if evidence:
        context['failure'] = evidence
    if guidance:
        context['user_guidance'] = guidance
    return context


def plan_phase(task_dir, drive, state):
    key = f"plan-{drive['goal_rounds']}"
    request = find(drive['requests'], key)
    if request is None:
        open_request(drive, 'decompose', key, plan_context(task_dir, drive, state, 'plan'))
    elif request['status'] == 'answered':
        apply_plan(task_dir, drive, request, replan=False)


def red_check(checks):
    """A check that passes only while at least one of `checks` still fails."""
    return {'id': 'red-before-green', 'argv': [sys.executable, str(SELF), '_red', '--checks', json.dumps(checks)]}


def tests_first(drive, entry):
    """Whether an outcome gets a checks phase. A plan that omits tests_first keeps the safer default."""
    mode = limit(drive, 'checks_first')
    return entry.get('tests_first', True) if mode == 'auto' else mode


def expand(drive, entries):
    """Give each outcome that wants it a checks phase that writes its tests first; the outcome then needs it."""
    expanded, partners = [], {}
    for entry in entries:
        if not tests_first(drive, entry):
            expanded.append(entry)
            continue
        checks_id = entry['id'] + CHECKS_SUFFIX
        expanded.append({
            'id': checks_id,
            'objective': ('Write the tests that will prove this outcome, before anyone implements it: '
                          f"{entry['objective']} Do not implement the behavior itself."),
            'rationale': ('Tests are written and reviewed before implementation so missing cases are caught '
                          'while they are cheap to add. ' + entry['rationale']),
            'scope': ('Test files and test fixtures only; no production code. These checks must fail until the '
                      'outcome is implemented: ' + '; '.join(shlex.join(c['argv']) for c in entry['checks'])),
            'authority': entry['authority'] + ' Limited to tests and fixtures.',
            'needs': list(entry['needs']), 'checks': [red_check(entry['checks'])]})
        expanded.append(dict(entry, needs=list(entry['needs']) + [checks_id]))
        partners[entry['id']] = checks_id
    return expanded, partners


def apply_plan(task_dir, drive, request, replan):
    value = request['answer']
    try:
        baseline = outcomes.run_checks(value['goal_checks'], drive['integration'], limit(drive, 'check_timeout'))
        if all(check['exit_code'] == 0 for check in baseline):
            raise DriveError('every goal check already passes on the current code, so none of them can show '
                             'whether the work was done; include at least one check that fails until the goal is met')
        entries, partners = (value['outcomes'], {}) if artifact_delivery(drive) else expand(drive, value['outcomes'])
        entries = [{k: v for k, v in entry.items() if k != 'tests_first'} for entry in entries]  # a plan choice, not a contract field
        spec = {'outcomes': [], 'goal_checks': value['goal_checks']}
        for entry in entries:
            if artifact_delivery(drive):
                drive.setdefault('workspaces', {}).pop(entry['id'], None)
            contract = dict(entry, cwd=str(ensure_worktree(task_dir, drive, entry['id'])))
            spec['outcomes'].append(contract)
        if replan:
            decision = f"goal round {drive['goal_rounds']}: {value['rationale']}"
            mutate(task_dir, drive, lambda s, p: outcomes.replan(s, spec, decision))
        else:
            mutate(task_dir, drive, lambda s, p: outcomes.initialize(s, spec))
    except tasks.StateError as error:
        reject_answer(drive, request, error)
        return
    request['status'] = 'applied'
    drive['checks_for'] = partners
    for entry in entries:
        drive['outcomes'][entry['id']] = {'attempts': 0, 'allowance': 0, 'feedback': [], 'blocked': None,
                                          'progress': {}, 'flags': {}}
    log(drive, 'plan_applied', request=request['id'], outcomes=[e['id'] for e in entries], replan=replan)


def resolve_block(task_dir, drive, state, oid):
    """Apply an answered assess request or replied escalation; returns True while still blocked."""
    record = outcome_record(drive, oid)
    blocked = record['blocked']
    if blocked.startswith('q:'):
        question = drive['questions'][blocked[2:]]
        if question['status'] != 'replied':
            return True
        question['status'] = 'resolved'
        record['blocked'] = None
        record['allowance'] += 1
        guidance = f"User decision: {question['reply']}"
        return not redirect(task_dir, drive, state, oid, guidance)
    request = drive['requests'][blocked]
    if request['status'] != 'answered':
        return True
    value = request['answer']
    request['status'] = 'applied'
    record['blocked'] = None
    action = value['action']
    log(drive, 'assessment_applied', outcome=oid, action=action, reason=value['reason'])
    if action == 'continue':
        record['progress'] = {'signature': None, 'at': now_ts()}
        return False
    if action == 'escalate':
        question = open_question(drive, 'escalation', 'escalate-' + request['id'], value['question'],
                                 {'outcome': oid, 'reason': value['reason']})
        record['blocked'] = 'q:' + question['id']
        return True
    if action == 'replan':
        drive['replan'] = {'reason': value['reason'], 'outcome': oid, 'guidance': value.get('guidance')}
        return True
    record['allowance'] += 1  # retry: one more attempt with the judge's guidance
    return not redirect(task_dir, drive, state, oid, value['guidance'])


def redirect(task_dir, drive, state, oid, guidance):
    """Start over with guidance: stop a live attempt first. Returns True when the outcome can proceed."""
    attempt = outcomes.outcome_of(state, oid).get('attempt')
    if attempt and attempt.get('status') not in {'finished', 'stopped'}:
        stop_attempt(task_dir, drive, oid, 'redirect', guidance)
        return False
    record = outcome_record(drive, oid)
    record['feedback'].append({'at': tasks.now(), 'text': guidance})
    if attempt:
        revise_attempt(task_dir, drive, state, oid)
    return True


def outcomes_phase(task_dir, drive):
    state = tasks.load(task_dir)
    plan = state['outcome_plan']
    for oid in list(plan['outcomes']):
        state = tasks.load(task_dir)
        item = outcomes.outcome_of(state, oid)
        record = outcome_record(drive, oid)
        if is_integrated(state, oid):
            continue
        if any(not is_integrated(state, need) for need in item['contract']['needs']):
            continue
        if record['blocked'] and resolve_block(task_dir, drive, state, oid):
            continue
        state = tasks.load(task_dir)
        item = outcomes.outcome_of(state, oid)
        if drive.get('replan') or drive.get('halted') or replan_pending(drive):
            attempt = item.get('attempt')
            if attempt and attempt.get('status') not in {'finished', 'stopped'}:
                observe(task_dir, drive, oid)
            continue
        if item.get('acceptance'):
            integrate(task_dir, drive, state, oid)
            continue
        if not item.get('attempt'):
            start_attempt(task_dir, drive, state, oid)
            continue
        observation = observe(task_dir, drive, oid)
        status = observation['status']
        if status == 'working':
            watch_progress(task_dir, drive, state, oid)
        elif status == 'unknown':
            reconcile_if_gone(task_dir, drive, oid)
        else:
            settled(task_dir, drive, oid, observation)


def replan_pending(drive):
    """A replan was requested but its plan has not landed: the old plan only settles, never advances."""
    return any(r['kind'] == 'decompose' and r['key'].startswith('replan-') and r['status'] in {'open', 'answered', 'failed'}
               for r in drive['requests'].values())


def observe(task_dir, drive, oid):
    state = tasks.load(task_dir)
    attempt = outcomes.outcome_of(state, oid).get('attempt', {})
    if attempt.get('runtime') == 'native':
        if attempt.get('status') in {'finished', 'stopped'}:
            root = Path(attempt['run_dir'])
            return {'status': attempt['status'], 'attempt_id': attempt['id'],
                    'blocker': str(root / 'blocker.json') if (root / 'blocker.json').exists() else None}
        if not attempt.get('handle'):
            enqueue_host(drive, oid, attempt['id'], 'spawn', route=attempt['route'],
                         message=(Path(attempt['run_dir']) / 'prompt.txt').read_text())
        else:
            stopping = outcome_record(drive, oid)['flags'].get(attempt['id'], {}).get('stopping')
            if stopping and not any(a['attempt'] == attempt['id'] and a['action'] == 'stop'
                                    for a in drive.get('host_actions', {}).values()):
                enqueue_host(drive, oid, attempt['id'], 'stop', handle=attempt['handle'])
            pending_stop = any(a['attempt'] == attempt['id'] and a['action'] == 'stop'
                               and a['status'] != 'answered' for a in drive.get('host_actions', {}).values())
            if not pending_stop:
                enqueue_host(drive, oid, attempt['id'], 'observe', handle=attempt['handle'])
        return {'status': 'working' if attempt['status'] == 'working' else 'unknown', 'attempt_id': attempt['id']}
    return mutate(task_dir, drive, lambda s, p: runtime.observe(s, oid))


def watch_progress(task_dir, drive, state, oid):
    record = outcome_record(drive, oid)
    attempt = outcomes.outcome_of(state, oid)['attempt']
    signature = progress_signature(attempt, attempt_cwd(state, oid))
    progress = record['progress']
    if signature != progress.get('signature'):
        record['progress'] = {'signature': signature, 'at': now_ts()}
        return
    idle = now_ts() - progress.get('at', now_ts())
    if idle < limit(drive, 'stall_seconds') or record['blocked']:
        return
    run_dir = Path(attempt['run_dir'])
    request = open_request(drive, 'assess', f"stall-{attempt['id']}-{int(progress['at'])}", {
        'event': 'no_progress', 'outcome': oid, 'contract': outcomes.outcome_of(state, oid)['contract'],
        'idle_minutes': round(idle / 60, 1), 'stdout_tail': read_tail(run_dir / 'stdout.log'),
        'stderr_tail': read_tail(run_dir / 'stderr.log'),
        'diff_stat': (None if artifact_delivery(drive) else
                      git(attempt_cwd(state, oid), '--no-optional-locks', 'diff-files', '--stat', check=False).stdout),
        'actions': ['continue', 'retry', 'escalate', 'replan']})
    record['blocked'] = request['id']


def attempt_cwd(state, oid):
    return outcomes.outcome_of(state, oid)['contract']['cwd']


def reconcile_if_gone(task_dir, drive, oid):
    """Code observes the process table; only a provably dead attempt is reconciled."""
    state = tasks.load(task_dir)
    attempt = outcomes.outcome_of(state, oid)['attempt']
    if attempt.get('runtime') == 'native':
        return  # Native delivery can only be settled by actual host observations.
    age = now_ts() - _timestamp(attempt.get('created_at'))
    resources = [attempt.get('launcher', {}), attempt.get('receipt', {})]
    live = [r for r in resources if r.get('pid') and runtime.process_live(r)]
    if live or age < limit(drive, 'unknown_grace_seconds'):
        return
    evidence = Path(attempt['run_dir']) / 'driver-reconcile.json'
    tasks.atomic_write(evidence, json.dumps({
        'attempt_id': attempt['id'], 'status': 'stopped',
        'basis': f'no live launcher or worker process after {int(age)}s; receipt: {attempt.get("receipt")}'}) + '\n')
    mutate(task_dir, drive, lambda s, p: runtime.reconcile(s, oid, attempt['id'], evidence,
                                                           'driver observed no live attempt process'))
    retry(task_dir, drive, tasks.load(task_dir), oid,
          'The worker process disappeared without finishing. Start again and keep the work in the foreground.')


def _timestamp(value):
    from datetime import datetime
    try:
        return datetime.fromisoformat(value).timestamp()
    except (TypeError, ValueError):
        return 0


def settled(task_dir, drive, oid, observation):
    state = tasks.load(task_dir)
    item = outcomes.outcome_of(state, oid)
    attempt = item['attempt']
    record = outcome_record(drive, oid)
    flags = record['flags'].setdefault(attempt['id'], {})
    stopping = flags.pop('stopping', None)
    if stopping:
        if stopping['reason'] == 'redirect':
            redirect(task_dir, drive, state, oid, stopping['guidance'])
        elif stopping['reason'] == 'halt':
            # A user halt is not a failed attempt: start over without spending the budget.
            record['allowance'] += 1
            revise_attempt(task_dir, drive, state, oid)
            log(drive, 'attempt_discarded_after_halt', outcome=oid)
        return  # replan: the new plan replaces this outcome
    if observation.get('blocker') and not flags.get('blocker_seen'):
        flags['blocker_seen'] = True
        request = open_request(drive, 'assess', 'blocked-' + attempt['id'], {
            'event': 'blocked', 'outcome': oid, 'contract': item['contract'],
            'blocker': read_tail(observation['blocker']), 'authority': state['details']['authority'],
            'actions': ['retry', 'escalate', 'replan']})
        record['blocked'] = request['id']
        return
    inspect_key = 'inspect-' + attempt['id']
    request = find(drive['requests'], inspect_key)
    if request is not None:
        if request['status'] == 'answered':
            apply_inspection(task_dir, drive, state, oid, request)
        return
    package = Path(attempt['run_dir']) / 'package.json'
    if attempt.get('runtime') == 'native' and not package.exists() and attempt.get('handle'):
        try:
            meta = json.loads((Path(attempt['run_dir']) / 'packaging.json').read_text())
            package_work(attempt['assignment_file'], item['contract']['cwd'], meta['base'])
        except (tasks.StateError, OSError, ValueError, subprocess.SubprocessError) as error:
            retry(task_dir, drive, state, oid, f'Worker output could not be packaged: {error}')
            return
    result = json.loads(package.read_text()) if package.is_file() else {'status': 'missing'}
    if result['status'] != 'reported':
        reason = {'no_changes': 'The attempt finished without changing any files.',
                  'missing': 'The attempt ended before its changes were packaged.'}.get(result['status'], result['status'])
        stderr = read_tail(Path(attempt['run_dir']) / 'stderr.log', 1500)
        retry(task_dir, drive, state, oid, f"{reason} Exit code: {result.get('exit_code')}."
              + (f' stderr tail:\n{stderr}' if stderr else ''))
        return
    frozen = frozen_tests_touched(state, drive, oid, result['report'])
    if frozen:
        retry(task_dir, drive, state, oid, 'You changed tests that were reviewed and approved before implementation: '
              + ', '.join(frozen) + '. Make them pass without modifying them; if one is wrong, write a blocker.')
        return
    try:
        verification = mutate(task_dir, drive, lambda s, p: outcomes.verify_result(
            s, oid, result['report'], limit(drive, 'check_timeout'), citation_sources(drive)))
    except tasks.StateError as error:
        retry(task_dir, drive, tasks.load(task_dir), oid, f'Independent verification refused the result: {error}')
        return
    failing = [c for c in verification['checks'] if c['exit_code'] != 0]
    blockers = verification['claimcheck']['blockers']
    if failing or blockers:
        lines = [f"Check {c['id']} failed (exit {c['exit_code']}).\nstdout:\n{tail(c['stdout'], 1500)}\n"
                 f"stderr:\n{tail(c['stderr'], 1500)}" for c in failing]
        lines += [f'Your summary cites something the runtime could not find: {b}' for b in blockers]
        signature = failure_signature(failing)
        previous = record.get('last_failure')
        record['last_failure'] = signature
        budget_left = record['attempts'] < limit(drive, 'attempts_per_outcome') + record['allowance']
        if failing and signature == previous and budget_left:
            # Same checks, same output, twice: another identical retry has no new evidence to act on.
            record['feedback'].append({'at': tasks.now(), 'text': '\n'.join(lines)})
            request = open_request(drive, 'assess', f"repeated-{oid}-{attempt['id']}", {
                'event': 'repeated_failure', 'outcome': oid, 'contract': item['contract'],
                'attempts': record['attempts'], 'failing_checks': [
                    {'id': c['id'], 'argv': c['argv'], 'exit_code': c['exit_code'],
                     'stdout_tail': tail(c['stdout'], 1500), 'stderr_tail': tail(c['stderr'], 1500)} for c in failing],
                'note': ('The same checks failed with identical output on two attempts in a row. Retrying unchanged '
                         'is unlikely to help; the check itself may be broken (wrong directory, missing module), '
                         'which only a replan can fix.'),
                'actions': ['retry', 'escalate', 'replan']})
            record['blocked'] = request['id']
            log(drive, 'repeated_failure', outcome=oid)
            return
        retry(task_dir, drive, tasks.load(task_dir), oid, '\n'.join(lines))
        return
    patch_file = Path(verification['artifact']['path'])
    with patch_file.open('rb') as stream:
        preview = stream.read(INLINE_PATCH + 1)
    patch = preview.decode('utf-8', errors='replace')
    if len(patch) > INLINE_PATCH:
        stat = '' if artifact_delivery(drive) else git(
            drive['integration'], 'apply', '--stat', str(patch_file), check=False).stdout
        patch = (stat + '\n' + patch[:INLINE_PATCH] + f'\n[truncated at {INLINE_PATCH} of '
                 f'{patch_file.stat().st_size} bytes; read patch_file for the rest]')
    implements = next((x for x, c in drive.get('checks_for', {}).items() if c == oid), None)
    extra = {}
    if implements:  # a checks phase: review the tests against what the outcome and the task must achieve
        extra = {'implements': outcomes.outcome_of(state, implements)['contract'],
                 'acceptance_criteria': state['details']['acceptance_criteria'],
                 'red_evidence': tail(verification['checks'][0]['stdout'], 1500)}
    open_request(drive, 'review_checks' if implements else 'inspect', inspect_key, dict(extra, **{
        'outcome': oid, 'contract': item['contract'], 'attempt': record['attempts'],
        'delivery': drive.get('delivery', 'patch'), 'source': drive['repo'],
        'artifact': verification['artifact'],
        'unverified_citations': verification['claimcheck'].get('unverified', []),
        'summary': json.loads(Path(result['report']).read_text()).get('summary'),
        'patch': patch,
        'patch_file': verification['artifact']['path'],
        'checks': [{'id': c['id'], 'argv': c['argv'], 'exit_code': c['exit_code'],
                    'stdout_tail': tail(c['stdout'], 1500)} for c in verification['checks']],
        'earlier_feedback': [f['text'] for f in record['feedback'][-3:]]}))


def failure_signature(failing):
    """Failing checks and their output, with numbers removed so timings and addresses do not differ."""
    normalized = [(c['id'], c['exit_code'], re.sub(r'\d+', '#', c['stdout'] + c['stderr'])) for c in failing]
    return hashlib.sha256(json.dumps(normalized).encode()).hexdigest()


def files_in_patch(path):
    """Let Git decode its patch protocol, including both sides of renames/copies."""
    patch = Path(path).read_bytes()
    if not patch.strip():
        return set()
    names = set()
    for direction in ([], ['--reverse']):
        # Run outside the repository: apply otherwise filters paths relative to
        # the caller's current subdirectory. -z preserves all filename bytes.
        result = subprocess.run(['git', 'apply', '--numstat', '-z', *direction, '-'],
                                input=patch, capture_output=True, cwd='/')
        if result.returncode:
            raise DriveError('cannot read patch paths: ' + os.fsdecode(result.stderr).strip())
        for record in result.stdout.split(b'\0'):
            if record:
                fields = record.split(b'\t', 2)
                if len(fields) != 3 or not fields[2]:
                    raise DriveError('invalid patch path metadata')
                names.add(os.fsdecode(fields[2]))
    return names


def frozen_tests_touched(state, drive, oid, report):
    """Files from this outcome's approved checks phase that its implementation patch changes."""
    partner = drive.get('checks_for', {}).get(oid)
    if not partner:
        return []
    receipt = outcomes.outcome_of(state, partner).get('integration')
    if not receipt:
        return []
    artifact = json.loads(Path(report).read_text())['artifact']['path']
    return sorted(files_in_patch(receipt['artifact']['path']) & files_in_patch(artifact))


def red(checks, cwd, timeout=600):
    """Exit 0 only while at least one check fails: tests that already pass prove nothing new."""
    failing = []
    for check in checks:
        try:
            code, _, _ = coord_process.run(check['argv'], cwd, timeout, new_session=False)
        except (subprocess.TimeoutExpired, OSError):
            code = None
        state = 'fails (good: it needs the implementation)' if code != 0 else 'passes already (guards regressions only)'
        print(f"{check['id']}: {state}")
        if code != 0:
            failing.append(check['id'])
    if not failing:
        print('Every check passes before any implementation, so none of them can show the work was done.')
    return 0 if failing else 1


def apply_inspection(task_dir, drive, state, oid, request):
    value = request['answer']
    request['status'] = 'applied'
    if value['verdict'] == 'reject':
        retry(task_dir, drive, state, oid, f"Review rejected the change: {value['reason']}\n{value['feedback']}")
        return
    try:
        mutate(task_dir, drive, lambda s, p: outcomes.accept(s, oid, 'Judgment inspection: ' + value['reason']))
    except tasks.StateError as error:
        retry(task_dir, drive, tasks.load(task_dir), oid, f'Acceptance refused: {error}')
        return
    log(drive, 'outcome_accepted', outcome=oid, reason=value['reason'])
    integrate(task_dir, drive, tasks.load(task_dir), oid)


def integrate(task_dir, drive, state, oid):
    """Commit the accepted patch onto the task branch; idempotent across crashes via its trailer."""
    item = outcomes.outcome_of(state, oid)
    acceptance = item['acceptance']
    assignment = item['assignment_id']
    integration = Path(drive['integration'])
    patch = Path(acceptance['artifact']['path'])
    if artifact_delivery(drive):
        target = integration / 'artifacts' / oid / item['contract']['artifact']
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('.' + target.name + '.tmp')
        shutil.copyfile(patch, temporary)
        temporary.replace(target)
        mutate(task_dir, drive, lambda s, p: outcomes.integrate(s, oid, target))
        log(drive, 'outcome_integrated', outcome=oid, artifact=str(target))
        return
    trailer = f'Coord-Assignment: {assignment}'
    if not git(integration, 'log', '--format=%H', '--fixed-strings', '--grep', trailer):
        applied = git(integration, 'apply', '--index', '--binary', str(patch), check=False)
        if applied.returncode:
            git(integration, 'reset', '--hard', 'HEAD')
            retry(task_dir, drive, state, oid, 'The change no longer applies on top of the integrated work '
                  f'(another outcome landed first): {applied.stderr.strip()}. Redo it against the current base.',
                  counted=False)
            return
        message = (f"coord({oid}): {item['contract']['objective'][:60]}\n\n"
                   f"Coord-Task: {state['id']}\n{trailer}\n")
        identity = [] if git(integration, 'config', 'user.name', check=False).stdout.strip() else \
            ['-c', 'user.name=coordinator', '-c', 'user.email=coordinator@localhost']
        subprocess.run(['git', *identity, '-C', str(integration), 'commit', '-q', '-m', message], check=True,
                       capture_output=True)
    receipt = integration / PACKAGE_DIR / 'integrated' / f'{oid}-{assignment}.patch'
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(patch.read_bytes())
    mutate(task_dir, drive, lambda s, p: outcomes.integrate(s, oid, receipt))
    log(drive, 'outcome_integrated', outcome=oid, commit=git(integration, 'rev-parse', 'HEAD'))


def goal_phase(task_dir, drive):
    state = tasks.load(task_dir)
    plan = state['outcome_plan']
    live = [oid for oid, item in plan['outcomes'].items()
            if (item.get('attempt') or {}).get('status') not in {None, 'finished', 'stopped'}]
    if drive.get('replan'):
        if live:
            for oid in live:
                flags = outcome_record(drive, oid)['flags'].get(plan['outcomes'][oid]['attempt']['id'], {})
                if 'stopping' not in flags:
                    stop_attempt(task_dir, drive, oid, 'replan')
            return
        replan = drive.pop('replan')
        open_replan(task_dir, drive, state, {'reason': replan['reason'], 'from_outcome': replan['outcome']},
                    replan.get('guidance'))
        return
    replan_request = find(drive['requests'], f"replan-{drive['goal_rounds']}")
    if replan_request is not None and replan_request['status'] in {'open', 'answered', 'failed'}:
        if replan_request['status'] == 'answered':
            apply_plan(task_dir, drive, replan_request, replan=True)
        return
    if any(not is_integrated(state, oid) for oid in plan['outcomes']):
        return
    gate = plan.get('goal_verification')
    manifest = {oid: outcomes.integrated(state, oid) for oid in plan['outcomes']}
    if not gate or gate.get('manifest') != manifest:
        gate = mutate(task_dir, drive, lambda s, p: outcomes.verify_goal(s, limit(drive, 'check_timeout')))
        log(drive, 'goal_checked', passed=outcomes.passed(gate['checks'], plan['goal_checks']))
    if outcomes.passed(gate['checks'], plan['goal_checks']):
        complete(task_dir, drive)
        return
    failing = [{'id': c['id'], 'argv': c['argv'], 'exit_code': c['exit_code'], 'stdout_tail': tail(c['stdout'], 2000),
                'stderr_tail': tail(c['stderr'], 2000)} for c in gate['checks'] if c['exit_code'] != 0]
    drive['goal_rounds'] += 1
    if drive['goal_rounds'] > limit(drive, 'goal_rounds') + drive.get('goal_allowance', 0):
        open_question(drive, 'goal_unmet', f"goal-unmet-{drive['goal_rounds']}",
                      f"Every outcome passed on its own, but the combined goal checks still fail after "
                      f"{drive['goal_rounds'] - 1} rounds: {', '.join(c['id'] for c in failing)}. "
                      'How should I proceed?', {'failing': failing})
        return
    open_replan(task_dir, drive, state, {'goal_checks_failed': failing})


def open_replan(task_dir, drive, state, evidence, guidance=None):
    key = f"replan-{drive['goal_rounds']}"
    if find(drive['requests'], key) and find(drive['requests'], key)['status'] != 'applied':
        drive['goal_rounds'] += 1
        key = f"replan-{drive['goal_rounds']}"
    open_request(drive, 'decompose', key, plan_context(task_dir, drive, state, 'replan', evidence, guidance))


def complete(task_dir, drive):
    patch_file = Path(task_dir) / '.drive-complete.json'
    tasks.atomic_write(patch_file, json.dumps({'status': 'completed', 'details': {
        'phase': 'done', 'next_action': (f"Review artifacts in {drive['integration']}" if artifact_delivery(drive)
                                       else f"Review and merge branch {drive['branch']}")}}) + '\n')
    try:
        state_mutate(task_dir, drive, 'checkpoint', patch_file=str(patch_file))
    except tasks.StateError as error:
        open_question(drive, 'completion_blocked', 'completion-' + hashlib.sha256(str(error).encode()).hexdigest()[:8],
                      f'All goal checks pass, but the task cannot close yet: {error}', {'error': str(error)})
        return
    log(drive, 'task_completed', branch=drive['branch'])


def consume_questions(task_dir, drive):
    """Replies that unblock judgment or goal work; escalations are consumed by their outcome."""
    for question in drive['questions'].values():
        if question['status'] != 'replied':
            continue
        kind = question['kind']
        if kind == 'judgment_failed':
            request = drive['requests'][question['payload']['request']]
            request.update(status='open', errors=[])
            request['context']['user_guidance'] = question['reply']
        elif kind == 'goal_unmet':
            drive['goal_allowance'] = drive.get('goal_allowance', 0) + 1
            open_replan(task_dir, drive, tasks.load(task_dir), {'goal_checks_failed': question['payload']['failing']},
                        question['reply'])
        elif kind != 'completion_blocked':
            continue
        question['status'] = 'resolved'


def advance(task_dir):
    """Do every deterministic step available now; return what the task is waiting on."""
    task_dir = Path(task_dir).resolve()
    with driving(task_dir) as drive:
        state = tasks.load(task_dir)
        if state['status'] != 'completed':
            consume_questions(task_dir, drive)
            if not state['selection']:
                selection_phase(task_dir, drive, state)
                state = tasks.load(task_dir)
            if state['selection']:
                if 'outcome_plan' not in state:
                    plan_phase(task_dir, drive, state)
                else:
                    outcomes_phase(task_dir, drive)
                    if not drive.get('halted'):
                        goal_phase(task_dir, drive)
        return summary(task_dir, drive)


# --------------------------------------------------------------------------- host profile

def profile_path():
    """Same location rules as coordinator-setup's host_profile.py."""
    explicit = os.environ.get('COORDINATOR_CONFIG_HOME')
    if explicit:
        root = Path(explicit)
        if not root.is_absolute():
            raise DriveError('COORDINATOR_CONFIG_HOME must be absolute')
    else:
        configured = os.environ.get('XDG_CONFIG_HOME', '')
        root = (Path(configured) if Path(configured).is_absolute() else Path.home() / '.config') / 'coordinator'
    return root / 'host.json'


def profile_driver():
    """The profile's driver entry, or {} when there is no profile or no driver yet."""
    path = profile_path()
    if not path.is_file():
        return {}
    entry = json.loads(path.read_text()).get('adapters', {}).get('driver')
    return entry if isinstance(entry, dict) else {}


def doctor(workers=None, delivery='patch'):
    """Is this host ready for driven tasks? Lists every problem rather than the first."""
    path = profile_path()
    problems = []
    if delivery == 'patch' and not shutil.which('git'):
        problems.append('git is not on PATH')
    driver = {}
    if workers is not None:
        driver = {'workers': workers}
    elif not path.is_file():
        problems.append(f'no host profile at {path}')
    else:
        try:
            driver = profile_driver()
        except (ValueError, OSError) as error:
            problems.append(f'host profile is unreadable: {error}')
        if not driver.get('workers'):
            problems.append('the host profile has no adapters.driver workers')
    if not driver.get('workers') and workers is not None:
        problems.append('configure at least one worker route')
    if not Path('/proc/self/stat').is_file() and any(w.get('runtime') != 'native' for w in driver.get('workers', [])):
        problems.append('the driven runtime needs Linux /proc (WSL2 works)')
    for worker in driver.get('workers', []):
        if worker.get('runtime') == 'native':
            continue
        if not shutil.which(worker['argv'][0]):
            problems.append(f"worker command {worker['argv'][0]!r} for "
                            f"{worker['route'].get('harness')}/{worker['route'].get('model')} is not on PATH")
    if driver.get('judge') and not shutil.which(driver['judge'][0]):
        problems.append(f"judge command {driver['judge'][0]!r} is not on PATH")
    return {'ready': not problems, 'profile_path': str(path), 'problems': problems,
            'workers': [w['route'] for w in driver.get('workers', [])], 'judge': driver.get('judge'),
            'next': None if not problems else 'Run the coordinator-setup driver interview with the user, then retry.'}


# --------------------------------------------------------------------------- front-desk operations

def summary(task_dir, drive, evidence=False):
    """What the task waits on. Delivery evidence is included once done, or on request: the front desk
    reads this after every command, so per-call output stays small."""
    state = tasks.load(task_dir)
    rows = []
    for oid, item in (state.get('outcome_plan') or {}).get('outcomes', {}).items():
        record = outcome_record(drive, oid)
        if is_integrated(state, oid):
            status = 'integrated'
        elif record['blocked']:
            status = 'waiting on ' + ('user' if record['blocked'].startswith('q:') else 'judgment')
        elif item.get('attempt'):
            status = 'attempt ' + item['attempt'].get('status', '?')
        else:
            status = 'pending'
        rows.append({'id': oid, 'status': status, 'attempts': record['attempts'],
                     'objective': item['contract']['objective']})
    requests = [{'id': r['id'], 'kind': r['kind']} for r in drive['requests'].values() if r['status'] == 'open']
    questions = [{'id': q['id'], 'kind': q['kind'], 'prompt': q['prompt']}
                 for q in drive['questions'].values() if q['status'] == 'open']
    working = any(row['status'] == 'attempt working' or row['status'] == 'attempt delivery_unknown'
                  or row['status'] == 'attempt unknown' for row in rows)
    done = state['status'] == 'completed'
    host_actions = [{'id': a['id'], 'action': a['action'], 'outcome': a['outcome'], 'status': a['status']}
                    for a in drive.get('host_actions', {}).values() if a['status'] != 'answered']
    waiting = (None if done else 'user' if questions else 'judgment' if requests else
               'host' if host_actions else 'workers' if working else 'driver')
    plan = state.get('outcome_plan') or {}
    def check_evidence(checks):
        return [{k: v for k, v in c.items() if k not in {'stdout', 'stderr'}} |
                {'stdout_tail': tail(c.get('stdout', ''), 1500), 'stderr_tail': tail(c.get('stderr', ''), 1500)}
                for c in checks]
    result = {'task': state['id'], 'title': state['title'], 'status': state['status'], 'done': done,
              'waiting_on': waiting, 'branch': drive['branch'], 'integration': drive['integration'],
              'delivery': drive.get('delivery', 'patch'), 'host_actions': host_actions,
              'halted': bool(drive.get('halted')), 'outcomes': rows, 'requests': requests, 'questions': questions,
              'recent': [' '.join(filter(None, (e.get('event'), e.get('outcome')))) for e in drive['log'][-5:]]}
    if done or evidence:
        result['evidence'] = {
            'goal_checks': check_evidence((plan.get('goal_verification') or {}).get('checks', [])),
            'outcomes': [{'id': oid, 'artifact': item['integration']['artifact'],
                          'decision': item['acceptance']['decision'],
                          'checks': check_evidence(item['acceptance']['checks'])}
                         for oid, item in plan.get('outcomes', {}).items() if item.get('integration')]}
    return result


def confirm_selection(task_dir, question_id, user_message, pool=None):
    with driving(task_dir) as drive:
        question = drive['questions'].get(question_id)
        if not question or question['kind'] != 'confirm_selection' or question['status'] != 'open':
            raise DriveError('no open selection question ' + question_id)
        nonempty(user_message, 'user message')
        pool = pool or question['payload']['pool']
        tasks.validate_pool(pool)
        missing = [r for r in pool if worker_for(drive, r) is None]
        if missing:
            raise DriveError(f'no worker command is configured for {missing}')
        pool_file = Path(task_dir) / '.drive-pool.json'
        tasks.atomic_write(pool_file, json.dumps(pool) + '\n')
        state_mutate(task_dir, drive, 'select', pool_file=str(pool_file), confirmed=True,
                     source=f'user, via front desk: "{user_message.strip()}"')
        question.update(status='resolved', reply=user_message.strip())
        log(drive, 'selection_confirmed', pool=pool)
    return advance(task_dir)


def reply(task_dir, question_id, user_message):
    with driving(task_dir) as drive:
        question = drive['questions'].get(question_id)
        if not question or question['status'] != 'open':
            raise DriveError('no open question ' + question_id)
        if question['kind'] == 'confirm_selection':
            raise DriveError('use confirm-selection for harness choices')
        nonempty(user_message, 'user message')
        question.update(status='replied', reply=user_message.strip(), replied_at=tasks.now())
        log(drive, 'user_replied', question=question_id)
    return advance(task_dir)


def real_use(task_dir, status, source, evidence=None):
    with driving(task_dir) as drive:
        state_mutate(task_dir, drive, 'real-use', status=status, source=source, evidence=evidence)
        for question in drive['questions'].values():
            if question['kind'] == 'completion_blocked' and question['status'] == 'open':
                question['status'] = 'resolved'
        log(drive, 'real_use_recorded', status=status)
    return advance(task_dir)


def halt(task_dir, resume=False):
    with driving(task_dir) as drive:
        drive['halted'] = not resume
        log(drive, 'resumed' if resume else 'halted')
        if not resume:
            state = tasks.load(task_dir)
            for oid, item in (state.get('outcome_plan') or {}).get('outcomes', {}).items():
                if (item.get('attempt') or {}).get('status') not in {None, 'finished', 'stopped'}:
                    stop_attempt(task_dir, drive, oid, 'halt')
    return advance(task_dir)


def start(root, repo, goal, criteria, workers, title=None, constraints=(), authority=None,
          real_use_required=False, limits=None, delivery='patch', sources=()):
    repo = Path(repo).expanduser().resolve()
    if delivery not in {'patch', 'artifact'}:
        raise DriveError('delivery must be patch or artifact')
    if not repo.is_dir():
        raise DriveError('source workspace must be an existing directory')
    sources = list(dict.fromkeys(str(Path(source).expanduser().resolve()) for source in sources))
    if sources and delivery != 'artifact':
        raise DriveError('source repositories are for artifact delivery; a patch cites its own repository')
    for source in sources:
        if git(source, 'rev-parse', '--git-dir', check=False).returncode:
            raise DriveError(f'source repository must be a git checkout: {source}')
    if delivery == 'patch' and git(repo, 'rev-parse', '--show-toplevel', check=False).stdout.strip() != str(repo):
        raise DriveError('repo must be the root of a git repository')
    nonempty(goal, 'goal')
    criteria = [c.strip() for c in criteria if c and c.strip()]
    if not criteria:
        raise DriveError('give at least one acceptance criterion: what observable result means done?')
    if not isinstance(workers, list) or not workers:
        raise DriveError('configure at least one worker route and its command')
    seen_routes = set()
    for worker in workers:
        if not isinstance(worker, dict):
            raise DriveError('each worker must be an object')
        native = worker.get('runtime') == 'native'
        if set(worker) != ({'route', 'runtime'} if native else {'route', 'argv'}):
            raise DriveError('each worker needs route and argv, or route and runtime: native')
        tasks.validate_pool([worker['route']])
        identity = json.dumps(worker['route'], sort_keys=True)
        if identity in seen_routes:
            raise DriveError('each worker route must identify exactly one runtime/command')
        seen_routes.add(identity)
        if not native and (not outcomes.argv(worker['argv']) or '{prompt}' not in worker['argv']):
            raise DriveError('worker argv must be a list of strings containing a "{prompt}" element')
    unknown = set(limits or {}) - set(DEFAULT_LIMITS)
    if unknown:
        raise DriveError('unknown limits: ' + ', '.join(sorted(unknown)))
    if (limits or {}).get('checks_first', 'auto') not in CHECKS_FIRST_MODES:
        raise DriveError('checks_first must be "auto", true, or false')
    base = git(repo, 'rev-parse', 'HEAD') if delivery == 'patch' else None
    dirty = bool(git(repo, 'status', '--porcelain')) if delivery == 'patch' else False
    created = tasks.create(argparse.Namespace(title=title or goal[:80], objective=goal, project=str(repo),
                                              conversation=None, owner=None), Path(root))
    task_dir = Path(created['state_path']).parent
    task_id = created['state']['id']
    branch = f'coord/{task_id[:8]}' if delivery == 'patch' else None
    integration = task_dir / 'integration'
    if delivery == 'patch':
        git(repo, 'worktree', 'add', '-q', '-b', branch, str(integration), base)
    else:
        integration.mkdir()
    with tasks.locked(task_dir / '.write.lock'):
        state = tasks.load(task_dir)
        state['project'] = str(integration)
        state['status'] = 'active'
        state['details'].update(
            acceptance_criteria=criteria, constraints=list(constraints),
            authority=authority or ((f'Read source material at {repo}; write only in assigned artifact workspaces. '
                                     'No edits to the source, external mutations, pushing, or publishing.') if delivery == 'artifact'
                                    else (f'Change files only in this task\'s isolated worktrees; results land on branch '
                                          f'{branch}. No pushing, publishing, merging, or edits to the original checkout.')),
            phase='selection', next_action='Choose configured worker harness/model')
        state['revision'] += 1
        state['updated_at'] = tasks.now()
        tasks.save(task_dir, state)
    drive = {'version': 1, 'owner': created['state']['owner'], 'repo': str(repo), 'base': base, 'branch': branch,
             'delivery': delivery, 'sources': sources,
             'integration': str(integration), 'workers': workers, 'limits': dict(DEFAULT_LIMITS, **(limits or {})),
             'requests': {}, 'questions': {}, 'outcomes': {}, 'goal_rounds': 0, 'log': []}
    log(drive, 'task_started', base=base, branch=branch)
    save_drive(task_dir, drive)
    if real_use_required:
        state_mutate(task_dir, drive, 'real-use', status='required',
                     source='set at task start: the user said this changes a skill or workflow', evidence=None)
    result = advance(task_dir)
    if dirty:
        result['warnings'] = [f'Your checkout has uncommitted changes; the task starts from commit {base[:10]} '
                              'without them.']
    return result


# --------------------------------------------------------------------------- worker wrapper

def work(assignment, cwd, base, argv):
    """Run the worker, then package its changes and publish the report on its behalf."""
    code = subprocess.call(argv, cwd=cwd, stdin=subprocess.DEVNULL)
    package_work(assignment, cwd, base, code)
    return code


def package_work(assignment, cwd, base, code=0):
    """Publish a settled worker's patch or contracted file; native and process workers share packaging."""
    assignment_file = Path(assignment)
    run_dir = assignment_file.parent
    descriptor = json.loads(assignment_file.read_text())
    attempt_id = descriptor['attempt_id']
    package_dir = Path(cwd) / PACKAGE_DIR / attempt_id
    package_dir.mkdir(parents=True, exist_ok=True)
    if 'artifact' in descriptor['contract']:
        patch_file = Path(cwd) / descriptor['contract']['artifact']
        if not patch_file.is_file():
            tasks.atomic_write(run_dir / 'package.json', json.dumps({'status': 'missing_artifact', 'exit_code': code}) + '\n')
            return
        outcomes.file_ref(patch_file, cwd)
    else:
        git(cwd, 'add', '-A', '--', '.', EXCLUDE_PACKAGE)
        patch = subprocess.run(['git', '-C', cwd, 'diff', '--cached', '--binary', base, '--', '.', EXCLUDE_PACKAGE],
                               capture_output=True, check=True).stdout
        if not patch.strip():
            tasks.atomic_write(run_dir / 'package.json', json.dumps({'status': 'no_changes', 'exit_code': code}) + '\n')
            return
        patch_file = package_dir / 'changes.patch'
        patch_file.write_bytes(patch)
    summary_file = package_dir / 'summary.md'
    summary = summary_file.read_text(errors='replace').strip() if summary_file.is_file() else ''
    report = outcomes.report(assignment_file, patch_file, summary or None)
    tasks.atomic_write(run_dir / 'package.json', json.dumps(
        {'status': 'reported', 'report': report['report'], 'exit_code': code}) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    worker = sub.add_parser('_work', help=argparse.SUPPRESS)
    worker.add_argument('--assignment', required=True)
    worker.add_argument('--cwd', required=True)
    worker.add_argument('--base', required=True)
    worker.add_argument('argv', nargs=argparse.REMAINDER)
    red_parser = sub.add_parser('_red', help=argparse.SUPPRESS)
    red_parser.add_argument('--checks', required=True)
    args = parser.parse_args(argv)
    if args.command == '_red':
        return red(json.loads(args.checks), Path.cwd())
    command = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
    return work(args.assignment, args.cwd, args.base, command)


if __name__ == '__main__':
    raise SystemExit(main())
