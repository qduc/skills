#!/usr/bin/env python3
"""Check commit hashes and test paths cited in a worker report. Read-only.

A commit citation is a 7–40 hex token. It blocks when `git rev-parse --verify`
cannot resolve it to a commit in --cwd. A test citation is a path that looks
like a test file. A path with a directory component must exist at that path
under --cwd. A bare basename resolves when `git ls-files` lists a tracked file
of that name, or, when --cwd is not a git repo, when a filesystem walk finds
one. A dotted unittest ID is checked only when at least one segment starts
with `test`; module candidates end at the last such segment before the class
or method, and leading package segments are dropped longest-first while
matching tracked paths by suffix. Tokens inside a URL are not test paths.
The command writes nothing.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

# 7–40 so a 64-char digest is not treated as a commit. Pure digits qualify.
COMMIT = re.compile(r"(?<![0-9a-fA-F_-])([0-9a-fA-F]{7,40})(?![0-9a-fA-F_-])")
DOTTED_TEST_ID = re.compile(r"(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
UUID = re.compile(r"(?i)(?<![0-9a-f])([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?![0-9a-f])")
FILENAME_TOKEN = re.compile(r"(?<![\w])[\w.-]+\.[A-Za-z0-9]{1,8}(?![\w])")
TEST_PATH = re.compile(
    r"(?<![\w@.-])("
    r"/?(?:[\w.-]+/)*tests?/[\w.-]+(?:/[\w.-]+)*\.[A-Za-z0-9]+"
    r"|/?(?=(?:[A-Za-z_]\w*\.)*test\w*\.)"
    r"(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+"
    r"|/?(?:[\w.-]+/)*test_[\w.-]*\.[A-Za-z0-9]+"
    r"|/?(?:[\w.-]+/)*[\w.-]+_test\.[A-Za-z0-9]+"
    r"|/?(?:[\w.-]+/)*[\w.-]+\.test\.[A-Za-z0-9]+"
    r")"
)


def commits(text):
    uuid_spans = [match.span() for match in UUID.finditer(text)]
    filename_spans = [match.span() for match in FILENAME_TOKEN.finditer(text)]
    found = []
    for match in COMMIT.finditer(text):
        start, end = match.span(1)
        citation = (re.search(r"(?i)\bcommit\s*$", text[max(0, start - 16):start])
                    or text[start - 1:start] == "`" and text[end:end + 1] == "`")
        inside_uuid = any(start < uuid_end and end > uuid_start for uuid_start, uuid_end in uuid_spans)
        inside_filename = any(start >= file_start and end <= file_end
                              for file_start, file_end in filename_spans)
        if (inside_uuid or inside_filename) and not citation:
            continue
        found.append(match.group(1))
    return list(dict.fromkeys(found))


def test_paths(text):
    found = []
    for match in TEST_PATH.finditer(text):
        window = text[max(0, match.start() - 10):match.start() + 3]
        chunk = text[:match.start()].split()[-1] if text[:match.start()].split() else ""
        if "://" in window or "://" in chunk:
            continue
        found.append(match.group(1).split("::", 1)[0])
    return list(dict.fromkeys(found))


def resolves_commit(cwd, token):
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--verify", "--quiet", f"{token}^{{commit}}"],
            capture_output=True, text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def git_tracked_basenames(cwd):
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "ls-files", "-z"],
            capture_output=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    names = set()
    for raw in result.stdout.split(b"\0"):
        if raw:
            path = raw.decode("utf-8", "surrogateescape")
            names.add(Path(path).name)
            names.add(path)
    return names


def walked_basenames(cwd):
    names = set()
    for path in cwd.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            names.add(path.name)
            names.add(path.relative_to(cwd).as_posix())
    return names


def resolves_test(cwd, cited, basenames=None):
    candidate = Path(cited)
    if candidate.is_absolute():
        try:
            candidate.resolve().relative_to(cwd.resolve())
        except ValueError:
            return False
        return candidate.is_file()
    if "/" not in cited and "\\" not in cited:
        if basenames is None:
            basenames = git_tracked_basenames(cwd)
            if basenames is None:
                basenames = walked_basenames(cwd)
        if cited in basenames:
            return True
        dotted = DOTTED_TEST_ID.fullmatch(cited)
        if dotted:
            parts = cited.split(".")
            if not any(part.startswith("test") for part in parts):
                return False
            # Module components end at a test-prefixed segment. Preserve a
            # supplied package path; only unqualified IDs match by basename.
            module_segments = [i for i, part in enumerate(parts[:-1]) if part.startswith("test")]
            module_end = max(module_segments) if module_segments else len(parts) - 3
            module = "/".join(parts[:module_end + 1]) + ".py"
            if module_end == 0:
                if any(Path(path).name == module for path in basenames):
                    return True
            elif any(path == module or path.endswith("/" + module) for path in basenames):
                return True
        return False
    return (cwd / candidate).is_file()


def blockers(cwd, text):
    found = []
    for token in commits(text):
        if not resolves_commit(cwd, token):
            found.append(f"commit {token} does not resolve in {cwd}")
    basenames = git_tracked_basenames(cwd)
    if basenames is None:
        basenames = walked_basenames(cwd)
    for path in test_paths(text):
        if not resolves_test(cwd, path, basenames):
            found.append(f"test path {path} is not a file under {cwd}")
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    cwd = args.cwd.expanduser().resolve()
    if not cwd.is_dir():
        print(f"claimcheck: cwd is not a directory: {cwd}", file=sys.stderr)
        return 2
    try:
        text = args.report.read_text()
    except OSError as error:
        print(f"claimcheck: {error}", file=sys.stderr)
        return 2
    found = blockers(cwd, text)
    if found:
        for item in found:
            print(f"blocker: {item}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
