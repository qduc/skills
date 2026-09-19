#!/usr/bin/env python3
"""Herdr worker transport. JSON receipts; explicit routes and opaque targets."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

import start_term2


def inherited_run(command, **kwargs):
    # Keep the coordinator's locks alive through an in-flight CLI request.
    inherited = os.environ.get("COORDINATOR_LOCK_FDS", "")
    if inherited:
        fds = tuple(int(value) for value in inherited.split(","))
        for fd in fds:
            os.fstat(fd)
        kwargs["pass_fds"] = fds
    return subprocess.run(command, **kwargs)


def save_receipt(path, receipt):
    if not path:
        return
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(receipt, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        Path(temporary).unlink(missing_ok=True)


class WorkerError(RuntimeError):
    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


# Herdr 0.9.1 renders successful acknowledgements as empty stdout for these
# CLI commands, although the socket response itself is {result: {type: ok}}.
EMPTY_ACK_COMMANDS = {("pane", "run"), ("pane", "send-text"), ("pane", "send-keys"),
                      ("agent", "send-keys")}


def route_argv(kind, model, provider=None, effort=None):
    for value in (kind, model, provider, effort):
        if value is not None and (not value.strip() or any(ord(c) < 32 for c in value)):
            raise WorkerError("Route values must be nonempty single-line strings")
    if not model:
        raise WorkerError("An explicit model is required")
    if kind in ("term2", "pi"):
        if not provider:
            raise WorkerError("This harness requires an explicit provider")
        argv = ["--provider", provider, "--model", model]
        if effort:
            argv += ["--reasoning" if kind == "term2" else "--thinking", effort]
    elif kind == "codex":
        argv = ["--model", model]
        if provider:
            argv += ["-c", "model_provider=" + json.dumps(provider)]
        if effort:
            argv += ["-c", "model_reasoning_effort=" + json.dumps(effort)]
    elif kind in ("claude", "agy"):
        if provider:
            raise WorkerError("This harness uses its provider environment; omit --provider")
        argv = ["--model", model]
        if effort:
            argv += ["--effort", effort]
    else:
        raise WorkerError("Unsupported launch route: " + kind + "; supported: term2, pi, codex, claude, agy")
    return argv


class Herdr:
    def __init__(self, executable="herdr", timeout_ms=30000, run=inherited_run):
        if not 1000 <= timeout_ms <= 120000:
            raise WorkerError("timeout-ms must be 1000..120000")
        self.executable, self.timeout_ms, self.run = executable, timeout_ms, run

    def call(self, *parts, raw=False):
        command = [self.executable, *parts]
        if self.executable.endswith(".py"):
            command.insert(0, sys.executable)
        result = self.run(command, capture_output=True, text=True, timeout=self.timeout_ms / 1000 + 5)
        detail = {"operation": list(parts[:2]), "exit_code": result.returncode,
                  "stdout": result.stdout[:4096], "stderr": result.stderr[:4096]}
        if result.returncode:
            raise WorkerError(result.stderr.strip() or result.stdout.strip() or "Herdr command failed", detail)
        if raw:
            return result.stdout
        if not result.stdout.strip() and tuple(parts[:2]) in EMPTY_ACK_COMMANDS:
            return {"result": {"type": "ok"}}
        try:
            data = json.loads(result.stdout)
            if not isinstance(data, dict) or not isinstance(data.get("result"), dict):
                raise ValueError("missing result object")
            return data
        except ValueError as error:
            raise WorkerError("Invalid Herdr JSON for " + " ".join(parts[:2]) + ": " + str(error), detail) from error

    def inspect(self, target):
        return self.call("agent", "get", target)

    def wait(self, target, until):
        flags = [part for status in until for part in ("--until", status)]
        result = self.call("agent", "wait", target, *flags, "--timeout", str(self.timeout_ms))
        if result.get("result", {}).get("agent", {}).get("agent_status") not in until:
            raise WorkerError("Wait returned without the requested lifecycle state")
        return result

    def start(self, args):
        argv = route_argv(args.kind, args.model, args.provider, args.effort)
        executable = shutil.which(args.kind)
        if not executable:
            raise WorkerError("Harness executable unavailable: " + args.kind)
        cwd = Path(args.cwd).resolve(strict=True)
        if not cwd.is_dir() or not args.workspace.strip() or not args.name.strip():
            raise WorkerError("Explicit workspace, name and directory required")
        receipt = dict(name=args.name, kind=args.kind, model=args.model,
                       provider=args.provider, effort=args.effort, cwd=str(cwd),
                       workspace_id=args.workspace, status="failed", owned_tab=True,
                       acknowledgement="not_verified",
                       operation_id=getattr(args, "operation_id", None) or uuid.uuid4().hex)
        receipt_file = getattr(args, "receipt_file", None)
        if receipt_file and Path(receipt_file).exists():
            raise WorkerError("Receipt already exists; inspect and recover instead of relaunching")
        receipt["status"] = "create_intended"
        save_receipt(receipt_file, receipt)
        try:
            created = self.call("tab", "create", "--workspace", args.workspace,
                                "--cwd", str(cwd), "--label", args.label or args.name, "--no-focus")["result"]
            receipt["tab_id"] = created["tab"]["tab_id"]
            save_receipt(receipt_file, receipt)
            receipt["pane_id"] = pane = created["root_pane"]["pane_id"]
            if not all(isinstance(receipt[k], str) and receipt[k] for k in ("tab_id", "pane_id")):
                raise WorkerError("Invalid tab/pane identity")
            receipt["status"] = "launch_intended"
            save_receipt(receipt_file, receipt)
            if args.kind == "term2":
                self.call("pane", "run", pane, shlex.join([executable, *argv]))
                self.call("pane", "wait-output", pane, "--source", "visible",
                          "--regex", start_term2.PROMPT_LINE, "--timeout", str(self.timeout_ms))
            else:
                self.call("agent", "start", args.name, "--kind", args.kind, "--pane", pane,
                          "--timeout", str(self.timeout_ms), "--", *argv)
            observed = self.inspect(pane)["result"]["agent"]
            if observed.get("agent") != args.kind or observed.get("agent_status") not in ("idle", "done"):
                raise WorkerError("Expected chosen harness ready in the created pane")
            receipt["status"] = "ready"
        except (WorkerError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as error:
            receipt.update(status="failed", error=str(error), next_action="Inspect the preserved pane before retrying; do not relaunch blindly")
            if isinstance(error, WorkerError) and error.detail:
                receipt["error_detail"] = error.detail
        save_receipt(receipt_file, receipt)
        return receipt

    def submit(self, target, message, steer=False):
        agent = self.inspect(target)["result"]["agent"]
        if os.environ.get("HERDR_PANE_ID") and agent.get("pane_id") == os.environ["HERDR_PANE_ID"]:
            raise WorkerError("Refusing mutation of the caller pane")
        if agent.get("agent_status") not in (("idle", "done", "working") if steer else ("idle", "done")):
            raise WorkerError("Worker is not ready for this operation")
        if agent.get("agent") == "term2":
            # Reuse the guarded TUI transport, including draft verification and
            # acknowledgement-after-echo semantics. Never inject into a shell.
            args = start_term2.build_steer_parser().parse_args([
                target, "--message", message, "--herdr", self.executable,
                "--timeout-ms", str(self.timeout_ms),
                *(["--ack-timeout-ms", str(self.timeout_ms)] if steer else ["--no-ack"])])
            receipt = start_term2.steer(args, run=self.run)
            if receipt["status"] == "failed":
                return receipt
        else:
            self.call("agent", "prompt", target, message)
            receipt = {"status": "delivered", "transport": "agent-prompt", "acknowledgement": "not_verified"}
        if not steer:
            try:
                self.wait(target, ["working"])
                receipt["status"] = "admitted"
            except WorkerError as error:
                receipt.update(status="admission_unknown", error=str(error),
                               next_action="Inspect output and inbox before resending")
        return receipt


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--herdr", default=os.environ.get("COORDINATOR_HERDR", "herdr"))
    root.add_argument("--timeout-ms", type=int, default=30000)
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    start = sub.add_parser("start")
    for name in ("name", "kind", "model", "workspace", "cwd"):
        start.add_argument("--" + name, required=True)
    for name in ("provider", "effort", "label", "receipt-file", "operation-id"):
        start.add_argument("--" + name)
    for name in ("inspect", "observe", "read", "wait", "stop", "submit", "steer", "close"):
        cmd = sub.add_parser(name)
        cmd.add_argument("target")
        if name in ("submit", "steer"):
            cmd.add_argument("--message-file", required=True)
        if name == "wait":
            cmd.add_argument("--until", action="append", required=True, choices=["working", "idle", "done", "blocked"])
        if name == "close":
            cmd.add_argument("--owned-tab", required=True, help="Task-owned tab ID recorded at creation")
    return root


def execute(args, client):
    if args.command == "inventory":
        live = client.call("agent", "list")["result"]["agents"]
        return {"available": True, "kinds": [dict(kind=k, binary=shutil.which(k), available=bool(shutil.which(k)))
                for k in ("term2", "pi", "codex", "claude", "agy")], "live_agents": live}
    if args.command == "start":
        return client.start(args)
    if not args.target.strip() or args.target == os.environ.get("HERDR_PANE_ID") and args.command in ("submit", "steer", "stop", "close"):
        raise WorkerError("Refusing an empty target or mutation of the caller pane")
    if args.command == "inspect":
        return client.inspect(args.target)
    if args.command == "observe":
        agent = client.inspect(args.target)["result"]["agent"]
        # Visible snapshot only: old scrollback markers are not current signals.
        visible = client.call("pane", "read", args.target, "--source", "visible", raw=True)
        text = " ".join(visible.split())
        prompts = ("Allow this read outside the workspace?", "Allow permission to edit this file outside the workspace?",
                   "Allow this action?", "Allow Docker host access?")
        approval = agent.get("agent") == "term2" and any(p in text for p in prompts) and (
            ("Allow once" in text and "Reject" in text) or
            ("Approve" in text and "Reject" in text) or ("Allow this command" in text and "Deny" in text))
        return {"agent": agent, "signal": "approval_suspected" if approval else "lifecycle",
                "visible_text": visible, "requires_inspection": bool(approval)}
    if args.command == "read":
        return {"text": client.call("pane", "read", args.target, "--source", "recent-unwrapped", "--lines", "100", raw=True)}
    if args.command == "wait":
        return client.wait(args.target, args.until)
    if args.command in ("submit", "steer"):
        message = Path(args.message_file).read_text()
        if not message.strip():
            raise WorkerError("Message file is empty")
        return client.submit(args.target, message, steer=args.command == "steer")
    observed = client.inspect(args.target)["result"]["agent"]
    if os.environ.get("HERDR_PANE_ID") and observed.get("pane_id") == os.environ["HERDR_PANE_ID"]:
        raise WorkerError("Refusing mutation of the caller pane")
    if args.command == "stop":
        if observed.get("agent_status") not in ("idle", "done"):
            if observed.get("agent_status") != "working":
                raise WorkerError("Unknown or blocked worker; inspect before interrupting")
            client.call("agent", "send-keys", args.target, "esc")
        return client.wait(args.target, ["idle", "done"])
    if observed.get("agent_status") not in ("idle", "done"):
        raise WorkerError("Worker must be settled before closing its tab")
    # Verify tab membership from the pane, not from a mutable agent name.
    pane = client.call("pane", "get", observed["pane_id"])["result"]["pane"]
    if pane.get("tab_id") != args.owned_tab:
        raise WorkerError("Pane does not belong to the recorded owned tab")
    panes = client.call("pane", "list", "--workspace", pane["workspace_id"])["result"]["panes"]
    siblings = [p for p in panes if p.get("tab_id") == args.owned_tab]
    if len(siblings) != 1 or siblings[0].get("pane_id") != observed["pane_id"]:
        raise WorkerError("Tab now contains other panes; inspect ownership before closing")
    return client.call("tab", "close", args.owned_tab)


def main():
    args = parser().parse_args()
    try:
        result = execute(args, Herdr(args.herdr, args.timeout_ms))
        print(json.dumps(result))
        return 1 if result.get("status") in ("failed", "admission_unknown") else 0
    except (WorkerError, OSError, KeyError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
