import json
import sys
import tempfile
import unittest
from pathlib import Path
from lab import Lab
from run import drive


class RunnerProbes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'run.sqlite')
        self.lab = Lab(self.path)
        self.lab.init({'question': 'Is the unavailable proposition supported?', 'budget': {'seconds': 2}})
        self.lab.db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def adapter(self, code):
        script = Path(self.tmp.name) / 'adapter.py'
        script.write_text(code)
        return [sys.executable, str(script)]

    def test_unattended_driver_completes_honest_uncertain_fixture(self):
        host = self.adapter('''import json,sys
r=json.load(sys.stdin)
responses={
'plan':{'claims':[{'id':'c1','text':'The proposition holds'}],'strategy':'Look for evidence'},
'research':{'sources':[],'claims':[{'id':'c1','text':'The proposition is unverified','status':'uncertain','sources':[],'uncertainty':'No source access in this fixture'}]},
'challenge':{'reviews':[{'claim':'c1','verdict':'uncertain','reason':'No inspected evidence','sources':[]}],'contradictions':[],'followups':['Obtain original evidence'],'needs_more':False},
'report':{'conclusion':'Insufficient evidence','judgment':'Decide whether to fund retrieval','uncertainties':['No source access'],'followups':['Retrieve evidence'],'lessons':['Access is a prerequisite']}}
print(json.dumps(responses[r['stage']]))
''')
        result = drive(self.path, host)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['used']['steps'], 4)
        self.assertEqual(result['claims'][0]['status'], 'uncertain')

    def test_adapter_timeout_is_terminal_and_returns_partial_state(self):
        result = drive(self.path, self.adapter('import time; time.sleep(20)'))
        self.assertEqual(result['stop_reason'], 'host_timeout')
        self.assertEqual(result['status'], 'stopped')

    def test_malformed_response_stops_without_retry(self):
        result = drive(self.path, self.adapter("print('not json')"))
        self.assertEqual(result['stop_reason'], 'invalid_host_response')
        self.assertEqual(result['used']['steps'], 1)

    def test_nonzero_exit_and_missing_host_stop(self):
        result = drive(self.path, self.adapter('raise SystemExit(7)'))
        self.assertEqual(result['stop_reason'], 'host_failure_or_oversize')
        other = str(Path(self.tmp.name) / 'other.sqlite')
        lab = Lab(other)
        lab.init({'question': 'Can missing host start?'})
        lab.db.close()
        result = drive(other, ['/nonexistent/research-host'])
        self.assertEqual(result['stop_reason'], 'host_unavailable')

    def test_recorded_real_protocol_replays_offline(self):
        from replay import replay
        recording = json.loads(Path(__file__).with_name('results').joinpath('autonomous/final.json').read_text())
        output = replay(recording, str(Path(self.tmp.name) / 'replayed.sqlite'))
        self.assertEqual(output['status'], 'completed')
        self.assertEqual(output['used'], recording['used'])
        self.assertEqual([(c['id'], c['status'], c['text']) for c in output['claims']], [(c['id'], c['status'], c['text']) for c in recording['claims']])
        with self.assertRaisesRegex(ValueError, 'must not exist'):
            replay(recording, str(Path(self.tmp.name) / 'replayed.sqlite'))

    def test_oversize_output_stops(self):
        result = drive(self.path, self.adapter("print('x' * (1024 * 1024 + 2))"))
        self.assertEqual(result['stop_reason'], 'host_failure_or_oversize')


if __name__ == '__main__':
    unittest.main()
