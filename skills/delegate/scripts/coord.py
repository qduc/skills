#!/usr/bin/env python3
"""Front-desk commands for code-driven coordination.

The front desk talks with the user and drives the runtime only through these
commands. None of them can accept, integrate, or skip a gate; the driver does
those in code once the evidence and typed judgments allow it.

  doctor             is the host set up? (missing profile or workers means: run the setup interview)
  start              submit a goal with acceptance criteria; workers come from the host profile
  host-next / host-result  perform a native host action and record its observed result
  status             what the task is waiting on, per outcome, with delivery evidence
  advance            run every deterministic step available now
  run                advance repeatedly; the profile's judge answers judgments unless --no-judge
  requests / prompt  open judgment requests and the full prompt for one
  answer             submit a typed judgment answer (validated before use)
  questions          open questions only the user can answer
  confirm-selection  resolve a legacy task's selection question with the user's reply
  reply              record the user's answer to any other question
  real-use           pass (with evidence) or waive (quoting the user) the real-use gate
  halt / resume      stop all workers and hold, or continue

Every command prints one JSON object. Task IDs accept a unique 6+ character prefix.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import coord_drive as drive
import coord_state as tasks


def task_dir(args):
    root = tasks.root_path(args.root)
    return tasks.task_path(root, tasks.resolve_task_id(root, args.task))


def read_json(path):
    return json.loads(sys.stdin.read() if path == '-' else Path(path).read_text())


def parse_judge_output(text):
    """Find the answer object in judge output, unwrapping `claude -p --output-format json`."""
    decoder = json.JSONDecoder()
    candidates = []
    for match in re.finditer(r'\{', text):
        try:
            value, _ = decoder.raw_decode(text, match.start())
        except ValueError:
            continue
        candidates.append(value)
        if isinstance(value, dict) and isinstance(value.get('result'), str):
            inner = parse_judge_output(value['result'])
            if inner is not None:
                return inner
    objects = [c for c in candidates if isinstance(c, dict)]
    return max(objects, key=lambda c: len(json.dumps(c))) if objects else None


def judge(directory, request_id, argv, timeout):
    """Ask the configured judge command for one typed answer; the driver validates it."""
    prompt = drive.request_prompt(directory, request_id)
    command = [prompt if part == '{prompt}' else part for part in argv]
    try:
        result = subprocess.run(command, input=None if '{prompt}' in argv else prompt, capture_output=True,
                                text=True, timeout=timeout)
        value = parse_judge_output(result.stdout)
        failure = (f'judge returned no JSON object (exit {result.returncode}): '
                   f'{drive.tail(result.stdout or result.stderr, 400)}')
    except (OSError, subprocess.TimeoutExpired) as error:
        value, failure = None, f'judge command failed: {error}'
    try:
        if value is None:
            raise drive.DriveError(failure)
        return drive.answer(directory, request_id, value)
    except tasks.StateError as error:
        if value is None:  # record the failure against the request like any rejected answer
            with drive.driving(directory) as record:
                request = record['requests'][request_id]
                if request['status'] == 'open':
                    drive.reject_answer(record, request, error)
        return {'id': request_id, 'rejected': str(error)}


def run(directory, judge_argv, poll, max_seconds, judge_timeout):
    deadline = time.monotonic() + max_seconds if max_seconds else None
    judged = []
    while True:
        status = drive.advance(directory)
        if status['done'] or status['questions'] or status['halted'] or status.get('host_actions'):
            break
        if status['requests']:
            if not judge_argv:
                break
            for request in status['requests']:
                judged.append(judge(directory, request['id'], judge_argv, judge_timeout))
            continue
        if deadline and time.monotonic() >= deadline:
            break
        time.sleep(poll)
    status['judged'] = [{'id': j.get('id'), 'kind': j.get('kind'), 'rejected': j.get('rejected')} for j in judged]
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', help='coordinator state directory (default: XDG state)')
    sub = parser.add_subparsers(dest='command', required=True)

    command = sub.add_parser('start')
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument('--repo', help='git repository root the work is for')
    source.add_argument('--workspace', help='source directory for report/artifact delivery; never modified')
    command.add_argument('--delivery', choices=['patch', 'artifact'],
                         help='default: patch for --repo, artifact for --workspace')
    command.add_argument('--goal', required=True)
    command.add_argument('--criterion', action='append', default=[], help='observable done condition; repeatable')
    command.add_argument('--constraint', action='append', default=[])
    command.add_argument('--authority', help='what workers may do; defaults to isolated worktrees and a task branch')
    command.add_argument('--title')
    command.add_argument('--workers-file',
                         help='JSON [{"route": {...}, "argv": [..., "{prompt}", ...]}]; default: the host profile')
    command.add_argument('--real-use-required', action='store_true',
                         help='the task changes a skill or workflow; completion needs a real-use pass or waiver')
    command.add_argument('--limits-file', help='JSON overrides for driver limits')

    command = sub.add_parser('doctor')
    command.add_argument('--workers-file', help='check a task-specific worker configuration instead of the profile')
    command.add_argument('--delivery', choices=['patch', 'artifact'], default='patch')
    for name in ('status', 'advance', 'requests', 'questions', 'halt', 'resume', 'host-next'):
        sub.add_parser(name).add_argument('--task', required=True)

    command = sub.add_parser('run')
    command.add_argument('--task', required=True)
    command.add_argument('--judge-command-file', help='JSON argv; default: the host profile judge')
    command.add_argument('--no-judge', action='store_true', help='stop at every judgment request instead')
    command.add_argument('--poll', type=float, default=5)
    command.add_argument('--max-seconds', type=float, default=0, help='0 waits until done or a question')
    command.add_argument('--judge-timeout', type=float, default=1800)

    command = sub.add_parser('prompt')
    command.add_argument('--task', required=True)
    command.add_argument('--request', required=True)

    command = sub.add_parser('answer')
    command.add_argument('--task', required=True)
    command.add_argument('--request', required=True)
    command.add_argument('--file', required=True, help="answer JSON file, or '-' for stdin")

    command = sub.add_parser('host-result', help='record the actual result of the issued host-tool request')
    command.add_argument('--task', required=True)
    command.add_argument('--action', required=True)
    command.add_argument('--file', required=True, help="observed result JSON file, or '-' for stdin")

    command = sub.add_parser('confirm-selection')
    command.add_argument('--task', required=True)
    command.add_argument('--question', required=True)
    command.add_argument('--user-message', required=True, help="the user's words approving the choice")
    command.add_argument('--pool-file', help='a different pool the user chose instead')

    command = sub.add_parser('reply')
    command.add_argument('--task', required=True)
    command.add_argument('--question', required=True)
    command.add_argument('--user-message', required=True, help="the user's words, verbatim")

    command = sub.add_parser('real-use')
    command.add_argument('--task', required=True)
    command.add_argument('--status', required=True, choices=['passed', 'waived'])
    command.add_argument('--source', help='for a waiver, quote the user; for a pass, identify the verifier')
    command.add_argument('--evidence', help='evidence file for a pass')

    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            result = drive.doctor(read_json(args.workers_file) if args.workers_file else None, args.delivery)
        elif args.command == 'start':
            limits = read_json(args.limits_file) if args.limits_file else None
            workers = read_json(args.workers_file) if args.workers_file else drive.profile_driver().get('workers')
            if not workers:
                raise drive.DriveError('no worker commands: the host profile has no adapters.driver workers. '
                                       'Run `coord.py doctor`, then the coordinator-setup driver interview.')
            delivery = args.delivery or ('artifact' if args.workspace else 'patch')
            if args.workspace and delivery != 'artifact':
                raise drive.DriveError('--workspace requires artifact delivery; use --repo for patches')
            result = drive.start(tasks.root_path(args.root), args.repo or args.workspace, args.goal, args.criterion,
                                 workers, args.title, args.constraint, args.authority,
                                 args.real_use_required, limits, delivery)
        else:
            directory = task_dir(args)
            if args.command == 'status':
                result = drive.summary(directory, drive.load_drive(directory))
            elif args.command == 'advance':
                result = drive.advance(directory)
            elif args.command == 'run':
                judge_argv = None if args.no_judge else (
                    read_json(args.judge_command_file) if args.judge_command_file else drive.profile_driver().get('judge'))
                result = run(directory, judge_argv, args.poll, args.max_seconds, args.judge_timeout)
            elif args.command == 'requests':
                record = drive.load_drive(directory)
                result = [{'id': r['id'], 'kind': r['kind'], 'errors': r['errors']}
                          for r in record['requests'].values() if r['status'] == 'open']
            elif args.command == 'prompt':
                result = {'request': args.request, 'prompt': drive.request_prompt(directory, args.request)}
            elif args.command == 'answer':
                result = drive.answer(directory, args.request, read_json(args.file))
                result = {'id': result['id'], 'kind': result['kind'], 'status': result['status'],
                          'next': drive.advance(directory)}
            elif args.command == 'host-next':
                result = drive.host_next(directory)
            elif args.command == 'host-result':
                result = drive.host_result(directory, args.action, read_json(args.file))
            elif args.command == 'questions':
                record = drive.load_drive(directory)
                result = [{'id': q['id'], 'kind': q['kind'], 'prompt': q['prompt'], 'payload': q['payload']}
                          for q in record['questions'].values() if q['status'] == 'open']
            elif args.command == 'confirm-selection':
                pool = read_json(args.pool_file) if args.pool_file else None
                result = drive.confirm_selection(directory, args.question, args.user_message, pool)
            elif args.command == 'reply':
                result = drive.reply(directory, args.question, args.user_message)
            elif args.command == 'real-use':
                if args.status == 'waived' and not args.source:
                    raise drive.DriveError('a real-use waiver requires --source quoting the user')
                result = drive.real_use(directory, args.status, args.source or 'front desk recorded real-use evidence', args.evidence)
            else:
                result = drive.halt(directory, resume=args.command == 'resume')
    except (tasks.StateError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({'ok': True, 'result': result}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
