#!/usr/bin/env python3
"""Native host and non-interactive process runtimes for outcome assignments.

The core sees attempt IDs, capabilities, reports, and uncertainty. Process IDs,
host handles, launch receipts, and harness argv are private runtime details.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid

import coord_outcomes as outcomes
import coord_state as tasks
import coord_process

_LAUNCHERS = {}


def capabilities(runtime):
    if runtime == 'native':
        return {'start': 'host_request', 'observe': 'host_observation', 'correct': 'host_request',
                'stop': 'host_request', 'resume': 'reconcile_handle'}
    if runtime == 'process':
        return {'start': 'subprocess', 'observe': 'receipt_and_process', 'correct': False,
                'stop': 'owned_process_group', 'resume': 'reconcile_receipt'}
    raise tasks.StateError('unsupported runtime: ' + runtime)


def method(name, catalogs):
    command = [sys.executable, str(Path(__file__).with_name('coord_protocol.py')), 'resolve', '--protocol', name]
    for catalog in catalogs:
        command += ['--catalog', str(catalog)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise tasks.StateError(result.stdout.strip() or result.stderr.strip())
    return json.loads(result.stdout)


def process_identity(pid):
    """Linux start time prevents a recycled PID from being controlled."""
    try:
        data = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        if data[0] == 'Z':
            return None
        return data[19]
    except (OSError, IndexError):
        return None


def process_live(resource):
    # Missing identities indicate uncertainty, never a positive identity match.
    identity = resource.get('identity')
    return identity is not None and process_identity(resource.get('pid')) == identity


def assignment_prompt(assignment, path):
    script = Path(path).parent / 'reporter' / 'coord_outcomes.py'
    return (
        f'Read the complete outcome assignment at {path}. Execute its objective within its scope and authority. '
        'Dependencies and acceptance criteria are fixed by the coordinator. '
        'When a protocol skill is selected, read its snapshot named in method.skill and use it for engineering method only. '
        'Do not change the assignment, protocol snapshot, reporter, checks, or authoritative task state. '
        'Do not spawn child agents, detach background jobs, or ask the user questions. '
        'Produce a file artifact inside contract.cwd. Run local checks, then publish a report with '
        f'{sys.executable} {script} report --assignment-file {path} --artifact <absolute-artifact-path>. '
        'Publication is evidence, not acceptance. If blocked, write blocker.json beside the assignment '
        'with the exact missing decision and stop; do not invent authority. Finish after reporting.'
    )


def start(state, task_dir, oid, runtime, route, protocol, catalogs, command=None):
    outcomes.require_current_goal(state)
    capabilities(runtime)
    tasks.validate_pool([route])
    selection = state.get('selection')
    if not selection or route not in selection:
        raise tasks.StateError('runtime route must be in the task confirmed selection pool')
    item = outcomes.outcome_of(state, oid)
    if item.get('attempt'):
        raise tasks.StateError('attempt already recorded; reconcile it before an explicit revision')
    selected = method(protocol, catalogs)
    attempt_id = uuid.uuid4().hex
    run_dir = task_dir / 'attempts' / attempt_id
    assignment_file = run_dir / 'assignment.json'
    assignment = outcomes.descriptor(state, oid, attempt_id, selected)
    if runtime == 'process' and not outcomes.argv(command):
        raise tasks.StateError('process runtime requires explicit command argv')
    run_dir.mkdir(parents=True)
    reporter = run_dir / 'reporter'
    reporter.mkdir()
    for name in ('coord_outcomes.py', 'coord_state.py', 'coord_process.py'):
        tasks.atomic_write(reporter / name, Path(__file__).with_name(name).read_text())
    if selected.get('skill'):
        source = Path(selected['skill'])
        snapshot = run_dir / 'protocol.md'
        tasks.atomic_write(snapshot, source.read_text())
        assignment['method'] = dict(selected, origin=outcomes.file_ref(source), skill=str(snapshot),
                                    snapshot=outcomes.file_ref(snapshot))
    tasks.atomic_write(assignment_file, json.dumps(assignment, indent=2) + '\n')
    attempt = {'id': attempt_id, 'runtime': runtime, 'route': route, 'status': 'start_intended',
               'assignment_file': str(assignment_file), 'assignment_ref': outcomes.file_ref(assignment_file),
               'run_dir': str(run_dir), 'created_at': tasks.now()}
    item['attempt'] = attempt
    # Persist launch intent before calling either host or process launcher.
    state['revision'] += 1
    state['updated_at'] = tasks.now()
    tasks.save(task_dir, state)
    prompt = assignment_prompt(assignment, assignment_file)
    tasks.atomic_write(run_dir / 'prompt.txt', prompt)
    if runtime == 'native':
        attempt['status'] = 'delivery_unknown'
        return {'attempt_id': attempt_id, 'request': {'action': 'spawn', 'message': prompt},
                'assignment_file': str(assignment_file), 'capabilities': capabilities(runtime)}
    replacements = {'{prompt}': prompt, '{assignment}': str(assignment_file), '{cwd}': item['contract']['cwd']}
    expanded = [replacements.get(part, part) for part in command]
    receipt = run_dir / 'receipt.json'
    launch = {'version': 1, 'attempt_id': attempt_id, 'argv': expanded, 'cwd': item['contract']['cwd']}
    tasks.atomic_write(run_dir / 'launch.json', json.dumps(launch) + '\n')
    # A separate launcher persists process identity even if the coordinator dies.
    # It inherits the owner lock until launch returns, as the legacy lifecycle does.
    launcher = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_launch',
                                 '--run-dir', str(run_dir)], start_new_session=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                pass_fds=(outcomes.ACTIVE_LOCK_FD,) if outcomes.ACTIVE_LOCK_FD is not None else (),
                                env=dict(os.environ, COORD_OUTCOME_LOCK_FD=str(outcomes.ACTIVE_LOCK_FD or '')))
    attempt['launcher'] = {'pid': launcher.pid, 'identity': process_identity(launcher.pid)}
    _LAUNCHERS[attempt_id] = launcher
    attempt['status'] = 'delivery_unknown'
    return {'attempt_id': attempt_id, 'receipt': str(receipt), 'capabilities': capabilities(runtime)}


def bind_native(state, oid, attempt_id, handle):
    item = outcomes.outcome_of(state, oid)
    attempt = item.get('attempt', {})
    if attempt.get('id') != attempt_id or attempt.get('runtime') != 'native' or not outcomes.text(handle):
        raise tasks.StateError('native handle does not match the current attempt')
    if attempt.get('handle') and attempt['handle'] != handle:
        raise tasks.StateError('native handle already bound')
    attempt.update(handle=handle, status='working')
    return attempt


def observe(state, oid, observation=None):
    attempt = outcomes.outcome_of(state, oid).get('attempt')
    if not attempt:
        raise tasks.StateError('outcome has no attempt')
    if not outcomes.unchanged(attempt['assignment_ref']):
        raise tasks.StateError('assignment descriptor changed')
    if attempt['runtime'] == 'native':
        if observation is None:
            return {'status': 'unknown', 'request': {'action': 'inspect', 'handle': attempt.get('handle')}}
        if (not isinstance(observation, dict) or not attempt.get('handle')
                or observation.get('handle') != attempt['handle']
                or observation.get('status') not in {'working', 'finished', 'stopped', 'unknown'}):
            raise tasks.StateError('host observation must match the bound native handle')
        attempt['status'] = observation['status']
        attempt['observation'] = observation
    else:
        receipt_file = Path(attempt['run_dir']) / 'receipt.json'
        if not receipt_file.exists():
            return {'status': 'unknown', 'reason': 'No launch receipt; inspect launcher, never redispatch automatically'}
        receipt = json.loads(receipt_file.read_text())
        if receipt.get('attempt_id') != attempt['id']:
            raise tasks.StateError('receipt belongs to another attempt')
        if receipt.get('status') == 'finished':
            attempt['status'] = 'finished'
        elif receipt.get('status') == 'failed':
            attempt['status'] = 'finished'
        elif receipt.get('status') == 'working':
            attempt['status'] = 'working' if process_live(receipt) else 'unknown'
        else:
            attempt['status'] = 'unknown'
        attempt['receipt'] = receipt
        launcher = _LAUNCHERS.get(attempt['id'])
        if launcher is not None and attempt['status'] == 'finished':
            launcher.wait(timeout=5)
            _LAUNCHERS.pop(attempt['id'], None)
    attempt['observed_at'] = tasks.now()
    root = Path(attempt['run_dir'])
    return {'status': attempt['status'], 'attempt_id': attempt['id'],
            'reports': [str(p) for p in sorted(root.glob('report-*.json'))],
            'blocker': str(root / 'blocker.json') if (root / 'blocker.json').exists() else None}


def control(state, oid, action, message=None):
    if action == 'correct':
        outcomes.require_current_goal(state)
    attempt = outcomes.outcome_of(state, oid).get('attempt')
    if not attempt:
        raise tasks.StateError('outcome has no attempt')
    if attempt['runtime'] == 'native':
        if not attempt.get('handle'):
            raise tasks.StateError('reconcile native delivery before controlling the attempt')
        return {'request': {'action': action, 'handle': attempt['handle'], 'message': message}}
    if action == 'correct':
        raise tasks.StateError('process runtime cannot accept mid-flight corrections; stop and revise explicitly')
    observe(state, oid)
    if attempt['status'] == 'finished':
        return {'status': 'finished'}
    receipt = attempt.get('receipt', {})
    if attempt['status'] != 'working' or not process_live(receipt):
        raise tasks.StateError('process identity unknown; reconcile before stopping')
    os.killpg(receipt['pid'], signal.SIGTERM)
    return {'status': 'stop_requested'}  # observation, not signalling, proves settlement


def reconcile(state, oid, attempt_id, evidence, decision):
    """Record explicit coordinator reconciliation; absence never triggers retry."""
    attempt = outcomes.outcome_of(state, oid).get('attempt', {})
    if attempt.get('id') != attempt_id or not outcomes.text(decision):
        raise tasks.StateError('reconciliation requires current attempt ID and inspection decision')
    ref = outcomes.file_ref(evidence)
    observation = json.loads(Path(evidence).read_text())
    if (not isinstance(observation, dict) or observation.get('attempt_id') != attempt_id
            or observation.get('status') not in {'finished', 'stopped', 'not_started'}
            or not outcomes.text(observation.get('basis'))):
        raise tasks.StateError('reconciliation evidence requires attempt_id, terminal status and observed basis')
    if attempt['runtime'] == 'process':
        resources = [attempt.get('launcher', {}), attempt.get('receipt', {})]
        receipt_file = Path(attempt['run_dir']) / 'receipt.json'
        if receipt_file.exists():
            receipt = json.loads(receipt_file.read_text())
            if receipt.get('attempt_id') != attempt_id:
                raise tasks.StateError('receipt belongs to another attempt')
            resources.append(receipt)
        for resource in resources:
            pid = resource.get('pid')
            if pid and (process_live(resource) or coord_process.live_group(pid)):
                raise tasks.StateError('known runtime resources remain live; settle them before reconciliation')
    attempt.setdefault('reconciliations', []).append({'evidence':ref, 'decision':decision, 'owner':state['owner'], 'at':tasks.now()})
    attempt['status'] = 'finished' if observation['status'] == 'finished' else 'stopped'
    return attempt


def launch(run_dir):
    with tasks.locked(Path(run_dir) / '.launch.lock'):
        return launch_once(run_dir)


def launch_once(run_dir):
    directory = Path(run_dir)
    spec = json.loads((directory / 'launch.json').read_text())
    receipt = directory / 'receipt.json'
    if receipt.exists():
        raise tasks.StateError('launch receipt already exists; refusing duplicate launch')
    tasks.atomic_write(receipt, json.dumps({'attempt_id': spec['attempt_id'], 'status': 'launch_intended'}) + '\n')
    process = None
    try:
        with (directory / 'stdout.log').open('w') as stdout, (directory / 'stderr.log').open('w') as stderr:
            process = subprocess.Popen(spec['argv'], cwd=spec['cwd'], stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            entry = {'attempt_id': spec['attempt_id'], 'status': 'working', 'pid': process.pid,
                     'identity': process_identity(process.pid)}
            tasks.atomic_write(receipt, json.dumps(entry) + '\n')
            inherited = os.environ.get('COORD_OUTCOME_LOCK_FD')
            if inherited:
                os.close(int(inherited))
            code = process.wait()
            coord_process.settle(process)
        tasks.atomic_write(receipt, json.dumps(dict(entry, status='finished', exit_code=code)) + '\n')
    except OSError as error:
        # A publication failure does not prove that execution never started.
        # Settle a created worker before issuing a terminal failure receipt.
        # If settlement itself fails, leave the existing receipt uncertain.
        if process is not None:
            coord_process.settle(process)
        tasks.atomic_write(receipt, json.dumps({'attempt_id': spec['attempt_id'], 'status': 'failed', 'error': str(error)}) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    discover = sub.add_parser('discover')
    discover.add_argument('--runtime', required=True, choices=['native', 'process'])
    hidden = sub.add_parser('_launch', help=argparse.SUPPRESS)
    hidden.add_argument('--run-dir', required=True)
    for name in ('start', 'bind-native', 'observe', 'control', 'reconcile'):
        cmd = sub.add_parser(name)
        for key in ('task-dir', 'owner', 'outcome'):
            cmd.add_argument('--' + key, required=True)
        cmd.add_argument('--revision', required=True, type=lambda v: v if v == 'latest' else int(v))
        if name == 'start':
            cmd.add_argument('--runtime', required=True, choices=['native', 'process'])
            cmd.add_argument('--route-file', required=True)
            cmd.add_argument('--protocol', default='bounded_worker')
            cmd.add_argument('--catalog', action='append', default=[])
            cmd.add_argument('--command-file')
        if name == 'bind-native':
            cmd.add_argument('--attempt-id', required=True)
            cmd.add_argument('--handle', required=True)
        if name == 'observe':
            cmd.add_argument('--observation-file')
        if name == 'control':
            cmd.add_argument('--action', choices=['stop', 'correct'], required=True)
            cmd.add_argument('--message')
        if name == 'reconcile':
            cmd.add_argument('--attempt-id', required=True)
            cmd.add_argument('--evidence-file', required=True)
            cmd.add_argument('--decision', required=True)
    args = parser.parse_args()
    try:
        if args.command == '_launch':
            launch(args.run_dir)
            return 0
        if args.command == 'discover':
            result = capabilities(args.runtime)
        else:
            def action(state, path):
                if args.command == 'start':
                    route = json.loads(Path(args.route_file).read_text())
                    command = json.loads(Path(args.command_file).read_text()) if args.command_file else None
                    return start(state, path, args.outcome, args.runtime, route, args.protocol, args.catalog, command)
                if args.command == 'bind-native':
                    return bind_native(state, args.outcome, args.attempt_id, args.handle)
                if args.command == 'observe':
                    observation = json.loads(Path(args.observation_file).read_text()) if args.observation_file else None
                    return observe(state, args.outcome, observation)
                if args.command == 'reconcile':
                    return reconcile(state, args.outcome, args.attempt_id, args.evidence_file, args.decision)
                return control(state, args.outcome, args.action, args.message)
            result = outcomes.mutate(args.task_dir, args.owner, args.revision, action)
        print(json.dumps({'ok': True, 'result': result}, indent=2))
        return 0
    except (tasks.StateError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
