"""Contract checks against Herdr 0.9.1 CLI receipts and bundled protocol 22.

Fixture provenance distinguishes observed read-only replies from schema facts.
No Herdr server or worker is needed when running these regression tests.
"""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import herdr_worker as worker

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/herdr-0.9.1.json').read_text())


def replay(name):
    receipt = FIXTURE['receipts'][name]
    return subprocess.CompletedProcess(['herdr'], **receipt)


class HerdrContractTests(unittest.TestCase):
    def test_observed_json_receipts_satisfy_schema_required_fields(self):
        for name in ('agent_get', 'agent_list', 'agent_wait', 'pane_get', 'pane_list', 'output_matched'):
            with self.subTest(name=name):
                result = json.loads(replay(name).stdout)['result']
                required = FIXTURE['result_required_fields'][result['type']]
                self.assertTrue(set(required) <= result.keys())

    def test_inspect_and_wait_use_actual_agent_info_envelope(self):
        client = worker.Herdr()
        with patch.object(client, 'run', return_value=replay('agent_get')):
            self.assertEqual(client.inspect('fixture:p')['result']['agent']['pane_id'], 'fixture:p')
        with patch.object(client, 'run', return_value=replay('agent_wait')):
            self.assertEqual(client.wait('fixture:p', ['done'])['result']['agent']['agent_status'], 'done')

    def test_list_and_membership_paths_match_real_receipts(self):
        client = worker.Herdr()
        with patch.object(client, 'run', return_value=replay('agent_list')):
            inventory = worker.execute(worker.parser().parse_args(['inventory']), client)
            self.assertIsInstance(inventory['live_agents'], list)
        with patch.object(client, 'run', return_value=replay('pane_get')):
            pane = client.call('pane', 'get', 'fixture:p')['result']['pane']
        with patch.object(client, 'run', return_value=replay('pane_list')):
            panes = client.call('pane', 'list', '--workspace', pane['workspace_id'])['result']['panes']
        self.assertEqual(panes[0]['tab_id'], pane['tab_id'])

    def test_reads_are_text_while_wait_output_is_json(self):
        client = worker.Herdr()
        args = worker.parser().parse_args(['read', 'fixture:p'])
        with patch.object(client, 'run', return_value=replay('pane_read')):
            self.assertEqual(worker.execute(args, client), {'text': 'fixture text\n'})
        with patch.object(client, 'run', return_value=replay('agent_read')):
            self.assertEqual(client.call('agent', 'read', 'fixture:p', raw=True), 'fixture text\n')
        with patch.object(client, 'run', return_value=replay('output_matched')):
            self.assertEqual(client.call('pane', 'wait-output', 'fixture:p')['result']['type'], 'output_matched')

    def test_nonzero_stderr_errors_fail_closed(self):
        client = worker.Herdr()
        for name, code in [('not_found', 'agent_not_found'), ('timeout', 'timeout')]:
            with self.subTest(name=name), patch.object(client, 'run', return_value=replay(name)):
                self.assertEqual(replay(name).stdout, '')
                with self.assertRaisesRegex(worker.WorkerError, code):
                    client.inspect('fixture:p')

    def test_mutation_envelope_requirements_from_bundled_schema(self):
        required = FIXTURE['result_required_fields']
        self.assertEqual(set(required['tab_created']), {'type', 'tab', 'root_pane'})
        self.assertEqual(set(required['agent_started']), {'type', 'agent', 'argv'})
        self.assertEqual(set(required['agent_prompted']), {'type', 'agent'})
        # Generic acknowledgements carry no additional fields. The helper must
        # accept this envelope without inventing e.g. result.success or result.ok.
        self.assertEqual(required['ok'], ['type'])
        client = worker.Herdr()
        with patch.object(client, 'run', return_value=subprocess.CompletedProcess([], 0, '{"id":"schema-example","result":{"type":"ok"}}', '')):
            self.assertEqual(client.call('tab', 'close', 'fixture:t')['result'], {'type': 'ok'})


if __name__ == '__main__':
    unittest.main()
