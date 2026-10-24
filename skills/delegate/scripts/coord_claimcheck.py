#!/usr/bin/env python3
"""Check commit hashes and test paths cited in a worker report. Read-only.

A commit citation is a 7–40 hex token. It blocks when `git rev-parse --verify`
cannot resolve it to a commit in --cwd or in any --source repository. When none
of those is a Git repository the citation cannot be checked either way: it is
reported as unverified, not as a blocker. Labeled compact Coordinator task,
assignment, attempt, and owner IDs are data, not commit citations.
A test citation is a path that looks like a test file. A path with a directory component must exist at that path
under --cwd or a --source directory. A bare basename resolves when `git ls-files` lists a tracked file
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
COMMIT = re.compile(r"(?<![\w/\\-])([0-9a-fA-F]{7,40})(?![\w/\\-])")
COORDINATOR_ID_LABEL = re.compile(
    r"(?i)\b(?:task|assignment|attempt|owner)(?:_id|[ -]id)?[\"'`]?\s*(?::|=)?\s*[\"'`]?$"
)
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
        if (len(match.group(1)) == 32
                and COORDINATOR_ID_LABEL.search(text[max(0, start - 64):start])):
            continue
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


def is_git(cwd):
    try:
        result = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--git-dir"], capture_output=True)
    except OSError:
        return False
    return result.returncode == 0


def where(roots):
    return str(roots[0]) if len(roots) == 1 else str(roots[0]) + " or " + ", ".join(map(str, roots[1:]))


def check(cwd, text, sources=()):
    """(blockers, unverified). Sources are read-only repositories the report may cite as provenance."""
    roots = list(dict.fromkeys([cwd, *sources]))
    repositories = [root for root in roots if is_git(root)]
    found, unverified = [], []
    for token in commits(text):
        if not repositories:
            unverified.append(f"commit {token} was not checked: no Git repository among {where(roots)}")
        elif not any(resolves_commit(root, token) for root in repositories):
            found.append(f"commit {token} does not resolve in {where(repositories)}")
    indexes = []
    for root in roots:
        basenames = git_tracked_basenames(root)
        indexes.append((root, walked_basenames(root) if basenames is None else basenames))
    for path in test_paths(text):
        if not any(resolves_test(root, path, basenames) for root, basenames in indexes):
            found.append(f"test path {path} is not a file under {where(roots)}")
    return found, unverified


def blockers(cwd, text, sources=()):
    return check(cwd, text, sources)[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", default=[],
                        help="read-only repository the report may cite; repeatable")
    args = parser.parse_args(argv)
    cwd = args.cwd.expanduser().resolve()
    sources = [source.expanduser().resolve() for source in args.source]
    for directory in (cwd, *sources):
        if not directory.is_dir():
            print(f"claimcheck: not a directory: {directory}", file=sys.stderr)
            return 2
    try:
        text = args.report.read_text()
    except OSError as error:
        print(f"claimcheck: {error}", file=sys.stderr)
        return 2
    found, unverified = check(cwd, text, sources)
    for item in unverified:
        print(f"unverified: {item}")
    if found:
        for item in found:
            print(f"blocker: {item}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
