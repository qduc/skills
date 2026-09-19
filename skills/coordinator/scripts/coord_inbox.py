"""Local, single-consumer inbox with concurrent publishers and explicit acknowledgement."""
from __future__ import annotations

import json
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import tempfile
import uuid

MAX_MESSAGE_BYTES = 1_048_576


class InboxError(RuntimeError):
    pass


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ("unread", "read", "processed"):
        (path / name).mkdir(exist_ok=True, mode=0o700)
    sync_directory(path)
    sync_directory(path.parent)


def require_inbox(path: Path) -> None:
    if not all((path / name).is_dir() for name in ("unread", "read", "processed")):
        raise InboxError(f"inbox is missing or incomplete: {path}")


def publish(path: Path, payload: dict) -> str:
    require_inbox(path)
    if not isinstance(payload, dict):
        raise InboxError("message must be a JSON object")
    content = (json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    if len(content) > MAX_MESSAGE_BYTES:
        raise InboxError(f"message exceeds {MAX_MESSAGE_BYTES} bytes")
    message_id = uuid.uuid4().hex
    pending = path / "unread"
    descriptor, temporary = tempfile.mkstemp(prefix=".publishing-", dir=pending)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, pending / f"{message_id}.json")
        sync_directory(pending)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return message_id


def read(path: Path, *, unread_only: bool = False) -> list[dict]:
    require_inbox(path)
    reports = []
    for status in (("unread",) if unread_only else ("unread", "read")):
        for message in sorted((path / status).glob("*.json")):
            if len(message.stem) != 32 or any(c not in "0123456789abcdef" for c in message.stem):
                continue
            item = {"message_id": message.stem, "status": status, "payload": None}
            try:
                if message.is_symlink() or not message.is_file():
                    raise InboxError("message is not a regular file")
                with message.open("rb") as stream:
                    data = stream.read(MAX_MESSAGE_BYTES + 1)
                if len(data) > MAX_MESSAGE_BYTES:
                    raise InboxError("message exceeds size limit")
                item["payload"] = json.loads(data)
                if not isinstance(item["payload"], dict):
                    item["payload"] = None
                    raise InboxError("message must be a JSON object")
            except (OSError, UnicodeError, ValueError, InboxError) as error:
                item["error"] = str(error)
            reports.append(item)
    return reports


@contextmanager
def locked(path: Path):
    with (path / '.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def transition(path: Path, message_id: str, target: str) -> None:
    require_inbox(path)
    with locked(path):
        _transition(path, message_id, target)


def _transition(path: Path, message_id: str, target: str) -> None:
    require_inbox(path)
    if len(message_id) != 32 or any(c not in "0123456789abcdef" for c in message_id):
        raise InboxError("invalid message ID")
    if target not in {"read", "processed"}:
        raise InboxError("invalid target status")
    filename = f"{message_id}.json"
    locations = [path / status / filename for status in ("unread", "read", "processed")]
    existing = [item for item in locations if item.exists() or item.is_symlink()]
    if len(existing) != 1:
        raise InboxError(f"expected one stored message for {message_id}, found {len(existing)}")
    source = existing[0]
    if source.parent.name in {target, "processed"}:
        return  # Retries never move processed reports back to read/unread.
    destination = path / target / filename
    os.replace(source, destination)
    sync_directory(destination.parent)
    sync_directory(source.parent)


def acknowledge(path: Path, message_id: str) -> None:
    transition(path, message_id, "processed")


def harvest(source: Path, destination: Path) -> int:
    """Copy immutable delivery files into durable storage without consuming them."""
    require_inbox(source)
    require_inbox(destination)
    with locked(destination):
        return _harvest(source, destination)


def _harvest(source: Path, destination: Path) -> int:
    copied = 0
    for item in (source / 'unread').glob('*.json'):
        if len(item.stem) != 32 or any(c not in "0123456789abcdef" for c in item.stem):
            raise InboxError(f'invalid delivery message ID: {item.name}')
        if item.is_symlink() or not item.is_file() or item.stat().st_size > MAX_MESSAGE_BYTES:
            raise InboxError('invalid or oversized delivery file')
        if any((destination / status / item.name).exists() for status in ('unread', 'read', 'processed')):
            continue
        data = item.read_bytes()
        if len(data) > MAX_MESSAGE_BYTES:
            raise InboxError('oversized delivery file')
        fd, temporary = tempfile.mkstemp(prefix='.harvest-', dir=destination / 'unread')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, destination / 'unread' / item.name)
                copied += 1
            except FileExistsError:
                pass
            sync_directory(destination / 'unread')
        finally:
            Path(temporary).unlink(missing_ok=True)
    return copied
