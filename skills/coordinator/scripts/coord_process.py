"""Bounded local commands and settlement of their Linux process groups.

Commands must keep descendants in their assigned session/group. A terminal
result is published only after no live member remains. Detached jobs require a
different runtime and explicit ownership; they cannot use this adapter.
"""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def live_group(pid):
    members = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if fields[0] != 'Z' and int(fields[2]) == pid and int(fields[3]) == pid:
                members.append(int(path.parent.name))
        except (OSError, ValueError, IndexError):
            continue
    return members


def settle(process):
    """Stop remaining group members and prove settlement before returning."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)
    deadline = time.monotonic() + 5
    while live_group(process.pid):
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args, 5)
        time.sleep(0.01)


def diagnostic(stream):
    stream.seek(0)
    data = stream.read(65537)
    return data[:65536].decode('utf-8', errors='replace') + ('\n[output truncated]' if len(data) > 65536 else '')


def run(argv, cwd, timeout):
    """Keep diagnostic memory bounded; timeout includes descendant cleanup."""
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        finally:
            settle(process)
        return code, diagnostic(stdout), diagnostic(stderr)
