"""Bounded local commands and settlement of their Linux sessions/process groups.

Top-level commands own a session. Nested checks own a process group within
that session, so either timeout can settle them. Commands must keep descendants
in their assigned session/group. A terminal result is published only after no
live member remains. Detached jobs require a different runtime and explicit
ownership; they cannot use this adapter.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def live_group(pid, *, session=True):
    members = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if fields[0] != 'Z' and int(fields[3 if session else 2]) == pid:
                members.append(int(path.parent.name))
        except (OSError, ValueError, IndexError):
            continue
    return members


def settle(process, *, session=True):
    """Stop the owned session (or nested group), including leaderless descendants."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    # Nested wrappers may not have created their group when timeout fires.
    # Kill the owned Popen leader as well before waiting for its settlement.
    process.kill()
    process.wait(timeout=5)
    deadline = time.monotonic() + 5
    while members := live_group(process.pid, session=session):
        # A nested check may have its own group in our session. Re-scan after
        # killing members so a concurrent fork cannot escape settlement.
        for pid in members:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args, 5)
        time.sleep(0.01)


def diagnostic(stream):
    stream.seek(0)
    data = stream.read(65537)
    return data[:65536].decode('utf-8', errors='replace') + ('\n[output truncated]' if len(data) > 65536 else '')


def run(argv, cwd, timeout, *, new_session=True):
    """Keep diagnostic memory bounded; timeout includes descendant cleanup."""
    if not new_session:
        # Set the group inside a fresh interpreter, then replace it with the
        # check. This works on Python 3.10 without preexec_fn's thread hazards
        # or a race between parent setpgid() and child exec().
        argv = [sys.executable, '-c',
                'import os,sys; os.setpgrp(); os.execvp(sys.argv[1], sys.argv[1:])', *argv]
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, start_new_session=new_session)
        try:
            code = process.wait(timeout=timeout)
        finally:
            settle(process, session=new_session)
        return code, diagnostic(stdout), diagnostic(stderr)
