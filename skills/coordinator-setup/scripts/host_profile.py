#!/usr/bin/env python3
"""Host discovery, external profile validation, and driver-route probes.

`discover` and `show` are read-only. `probe-worker` and `probe-judge` run a
command once against a throwaway git repository. `set-driver` probes every
proposed route and saves only those that worked into `adapters.driver`,
keeping the rest of an existing profile unchanged.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

PROBE_FILE = "coord-probe.txt"
PROBE_TEXT = "probe ok"
WORKER_PROMPT = (f"Create a file named {PROBE_FILE} in the current directory containing exactly the text: "
                 f"{PROBE_TEXT}\nDo not change anything else, and do not ask questions.")
JUDGE_PROMPT = 'Reply with only this JSON object and nothing else: {"probe": "ok"}'


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


def argv_list(value, need_prompt):
    if not isinstance(value, list) or not value or not all(isinstance(p, str) and p.strip() for p in value):
        raise ValueError("argv must be a non-empty list of strings")
    if need_prompt and "{prompt}" not in value:
        raise ValueError('worker argv needs a "{prompt}" element where the prompt goes')
    return value


def substitute(argv, prompt):
    return [prompt if part == "{prompt}" else part for part in argv], (None if "{prompt}" in argv else prompt)


def probe_worker(argv, timeout=300):
    """Run one real attempt in a throwaway repo: the probe file must appear with the exact text."""
    argv_list(argv, need_prompt=True)
    with tempfile.TemporaryDirectory(prefix="coord-probe-") as directory:
        repo = Path(directory)
        (repo / "README.md").write_text("Probe repository for the coordinator setup.\n")
        for args in (["init", "-q"], ["add", "-A"],
                     ["-c", "user.name=probe", "-c", "user.email=probe@localhost", "commit", "-q", "-m", "probe"]):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
        command, stdin = substitute(argv, WORKER_PROMPT)
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=repo, input=stdin, capture_output=True, text=True, timeout=timeout,
                                    stdin=None if stdin is not None else subprocess.DEVNULL)
            code, output = result.returncode, (result.stderr or result.stdout)[-400:]
        except subprocess.TimeoutExpired:
            code, output = None, f"timed out after {timeout}s; the command must finish without interaction"
        except OSError as error:
            code, output = None, str(error)
        seconds = round(time.monotonic() - started, 1)
        written = repo / PROBE_FILE
        ok = written.is_file() and written.read_text().strip() == PROBE_TEXT
        reason = None if ok else ("the probe file was not created with the exact text" if code is not None else output)
        return {"ok": ok, "seconds": seconds, "exit_code": code, "reason": reason,
                "output_tail": None if ok else output}


def first_object(text):
    """The JSON object in the output, unwrapping a CLI envelope whose `result` holds the answer text."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text or ""):
        try:
            value, _ = decoder.raw_decode(text, match.start())
        except ValueError:
            continue
        if isinstance(value, dict) and isinstance(value.get("result"), str):
            return first_object(value["result"])
        if isinstance(value, dict):
            return value
    return None


def probe_judge(argv, timeout=300):
    argv_list(argv, need_prompt=False)
    command, stdin = substitute(argv, JUDGE_PROMPT)
    started = time.monotonic()
    try:
        result = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=timeout,
                                stdin=None if stdin is not None else subprocess.DEVNULL)
        value, output = first_object(result.stdout), (result.stderr or result.stdout)[-400:]
    except (subprocess.TimeoutExpired, OSError) as error:
        value, output = None, str(error)
    ok = value == {"probe": "ok"}
    return {"ok": ok, "seconds": round(time.monotonic() - started, 1),
            "reason": None if ok else "the command did not print the requested JSON object",
            "output_tail": None if ok else output}


def set_driver(workers, judge, timeout=300):
    """Probe each proposed route and save only verified ones; other profile content is preserved."""
    if not isinstance(workers, list) or not workers:
        raise ValueError("propose at least one worker route")
    path = profile_path()
    profile = validate(json.loads(path.read_text())) if path.is_file() else discover()
    results, verified = [], []
    for worker in workers:
        if not isinstance(worker, dict) or set(worker) != {"route", "argv"} or not isinstance(worker["route"], dict):
            raise ValueError("each worker needs route and argv")
        route = worker["route"]
        if not all(isinstance(route.get(k), str) and route[k].strip() for k in ("harness", "model")):
            raise ValueError("each route needs explicit harness and model")
        probe = probe_worker(worker["argv"], timeout)
        results.append({"route": route, **probe})
        if probe["ok"]:
            verified.append(worker)
    judge_result = probe_judge(judge, timeout) if judge else None
    if not verified:
        return {"saved": False, "profile_path": str(path), "workers": results, "judge": judge_result,
                "reason": "no worker route passed its probe; nothing was saved"}
    today = datetime.now(timezone.utc).date().isoformat()
    entry = {"status": "verified", "verified_at": today, "workers": verified,
             "evidence": f"set-driver probes on {today}: each saved worker created the probe file in a throwaway repo"}
    if judge_result and judge_result["ok"]:
        entry["judge"] = judge
    profile["adapters"]["driver"] = entry
    validate(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(profile, indent=2) + "\n")
    temporary.replace(path)
    return {"saved": True, "profile_path": str(path), "workers": results, "judge": judge_result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover")
    sub.add_parser("show")
    for name in ("probe-worker", "probe-judge"):
        command = sub.add_parser(name)
        command.add_argument("--argv", required=True, help="JSON argv list")
        command.add_argument("--timeout", type=float, default=300)
    command = sub.add_parser("set-driver")
    command.add_argument("--workers-file", required=True, help='JSON [{"route": {...}, "argv": [...]}]')
    command.add_argument("--judge", help="JSON argv list for the judge command")
    command.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args(argv)
    try:
        if args.command == "probe-worker":
            result = probe_worker(json.loads(args.argv), args.timeout)
        elif args.command == "probe-judge":
            result = probe_judge(json.loads(args.argv), args.timeout)
        elif args.command == "set-driver":
            judge = json.loads(args.judge) if args.judge else None
            result = set_driver(json.loads(Path(args.workers_file).read_text()), judge, args.timeout)
        else:
            path = profile_path()
            profile = discover() if args.command == "discover" else validate(json.loads(path.read_text()))
            result = {"profile_path": str(path), "profile": profile}
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok", result.get("saved", True)) else 1
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
