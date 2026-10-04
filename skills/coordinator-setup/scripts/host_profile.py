#!/usr/bin/env python3
"""Read-only host discovery and external profile validation."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def profile_path():
    explicit = os.environ.get("COORDINATOR_CONFIG_HOME")
    if explicit:
        root = Path(explicit)
        if not root.is_absolute():
            raise ValueError("COORDINATOR_CONFIG_HOME must be absolute")
    elif os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "coordinator"
    else:
        configured = os.environ.get("XDG_CONFIG_HOME", "")
        root = (Path(configured) if Path(configured).is_absolute() else Path.home() / ".config") / "coordinator"
    return root / "host.json"


def discover():
    return {
        "version": 1,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.system(),
        "python": sys.executable,
        "prerequisites": {
            "unix_locking": importlib.util.find_spec("fcntl") is not None,
            "linux_process": platform.system() == "Linux" and Path("/proc/self/stat").is_file(),
        },
        "executables": {name: shutil.which(name) for name in
                        ("git", "herdr", "herdr-worker", "term2", "codex", "claude", "pi", "agy")},
        "adapters": {},
        "catalogs": [],
        "memory_sidecar": "disabled",
    }


def validate(profile):
    if not isinstance(profile, dict) or profile.get("version") != 1:
        raise ValueError("unsupported host profile version")
    if not isinstance(profile.get("adapters"), dict):
        raise ValueError("adapters must be an object")
    catalogs = profile.get("catalogs")
    if not isinstance(catalogs, list) or any(not isinstance(p, str) or not Path(p).is_absolute() for p in catalogs):
        raise ValueError("catalogs must be absolute directory paths")
    if profile.get("memory_sidecar") != "disabled":
        raise ValueError("memory sidecar must remain disabled")
    return profile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("discover", "show"))
    args = parser.parse_args(argv)
    try:
        path = profile_path()
        profile = discover() if args.command == "discover" else validate(json.loads(path.read_text()))
        print(json.dumps({"profile_path": str(path), "profile": profile}, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
