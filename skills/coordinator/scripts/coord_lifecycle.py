#!/usr/bin/env python3
"""Deterministic lifecycle mechanics for external-agent coordination."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

import coord_inbox
import coord_state
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ADAPTER_ENV = {"herdr": "COORDINATOR_HERDR_HELPER"}
SETTLED = {"idle", "done", "missing"}
MAX_ADAPTER_OUTPUT_BYTES = 1_048_576
MAX_ARTIFACT_BYTES = 268_435_456
DEFAULT_COMMAND_TIMEOUT_SECONDS = 60.0
# The CLI owns these descriptors while a mutation is in flight. Child adapters
# inherit them so killing the coordinator cannot unlock an active adapter.
_ACTIVE_LOCK_FDS: tuple[int, ...] = ()
READ_COMMANDS = {"doctor", "inventory", "receive", "watch"}
WORKER_COMMANDS = {"report", "send"}
MUTATION_COMMANDS = {"prepare", "bind", "preserve", "start-worker", "dispatch", "recover-worker",
                     "resolve-dispatch", "ack", "mark-read", "verify", "reconcile", "stop", "run-task"}
EXTERNAL_COMMANDS = {"preserve", "start-worker", "dispatch", "recover-worker", "resolve-dispatch", "reconcile", "run-task"}


class LifecycleError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(
    command: list[str], *, allow_failure: bool = False,
    timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command, text=True, capture_output=True, timeout=timeout_seconds,
            **({"pass_fds": _ACTIVE_LOCK_FDS,
                "env": dict(os.environ, COORDINATOR_LOCK_FDS=",".join(map(str, _ACTIVE_LOCK_FDS)))}
               if _ACTIVE_LOCK_FDS else {}),
        )
    except subprocess.TimeoutExpired as error:
        raise LifecycleError(f"command timed out after {timeout_seconds:g}s: {' '.join(command)}") from error
    if result.returncode and not allow_failure:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise LifecycleError(f"command failed: {' '.join(command)}: {detail}")
    return result


def decode_json(result: subprocess.CompletedProcess[str], label: str) -> Any:
    if len(result.stdout.encode("utf-8")) > MAX_ADAPTER_OUTPUT_BYTES:
        raise LifecycleError(f"{label} exceeded the {MAX_ADAPTER_OUTPUT_BYTES}-byte output limit")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise LifecycleError(f"{label} returned invalid JSON: {error}") from error


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text())
    except FileNotFoundError as error:
        raise LifecycleError(f"state does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise LifecycleError(f"state is invalid JSON: {path}: {error}") from error
    if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("workers"), dict):
        raise LifecycleError(f"unsupported state: {path}")
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        coord_inbox.sync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def record(state: dict[str, Any], event: str, **fields: Any) -> None:
    state.setdefault("events", []).append({"at": now(), "event": event, **fields})


def resolve_adapter(name: str) -> str | None:
    """Resolve an optional external adapter without assuming package siblings."""
    configured = os.environ.get(ADAPTER_ENV[name])
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return str(path.resolve())
        resolved = shutil.which(configured)
        if resolved:
            return resolved
        return None
    candidates = ("herdr-worker",)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def adapter_command(name: str, *args: str) -> list[str]:
    """Build an adapter command, failing clearly only for optional operations."""
    executable = resolve_adapter(name)
    if not executable:
        variable = ADAPTER_ENV[name]
        raise LifecycleError(
            f"optional adapter unavailable: {name}; install a compatible command "
            f"or set {variable}, then rerun doctor"
        )
    command = [executable]
    if executable.endswith(".py"):
        command = [sys.executable, executable]
    return command + list(args)


def bind(args):
    path = Path(args.state).resolve()
    state = load_state(path)
    if state.get("task_dir"):
        raise LifecycleError("lifecycle already bound; use the existing task record")
    state["task_dir"] = str(Path(args.task_dir).resolve())
    record(state, "task_bound", task_dir=state["task_dir"])
    save_state(path, state)
    return state


def invoke(args):
    """One CLI mutation boundary: serialize state and fence the task owner.

    Worker publication and read-only monitoring remain available while the main
    coordinator is offline. Unbound legacy state supports only file operations
    until explicitly bound; it cannot control external workers.
    """
    global _ACTIVE_LOCK_FDS
    if args.command in READ_COMMANDS | WORKER_COMMANDS:
        return args.handler(args)
    if args.command not in MUTATION_COMMANDS:
        raise LifecycleError("command has no declared ownership policy")
    path = Path(args.state).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_fds = _ACTIVE_LOCK_FDS
    with ExitStack() as stack:
        lifecycle_lock = stack.enter_context(coord_state.locked(path.with_name(path.name + ".lock")))
        existing = load_state(path) if path.exists() else {}
        stored = existing.get("task_dir")
        supplied = getattr(args, "task_dir", None)
        if supplied and args.command not in {"prepare", "bind", "run-task"}:
            raise LifecycleError("task binding is fixed at prepare/bind")
        if stored and supplied and str(Path(supplied).resolve()) != stored:
            raise LifecycleError("cannot replace a lifecycle task binding")
        task_dir = stored or supplied
        if not task_dir and (args.command in EXTERNAL_COMMANDS or args.command == "bind"):
            raise LifecycleError("external operations require a bound task; use prepare --task-dir or bind")
        fds = [lifecycle_lock.fileno()]
        if task_dir:
            task_path = Path(task_dir).resolve()
            task_lock = stack.enter_context(coord_state.locked(task_path / ".write.lock"))
            task = coord_state.load(task_path)
            if not getattr(args, "owner", None) or getattr(args, "revision", None) is None:
                raise LifecycleError("bound mutations require --owner <session-token> and --revision <number|latest>")
            coord_state.check_owner(task, args.owner)
            coord_state.check_revision(task, task["revision"] if args.revision == "latest" else args.revision)
            if task["archived_at"]:
                raise LifecycleError("task is archived")
            task_id = existing.get("task_id") or getattr(args, "task_id", None)
            if task_id != task["id"]:
                raise LifecycleError("lifecycle task ID does not match bound task")
            fds.append(task_lock.fileno())
        _ACTIVE_LOCK_FDS = tuple(fds)
        try:
            return args.handler(args)
        finally:
            _ACTIVE_LOCK_FDS = previous_fds


def doctor(_args: argparse.Namespace) -> dict[str, Any]:
    adapter = inventory(_args)
    return {"core": {"available": True, "python": sys.executable, "transport": "file-inbox"},
            "optional_adapters": {"herdr": adapter}, "ready": True}


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    if state_path.exists():
        raise LifecycleError(f"refusing to overwrite existing state: {state_path}")
    run_id = str(uuid.uuid4())
    inbox_root = Path(args.inbox).expanduser().resolve() if args.inbox else state_path.parent / "inbox"
    inbox_path = inbox_root / run_id
    inbox_path.mkdir(parents=True, mode=0o700)
    state: dict[str, Any] = {
        "version": 1, "run_id": run_id, "created_at": now(),
        "task_id": getattr(args, "task_id", None),
        "task_dir": str(Path(args.task_dir).resolve()) if getattr(args, "task_dir", None) else None,
        "verify_command": getattr(args, "verify_command", None),
        "return_sink": {"path": str(inbox_path), "role": "return-only", "transport": "file"},
        "workers": {}, "events": [],
    }
    record(state, "sink_prepared", run_id=run_id, path=str(inbox_path))
    try:
        save_state(state_path, state)
    except OSError as error:
        inbox_path.rmdir()  # Nothing has been dispatched or published yet.
        raise LifecycleError(f"could not persist lifecycle state: {error}") from error
    return state


def require_file_sink(state: dict[str, Any]) -> Path:
    sink = state.get("return_sink", {})
    if sink.get("transport") != "file" or not isinstance(sink.get("path"), str):
        raise LifecycleError("legacy transport state is read-only; prepare a new file-inbox run and reconcile existing workers manually")
    return Path(sink["path"])


def register_mailbox(state: dict[str, Any], worker: str) -> Path:
    root = require_file_sink(state)
    entry = state["workers"][worker]
    if "inbox" not in entry:
        entry["assignment_id"] = uuid.uuid4().hex
        entry["inbox"] = str(root / entry["assignment_id"])
        coord_inbox.create(Path(entry["inbox"]))
    mailbox = Path(entry["inbox"])
    save_state(mailbox / "assignment.json", {
        "version": 1, "run_id": state["run_id"], "task_id": state.get("task_id"),
        "assignment_id": entry["assignment_id"], "worker": worker,
        "verify_command": state.get("verify_command"), "cwd": entry.get("cwd"),
    })
    return mailbox


def inventory(_args: argparse.Namespace) -> dict[str, Any]:
    if not resolve_adapter("herdr"):
        return {"available": False, "reason": "Set COORDINATOR_HERDR_HELPER to the installed Herdr worker helper", "kinds": []}
    result = run(adapter_command("herdr", "inventory"), allow_failure=True)
    if result.returncode:
        return {"available": False, "reason": result.stdout or result.stderr, "kinds": []}
    try:
        data = decode_json(result, "Herdr worker inventory")
        if not isinstance(data, dict) or not isinstance(data.get("kinds"), list):
            raise LifecycleError("invalid inventory shape")
        return data
    except LifecycleError as error:
        return {"available": False, "reason": str(error), "kinds": []}


def start_worker(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    if args.name in state["workers"]:
        raise LifecycleError(f"worker already recorded: {args.name}")
    operation_id = uuid.uuid4().hex
    receipt_path = state_path.parent / "operations" / state["run_id"] / (operation_id + ".json")
    intent = dict(name=args.name, kind=args.kind, model=args.model,
                  provider=getattr(args, "provider", None), effort=getattr(args, "effort", None),
                  cwd=str(Path(args.cwd).resolve()), workspace_id=args.workspace,
                  operation_id=operation_id, receipt_file=str(receipt_path),
                  status="start_intended", children=[])
    state["workers"][args.name] = intent
    record(state, "worker_start_intended", worker=args.name, operation_id=operation_id)
    save_state(state_path, state)
    command = adapter_command("herdr", "start", "--name", args.name, "--kind", args.kind,
                              "--model", args.model, "--workspace", args.workspace, "--cwd", args.cwd,
                              "--receipt-file", str(receipt_path), "--operation-id", operation_id)
    for field in ("provider", "effort", "label"):
        value = getattr(args, field, None)
        if value:
            command += ["--" + field, value]
    try:
        response = run(command, allow_failure=True, timeout_seconds=150)
        receipt = decode_json(response, "Herdr worker start")
        if not isinstance(receipt, dict):
            raise LifecycleError("invalid launch receipt")
    except (LifecycleError, OSError) as error:
        intent["status"] = "start_unknown"
        record(state, "worker_start_unknown", worker=args.name, error=str(error))
        save_state(state_path, state)
        raise
    state["workers"][args.name] = {**intent, **receipt, "name": args.name}
    record(state, "worker_started" if response.returncode == 0 else "worker_start_failed",
           worker=args.name, receipt=receipt)
    save_state(state_path, state)
    if response.returncode or receipt.get("status") != "ready":
        raise LifecycleError(f"worker start failed; inspect preserved resources: {receipt}")
    return state["workers"][args.name]


def recover_worker(args):
    """Reconcile an interrupted launch from its receipt; never repeat a mutation."""
    path = Path(args.state).resolve()
    state = load_state(path)
    worker = state["workers"].get(args.worker)
    if not worker:
        raise LifecycleError("unknown worker")
    receipt_path = worker.get("receipt_file")
    if receipt_path and Path(receipt_path).is_file():
        receipt = json.loads(Path(receipt_path).read_text())
        if not isinstance(receipt, dict) or receipt.get("operation_id") != worker.get("operation_id"):
            raise LifecycleError("launch receipt belongs to another operation")
        for field in ("name", "kind", "model", "provider", "effort", "cwd", "workspace_id"):
            if receipt.get(field) != worker.get(field):
                raise LifecycleError(f"launch receipt {field} does not match intent")
        # Never erase dispatch state with an older launch receipt.
        for field in ("pane_id", "tab_id", "owned_tab"):
            if field in receipt:
                worker[field] = receipt[field]
    pane = worker.get("pane_id")
    if not pane:
        record(state, "recovery_unresolved", worker=args.worker,
               reason="No durable pane ID; inspect workspace before any new launch")
        save_state(path, state)
        raise LifecycleError("launch outcome unknown; inspect recorded workspace; no relaunch attempted")
    observed = decode_json(run(adapter_command("herdr", "inspect", pane)), "Herdr recovery")["result"]["agent"]
    if (observed.get("pane_id") != pane or observed.get("tab_id") != worker.get("tab_id")
            or observed.get("workspace_id") != worker.get("workspace_id")
            or observed.get("agent") != worker.get("kind")):
        raise LifecycleError("live worker does not match the launch receipt; inspect before recovery")
    if worker.get("delivery_retired"):
        raise LifecycleError("assignment delivery is retired; create a new assignment")
    if worker.get("dispatch_status"):
        worker["status"] = "admission_unknown" if worker["dispatch_status"] == "intended" else worker["status"]
    else:
        worker["status"] = "ready" if observed.get("agent_status") in {"idle", "done"} else "start_unknown"
    if worker["status"] == "ready":
        previous_error = {key: worker.pop(key) for key in ("error", "error_detail", "next_action") if key in worker}
        if previous_error:
            record(state, "worker_error_resolved", worker=args.worker, previous=previous_error)
    record(state, "worker_recovered", worker=args.worker, observed=observed)
    save_state(path, state)
    return worker


def resolve_dispatch(args):
    path = Path(args.state).resolve()
    state = load_state(path)
    worker = state["workers"].get(args.worker)
    if not worker or not worker.get("dispatch_status"):
        raise LifecycleError("no recorded dispatch to resolve")
    if not args.evidence.strip():
        raise LifecycleError("resolution requires inspection evidence")
    record(state, "dispatch_resolved", worker=args.worker, outcome=args.outcome,
           evidence=args.evidence, operation_id=worker.get("dispatch_id"))
    if args.outcome == "not-delivered":
        worker.pop("dispatch_status", None)
        worker["status"] = "ready"
    else:
        worker["dispatch_status"] = "delivered"
        worker["status"] = "dispatched"
    save_state(path, state)
    return worker


def prepare_delivery(state, worker, brief):
    """Pin a new assignment's publisher inside its writable workspace."""
    entry = state["workers"][worker]
    if entry.get("delivery_inbox"):
        return Path(entry["delivery_inbox"]) / "brief.md"
    root = Path(entry["cwd"]).resolve()
    bundle = root / ".coord" / state["run_id"] / entry["assignment_id"]
    canonical = Path(entry["inbox"]).resolve()
    if canonical.is_relative_to(root):
        raise LifecycleError("durable inbox must be outside the worker workspace; prepare with a durable --inbox")
    coord_inbox.create(bundle)
    for name in ("coord_lifecycle.py", "coord_state.py", "coord_inbox.py"):
        shutil.copyfile(Path(__file__).with_name(name), bundle / name)
    shutil.copyfile(canonical / "assignment.json", bundle / "assignment.json")
    shutil.copyfile(brief, bundle / "brief.md")
    entry.update(delivery_inbox=str(bundle), reporter=str(bundle / "coord_lifecycle.py"), protocol_version=1)
    return bundle / "brief.md"


def harvest_worker(entry):
    if entry.get("delivery_inbox") and not entry.get("delivery_retired"):
        coord_inbox.harvest(Path(entry["delivery_inbox"]), Path(entry["inbox"]))


def preserve_files(state, name):
    """Preserve evidence before workspace deletion; this does not accept results."""
    entry = state["workers"][name]
    if "inbox" not in entry:
        return {}
    harvest_worker(entry)
    mailbox = Path(entry["inbox"])
    if mailbox.resolve().is_relative_to(Path(entry["cwd"]).resolve()):
        raise LifecycleError("legacy inbox is inside worker workspace; copy and verify its evidence outside before cleanup")
    artifacts = mailbox / "artifacts"
    artifacts.mkdir(exist_ok=True)
    manifest = dict(entry.get("preserved_artifacts", {}))
    for status in ("unread", "read", "processed"):
        for message in (mailbox / status).glob("*.json"):
            if message.is_symlink() or message.stat().st_size > coord_inbox.MAX_MESSAGE_BYTES:
                raise LifecycleError("invalid stored report; resolve before cleanup")
            payload = json.loads(message.read_text())
            if not isinstance(payload, dict) or payload.get("kind") != "complete":
                continue
            if not isinstance(payload.get("artifact"), str) or not payload["artifact"]:
                raise LifecycleError("completion has no artifact path; resolve before cleanup")
            source = Path(payload["artifact"]).resolve()
            if not source.is_relative_to(Path(entry["cwd"]).resolve()):
                raise LifecycleError("reported artifact is outside assigned workspace")
            digest = payload.get("sha256")
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise LifecycleError("invalid artifact hash")
            target = artifacts / digest
            if not target.exists():
                fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=artifacts)
                try:
                    with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
                        size = 0
                        hasher = hashlib.sha256()
                        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                            size += len(chunk)
                            if size > MAX_ARTIFACT_BYTES:
                                raise LifecycleError("artifact exceeds size limit")
                            hasher.update(chunk)
                            output.write(chunk)
                        if hasher.hexdigest() != digest:
                            raise LifecycleError("artifact changed since report; resolve before cleanup")
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temporary, target)
                    coord_inbox.sync_directory(artifacts)
                finally:
                    Path(temporary).unlink(missing_ok=True)
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise LifecycleError("preserved artifact hash mismatch")
            manifest[message.stem] = {"original": str(source), "path": str(target), "sha256": digest}
    entry["preserved_artifacts"] = manifest
    entry["delivery_retired"] = True
    record(state, "worker_reports_preserved", worker=name, artifacts=manifest)
    return manifest


def preserve(args):
    path = Path(args.state).resolve()
    state = load_state(path)
    entry = state["workers"][args.worker]
    if entry.get("dispatch_status") in {"intended", "unknown"}:
        raise LifecycleError("resolve dispatch before retiring delivery")
    observed = decode_json(run(adapter_command("herdr", "inspect", entry["pane_id"])), "Herdr inspect")
    if observed["result"]["agent"].get("agent_status") not in {"idle", "done"}:
        raise LifecycleError("worker must be settled before preserving and retiring delivery")
    result = preserve_files(state, args.worker)
    save_state(path, state)
    return {"worker": args.worker, "preserved_artifacts": result, "delivery_retired": True}


def completion_contract(state: dict[str, Any], worker: str) -> str:
    entry = state["workers"][worker]
    sink = entry.get("delivery_inbox", entry["inbox"])
    command = shlex.join([
        sys.executable, entry.get("reporter", str(Path(__file__).resolve())), "report", "--assignment-file",
        str(Path(sink) / "assignment.json"),
    ])
    return (
        f"The return-only file inbox is {sink}; never assign work to it. "
        f"Report through this command: {command}. "
        "Append --kind progress --summary '<update>' for progress, "
        "--kind blocked --summary '<blocker>' when blocked, or "
        "--kind complete --artifact '<artifact-path>' when finished. "
        "If you started children, also pass --children-file '<JSON-file>' containing "
        "objects with their stable name; declare all children. "
        "The helper fills protocol IDs and verification argv, hashes the artifact, "
        "and publishes atomically. It does not run checks or prove acceptance. "
        "Leave the generated assignment descriptor and published reports unchanged."
    )


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    worker = state["workers"].get(args.worker)
    if not worker:
        raise LifecycleError(f"unknown worker: {args.worker}")
    if worker.get("delivery_retired"):
        raise LifecycleError("assignment delivery is retired; create a new assignment")
    if worker.get("dispatch_status"):
        raise LifecycleError("dispatch already recorded; inspect inbox/output and resolve-dispatch before retrying")
    if worker.get("status") in {"start_intended", "start_unknown", "failed"}:
        raise LifecycleError("recover the launch before dispatching")
    brief = Path(args.brief).resolve()
    if not brief.is_file():
        raise LifecycleError(f"brief does not exist: {brief}")
    if not state.get("task_id") or not state.get("verify_command"):
        raise LifecycleError("dispatch requires task ID and coordinator verification argv in prepared state")
    existing_assignment = "inbox" in worker
    register_mailbox(state, args.worker)
    if not existing_assignment or worker.get("delivery_inbox"):
        brief = prepare_delivery(state, args.worker, brief)
    worker["dispatch_id"] = uuid.uuid4().hex
    worker["dispatch_status"] = "intended"
    record(state, "dispatch_intended", worker=args.worker, brief=str(brief), operation_id=worker["dispatch_id"])
    save_state(state_path, state)
    prompt = f"Read {brief} and execute it in full. {completion_contract(state, args.worker)}"
    message_file = Path(worker["inbox"]) / "dispatch.txt"
    message_file.write_text(prompt)
    admitted_result = run(adapter_command(
        "herdr", "--timeout-ms", str(args.timeout_ms), "submit", worker["pane_id"],
        "--message-file", str(message_file)), allow_failure=True,
        timeout_seconds=args.timeout_ms / 1000 * 5 + 30)
    admission = decode_json(admitted_result, "Herdr submission")
    admitted = admitted_result.returncode == 0 and admission.get("status") == "admitted"
    prompted = {"message_file": str(message_file)}
    worker["dispatch_status"] = "admitted" if admitted else "unknown"
    worker["status"] = "working" if admitted else "admission_unknown"
    worker["brief"] = str(brief)
    record(state, "worker_dispatched", worker=args.worker, admitted=admitted, prompt=prompted, admission=admission)
    save_state(state_path, state)
    if not admitted:
        raise LifecycleError(f"worker admission unknown: {args.worker}: {admission}")
    return {"worker": args.worker, "admitted": True, "return_sink": state["return_sink"]}


def report(args: argparse.Namespace) -> dict[str, Any]:
    descriptor = Path(args.assignment_file).expanduser().resolve()
    assignment = json.loads(descriptor.read_text())
    if not isinstance(assignment, dict) or assignment.get("version") != 1:
        raise LifecycleError("unsupported assignment descriptor")
    identities = ("run_id", "task_id", "assignment_id", "worker")
    if any(not isinstance(assignment.get(key), str) or not assignment[key] for key in identities):
        raise LifecycleError("assignment descriptor is missing protocol identities")
    payload = {key: assignment[key] for key in identities}
    payload["kind"] = args.kind
    if args.summary:
        payload["summary"] = args.summary
    if args.kind in {"progress", "blocked"}:
        if not args.summary or not args.summary.strip():
            raise LifecycleError("progress and blocked reports require a summary")
        if args.artifact or args.children_file:
            raise LifecycleError("artifact and children-file apply only to complete reports")
    else:
        if not args.artifact or not isinstance(assignment.get("cwd"), str):
            raise LifecycleError("completion requires an artifact and an assigned working directory")
        root = Path(assignment["cwd"]).resolve()
        artifact = Path(args.artifact).expanduser()
        artifact = (root / artifact).resolve() if not artifact.is_absolute() else artifact.resolve()
        if not artifact.is_relative_to(root) or not artifact.is_file():
            raise LifecycleError("artifact must be a file inside the assigned working directory")
        if artifact.stat().st_size > MAX_ARTIFACT_BYTES:
            raise LifecycleError("artifact exceeds the size limit")
        command = assignment.get("verify_command")
        if not isinstance(command, list) or not command or not all(isinstance(p, str) and p for p in command):
            raise LifecycleError("assignment is missing coordinator verification argv")
        children = json.loads(Path(args.children_file).read_text()) if args.children_file else []
        if not isinstance(children, list) or any(
            not isinstance(child, dict) or not isinstance(child.get("name"), str) or not child["name"].strip()
            for child in children
        ):
            raise LifecycleError("children-file must contain objects with stable non-empty names")
        if len({child["name"] for child in children}) != len(children):
            raise LifecycleError("child names must be unique")
        hasher = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        payload.update(artifact=str(artifact), sha256=hasher.hexdigest(), verify_command=command, children=children)
    message_id = coord_inbox.publish(descriptor.parent, payload)
    return {"message_id": message_id, "status": "published", "kind": args.kind,
            "assignment_id": payload["assignment_id"]}


def send(args: argparse.Namespace) -> dict[str, Any]:
    with Path(args.message_file).open("rb") as stream:
        data = stream.read(coord_inbox.MAX_MESSAGE_BYTES + 1)
    if len(data) > coord_inbox.MAX_MESSAGE_BYTES:
        raise LifecycleError("message exceeds size limit")
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise LifecycleError(f"invalid message JSON: {error}") from error
    message_id = coord_inbox.publish(Path(args.inbox).expanduser().resolve(), payload)
    return {"message_id": message_id, "status": "published"}


def receive(args: argparse.Namespace) -> list[dict[str, Any]]:
    state = load_state(Path(args.state).resolve())
    require_file_sink(state)
    if args.wait < 0:
        raise LifecycleError("wait must be non-negative")
    deadline = time.monotonic() + args.wait
    while True:
        state = load_state(Path(args.state).resolve())
        messages = []
        for worker, entry in state["workers"].items():
            if "inbox" not in entry:
                continue
            harvest_worker(entry)
            for report in coord_inbox.read(Path(entry["inbox"]), unread_only=getattr(args, "unread_only", False)):
                item = {
                    "envelope": {"from": f"{worker}-result", "worker": worker,
                                 "assignment_id": entry["assignment_id"],
                                 "message_id": report["message_id"], "status": report["status"]},
                    "completion": report["payload"],
                }
                if "error" in report:
                    item["error"] = report["error"]
                messages.append(item)
        if messages or time.monotonic() >= deadline:
            return messages  # Reading never consumes or acknowledges a report.
        time.sleep(min(1.0, max(0, deadline - time.monotonic())))


def mark_read(args: argparse.Namespace) -> dict[str, Any]:
    state = load_state(Path(args.state).resolve())
    require_file_sink(state)
    worker = state["workers"].get(args.worker, {})
    if "inbox" not in worker:
        raise LifecycleError(f"worker has no registered inbox: {args.worker}")
    coord_inbox.transition(Path(worker["inbox"]), args.message_id, "read")
    return {"message_id": args.message_id, "status": "read_or_processed"}


def watch(args: argparse.Namespace) -> dict[str, Any]:
    """Return unread message identities without changing their read state."""
    if not 0 <= args.wait <= 60 or (getattr(args, "quiet_timeout", False) and args.wait == 0):
        raise LifecycleError("watch wait must be between 0 and 60 seconds, and positive for quiet timeouts")
    messages = receive(argparse.Namespace(state=args.state, wait=args.wait, unread_only=True))
    return {"event": "inbox_unread" if messages else "timeout", "state": str(Path(args.state).resolve()),
            "messages": [item["envelope"] for item in messages]}


def acknowledge(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    require_file_sink(state)
    worker = state["workers"].get(args.worker, {})
    if "inbox" not in worker:
        raise LifecycleError(f"worker has no registered inbox: {args.worker}")
    record(state, "message_handled", worker=args.worker, message_id=args.message_id,
           outcome=args.outcome)
    save_state(state_path, state)  # Persist the decision before archiving the report.
    coord_inbox.acknowledge(Path(worker["inbox"]), args.message_id)
    return {"message_id": args.message_id, "status": "processed"}


def verify(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    artifact = Path(args.artifact).resolve()
    if not artifact.is_file():
        raise LifecycleError(f"artifact does not exist: {artifact}")
    allowed_root = getattr(args, "root", None)
    if allowed_root:
        root = Path(allowed_root).resolve()
        if not artifact.is_relative_to(root):
            raise LifecycleError(f"artifact is outside the approved root: {root}")
    size = artifact.stat().st_size
    if size > MAX_ARTIFACT_BYTES:
        raise LifecycleError(f"artifact exceeds the {MAX_ARTIFACT_BYTES}-byte size limit")
    hasher = hashlib.sha256()
    with artifact.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    matched = digest == args.sha256.lower()
    evidence = {"artifact": str(artifact), "claimed_sha256": args.sha256.lower(), "actual_sha256": digest, "matched": matched}
    record(state, "artifact_verified", **evidence)
    save_state(state_path, state)
    if not matched:
        raise LifecycleError(f"digest mismatch: claimed {args.sha256.lower()}, actual {digest}")
    return evidence


def reconcile(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    results: dict[str, Any] = {}
    failures: list[str] = []
    for name, worker in state["workers"].items():
        if (not worker.get("pane_id") or worker.get("status") in {"failed", "start_intended", "start_unknown"}
                or worker.get("dispatch_status") in {"intended", "unknown"}):
            failures.append(f"{name}: recover unresolved operation before reconciliation")
            results[name] = {"status": "recovery_required"}
            continue
        observed_result = run(adapter_command("herdr", "inspect", worker["pane_id"]), allow_failure=True)
        if observed_result.returncode:
            observed: Any = {"unknown": True, "detail": observed_result.stderr.strip()}
            status = "unknown"
        else:
            observed = decode_json(observed_result, "Herdr agent get")
            status = observed["result"]["agent"].get("agent_status", "unknown")
        disposition = args.disposition
        if disposition == "close-owned":
            if not worker.get("owned_tab"):
                failures.append(f"{name}: tab is not owned")
            elif status not in {"idle", "done", "missing"}:
                failures.append(f"{name}: not settled ({status})")
            else:
                preserve_files(state, name)
                save_state(state_path, state)
                run(adapter_command("herdr", "close", worker["pane_id"], "--owned-tab", worker["tab_id"]))
                status = "closed"
        elif disposition == "reusable" and status not in {"idle", "done"}:
            failures.append(f"{name}: not reusable ({status})")
        worker["status"] = status
        worker["disposition"] = disposition
        results[name] = {"status": status, "disposition": disposition, "observed": observed}
    record(state, "workers_reconciled", results=results, failures=failures)
    save_state(state_path, state)
    if failures:
        raise LifecycleError("; ".join(failures))
    return results


def stop(args: argparse.Namespace) -> dict[str, Any]:
    # A file inbox has no daemon to stop. Preserve pending and processed reports.
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    path = require_file_sink(state)
    record(state, "sink_retained", path=str(path))
    save_state(state_path, state)
    return {"path": str(path), "status": "retained"}


def cleanup_failed_run(state_path: Path, worker: str) -> dict[str, Any]:
    """Best-effort cleanup of surfaces owned by a failed high-level run."""
    actions: dict[str, Any] = {}
    state = load_state(state_path)
    owned = state.get("workers", {}).get(worker, {})
    if owned.get("status") in {"failed", "start_intended", "start_unknown", "admission_unknown"} or owned.get("dispatch_status") == "intended":
        return {"preserved": owned, "reason": "Operation unresolved; inspect before cleanup"}
    if owned.get("owned_tab"):
        actions["interrupt"] = run(adapter_command("herdr", "stop", owned["pane_id"]),
                                   allow_failure=True).returncode == 0
        try:
            actions["reconciliation"] = reconcile(argparse.Namespace(
                state=str(state_path), disposition="close-owned",
            ))
        except LifecycleError as error:
            actions["reconciliation_error"] = str(error)
    try:
        actions["sink"] = stop(argparse.Namespace(state=str(state_path)))
    except LifecycleError as error:
        actions["sink_error"] = str(error)
    return actions


def validate_completion(
    item: dict[str, Any], *, state: dict[str, Any], worker: str,
    task_id: str, verify_command: list[str], min_children: int,
) -> dict[str, Any] | None:
    completion = item.get("completion")
    envelope = item.get("envelope", {})
    required = {"run_id", "task_id", "worker", "artifact", "sha256", "verify_command", "children"}
    if not isinstance(completion, dict) or not required.issubset(completion):
        return None
    if envelope.get("from") != f"{worker}-result" or completion.get("worker") != worker:
        return None
    assignment = state.get("workers", {}).get(worker, {}).get("assignment_id")
    if not assignment or completion.get("assignment_id") != assignment or envelope.get("assignment_id") != assignment:
        return None
    if completion.get("kind") != "complete":
        return None
    if completion.get("run_id") != state["run_id"] or completion.get("task_id") != task_id:
        return None
    if completion.get("verify_command") != verify_command:
        return None
    children = completion.get("children")
    if not isinstance(children, list) or len(children) < min_children:
        return None
    if any(not isinstance(child, dict) or not isinstance(child.get("name"), str) for child in children):
        return None
    return item


def reconcile_children(children: list[dict[str, Any]]) -> dict[str, Any]:
    reconciled: dict[str, Any] = {}
    for child in children:
        name = child["name"]
        observed_result = run(adapter_command("herdr", "inspect", name), allow_failure=True)
        if observed_result.returncode:
            raise LifecycleError(f"declared child could not be reconciled: {name}")
        observed = decode_json(observed_result, f"Herdr child {name}")
        try:
            status = observed["result"]["agent"]["agent_status"]
        except (KeyError, TypeError) as error:
            raise LifecycleError(f"declared child returned invalid state: {name}") from error
        if status not in {"idle", "done"}:
            raise LifecycleError(f"declared child is not settled: {name} ({status})")
        reconciled[name] = {"status": status, "observed": observed}
    return reconciled


def run_task(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    state = prepare(argparse.Namespace(
        state=str(state_path), inbox=args.inbox, task_id=args.task_id,
        verify_command=args.verify_command, task_dir=getattr(args, "task_dir", None),
    ))
    state["task_id"] = args.task_id
    state["verify_command"] = args.verify_command
    save_state(state_path, state)
    try:
        start_worker(argparse.Namespace(
            state=str(state_path), name=args.worker, kind=args.kind,
            workspace=args.workspace, cwd=args.cwd, label=args.label,
            model=args.model, provider=args.provider, effort=args.effort,
        ))
        dispatch(argparse.Namespace(
            state=str(state_path), worker=args.worker, brief=args.brief,
            timeout_ms=args.admission_timeout_ms,
        ))
        state = load_state(state_path)
        accepted: dict[str, Any] | None = None
        deadline = time.monotonic() + args.wait
        while accepted is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            messages = receive(argparse.Namespace(state=str(state_path), wait=min(60, remaining)))
            for item in messages:
                accepted = validate_completion(
                    item, state=state, worker=args.worker, task_id=args.task_id,
                    verify_command=args.verify_command, min_children=args.min_children,
                )
                if accepted is not None:
                    break
                acknowledge(argparse.Namespace(
                    state=str(state_path), worker=item["envelope"]["worker"],
                    message_id=item["envelope"]["message_id"],
                    outcome=json.dumps({"status": "not_completion", "report": item}),
                ))
        if accepted is None:
            requirement = f" with at least {args.min_children} declared child(ren)" if args.min_children else ""
            raise LifecycleError(f"no attributable completion from {args.worker}-result{requirement}")
        completion = accepted["completion"]
        verification = verify(argparse.Namespace(
            state=str(state_path), artifact=completion["artifact"], sha256=completion["sha256"], root=args.cwd,
        ))
        check = run(args.verify_command, allow_failure=True, timeout_seconds=args.verify_timeout_seconds)
        if check.returncode:
            raise LifecycleError(f"verification command failed: {check.stderr.strip() or check.stdout.strip() or check.returncode}")
        child_reconciliation = reconcile_children(completion["children"])
        settled = run(adapter_command(
            "herdr", "--timeout-ms", str(args.settle_timeout_ms), "wait", state["workers"][args.worker]["pane_id"], "--until", "idle", "--until", "done",
        ), allow_failure=True)
        if settled.returncode:
            raise LifecycleError(f"worker did not settle after completion: {args.worker}")
        reconciliation = reconcile(argparse.Namespace(state=str(state_path), disposition="close-owned"))
        acknowledge(argparse.Namespace(
            state=str(state_path), worker=args.worker,
            message_id=accepted["envelope"]["message_id"],
            outcome=json.dumps({"status": "verified", "verification": verification,
                                "check": {"argv": args.verify_command, "exit_code": check.returncode,
                                          "stdout": check.stdout, "stderr": check.stderr}}),
        ))
        stopped = stop(argparse.Namespace(state=str(state_path)))
        return {
            "completion": completion,
            "envelope": accepted["envelope"],
            "verification": verification,
            "verification_command": {"argv": args.verify_command, "stdout": check.stdout, "stderr": check.stderr},
            "children": child_reconciliation,
            "reconciliation": reconciliation,
            "sink": stopped,
            "state": str(state_path),
        }
    except Exception as error:
        try:
            cleanup = cleanup_failed_run(state_path, args.worker)
        except Exception as cleanup_error:
            cleanup = {"error": str(cleanup_error)}
        raise LifecycleError(f"{error}; owned cleanup: {json.dumps(cleanup, sort_keys=True)}") from error


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    command = sub.add_parser("doctor", help="check dependency-free core and optional adapters")
    command.set_defaults(handler=doctor)

    command = sub.add_parser("inventory")
    command.set_defaults(handler=inventory)

    command = sub.add_parser("prepare")
    command.add_argument("--state", required=True)
    command.add_argument("--inbox", help="inbox root directory; defaults beside lifecycle state")
    command.add_argument("--task-id", required=True)
    command.add_argument("--verify-command", required=True, help="JSON array argv for coordinator verification")
    command.set_defaults(handler=prepare)

    command = sub.add_parser("start-worker")
    command.add_argument("--state", required=True)
    command.add_argument("--name", required=True)
    command.add_argument("--kind", required=True)
    command.add_argument("--model", required=True)
    command.add_argument("--provider")
    command.add_argument("--effort")
    command.add_argument("--workspace", required=True)
    command.add_argument("--cwd", required=True)
    command.add_argument("--label")
    command.set_defaults(handler=start_worker)

    command = sub.add_parser("dispatch")
    command.add_argument("--state", required=True)
    command.add_argument("--worker", required=True)
    command.add_argument("--brief", required=True)
    command.add_argument("--timeout-ms", type=int, default=5000)
    command.set_defaults(handler=dispatch)

    command = sub.add_parser("receive")
    command.add_argument("--state", required=True)
    command.add_argument("--wait", type=float, default=0, help="seconds to wait; zero reads immediately")
    command.add_argument("--unread-only", action="store_true")
    command.set_defaults(handler=receive)

    command = sub.add_parser("watch", help="wait for unread messages and signal the coordinator host")
    command.add_argument("--state", required=True)
    command.add_argument("--wait", type=float, default=60)
    command.add_argument("--quiet-timeout", action="store_true", help="exit 124 without output on timeout (for the Bash watcher)")
    command.set_defaults(handler=watch)

    command = sub.add_parser("mark-read", help="mark an inspected message read without acknowledging handling")
    command.add_argument("--state", required=True)
    command.add_argument("--worker", required=True)
    command.add_argument("--message-id", required=True)
    command.set_defaults(handler=mark_read)

    command = sub.add_parser("report", help="build and publish a worker report from its assignment")
    command.add_argument("--assignment-file", required=True)
    command.add_argument("--kind", required=True, choices=["progress", "blocked", "complete"])
    command.add_argument("--summary")
    command.add_argument("--artifact")
    command.add_argument("--children-file")
    command.set_defaults(handler=report)

    command = sub.add_parser("send", help="atomically publish a report to the assigned inbox")
    command.add_argument("--inbox", required=True)
    command.add_argument("--message-file", required=True)
    command.set_defaults(handler=send)

    command = sub.add_parser("ack", help="record handling outcome and archive a report")
    command.add_argument("--state", required=True)
    command.add_argument("--worker", required=True)
    command.add_argument("--message-id", required=True)
    command.add_argument("--outcome", required=True)
    command.set_defaults(handler=acknowledge)

    command = sub.add_parser("preserve", help="preserve reports and artifacts before removing a settled worker workspace")
    command.add_argument("--state", required=True)
    command.add_argument("--worker", required=True)
    command.set_defaults(handler=preserve)

    command = sub.add_parser("verify")
    command.add_argument("--state", required=True)
    command.add_argument("--artifact", required=True)
    command.add_argument("--sha256", required=True)
    command.add_argument("--root")
    command.set_defaults(handler=verify)

    command = sub.add_parser("reconcile")
    command.add_argument("--state", required=True)
    command.add_argument("--disposition", choices=["reusable", "close-owned"], required=True)
    command.set_defaults(handler=reconcile)

    command = sub.add_parser("stop")
    command.add_argument("--state", required=True)
    command.set_defaults(handler=stop)

    command = sub.add_parser("run-task")
    command.add_argument("--state", required=True)
    command.add_argument("--inbox", help="inbox root directory; defaults beside lifecycle state")
    command.add_argument("--worker", required=True)
    command.add_argument("--kind", required=True)
    command.add_argument("--model", required=True)
    command.add_argument("--provider")
    command.add_argument("--effort")
    command.add_argument("--workspace", required=True)
    command.add_argument("--cwd", required=True)
    command.add_argument("--brief", required=True)
    command.add_argument("--task-id", required=True)
    command.add_argument("--verify-command", required=True,
                         help="JSON array argv for the coordinator-owned focused check")
    command.add_argument("--label")
    command.add_argument("--wait", type=int, default=300)
    command.add_argument("--admission-timeout-ms", type=int, default=5000)
    command.add_argument("--settle-timeout-ms", type=int, default=30000)
    command.add_argument("--verify-timeout-seconds", type=float, default=300)
    command.add_argument("--min-children", type=int, default=0,
                         help="fail closed unless completion declares at least this many children")
    command.set_defaults(handler=run_task)
    command = sub.add_parser("recover-worker", help="recover recorded resources without relaunch or resubmission")
    command.add_argument("--state", required=True)
    command.add_argument("--worker", required=True)
    command.set_defaults(handler=recover_worker)
    command = sub.add_parser("resolve-dispatch", help="record delivery evidence before permitting a retry")
    command.add_argument("--state", required=True)
    command.add_argument("--worker", required=True)
    command.add_argument("--outcome", choices=["delivered", "not-delivered"], required=True)
    command.add_argument("--evidence", required=True)
    command.set_defaults(handler=resolve_dispatch)
    command = sub.add_parser("bind", help="bind legacy file state to its durable task")
    command.add_argument("--state", required=True)
    command.add_argument("--task-dir", required=True)
    command.set_defaults(handler=bind)
    for name, command in sub.choices.items():
        if name in MUTATION_COMMANDS:
            command.add_argument("--owner", help="current coordinator owner token")
            command.add_argument("--revision", type=lambda value: value if value == "latest" else int(value), help="durable task revision, or explicit latest under the owner lock")
        if name in {"prepare", "run-task"}:
            command.add_argument("--task-dir", help="durable task directory containing state.json")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if getattr(args, "command", None) in {"run-task", "prepare"}:
            try:
                args.verify_command = json.loads(args.verify_command)
            except json.JSONDecodeError as error:
                raise LifecycleError(f"--verify-command must be a JSON array: {error}") from error
            if not isinstance(args.verify_command, list) or not args.verify_command or not all(
                isinstance(part, str) and part for part in args.verify_command
            ):
                raise LifecycleError("--verify-command must be a non-empty JSON array of strings")
        output = invoke(args)
        if args.command == "watch" and args.quiet_timeout and output["event"] == "timeout":
            return 124
    except (LifecycleError, coord_inbox.InboxError, coord_state.StateError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "result": output}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
