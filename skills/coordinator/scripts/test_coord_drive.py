"""End-to-end driver runs: real git worktrees, real worker processes, a scripted judge.

The fake worker and judge are scripts driven by a scenario file, so each test
exercises the actual launcher, packaging, checks, claimcheck, integration, goal
checks, and completion code, and only the AI's typed answers are scripted.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import coord
import coord_drive as drive
import coord_state as tasks

WORKER = r'''
import json, re, sys, time
from pathlib import Path
scenario_file, prompt = Path(sys.argv[1]), sys.argv[2]
scenario = json.loads(scenario_file.read_text())
cwd = Path(re.search(r"Working directory: (\S+)", prompt).group(1))
summary = Path(re.search(r"write a short summary to (\S+):", prompt).group(1))
objective = re.search(r"Objective: (.+)", prompt).group(1)
key = next(k for k in scenario["workers"] if k in objective)
log = scenario_file.parent / ("prompts-" + key + ".jsonl")
attempt = len(log.read_text().splitlines()) if log.exists() else 0
with log.open("a") as stream:
    stream.write(json.dumps(prompt) + "\n")
steps = scenario["workers"][key]
step = steps[min(attempt, len(steps) - 1)]
time.sleep(step.get("sleep", 0))
if "blocker" in step:
    blocker = re.search(r"to (\S+/blocker\.json)", prompt).group(1)
    Path(blocker).write_text(json.dumps({"decision": step["blocker"]}))
    sys.exit(0)
for name, text in step.get("files", {}).items():
    (cwd / name).write_text(text)
if "summary" in step:
    summary.write_text(step["summary"])
'''

JUDGE = r'''
import json, re, sys
from pathlib import Path
scenario_file = Path(sys.argv[1])
scenario = json.loads(scenario_file.read_text())
prompt = sys.stdin.read()
context = json.loads(re.search(r"## This request\s+```json\n(.*?)\n```", prompt, re.S).group(1))
kind = re.search(r"# Judgment: (\w+)", prompt).group(1)
kind = {"recommend": "harness", "decompose": "decompose", "assess": "assess", "inspect": "inspect"}[kind]
counts_file = scenario_file.parent / "judge-counts.json"
counts = json.loads(counts_file.read_text()) if counts_file.exists() else {}
n = counts.get(kind, 0)
counts[kind] = n + 1
counts_file.write_text(json.dumps(counts))
with (scenario_file.parent / "judge-log.jsonl").open("a") as stream:
    stream.write(json.dumps({"kind": kind, "context": context}) + "\n")
if kind == "harness":
    answer = {"pool": context["routes"][:1], "rationale": "routine change in one module"}
else:
    answers = scenario["judge"].get(kind, [])
    answer = answers[min(n, len(answers) - 1)] if answers else {"verdict": "accept", "reason": "in scope"}
print(answer if isinstance(answer, str) else json.dumps(answer))
'''

CALC = 'def add(a, b):\n    return a + b\n'
TEST_CALC = ('import unittest\nimport calc\n\n\nclass CalcTest(unittest.TestCase):\n'
             '    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n')
MUL = CALC + '\n\ndef mul(a, b):\n    return a * b\n'
WRONG_MUL = CALC + '\n\ndef mul(a, b):\n    return a + b\n'
DIV = MUL + '\n\ndef div(a, b):\n    return a / b\n'


def check(cid, code):
    return {'id': cid, 'argv': [sys.executable, '-c', code]}


MUL_CHECK = check('mul-works', 'import calc; assert calc.mul(2, 3) == 6')
SUITE = {'id': 'suite', 'argv': [sys.executable, '-m', 'unittest', '-q']}


def outcome(oid, objective, checks, needs=()):
    return {'id': oid, 'objective': objective, 'rationale': 'The ledger needs it', 'scope': 'calc.py only',
            'authority': 'Edit calc.py; nothing else', 'needs': list(needs), 'checks': checks}


def plan(*items, goal_checks=None):
    return {'outcomes': list(items), 'goal_checks': goal_checks or [MUL_CHECK, SUITE],
            'rationale': 'One focused change'}


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'state'
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        (self.repo / 'calc.py').write_text(CALC)
        (self.repo / 'test_calc.py').write_text(TEST_CALC)
        for args in (['init', '-q', '-b', 'main'], ['add', '-A'],
                     ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init']):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True)
        self.head = self.git('rev-parse', 'HEAD')
        self.scenario_file = self.base / 'scenario.json'
        (self.base / 'worker.py').write_text(WORKER)
        (self.base / 'judge.py').write_text(JUDGE)
        self.workers = [{'route': {'harness': 'fake', 'model': 'scripted'},
                         'argv': [sys.executable, str(self.base / 'worker.py'), str(self.scenario_file), '{prompt}']}]
        self.judge = [sys.executable, str(self.base / 'judge.py'), str(self.scenario_file)]

    def git(self, *args, cwd=None):
        return subprocess.run(['git', '-C', str(cwd or self.repo), *args], capture_output=True, text=True,
                              check=True).stdout.strip()

    def scenario(self, workers, **judge):
        self.scenario_file.write_text(json.dumps({'workers': workers, 'judge': judge}))

    def start(self, **kwargs):
        result = drive.start(self.root, self.repo, 'Add multiplication to the calculator',
                             ['calc.mul multiplies two numbers', 'existing tests still pass'], self.workers,
                             limits=dict({'check_timeout': 60}, **kwargs.pop('limits', {})), **kwargs)
        self.task = Path(self.root) / 'tasks' / result['task']
        return result

    def run_until(self, stop_on_questions=True, seconds=60):
        deadline = time.monotonic() + seconds
        while True:
            status = coord.run(self.task, self.judge, poll=0.1, max_seconds=2, judge_timeout=60)
            if status['done'] or (stop_on_questions and status['questions']):
                return status
            if time.monotonic() > deadline:
                self.fail(f'driver did not settle: {json.dumps(status, indent=2)}')

    def confirm(self):
        status = self.run_until()
        question = status['questions'][0]
        self.assertEqual(question['kind'], 'confirm_selection')
        return drive.confirm_selection(self.task, question['id'], 'yes, use the scripted worker')

    def prompts(self, key):
        return [json.loads(line) for line in (self.base / f'prompts-{key}.jsonl').read_text().splitlines()]

    def judged(self, kind):
        lines = (self.base / 'judge-log.jsonl').read_text().splitlines()
        return [entry['context'] for entry in map(json.loads, lines) if entry['kind'] == kind]

    def assert_done_on_branch(self, status, expected_calc):
        self.assertTrue(status['done'], json.dumps(status, indent=2))
        state = tasks.load(self.task)
        self.assertEqual(state['status'], 'completed')
        branch = status['branch']
        self.assertEqual(self.git('show', f'{branch}:calc.py') + '\n', expected_calc)
        self.assertIn('Coord-Assignment:', self.git('log', '-1', '--format=%B', branch))
        # The user's checkout never moved and stays clean.
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.head)
        self.assertEqual(self.git('branch', '--show-current'), 'main')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_story_end_to_end(self):
        self.scenario({'multiplication': [{'files': {'calc.py': MUL},
                                           'summary': 'Added calc.mul; ran test_calc.py.'}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        started = self.start()
        self.assertEqual(started['waiting_on'], 'judgment')
        self.assertIsNone(tasks.load(self.task)['selection'])  # nothing runs before the user confirms
        status = self.confirm()
        self.assertIn('user, via front desk', tasks.load(self.task)['choice_events'][-1]['source'])
        self.assertEqual(status['waiting_on'], 'judgment')
        status = self.run_until()
        self.assert_done_on_branch(status, MUL)
        inspected = self.judged('inspect')[0]
        self.assertIn('def mul', inspected['patch'])
        self.assertEqual(inspected['checks'][0]['exit_code'], 0)

    def test_failed_checks_return_to_worker_with_evidence(self):
        self.scenario({'multiplication': [{'files': {'calc.py': WRONG_MUL}, 'summary': 'Added mul.'},
                                          {'files': {'calc.py': MUL}, 'summary': 'Fixed mul.'}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start()
        self.confirm()
        status = self.run_until()
        self.assert_done_on_branch(status, MUL)
        prompts = self.prompts('multiplication')
        self.assertEqual(len(prompts), 2)
        self.assertIn('Check mul-works failed', prompts[1])
        self.assertEqual(len(self.judged('inspect')), 1)  # the judge never saw the failing attempt

    def test_fabricated_test_citation_is_caught_by_code(self):
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}, 'summary': 'tests/test_mul.py passes.'},
                                          {'files': {'calc.py': MUL}, 'summary': 'test_calc.py passes.'}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start()
        self.confirm()
        status = self.run_until()
        self.assert_done_on_branch(status, MUL)
        self.assertIn('does not exist', self.prompts('multiplication')[1])

    def test_inspection_reject_feeds_the_next_attempt(self):
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      inspect=[{'verdict': 'reject', 'reason': 'no docstring',
                                'feedback': 'Add a docstring to mul explaining the arguments.'},
                               {'verdict': 'accept', 'reason': 'fine'}])
        self.start()
        self.confirm()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertIn('Add a docstring to mul', self.prompts('multiplication')[1])

    def test_goal_failure_replans_without_dropping_goal_checks(self):
        div_check = check('div-works', 'import calc; assert calc.div(6, 3) == 2')
        first = plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]),
                     goal_checks=[MUL_CHECK, div_check, SUITE])
        second = plan(outcome('div', 'Add division to calc', [div_check]), goal_checks=[MUL_CHECK, div_check, SUITE])
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}], 'division': [{'files': {'calc.py': DIV}}]},
                      decompose=[first, second])
        self.start()
        self.confirm()
        status = self.run_until()
        self.assert_done_on_branch(status, DIV)
        replan = self.judged('decompose')[1]
        self.assertEqual(replan['mode'], 'replan')
        self.assertEqual(replan['failure']['goal_checks_failed'][0]['id'], 'div-works')
        self.assertEqual([c['id'] for c in replan['required_goal_checks']], ['mul-works', 'div-works', 'suite'])

    def test_replan_answer_that_drops_a_goal_check_is_refused(self):
        request = {'kind': 'decompose', 'context': {'required_goal_checks': [MUL_CHECK, SUITE]}}
        weaker = plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]), goal_checks=[SUITE])
        with self.assertRaisesRegex(tasks.StateError, 'never drop or change'):
            drive.validate_answer({'workers': self.workers}, request, weaker)

    def test_unusable_judgments_escalate_to_the_user(self):
        self.scenario({}, decompose=['I think we should add mul.'])
        self.start(limits={'judgment_retries': 1})
        self.confirm()
        status = self.run_until()
        self.assertEqual(status['questions'][0]['kind'], 'judgment_failed')
        self.assertEqual(len(self.judged('decompose')), 2)
        self.assertNotIn('outcome_plan', tasks.load(self.task))

    def test_real_use_gate_blocks_completion_until_waived(self):
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start(real_use_required=True)
        self.confirm()
        status = self.run_until()
        self.assertFalse(status['done'])
        self.assertEqual(status['questions'][0]['kind'], 'completion_blocked')
        self.assertIn('real-use', status['questions'][0]['prompt'])
        status = drive.real_use(self.task, 'waived', 'user: "no need for a real-use run on this one"')
        self.assert_done_on_branch(status, MUL)

    def test_exhausted_attempts_go_to_judgment_then_user(self):
        self.scenario({'multiplication': [{'files': {'calc.py': WRONG_MUL}}, {'files': {'calc.py': WRONG_MUL}},
                                          {'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      assess=[{'action': 'escalate', 'reason': 'two attempts added instead of multiplying',
                               'question': 'Should mul multiply, or is addition intended?'}])
        self.start(limits={'attempts_per_outcome': 2})
        self.confirm()
        status = self.run_until()
        question = status['questions'][0]
        self.assertEqual(question['kind'], 'escalation')
        self.assertEqual(self.judged('assess')[0]['event'], 'attempts_exhausted')
        drive.reply(self.task, question['id'], 'mul must multiply: mul(2, 3) is 6')
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertIn('User decision: mul must multiply', self.prompts('multiplication')[2])

    def test_worker_blocker_is_assessed_not_guessed(self):
        self.scenario({'multiplication': [{'blocker': 'Which rounding mode should mul use?'},
                                          {'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      assess=[{'action': 'retry', 'reason': 'integers only; no rounding needed',
                               'guidance': 'Inputs are integers; no rounding is involved.'}])
        self.start()
        self.confirm()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertEqual(self.judged('assess')[0]['event'], 'blocked')
        self.assertIn('rounding mode', self.judged('assess')[0]['blocker'])
        self.assertIn('no rounding is involved', self.prompts('multiplication')[1])

    def test_stalled_worker_is_assessed(self):
        self.scenario({'multiplication': [{'sleep': 4, 'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      assess=[{'action': 'continue', 'reason': 'short sleep, still plausible'}])
        self.start(limits={'stall_seconds': 1})
        self.confirm()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertEqual(self.judged('assess')[0]['event'], 'no_progress')

    def test_halt_stops_work_and_resume_does_not_spend_an_attempt(self):
        self.scenario({'multiplication': [{'sleep': 30, 'files': {'calc.py': MUL}}, {'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start(limits={'attempts_per_outcome': 1})
        self.confirm()
        deadline = time.monotonic() + 30
        while not (self.base / 'prompts-multiplication.jsonl').exists():  # first worker is running
            coord.run(self.task, self.judge, poll=0.1, max_seconds=0.5, judge_timeout=60)
            self.assertLess(time.monotonic(), deadline)
        status = drive.halt(self.task)
        self.assertTrue(status['halted'])
        deadline = time.monotonic() + 30
        while drive.advance(self.task)['outcomes'][0]['status'] != 'attempt finished':
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.1)
        drive.halt(self.task, resume=True)
        self.assert_done_on_branch(self.run_until(), MUL)
        prompts = self.prompts('multiplication')
        self.assertEqual(len(prompts), 2)  # with a budget of 1, the halted attempt was not counted
        self.assertNotIn('Earlier attempts', prompts[1])

    def test_second_task_on_same_repo_sees_the_earlier_choice(self):
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start()
        self.confirm()
        first = self.task
        self.start()
        self.run_until()
        harness = self.judged('harness')[-1]
        self.assertNotEqual(self.task, first)
        self.assertEqual(harness['recent_choices'][0]['pool'], [{'harness': 'fake', 'model': 'scripted'}])
        self.assertIn('yes, use the scripted worker', harness['recent_choices'][0]['source'])

    def test_selection_must_name_configured_routes(self):
        self.scenario({}, decompose=[])
        self.start()
        status = self.run_until()
        with self.assertRaisesRegex(tasks.StateError, 'no worker command'):
            drive.confirm_selection(self.task, status['questions'][0]['id'], 'yes',
                                    [{'harness': 'other', 'model': 'x'}])
        self.assertIsNone(tasks.load(self.task)['selection'])

    def test_start_requires_checkable_criteria(self):
        with self.assertRaisesRegex(tasks.StateError, 'acceptance criterion'):
            drive.start(self.root, self.repo, 'Make it better', ['  '], self.workers)

    def test_parallel_conflict_is_redone_on_the_new_base(self):
        sub = check('sub-works', 'import calc; assert calc.sub(5, 3) == 2')
        sub_only = CALC + '\n\ndef sub(a, b):\n    return a - b\n'
        both = MUL + '\n\ndef sub(a, b):\n    return a - b\n'
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}],
                       'subtraction': [{'sleep': 1.5, 'files': {'calc.py': sub_only}}, {'files': {'calc.py': both}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]),
                                      outcome('sub', 'Add subtraction to calc', [sub]),
                                      goal_checks=[MUL_CHECK, sub, SUITE])])
        self.start()
        self.confirm()
        self.assert_done_on_branch(self.run_until(), both)
        self.assertIn('no longer applies', self.prompts('subtraction')[1])

    def test_judge_output_parsing_unwraps_cli_envelopes(self):
        wrapped = json.dumps({'type': 'result', 'result': 'Here you go:\n{"verdict": "accept", "reason": "ok"}'})
        self.assertEqual(coord.parse_judge_output(wrapped), {'verdict': 'accept', 'reason': 'ok'})
        self.assertEqual(coord.parse_judge_output('noise {"a": {"b": 1}} tail'), {'a': {'b': 1}})
        self.assertIsNone(coord.parse_judge_output('no json here'))


if __name__ == '__main__':
    unittest.main()
