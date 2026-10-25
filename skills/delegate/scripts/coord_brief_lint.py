#!/usr/bin/env python3
"""Check a worker brief's mechanical inputs. Read-only.

A brief must be an existing file containing non-whitespace text. Adequacy of
its outcome, scope, authority, return instructions, and verification belongs
to the assigning human/agent: keyword presence cannot establish those facts.
No heading, phrase, path spelling, or Markdown command format is required.

The historical command name, kind choices, authorization flags, and JSON-lines
output are retained for callers. The flags do not enforce worker permissions
or bypass invalid inputs; there are no longer any prose checks to suppress.

Usage:
  coord_brief_lint.py lint --brief <path> [--kind build|research|review]
                           [--allow-ask-user] [--allow-delegation]

Prints one JSON finding per line and exits 1 for invalid input; prints
one `{"ok": true, ...}` line and exits 0 otherwise. Writes nothing.
Passing means only that the mechanical inputs are valid, not that the brief
is sufficient or safe to execute.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

def findings_for(text, kind, allow_ask_user, allow_delegation):
    """Return structural errors, retaining the legacy caller signature.

    Kind and authorization arguments are accepted for compatibility only;
    prose cannot reliably prove completion criteria or runtime permissions.
    """
    if not text.strip():
        return [{"check": "empty_brief", "severity": "error",
                 "message": "brief must contain non-whitespace text"}]
    return []


def cmd_lint(a):
    path = Path(a.brief)
    if not path.is_file():
        print(json.dumps({"error": "missing_brief", "brief": str(path)}))
        return 1
    findings = findings_for(path.read_text(errors="replace"), a.kind,
                            a.allow_ask_user, a.allow_delegation)
    for finding in findings:
        print(json.dumps(finding))
    if findings:
        return 1
    print(json.dumps({"ok": True, "brief": str(path), "kind": a.kind}))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lint = sub.add_parser("lint", help="check that a brief file exists and is nonempty")
    lint.add_argument("--brief", required=True, help="brief file to check")
    lint.add_argument("--kind", default="build", choices=["build", "research", "review"])
    lint.add_argument("--allow-ask-user", action="store_true",
                      help="legacy option; no prose checks or permission enforcement")
    lint.add_argument("--allow-delegation", action="store_true",
                      help="legacy option; no prose checks or permission enforcement")
    lint.set_defaults(func=cmd_lint)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
