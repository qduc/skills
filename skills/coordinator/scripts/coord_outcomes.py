#!/usr/bin/env python3
"""Outcome contracts and acceptance, independent of worker runtimes.

This is an opt-in extension of the existing task record. Worker reports are
files; only owner-fenced coordinator commands can change authoritative state.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import uuid

import coord_state as tasks
import coord_process

MAX_ARTIFACT_BYTES = 268_435_456
ACTIVE_LOCK_FD = None


def text(value):
    return isinstance(value, str) and bool(value.strip())


def argv(value):
    return isinstance(value, list) and bool(value) and all(text(x) for x in value)


def checks(value):
    if not isinstance(value, list) or not value:
        raise tasks.StateError('checks must be a non-empty array')
    ids = set()
    for check in value:
        if not isinstance(check, dict) or set(check) != {'id', 'argv'} or not text(check['id']) or not argv(check['argv']):
            raise tasks.StateError('each check requires an id and non-empty argv')
        if check['id'] in ids:
            raise tasks.StateError('duplicate check ID')
        ids.add(check['id'])


def contract(value):
    required = {'id', 'objective', 'rationale', 'scope', 'authority', 'cwd', 'needs', 'checks'}
    if not isinstance(value, dict) or set(value) != required:
        raise tasks.StateError('contract requires ' + ', '.join(sorted(required)))
    if any(not text(value[k]) for k in required - {'needs', 'checks'}):
        raise tasks.StateError('contract text fields must be non-empty')
    if not Path(value['cwd']).is_absolute() or not Path(value['cwd']).is_dir():
        raise tasks.StateError('contract cwd must be an existing absolute directory')
    if not isinstance(value['needs'], list) or any(not text(n) for n in value['needs']) or len(set(value['needs'])) != len(value['needs']):
        raise tasks.StateError('needs must contain unique outcome IDs')
    checks(value['checks'])


def file_ref(path, root=None):
    source = Path(path).resolve()
    if root and not source.is_relative_to(Path(root).resolve()):
        raise tasks.StateError('artifact is outside the assigned working directory')
    if not source.is_file() or source.stat().st_size > MAX_ARTIFACT_BYTES:
        raise tasks.StateError('artifact must be a file within the size limit')
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(source), 'sha256': digest.hexdigest()}


def unchanged(ref):
    return file_ref(ref['path']) == ref


def run_checks(specs, cwd, timeout):
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise tasks.StateError('verification timeout must be positive and finite')
    evidence = []
    for spec in specs:
        try:
            code, stdout, stderr = coord_process.run(spec['argv'], cwd, timeout)
            entry = dict(spec, cwd=str(Path(cwd).resolve()), exit_code=code,
                         stdout=stdout, stderr=stderr)
        except (subprocess.TimeoutExpired, OSError) as error:
            entry = dict(spec, cwd=str(Path(cwd).resolve()), exit_code=None, stdout='', stderr=str(error))
        evidence.append(entry)
    return evidence


def passed(evidence, specs):
    return (isinstance(evidence, list) and len(evidence) == len(specs)
            and all(e.get('id') == s['id'] and e.get('argv') == s['argv']
                    and type(e.get('exit_code')) is int and e['exit_code'] == 0
                    for e, s in zip(evidence, specs)))


def plan_of(state):
    plan = state.get('outcome_plan')
    if not isinstance(plan, dict) or plan.get('version') != 1:
        raise tasks.StateError('task has no outcome plan; initialize it with plan')
    return plan


def outcome_of(state, outcome_id):
    result = plan_of(state)['outcomes'].get(outcome_id)
    if result is None:
        raise tasks.StateError('unknown outcome: ' + outcome_id)
    return result


def goal_identity(state):
    details = state['details']
    return {k: copy.deepcopy(details[k]) for k in ('objective', 'authority', 'constraints', 'acceptance_criteria')}


def validate_record(state):
    """Validate optional records without upgrading legacy task files."""
    if 'outcome_plan' not in state:
        return
    plan = plan_of(state)
    if not isinstance(plan.get('outcomes'), dict) or not plan['outcomes']:
        raise tasks.StateError('outcome plan requires outcomes')
    checks(plan.get('goal_checks'))
    items = []
    for oid, item in plan['outcomes'].items():
        if not isinstance(item, dict):
            raise tasks.StateError('outcome must be an object')
        spec = item.get('contract')
        # Historical workspaces may have been retired; their contracts remain readable.
        if not isinstance(spec, dict) or spec.get('id') != oid or not text(item.get('assignment_id')):
            raise tasks.StateError('invalid outcome identity')
        checks(spec.get('checks'))
        items.append({'id': oid, 'status': 'pending', 'needs': spec.get('needs')})
    tasks.validate_details({'work_items': items})


def require_current_goal(state):
    if plan_of(state)['goal'] != goal_identity(state):
        raise tasks.StateError('goal or authority changed; explicitly replan before executing')


def accepted(state, oid):
    item = outcome_of(state, oid)
    result = item.get('acceptance')
    if not result or result['assignment_id'] != item['assignment_id']:
        raise tasks.StateError('outcome is not accepted: ' + oid)
    if (not unchanged(result['artifact']) or not unchanged(result['report'])
            or not passed(result['checks'], item['contract']['checks'])):
        raise tasks.StateError('accepted artifact or evidence changed: ' + oid)
    for dependency, identity in result['dependencies'].items():
        upstream = integrated(state, dependency)
        if upstream != identity:
            raise tasks.StateError('dependency changed: ' + dependency)
    return result


def integrated(state, oid):
    item = outcome_of(state, oid)
    receipt = item.get('integration')
    if not receipt or receipt['assignment_id'] != item['assignment_id'] or not unchanged(receipt['artifact']):
        raise tasks.StateError('outcome needs integration or revalidation: ' + oid)
    acceptance = accepted(state, oid)
    if acceptance['artifact']['sha256'] != receipt['artifact']['sha256']:
        raise tasks.StateError('integrated bytes differ from the accepted artifact')
    return {'assignment_id': item['assignment_id'], 'artifact': receipt['artifact']}


def completion_guard(state):
    if 'outcome_plan' not in state:
        return
    require_current_goal(state)
    plan = plan_of(state)
    manifest = {oid: integrated(state, oid) for oid in plan['outcomes']}
    gate = plan.get('goal_verification')
    if not gate or gate.get('manifest') != manifest or not passed(gate.get('checks'), plan['goal_checks']):
        raise tasks.StateError('independent integrated goal verification is required')
    if any(item.get('attempt', {}).get('status') not in {None, 'finished', 'stopped'} for item in plan['outcomes'].values()):
        raise tasks.StateError('settle all outcome attempts before completion')


def initialize(state, spec):
    if 'outcome_plan' in state:
        raise tasks.StateError('plan already exists; revise individual outcomes explicitly')
    if not isinstance(spec, dict) or set(spec) != {'outcomes', 'goal_checks'} or not isinstance(spec['outcomes'], list) or not spec['outcomes']:
        raise tasks.StateError('plan requires outcomes and goal_checks')
    checks(spec['goal_checks'])
    outcomes = {}
    for entry in spec['outcomes']:
        contract(entry)
        if entry['id'] in outcomes:
            raise tasks.StateError('duplicate outcome ID')
        outcomes[entry['id']] = {'contract': copy.deepcopy(entry), 'assignment_id': uuid.uuid4().hex, 'history': []}
    items = [{'id': oid, 'status': 'pending', 'needs': item['contract']['needs']} for oid, item in outcomes.items()]
    tasks.validate_details({'work_items': items})
    existing = state['details']['work_items']
    if existing and existing != items:
        raise tasks.StateError('plan must be initialized before dispatch; existing work items differ')
    state['details']['work_items'] = items
    state['outcome_plan'] = {'version': 1, 'goal': goal_identity(state), 'goal_checks': spec['goal_checks'], 'outcomes': outcomes}
    return state['outcome_plan']


def revise(state, oid, spec):
    require_current_goal(state)
    contract(spec)
    if spec['id'] != oid:
        raise tasks.StateError('revision must preserve the outcome ID')
    plan = plan_of(state)
    affected = {oid}
    while True:
        extra = {key for key, item in plan['outcomes'].items() if affected.intersection(item['contract']['needs'])}
        if extra <= affected:
            break
        affected |= extra
    if any(plan['outcomes'][key].get('attempt', {}).get('status') not in {None, 'finished', 'stopped'} for key in affected):
        raise tasks.StateError('reconcile and settle affected attempts before revision')
    for key in affected:
        item = plan['outcomes'][key]
        history = item.get('history', []) + [{k: copy.deepcopy(v) for k, v in item.items() if k != 'history'}]
        plan['outcomes'][key] = {'contract': spec if key == oid else item['contract'],
                                 'assignment_id': uuid.uuid4().hex, 'history': history}
    items = state['details']['work_items']
    for item in items:
        if item['id'] in affected:
            item.update(status='pending', needs=plan['outcomes'][item['id']]['contract']['needs'])
    tasks.validate_details({'work_items': items})
    plan.pop('goal_verification', None)
    state['status'] = 'active'
    return {'invalidated': sorted(affected)}


def replan(state, spec, decision):
    if not text(decision):
        raise tasks.StateError('replanning requires an explicit coordinator decision and authority source')
    previous = plan_of(state)
    if any(item.get('attempt', {}).get('status') not in {None, 'finished', 'stopped'}
           for item in previous['outcomes'].values()):
        raise tasks.StateError('reconcile and settle all attempts before replanning')
    state.setdefault('outcome_history', []).append(dict(copy.deepcopy(previous), decision=decision))
    state.pop('outcome_plan')
    state['details']['work_items'] = []
    state['status'] = 'active'
    return initialize(state, spec)


def dependencies(state, item):
    return {oid: integrated(state, oid) for oid in item['contract']['needs']}


def descriptor(state, oid, attempt_id, method):
    item = outcome_of(state, oid)
    return {'version': 1, 'task_id': state['id'], 'outcome_id': oid,
            'assignment_id': item['assignment_id'], 'attempt_id': attempt_id,
            'goal': copy.deepcopy(plan_of(state)['goal']),
            'contract': copy.deepcopy(item['contract']), 'dependencies': dependencies(state, item),
            'method': method}


def report(assignment_file, artifact):
    assignment = json.loads(Path(assignment_file).read_text())
    ref = file_ref(artifact, assignment['contract']['cwd'])
    result = {k: assignment[k] for k in ('task_id', 'outcome_id', 'assignment_id', 'attempt_id')}
    result.update(artifact=ref, dependencies=assignment['dependencies'], disposition='worker_evidence')
    # Report publication never loads or writes the authoritative task record.
    path = Path(assignment_file).parent / ('report-' + uuid.uuid4().hex + '.json')
    tasks.atomic_write(path, json.dumps(result, indent=2) + '\n')
    return {'report': str(path), 'disposition': 'worker_evidence'}


def verify_result(state, oid, report_path, timeout):
    require_current_goal(state)
    item = outcome_of(state, oid)
    report_ref = file_ref(report_path)
    candidate = json.loads(Path(report_path).read_text())
    attempt = item.get('attempt', {})
    for key, expected in {'task_id': state['id'], 'outcome_id': oid, 'assignment_id': item['assignment_id'],
                          'attempt_id': attempt.get('id'), 'dependencies': dependencies(state, item)}.items():
        if candidate.get(key) != expected or expected is None:
            raise tasks.StateError('stale or mismatched result: ' + key)
    if attempt.get('status') not in {'finished', 'stopped'}:
        raise tasks.StateError('settle the worker before independent verification')
    actual = file_ref(candidate['artifact']['path'], item['contract']['cwd'])
    if actual != candidate['artifact']:
        raise tasks.StateError('reported artifact changed')
    evidence = run_checks(item['contract']['checks'], item['contract']['cwd'], timeout)
    if file_ref(actual['path']) != actual:
        raise tasks.StateError('artifact changed during verification')
    item.pop('acceptance', None)
    item.pop('integration', None)
    item['verification'] = {'assignment_id': item['assignment_id'], 'attempt_id': attempt['id'],
                            'artifact': actual, 'report': report_ref, 'checks': evidence,
                            'dependencies': candidate['dependencies'], 'at': tasks.now()}
    plan_of(state).pop('goal_verification', None)
    return item['verification']


def accept(state, oid, decision):
    require_current_goal(state)
    if not text(decision):
        raise tasks.StateError('acceptance requires the coordinator inspection decision')
    item = outcome_of(state, oid)
    evidence = item.get('verification')
    if not evidence or evidence['assignment_id'] != item['assignment_id']:
        raise tasks.StateError('current independent verification is required')
    if not passed(evidence['checks'], item['contract']['checks']) or not unchanged(evidence['artifact']) or not unchanged(evidence['report']):
        raise tasks.StateError('verification failed or evidence changed')
    if evidence['dependencies'] != dependencies(state, item):
        raise tasks.StateError('verification dependencies changed')
    item['acceptance'] = dict(copy.deepcopy(evidence), decision=decision, owner=state['owner'], accepted_at=tasks.now())
    return item['acceptance']


def integrate(state, oid, target):
    require_current_goal(state)
    item = outcome_of(state, oid)
    result = accepted(state, oid)
    ref = file_ref(target, state['project'])
    if ref['sha256'] != result['artifact']['sha256']:
        raise tasks.StateError('integrated bytes differ from the accepted artifact')
    # Incorporation is performed by the coordinator, then reconciled here. A
    # crash between those operations is recoverable by inspecting the target.
    item['integration'] = {'assignment_id': item['assignment_id'], 'artifact': ref, 'at': tasks.now()}
    for work in state['details']['work_items']:
        if work['id'] == oid:
            work['status'] = 'completed'
    plan_of(state).pop('goal_verification', None)
    return item['integration']


def verify_goal(state, timeout):
    require_current_goal(state)
    plan = plan_of(state)
    before = {oid: integrated(state, oid) for oid in plan['outcomes']}
    evidence = run_checks(plan['goal_checks'], state['project'], timeout)
    after = {oid: integrated(state, oid) for oid in plan['outcomes']}
    if before != after:
        raise tasks.StateError('integrated artifacts changed during goal verification')
    plan['goal_verification'] = {'manifest': after, 'checks': evidence, 'at': tasks.now()}
    return plan['goal_verification']


def mutate(task_dir, owner, revision, action):
    global ACTIVE_LOCK_FD
    path = Path(task_dir).resolve()
    with tasks.locked(path / '.write.lock') as lock:
        state = tasks.load(path)
        tasks.check_owner(state, owner)
        tasks.check_revision(state, state['revision'] if revision == 'latest' else revision)
        if state['archived_at'] or state['status'] == 'completed':
            raise tasks.StateError('task is completed or archived')
        previous_fd = ACTIVE_LOCK_FD
        ACTIVE_LOCK_FD = lock.fileno()
        try:
            result = action(state, path)
        finally:
            ACTIVE_LOCK_FD = previous_fd
        validate_record(state)
        state['revision'] += 1
        state['updated_at'] = tasks.now()
        warnings = tasks.save(path, state)
    return {'result': result, 'revision': state['revision'], 'warnings': warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    worker = sub.add_parser('report')
    worker.add_argument('--assignment-file', required=True)
    worker.add_argument('--artifact', required=True)
    for name in ('plan', 'replan', 'revise', 'verify', 'accept', 'integrate', 'verify-goal'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--task-dir', required=True)
        cmd.add_argument('--owner', required=True)
        cmd.add_argument('--revision', required=True, type=lambda v: v if v == 'latest' else int(v))
        if name in {'revise', 'verify', 'accept', 'integrate'}:
            cmd.add_argument('--outcome', required=True)
        if name in {'plan', 'replan', 'revise'}:
            cmd.add_argument('--spec-file', required=True)
        if name == 'verify':
            cmd.add_argument('--report', required=True)
        if name in {'accept', 'replan'}:
            cmd.add_argument('--decision', required=True)
        if name == 'integrate':
            cmd.add_argument('--artifact', required=True)
        if name in {'verify', 'verify-goal'}:
            cmd.add_argument('--timeout', type=float, default=60)
    args = parser.parse_args()
    try:
        if args.command == 'report':
            result = report(args.assignment_file, args.artifact)
        else:
            def action(state, path):
                if args.command == 'plan':
                    return initialize(state, json.loads(Path(args.spec_file).read_text()))
                if args.command == 'replan':
                    return replan(state, json.loads(Path(args.spec_file).read_text()), args.decision)
                if args.command == 'revise':
                    return revise(state, args.outcome, json.loads(Path(args.spec_file).read_text()))
                if args.command == 'verify':
                    return verify_result(state, args.outcome, args.report, args.timeout)
                if args.command == 'accept':
                    return accept(state, args.outcome, args.decision)
                if args.command == 'integrate':
                    return integrate(state, args.outcome, args.artifact)
                return verify_goal(state, args.timeout)
            result = mutate(args.task_dir, args.owner, args.revision, action)
        print(json.dumps({'ok': True, **result}, indent=2))
        return 0
    except (tasks.StateError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
