#!/usr/bin/env python3
"""Code-driven coordinator runtime. Code owns order and gates; the AI answers typed judgments.

`advance()` performs every deterministic step it can: worktrees, worker launch,
observation, independent checks and claimcheck, patch integration, goal checks,
and completion. It stops only to wait for workers, for a typed judgment request
(harness, decompose, assess, inspect), or for a user question. Judgment answers
are validated against their schema before anything acts on them; an invalid
answer is returned with its error, a bounded number of times, then escalated.

Isolation: each outcome works in its own git worktree under the task directory.
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
import re
import shlex
import subprocess
import sys
import time
import uuid

import coord_outcomes as outcomes
import coord_runtime as runtime
import coord_state as tasks

SELF = Path(__file__).resolve()
JUDGMENT_DOCS = SELF.parents[1] / 'references' / 'judgments'
DRIVE_FILE = 'drive.json'
PACKAGE_DIR = '.coord'
EXCLUDE_PACKAGE = ':(exclude)' + PACKAGE_DIR
DEFAULT_LIMITS = {'attempts_per_outcome': 3, 'goal_rounds': 3, 'judgment_retries': 2,
                  'stall_seconds': 900, 'check_timeout': 300, 'unknown_grace_seconds': 120}
OUTCOME_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,39}')
TAIL = 4000


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
            return worker['argv']
    return None


def route_matches(configured, route):
    return all(configured.get(key) == route.get(key) for key in ('harness', 'model', 'provider')
               if configured.get(key) or route.get(key))


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
                  '"authority": str, "needs": [outcome ids], "checks": [{"id": str, "argv": [str]}]}], '
                  '"goal_checks": [{"id": str, "argv": [str]}], "rationale": str}'),
    'assess': '{"action": one of context.actions, "reason": str, "guidance"?: str, "question"?: str}',
    'inspect': '{"verdict": "accept" | "reject", "reason": str, "feedback"?: str}',
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
        missing = [r for r in answer['pool'] if command_for(drive, r) is None]
        if missing:
            raise DriveError(f'no worker command is configured for {missing}; choose from context.routes')
    elif kind == 'decompose':
        if set(answer) != {'outcomes', 'goal_checks', 'rationale'}:
            raise DriveError('decompose answer needs exactly outcomes, goal_checks, rationale')
        nonempty(answer['rationale'], 'rationale')
        if not isinstance(answer['outcomes'], list) or not answer['outcomes']:
            raise DriveError('outcomes must be a non-empty list')
        for entry in answer['outcomes']:
            if not isinstance(entry, dict) or set(entry) != OUTCOME_FIELDS:
                raise DriveError('each outcome needs exactly ' + ', '.join(sorted(OUTCOME_FIELDS)))
            if not isinstance(entry['id'], str) or not OUTCOME_ID.fullmatch(entry['id']):
                raise DriveError(f"outcome id {entry['id']!r} must be a lowercase slug")
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
    elif kind == 'inspect':
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
    path = Path(task_dir) / 'worktrees' / oid
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        git(drive['integration'], 'worktree', 'add', '--detach', str(path), 'HEAD')
    return path


def reset_worktree(path, head):
    git(path, 'checkout', '--detach', '--force', head)
    git(path, 'clean', '-fd', '-e', PACKAGE_DIR)  # previous attempts' patches stay as evidence


def worker_instructions(feedback):
    def build(assignment, path):
        contract = assignment['contract']
        cwd = contract['cwd']
        summary = Path(cwd) / PACKAGE_DIR / assignment['attempt_id'] / 'summary.md'
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
        ]
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
    head = git(drive['integration'], 'rev-parse', 'HEAD')
    reset_worktree(worktree, head)
    pool = state['selection']
    route = pool[record['attempts'] % len(pool)]  # rotate across the confirmed pool on retries
    command = [sys.executable, str(SELF), '_work', '--assignment', '{assignment}', '--cwd', '{cwd}',
               '--base', head, '--', *command_for(drive, route)]
    build = worker_instructions(record['feedback'])
    started = mutate(task_dir, drive, lambda s, p: runtime.start(s, p, oid, 'process', route, 'bounded_worker',
                                                                  [], command, instructions=build))
    record['attempts'] += 1
    record['progress'] = {'signature': None, 'at': now_ts()}
    log(drive, 'attempt_started', outcome=oid, attempt=started['attempt_id'], route=route, base=head)


def progress_signature(attempt, worktree):
    run_dir = Path(attempt['run_dir'])
    sizes = [(run_dir / name).stat().st_size if (run_dir / name).exists() else 0
             for name in ('stdout.log', 'stderr.log')]
    status = git(worktree, 'status', '--porcelain', '--', '.', EXCLUDE_PACKAGE, check=False).stdout
    diff = git(worktree, 'diff', '--', '.', EXCLUDE_PACKAGE, check=False).stdout
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
    contract = outcomes.outcome_of(state, oid)['contract']
    mutate(task_dir, drive, lambda s, p: outcomes.revise(s, oid, copy.deepcopy(contract)))


def stop_attempt(task_dir, drive, oid, reason, guidance=None):
    record = outcome_record(drive, oid)
    state = tasks.load(task_dir)
    attempt = outcomes.outcome_of(state, oid).get('attempt') or {}
    if attempt.get('status') in {'finished', 'stopped'}:
        record['flags'].setdefault(attempt['id'], {})['stopping'] = {'reason': reason, 'guidance': guidance}
        return
    try:
        mutate(task_dir, drive, lambda s, p: runtime.control(s, oid, 'stop'))
    except tasks.StateError as error:
        # Identity unknown: the unknown-attempt path reconciles it once no process remains.
        log(drive, 'attempt_stop_deferred', outcome=oid, error=str(error))
    record['flags'].setdefault(attempt['id'], {})['stopping'] = {'reason': reason, 'guidance': guidance}
    log(drive, 'attempt_stop_requested', outcome=oid, reason=reason)


# --------------------------------------------------------------------------- phases

def selection_phase(task_dir, drive, state):
    request = find(drive['requests'], 'harness')
    if request is None:
        details = state['details']
        open_request(drive, 'harness', 'harness', {
            'goal': details['objective'], 'acceptance_criteria': details['acceptance_criteria'],
            'routes': [w['route'] for w in drive['workers']],
            'recent_choices': recent_choices(task_dir, drive['repo'])})
    elif request['status'] == 'answered':
        value = request['answer']
        open_question(drive, 'confirm_selection', 'confirm_selection',
                      'Workers would run on ' + ', '.join(f"{r['harness']}/{r['model']}" for r in value['pool'])
                      + f". Why: {value['rationale']} OK to use these?", {'pool': value['pool']})
        request['status'] = 'applied'


def recent_choices(task_dir, repo):
    """Confirmed choices for the same repository, whether its tasks were driven or manual."""
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
    files = git(integration, 'ls-files', check=False).stdout.splitlines()
    context = {'mode': mode, 'goal': details['objective'], 'acceptance_criteria': details['acceptance_criteria'],
               'constraints': details['constraints'], 'authority': details['authority'],
               'repository': integration, 'files': files[:400] + (['...'] if len(files) > 400 else []),
               'rules': ['Outcome checks run from that outcome\'s isolated worktree root.',
                         'Goal checks run from the repository root after every outcome is integrated.',
                         'Each check is argv run without a shell; exit code 0 means pass.',
                         'An outcome may only need outcomes listed earlier.']}
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


def apply_plan(task_dir, drive, request, replan):
    value = request['answer']
    try:
        spec = {'outcomes': [], 'goal_checks': value['goal_checks']}
        for entry in value['outcomes']:
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
    for entry in value['outcomes']:
        drive['outcomes'][entry['id']] = {'attempts': 0, 'allowance': 0, 'feedback': [], 'blocked': None,
                                          'progress': {}, 'flags': {}}
    log(drive, 'plan_applied', request=request['id'], outcomes=[e['id'] for e in value['outcomes']], replan=replan)


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
        contract = outcomes.outcome_of(state, oid)['contract']
        mutate(task_dir, drive, lambda s, p: outcomes.revise(s, oid, copy.deepcopy(contract)))
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
        if drive.get('replan') or drive.get('halted'):
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


def observe(task_dir, drive, oid):
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
        'diff_stat': git(attempt_cwd(state, oid), 'diff', '--stat', check=False).stdout,
        'actions': ['continue', 'retry', 'escalate', 'replan']})
    record['blocked'] = request['id']


def attempt_cwd(state, oid):
    return outcomes.outcome_of(state, oid)['contract']['cwd']


def reconcile_if_gone(task_dir, drive, oid):
    """Code observes the process table; only a provably dead attempt is reconciled."""
    state = tasks.load(task_dir)
    attempt = outcomes.outcome_of(state, oid)['attempt']
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
            contract = item['contract']
            mutate(task_dir, drive, lambda s, p: outcomes.revise(s, oid, copy.deepcopy(contract)))
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
    result = json.loads(package.read_text()) if package.is_file() else {'status': 'missing'}
    if result['status'] != 'reported':
        reason = {'no_changes': 'The attempt finished without changing any files.',
                  'missing': 'The attempt ended before its changes were packaged.'}.get(result['status'], result['status'])
        stderr = read_tail(Path(attempt['run_dir']) / 'stderr.log', 1500)
        retry(task_dir, drive, state, oid, f"{reason} Exit code: {result.get('exit_code')}."
              + (f' stderr tail:\n{stderr}' if stderr else ''))
        return
    try:
        verification = mutate(task_dir, drive, lambda s, p: outcomes.verify_result(
            s, oid, result['report'], limit(drive, 'check_timeout')))
    except tasks.StateError as error:
        retry(task_dir, drive, tasks.load(task_dir), oid, f'Independent verification refused the result: {error}')
        return
    failing = [c for c in verification['checks'] if c['exit_code'] != 0]
    blockers = verification['claimcheck']['blockers']
    if failing or blockers:
        lines = [f"Check {c['id']} failed (exit {c['exit_code']}).\nstdout:\n{tail(c['stdout'], 1500)}\n"
                 f"stderr:\n{tail(c['stderr'], 1500)}" for c in failing]
        lines += [f'Your summary cites something that does not exist: {b}' for b in blockers]
        retry(task_dir, drive, tasks.load(task_dir), oid, '\n'.join(lines))
        return
    patch = Path(verification['artifact']['path']).read_text(errors='replace')
    open_request(drive, 'inspect', inspect_key, {
        'outcome': oid, 'contract': item['contract'], 'attempt': record['attempts'],
        'summary': json.loads(Path(result['report']).read_text()).get('summary'),
        'patch': patch if len(patch) <= 60000 else patch[:60000] + '\n[patch truncated; read the artifact file]',
        'patch_file': verification['artifact']['path'],
        'checks': [{'id': c['id'], 'argv': c['argv'], 'exit_code': c['exit_code'],
                    'stdout_tail': tail(c['stdout'], 1500)} for c in verification['checks']],
        'earlier_feedback': [f['text'] for f in record['feedback'][-3:]]})


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
        'phase': 'done', 'next_action': f"Review and merge branch {drive['branch']}"}}) + '\n')
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
            elif 'outcome_plan' not in state:
                plan_phase(task_dir, drive, state)
            else:
                outcomes_phase(task_dir, drive)
                if not drive.get('halted'):
                    goal_phase(task_dir, drive)
        return summary(task_dir, drive)


# --------------------------------------------------------------------------- front-desk operations

def summary(task_dir, drive):
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
    waiting = None if done else 'user' if questions else 'judgment' if requests else 'workers' if working else 'driver'
    return {'task': state['id'], 'title': state['title'], 'status': state['status'], 'done': done,
            'waiting_on': waiting, 'branch': drive['branch'], 'integration': drive['integration'],
            'halted': bool(drive.get('halted')), 'outcomes': rows, 'requests': requests, 'questions': questions,
            'recent': drive['log'][-8:]}


def confirm_selection(task_dir, question_id, user_message, pool=None):
    with driving(task_dir) as drive:
        question = drive['questions'].get(question_id)
        if not question or question['kind'] != 'confirm_selection' or question['status'] != 'open':
            raise DriveError('no open selection question ' + question_id)
        nonempty(user_message, 'user message')
        pool = pool or question['payload']['pool']
        tasks.validate_pool(pool)
        missing = [r for r in pool if command_for(drive, r) is None]
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
          real_use_required=False, limits=None):
    repo = Path(repo).expanduser().resolve()
    if git(repo, 'rev-parse', '--show-toplevel', check=False).stdout.strip() != str(repo):
        raise DriveError('repo must be the root of a git repository')
    nonempty(goal, 'goal')
    criteria = [c.strip() for c in criteria if c and c.strip()]
    if not criteria:
        raise DriveError('give at least one acceptance criterion: what observable result means done?')
    if not isinstance(workers, list) or not workers:
        raise DriveError('configure at least one worker route and its command')
    for worker in workers:
        if not isinstance(worker, dict) or set(worker) != {'route', 'argv'}:
            raise DriveError('each worker needs route and argv')
        tasks.validate_pool([worker['route']])
        if not outcomes.argv(worker['argv']) or '{prompt}' not in worker['argv']:
            raise DriveError('worker argv must be a list of strings containing a "{prompt}" element')
    unknown = set(limits or {}) - set(DEFAULT_LIMITS)
    if unknown:
        raise DriveError('unknown limits: ' + ', '.join(sorted(unknown)))
    base = git(repo, 'rev-parse', 'HEAD')
    dirty = bool(git(repo, 'status', '--porcelain'))
    created = tasks.create(argparse.Namespace(title=title or goal[:80], objective=goal, project=str(repo),
                                              conversation=None, owner=None), Path(root))
    task_dir = Path(created['state_path']).parent
    task_id = created['state']['id']
    branch = f'coord/{task_id[:8]}'
    integration = task_dir / 'integration'
    git(repo, 'worktree', 'add', '-q', '-b', branch, str(integration), base)
    with tasks.locked(task_dir / '.write.lock'):
        state = tasks.load(task_dir)
        state['project'] = str(integration)
        state['status'] = 'active'
        state['details'].update(
            acceptance_criteria=criteria, constraints=list(constraints),
            authority=authority or (f'Change files only in this task\'s isolated worktrees; results land on branch '
                                    f'{branch}. No pushing, publishing, merging, or edits to the original checkout.'),
            phase='selection', next_action='Choose and confirm worker harness/model')
        state['revision'] += 1
        state['updated_at'] = tasks.now()
        tasks.save(task_dir, state)
    drive = {'version': 1, 'owner': created['state']['owner'], 'repo': str(repo), 'base': base, 'branch': branch,
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
    assignment_file = Path(assignment)
    run_dir = assignment_file.parent
    attempt_id = json.loads(assignment_file.read_text())['attempt_id']
    package_dir = Path(cwd) / PACKAGE_DIR / attempt_id
    package_dir.mkdir(parents=True, exist_ok=True)
    code = subprocess.call(argv, cwd=cwd, stdin=subprocess.DEVNULL)
    git(cwd, 'add', '-A', '--', '.', EXCLUDE_PACKAGE)
    patch = subprocess.run(['git', '-C', cwd, 'diff', '--cached', '--binary', base, '--', '.', EXCLUDE_PACKAGE],
                           capture_output=True, check=True).stdout
    if not patch.strip():
        tasks.atomic_write(run_dir / 'package.json', json.dumps({'status': 'no_changes', 'exit_code': code}) + '\n')
        return code
    patch_file = package_dir / 'changes.patch'
    patch_file.write_bytes(patch)
    summary_file = package_dir / 'summary.md'
    summary = summary_file.read_text(errors='replace').strip() if summary_file.is_file() else ''
    report = outcomes.report(assignment_file, patch_file, summary or None)
    tasks.atomic_write(run_dir / 'package.json', json.dumps(
        {'status': 'reported', 'report': report['report'], 'exit_code': code}) + '\n')
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    worker = sub.add_parser('_work', help=argparse.SUPPRESS)
    worker.add_argument('--assignment', required=True)
    worker.add_argument('--cwd', required=True)
    worker.add_argument('--base', required=True)
    worker.add_argument('argv', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
    return work(args.assignment, args.cwd, args.base, command)


if __name__ == '__main__':
    raise SystemExit(main())
