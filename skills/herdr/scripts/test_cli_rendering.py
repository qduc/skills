"""Exercise the installed CLI renderer, not only socket response fixtures."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import herdr_worker as worker


class RenderingTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('herdr'), 'installed Herdr required')
    def test_socket_ok_is_rendered_as_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'socket')
            server = socket.socket(socket.AF_UNIX)
            server.bind(path)
            server.listen()
            server.settimeout(0.1)
            stopped = threading.Event()
            methods = []
            def serve():
                while not stopped.is_set():
                    try:
                        connection, _ = server.accept()
                    except socket.timeout:
                        continue
                    with connection, connection.makefile('r') as stream:
                        for line in stream:
                            request = json.loads(line)
                            methods.append(request['method'])
                            result = ({'type': 'pong', 'version': '0.9.1', 'protocol': 22}
                                      if request['method'] == 'ping' else {'type': 'ok'})
                            connection.sendall((json.dumps({'id': request['id'], 'result': result}) + '\n').encode())
            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            try:
                with patch.dict(os.environ, {'HERDR_SOCKET_PATH': path}):
                    for arguments in [('pane', 'run', 'fixture:p', 'true'),
                                      ('pane', 'send-text', 'fixture:p', 'hello'),
                                      ('pane', 'send-keys', 'fixture:p', 'Enter'),
                                      ('agent', 'send-keys', 'fixture:p', 'esc'),
                                      ('tab', 'close', 'fixture:t')]:
                        result = worker.Herdr(timeout_ms=1000).call(*arguments)
                        self.assertEqual(result['result'], {'type': 'ok'})
                self.assertIn('pane.send_input', methods)
            finally:
                stopped.set()
                thread.join(timeout=2)
                server.close()

    def test_empty_ack_allowlist_and_error_diagnostics(self):
        def run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, '', 'diagnostic')
        client = worker.Herdr(run=run)
        for operation in worker.EMPTY_ACK_COMMANDS:
            self.assertEqual(client.call(*operation)['result']['type'], 'ok')
        for operation in [('agent', 'get'), ('tab', 'create'), ('agent', 'wait')]:
            with self.assertRaises(worker.WorkerError) as error:
                client.call(*operation)
            self.assertEqual(error.exception.detail['operation'], list(operation))
            self.assertEqual(error.exception.detail['stderr'], 'diagnostic')

    def test_observe_approval_uses_visible_text_and_preserves_working_status(self):
        client = worker.Herdr()
        args = worker.parser().parse_args(['observe', 'p'])
        for text, signal in [('Allow this read outside\n the workspace? Allow once Reject', 'approval_suspected'),
                             ('TASK_BLOCKED from yesterday; now working', 'lifecycle')]:
            with patch.object(client, 'inspect', return_value={'result': {'agent': {'agent': 'term2', 'agent_status': 'working'}}}), patch.object(client, 'call', return_value=text) as call:
                result = worker.execute(args, client)
                self.assertEqual(result['signal'], signal)
                self.assertEqual(result['agent']['agent_status'], 'working')
                call.assert_called_once_with('pane', 'read', 'p', '--source', 'visible', raw=True)

    def test_agy_explicit_route(self):
        self.assertEqual(worker.route_argv('agy', 'selected', effort='high'),
                         ['--model', 'selected', '--effort', 'high'])
        with self.assertRaises(worker.WorkerError):
            worker.route_argv('agy', 'selected', provider='unmapped')
