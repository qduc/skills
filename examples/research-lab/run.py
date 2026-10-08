#!/usr/bin/env python3
"""Automate ledger requests using a preapproved local JSON host adapter (no shell)."""
import argparse
import json
import os
import signal
import resource
import subprocess
import tempfile
from pathlib import Path
from lab import Lab


def bound_adapter_files():
    # Bound both stdout/stderr temporary files before a runaway adapter fills disk.
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))


def drive(db, host):
    lab = Lab(db)
    try:
        while True:
            request = lab.request()
            if 'schema' not in request:
                return lab.export()
            # The host receives this path so its trusted tool gateway can reserve and observe.
            request['ledger_path'] = str(Path(db).resolve())
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                try:
                    process = subprocess.Popen(host, stdin=subprocess.PIPE, stdout=output, stderr=errors, start_new_session=True, preexec_fn=bound_adapter_files)
                except OSError as error:
                    with lab.transaction():
                        state = lab.state()
                        lab.event('verify', {'adapter_error': str(error)})
                        lab.stop(state, 'host_unavailable')
                    return lab.export()
                try:
                    process.communicate(json.dumps(request).encode(), timeout=max(.01, request['seconds_remaining']))
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    with lab.transaction():
                        state = lab.state()
                        lab.stop(state, 'host_timeout')
                    return lab.export()
                output.seek(0)
                data = output.read(1024 * 1024 + 1)
                # Adapter failure terminates; no blind retries or unbounded context output.
                if process.returncode or len(data) > 1024 * 1024:
                    with lab.transaction():
                        state = lab.state()
                        lab.stop(state, 'host_failure_or_oversize')
                    return lab.export()
                try:
                    response = json.loads(data)
                    result = lab.submit(request['id'], response)
                except (ValueError, TypeError, KeyError) as error:
                    with lab.transaction():
                        state = lab.state()
                        lab.event('verify', {'adapter_error': str(error)})
                        lab.stop(state, 'invalid_host_response')
                    return lab.export()
                if result['status'] != 'running':
                    return lab.export()
    finally:
        lab.db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('host', nargs=argparse.REMAINDER, help='preapproved local executable and args after --')
    args = parser.parse_args()
    host = args.host[1:] if args.host[:1] == ['--'] else args.host
    if not host:
        parser.error('supply a trusted host executable after --')
    print(json.dumps(drive(args.db, host), indent=2))
