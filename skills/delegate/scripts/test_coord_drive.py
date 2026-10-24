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
import unittest.mock

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
with (scenario_file.parent / "worker-argv.jsonl").open("a") as stream:
    stream.write(json.dumps(sys.argv) + "\n")
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
kind = {"recommend": "harness", "decompose": "decompose", "assess": "assess", "inspect": "inspect",
        "review": "review_checks"}[kind]
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


GOOD_TESTS = ('import unittest\nimport calc\n\n\nclass MulTest(unittest.TestCase):\n'
              '    def test_mul(self):\n        self.assertEqual(calc.mul(2, 3), 6)\n'
              '        self.assertEqual(calc.mul(0, 5), 0)\n')
MORE_TESTS = GOOD_TESTS + '        self.assertEqual(calc.mul(-2, 3), -6)\n'
VACUOUS_TESTS = ('import unittest\nimport calc\n\n\nclass MulTest(unittest.TestCase):\n'
                 '    def test_mul(self):\n        self.assertTrue(callable(calc.add))\n')


def check(cid, code):
    return {'id': cid, 'argv': [sys.executable, '-c', code]}


MUL_CHECK = check('mul-works', 'import calc; assert calc.mul(2, 3) == 6')
SUITE = {'id': 'suite', 'argv': [sys.executable, '-m', 'unittest', '-q']}
MUL_TESTS = {'id': 'mul-tests', 'argv': [sys.executable, '-m', 'unittest', '-q', 'test_mul']}


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
                             limits=dict({'check_timeout': 60, 'checks_first': False}, **kwargs.pop('limits', {})),
                             **kwargs)
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

    def select(self, pool=None):
        status = drive.advance(self.task)
        request = next(r for r in status['requests'] if r['kind'] == 'harness')
        drive.answer(self.task, request['id'], {
            'pool': pool or [self.workers[0]['route']], 'rationale': 'Configured fixture route'})
        return drive.advance(self.task)

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
        self.assertIsNone(tasks.load(self.task)['selection'])  # recommendation is still required
        status = self.select()
        self.assertIn('coordinator recommendation:', tasks.load(self.task)['choice_events'][-1]['source'])
        self.assertEqual(status['waiting_on'], 'judgment')
        self.assertFalse(status['questions'])
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
        self.select()
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
        self.select()
        status = self.run_until()
        self.assert_done_on_branch(status, MUL)
        self.assertIn('could not find: test path', self.prompts('multiplication')[1])

    def test_inspection_reject_feeds_the_next_attempt(self):
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      inspect=[{'verdict': 'reject', 'reason': 'no docstring',
                                'feedback': 'Add a docstring to mul explaining the arguments.'},
                               {'verdict': 'accept', 'reason': 'fine'}])
        self.start()
        self.select()
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
        self.select()
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
        self.select()
        status = self.run_until()
        self.assertEqual(status['questions'][0]['kind'], 'judgment_failed')
        self.assertEqual(len(self.judged('decompose')), 2)
        self.assertNotIn('outcome_plan', tasks.load(self.task))

    def test_real_use_gate_blocks_completion_until_waived(self):
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start(real_use_required=True)
        self.select()
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
        self.select()
        status = self.run_until()
        question = status['questions'][0]
        self.assertEqual(question['kind'], 'escalation')
        self.assertEqual(self.judged('assess')[0]['event'], 'attempts_exhausted')
        drive.reply(self.task, question['id'], 'mul must multiply: mul(2, 3) is 6')
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertIn('User decision: mul must multiply', self.prompts('multiplication')[2])

    def test_progress_polling_never_writes_the_worker_index(self):
        # Plain `git status` refreshes and rewrites the index when timestamps change; while a worker
        # runs, that takes index.lock and can make the worker's own git commands fail.
        index = self.repo / '.git' / 'index'
        before = index.read_bytes()
        time.sleep(1.1)
        os.utime(self.repo / 'calc.py')  # newer mtime, same content: stale stat info in the index
        run_dir = self.base / 'run'
        run_dir.mkdir()
        drive.progress_signature({'run_dir': str(run_dir)}, self.repo)
        self.assertEqual(index.read_bytes(), before)
        subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain'], check=True, capture_output=True)
        self.assertNotEqual(index.read_bytes(), before)  # the hazard is real without the flag

    def test_old_plan_is_held_while_a_replan_is_pending(self):
        self.scenario({'multiplication': [{'files': {'calc.py': WRONG_MUL}}], 'product': [{'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK])),
                                 plan(outcome('product', 'Add the product function to calc', [MUL_CHECK]))],
                      assess=[{'action': 'replan', 'reason': 'the contract needs a different approach'}])
        self.start(limits={'attempts_per_outcome': 1})
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertEqual(len(self.prompts('multiplication')), 1)
        self.assertEqual(len(self.judged('assess')), 1)  # no second judgment about the abandoned plan

    def test_identical_failures_go_to_judgment_before_the_budget_runs_out(self):
        self.scenario({'multiplication': [{'files': {'calc.py': WRONG_MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      assess=[{'action': 'escalate', 'reason': 'same failure twice',
                               'question': 'Is the mul check right?'}])
        self.start(limits={'attempts_per_outcome': 5})
        self.select()
        status = self.run_until()
        self.assertEqual(status['questions'][0]['kind'], 'escalation')
        assessed = self.judged('assess')[0]
        self.assertEqual(assessed['event'], 'repeated_failure')
        self.assertEqual(assessed['failing_checks'][0]['id'], 'mul-works')
        self.assertEqual(len(self.prompts('multiplication')), 2)  # not 5

    def test_worker_blocker_is_assessed_not_guessed(self):
        self.scenario({'multiplication': [{'blocker': 'Which rounding mode should mul use?'},
                                          {'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      assess=[{'action': 'retry', 'reason': 'integers only; no rounding needed',
                               'guidance': 'Inputs are integers; no rounding is involved.'}])
        self.start()
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertEqual(self.judged('assess')[0]['event'], 'blocked')
        self.assertIn('rounding mode', self.judged('assess')[0]['blocker'])
        self.assertIn('no rounding is involved', self.prompts('multiplication')[1])

    def test_stalled_worker_is_assessed(self):
        self.scenario({'multiplication': [{'sleep': 4, 'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))],
                      assess=[{'action': 'continue', 'reason': 'short sleep, still plausible'}])
        self.start(limits={'stall_seconds': 1})
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertEqual(self.judged('assess')[0]['event'], 'no_progress')

    def test_halt_stops_work_and_resume_does_not_spend_an_attempt(self):
        self.scenario({'multiplication': [{'sleep': 30, 'files': {'calc.py': MUL}}, {'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start(limits={'attempts_per_outcome': 1})
        self.select()
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
        self.select()
        first = self.task
        self.start()
        self.run_until()
        harness = self.judged('harness')[-1]
        self.assertNotEqual(self.task, first)
        self.assertEqual(harness['recent_choices'][0]['pool'], [{'harness': 'fake', 'model': 'scripted'}])
        self.assertIn('coordinator recommendation:', harness['recent_choices'][0]['source'])

    def test_selection_must_name_configured_routes(self):
        self.scenario({}, decompose=[])
        self.start()
        with self.assertRaisesRegex(tasks.StateError, 'no worker command'):
            self.select([{'harness': 'other', 'model': 'x'}])
        self.assertIsNone(tasks.load(self.task)['selection'])

    def test_selected_effort_selects_actual_worker_command(self):
        low = {'harness': 'fake', 'model': 'scripted', 'effort': 'low', 'role': 'implementer'}
        high = dict(low, effort='high')
        argv = self.workers[0]['argv']
        self.workers = [{'route': low, 'argv': argv + ['low-command']},
                        {'route': high, 'argv': argv + ['high-command']}]
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start()
        status = self.select([high])
        self.assertFalse(status['questions'])
        self.assert_done_on_branch(self.run_until(), MUL)
        argv = json.loads((self.base / 'worker-argv.jsonl').read_text().splitlines()[0])
        self.assertEqual(argv[-1], 'high-command')

    def test_selection_rejects_missing_or_unsupported_route_variants(self):
        configured = {'harness': 'fake', 'model': 'scripted', 'provider': 'test',
                      'effort': 'high', 'role': 'implementer'}
        self.workers[0]['route'] = configured
        self.scenario({}, decompose=[])
        self.start(limits={'judgment_retries': 10})
        variants = [dict(configured, effort='low'), dict(configured, role='reviewer')]
        variants += [{k: v for k, v in configured.items() if k != field}
                     for field in ('provider', 'effort', 'role')]
        for route in variants:
            with self.subTest(route=route), self.assertRaisesRegex(tasks.StateError, 'no worker command'):
                self.select([route])
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
        self.select()
        self.assert_done_on_branch(self.run_until(), both)
        self.assertIn('no longer applies', self.prompts('subtraction')[1])

    # Checks first: tests are written, proven red, and reviewed before implementation.
    def checks_first_plan(self):
        return plan(outcome('mul', 'Add multiplication to calc', [MUL_TESTS]))

    def test_checks_first_story(self):
        self.scenario({'Write the tests': [{'files': {'test_mul.py': GOOD_TESTS}}],
                       'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[self.checks_first_plan()])
        self.start(limits={'checks_first': True})
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertEqual(self.git('show', f'coord/{self.task.name[:8]}:test_mul.py') + '\n', GOOD_TESTS)
        subjects = self.git('log', '--format=%s', f'main..coord/{self.task.name[:8]}').splitlines()
        self.assertEqual([s.split(':')[0] for s in subjects], ['coord(mul)', 'coord(mul-checks)'])
        review = self.judged('review_checks')[0]
        self.assertEqual(review['implements']['id'], 'mul')
        self.assertIn('fails (good', review['red_evidence'])
        self.assertIn('test_mul.py', review['patch'])
        self.assertEqual(len(self.judged('inspect')), 1)  # the implementation still gets its own inspection
        self.assertIn('test_mul.py', self.prompts('multiplication')[0])  # the implementer is told its checks

    def test_auto_checks_first_follows_each_outcomes_choice(self):
        sub = check('sub-works', 'import calc; assert calc.sub(5, 3) == 2')
        both = MUL + '\n\ndef sub(a, b):\n    return a - b\n'
        skip = dict(outcome('sub', 'Add subtraction to calc', [sub], needs=['mul']), tests_first=False)
        self.scenario({'Write the tests': [{'files': {'test_mul.py': GOOD_TESTS}}],
                       'multiplication': [{'files': {'calc.py': MUL}}],
                       'subtraction': [{'files': {'calc.py': both}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', [MUL_TESTS]), skip,
                                      goal_checks=[MUL_CHECK, sub, SUITE])])
        self.start(limits={'checks_first': 'auto'})
        self.select()
        self.assert_done_on_branch(self.run_until(), both)
        self.assertEqual([r['implements']['id'] for r in self.judged('review_checks')], ['mul'])
        self.assertEqual(len(self.prompts('Write the tests')), 1)  # only mul, which left tests_first unset

    def test_checks_first_limit_rejects_unknown_modes(self):
        with self.assertRaisesRegex(drive.DriveError, 'checks_first must be'):
            self.start(limits={'checks_first': 'sometimes'})

    def test_tests_first_must_be_a_boolean(self):
        request, state = {'kind': 'decompose', 'context': {}}, {'delivery': 'patch'}
        chosen = dict(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]), tests_first=False)
        drive.validate_answer(state, request, plan(chosen))
        with self.assertRaisesRegex(drive.DriveError, 'tests_first must be true or false'):
            drive.validate_answer(state, request, plan(dict(chosen, tests_first='no')))

    def test_tests_that_already_pass_are_sent_back(self):
        self.scenario({'Write the tests': [{'files': {'test_mul.py': VACUOUS_TESTS}}, {'files': {'test_mul.py': GOOD_TESTS}}],
                       'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[self.checks_first_plan()])
        self.start(limits={'checks_first': True})
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertIn('Every check passes before any implementation', self.prompts('Write the tests')[1])
        self.assertEqual(len(self.judged('review_checks')), 1)  # the vacuous tests never reached review

    def test_review_sends_missing_cases_back_to_the_test_writer(self):
        self.scenario({'Write the tests': [{'files': {'test_mul.py': GOOD_TESTS}}, {'files': {'test_mul.py': MORE_TESTS}}],
                       'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[self.checks_first_plan()],
                      review_checks=[{'verdict': 'reject', 'reason': 'no negative numbers',
                                      'feedback': 'Add a case: mul(-2, 3) must be -6.'},
                                     {'verdict': 'accept', 'reason': 'covers zero and negatives'}])
        self.start(limits={'checks_first': True})
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertIn('mul(-2, 3) must be -6', self.prompts('Write the tests')[1])
        self.assertEqual(self.git('show', f'coord/{self.task.name[:8]}:test_mul.py') + '\n', MORE_TESTS)

    def test_implementation_cannot_edit_approved_tests(self):
        self.scenario({'Write the tests': [{'files': {'test_mul.py': GOOD_TESTS}}],
                       'multiplication': [{'files': {'calc.py': WRONG_MUL, 'test_mul.py': VACUOUS_TESTS}},
                                          {'files': {'calc.py': MUL}}]},
                      decompose=[self.checks_first_plan()])
        self.start(limits={'checks_first': True})
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertIn('You changed tests that were reviewed and approved', self.prompts('multiplication')[1])
        self.assertEqual(self.git('show', f'coord/{self.task.name[:8]}:test_mul.py') + '\n', GOOD_TESTS)

    def test_implementation_cannot_vacate_space_or_unicode_approved_tests(self):
        names = ['approved test.py', 'approved_é.py']
        checks = [check(f'approved-tests-{index}',
                        'exec(compile(open(' + repr(name) + ').read(), ' + repr(name)
                        + ', "exec")); unittest.main()') for index, name in enumerate(names)]
        self.scenario({'Write the tests': [{'files': dict.fromkeys(names, GOOD_TESTS)}],
                       'multiplication': [{'files': {'calc.py': WRONG_MUL,
                                                    **dict.fromkeys(names, VACUOUS_TESTS)}},
                                          {'files': {'calc.py': MUL}}]},
                      decompose=[plan(outcome('mul', 'Add multiplication to calc', checks),
                                      goal_checks=checks + [SUITE])])
        self.start(limits={'checks_first': True})
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        self.assertIn('You changed tests that were reviewed and approved', self.prompts('multiplication')[1])
        for name in names:
            self.assertEqual(self.git('show', f'coord/{self.task.name[:8]}:{name}') + '\n', GOOD_TESTS)

    def test_patch_paths_use_git_decoding_in_both_directions(self):
        names = ['space name', 'é', 'tab\tname', 'line\nname', 'quote"name', 'back\\slash',
                 os.fsdecode(b'invalid-\xff')]
        for index, name in enumerate(names):
            (self.repo / name).write_bytes(b'\0binary-' + str(index).encode())
        self.git('add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'odd paths')
        destinations = []
        for name in names:
            destination = 'renamed ' + name
            (self.repo / name).rename(self.repo / destination)
            destinations.append(destination)
        self.git('add', '-A')
        patch = self.base / 'paths.patch'
        patch.write_bytes(subprocess.check_output(['git', '-C', str(self.repo), 'diff', '--cached', '--binary']))
        self.assertEqual(drive.files_in_patch(patch), set(names + destinations))
        patch.write_bytes(subprocess.check_output(['git', '-C', str(self.repo), '-c',
                                                  'core.quotePath=false', 'diff', '--cached', '--binary']))
        self.assertEqual(drive.files_in_patch(patch), set(names + destinations))
        # Actual binary hunks, additions and deletions must also yield every name.
        for name in destinations:
            (self.repo / name).write_bytes(b'\0changed')
        (self.repo / 'new binary').write_bytes(b'\0new')
        (self.repo / destinations[0]).unlink()
        self.git('add', '-A')
        patch.write_bytes(subprocess.check_output(['git', '-C', str(self.repo), 'diff', '--cached', '--binary']))
        self.assertEqual(drive.files_in_patch(patch), set(names + destinations[1:] + ['new binary']))

    def test_copied_patch_includes_source_and_destination(self):
        source, destination = 'source é', 'copy "é"'
        (self.repo / source).write_bytes(b'\0binary')
        self.git('add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'source')
        (self.repo / destination).write_bytes((self.repo / source).read_bytes())
        self.git('add', '-A')
        patch = self.base / 'copy.patch'
        patch.write_bytes(subprocess.check_output(['git', '-C', str(self.repo), 'diff', '--cached',
                                                  '--binary', '--find-copies-harder']))
        self.assertIn(b'copy from', patch.read_bytes())
        self.assertEqual(drive.files_in_patch(patch), {source, destination})

    def test_malformed_patch_metadata_is_rejected(self):
        patch = self.base / 'malformed.patch'
        patch.write_bytes(b'diff --git "a/unterminated b/file\nrename from x\n')
        with self.assertRaisesRegex(tasks.StateError, 'patch'):
            drive.files_in_patch(patch)

    def test_plan_with_no_failing_goal_check_is_refused(self):
        already_green = plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]), goal_checks=[SUITE])
        self.scenario({'multiplication': [{'files': {'calc.py': MUL}}]},
                      decompose=[already_green, plan(outcome('mul', 'Add multiplication to calc', [MUL_CHECK]))])
        self.start()
        self.select()
        self.assert_done_on_branch(self.run_until(), MUL)
        request = next(r for r in drive.load_drive(self.task)['requests'].values() if r['kind'] == 'decompose')
        self.assertIn('already passes on the current code', request['errors'][0])

    def test_judge_output_parsing_unwraps_cli_envelopes(self):
        wrapped = json.dumps({'type': 'result', 'result': 'Here you go:\n{"verdict": "accept", "reason": "ok"}'})
        self.assertEqual(coord.parse_judge_output(wrapped), {'verdict': 'accept', 'reason': 'ok'})
        self.assertEqual(coord.parse_judge_output('noise {"a": {"b": 1}} tail'), {'a': {'b': 1}})
        self.assertIsNone(coord.parse_judge_output('no json here'))


class RedProcessTests(unittest.TestCase):
    """Exercise the actual _red command behind the outer verification boundary."""

    def exercise_nested_check(self, *, timeout, leader_exits=False, inner_timeout=None):
        import signal
        import coord_outcomes as outcomes
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'late-write'
            identities = root / 'children.json'
            parent_identity = root / 'parent.pid'
            descendant = ("import os,time,pathlib;"
                          f"pathlib.Path({str(identities)!r}).write_text(str(os.getpid()));"
                          "time.sleep(1.2);"
                          f"pathlib.Path({str(marker)!r}).write_text('late')")
            parent = ("import os,pathlib,subprocess,sys,time;"
                      f"pathlib.Path({str(parent_identity)!r}).write_text(str(os.getpid()));"
                      f"subprocess.Popen([sys.executable,'-c',{descendant!r}]);"
                      + ("time.sleep(0.15)" if leader_exits else "time.sleep(30)"))
            spec = drive.red_check([check('spawns-grandchild', parent)])
            try:
                if inner_timeout is None:
                    evidence = outcomes.run_checks([spec], root, timeout)
                else:
                    self.assertEqual(drive.red([check('inner-timeout', parent)], root, inner_timeout), 0)
                    evidence = [{'exit_code': None}]
                self.assertTrue(identities.exists(), 'grandchild must start to test settlement')
                if leader_exits:
                    self.assertEqual(evidence[0]['exit_code'], 1)
                else:
                    self.assertIsNone(evidence[0]['exit_code'])
                # Zombies have stopped executing; check both the leader and grandchild.
                stats = [Path(f'/proc/{int(identity.read_text())}/stat')
                         for identity in (parent_identity, identities)]
                live = any(stat.exists() and stat.read_text().rsplit(')', 1)[1].split()[0] != 'Z'
                           for stat in stats)
                time.sleep(1.3)
                self.assertEqual((live, marker.exists()), (False, False),
                                 'terminal verification left a live/writing grandchild')
            finally:
                # Baseline failures must also settle the deliberately exposed orphan.
                for identity in (parent_identity, identities):
                    if identity.exists():
                        try:
                            os.kill(int(identity.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_inner_timeout_before_group_creation_settles_wrapper(self):
        import coord_process
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'startup-write'
            # Delay Python startup before the nested wrapper calls setpgrp().
            (root / 'sitecustomize.py').write_text('import time; time.sleep(0.4)')
            command = [sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()']
            with unittest.mock.patch.dict(os.environ, {'PYTHONPATH': str(root)}):
                with self.assertRaises(subprocess.TimeoutExpired):
                    coord_process.run(command, root, 0.05, new_session=False)
            time.sleep(0.5)
            self.assertFalse(marker.exists(), 'timed-out startup wrapper still executed its check')

    def test_outer_timeout_settles_nested_red_check_and_grandchild(self):
        self.exercise_nested_check(timeout=0.6)

    def test_inner_red_timeout_settles_grandchild(self):
        self.exercise_nested_check(timeout=5, inner_timeout=0.6)

    def test_nested_red_check_leader_exit_settles_grandchild(self):
        self.exercise_nested_check(timeout=5, leader_exits=True)


class SetupTests(unittest.TestCase):
    """doctor and profile defaults: the front desk knows when to run the setup interview."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name) / 'config'
        env = unittest.mock.patch.dict(os.environ, {'COORDINATOR_CONFIG_HOME': str(self.config)})
        env.start()
        self.addCleanup(env.stop)

    def save_profile(self, driver):
        self.config.mkdir(parents=True, exist_ok=True)
        (self.config / 'host.json').write_text(json.dumps({'version': 1, 'adapters': {'driver': driver},
                                                           'catalogs': [], 'memory_sidecar': 'disabled'}))

    def test_missing_profile_points_to_the_interview(self):
        result = drive.doctor()
        self.assertFalse(result['ready'])
        self.assertTrue(any('no host profile' in p for p in result['problems']))
        self.assertIn('driver interview', result['next'])

    def test_uninstalled_worker_command_is_reported(self):
        self.save_profile({'workers': [{'route': {'harness': 'ghost', 'model': 'm'},
                                        'argv': ['definitely-not-installed-cli', '{prompt}']}]})
        result = drive.doctor()
        self.assertFalse(result['ready'])
        self.assertTrue(any('definitely-not-installed-cli' in p for p in result['problems']))

    def test_ready_profile_supplies_workers_and_judge(self):
        workers = [{'route': {'harness': 'fake', 'model': 'm'}, 'argv': [sys.executable, '-c', 'pass', '{prompt}']}]
        self.save_profile({'workers': workers, 'judge': [sys.executable, '-c', 'pass']})
        self.assertTrue(drive.doctor()['ready'])
        self.assertEqual(drive.profile_driver()['workers'], workers)

    def test_start_without_workers_explains_setup(self):
        repo = Path(self.tmp.name) / 'repo'
        repo.mkdir()
        subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
        with unittest.mock.patch('sys.stderr') as stderr:
            code = coord.main(['--root', str(Path(self.tmp.name) / 'state'), 'start', '--repo', str(repo),
                               '--goal', 'g', '--criterion', 'c'])
        self.assertEqual(code, 1)
        self.assertIn('coordinator-setup driver interview', ''.join(c.args[0] for c in stderr.write.call_args_list))


if __name__ == '__main__':
    unittest.main()
