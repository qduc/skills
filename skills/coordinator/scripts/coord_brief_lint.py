#!/usr/bin/env python3
"""Lint a worker brief against the communication contract. Read-only.

The contract in references/communication.md requires every brief to carry a
checkable done criterion, a return path, no-ask_user and no-delegation
clauses, and (for build work) a runnable verification command. Briefs that
drop one of these are how docs-only deliveries and question-asking workers
happen, so this lint rejects them before dispatch instead of trusting the
coordinator to remember. It is a heuristic gate on the contract's clauses,
not a judge of the plan: passing it does not make an assignment correct.

Checks:
  done_criteria         the brief states what done means (`done means`/
                        `done when`/acceptance criteria)
  return_path           a line about reports/returns/results names a file
                        path or native result channel
  ask_user_clause       the brief forbids the worker calling `ask_user`
                        (suppress with --allow-ask-user when authorized)
  delegation_clause     the brief forbids delegation/subagents
                        (suppress with --allow-delegation when authorized)
  verification_command  (kind=build only) an inline-code or fenced span
                        that looks like a runnable command

Usage:
  coord_brief_lint.py lint --brief <path> [--kind build|research|review]
                           [--allow-ask-user] [--allow-delegation]

Prints one JSON finding per line and exits 1 when any check fails; prints
one `{"ok": true, ...}` line and exits 0 otherwise. Writes nothing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

DONE = re.compile(
    r"(?i)\b("
    r"done\s+(?:means|when|if|is|criteri(?:a|on))"
    r"|acceptance\s+criteri(?:a|on)"
    r"|success\s+criteri(?:a|on)"
    r"|definition\s+of\s+done"
    r")\b"
)
RETURN_LINE = re.compile(r"(?i)\b(report|return|result|inbox|response|deliver|channel|harness)\b")
PATH_TOKEN = re.compile(r"(?<![\w.-])(/[\w.@./-]+|[\w.-]+\.(?:md|txt|json))\b")
NATIVE_CHANNEL = re.compile(
    r"(?i)\b(?:native\s+(?:result\s+|return\s+)?channel|native\s+result|through\s+the\s+harness|harness\s+(?:result\s+)?channel)\b"
)
NEGATION = r"(?i)(?:never|do\s+not|don't|must\s+not|no[- \t]+|cannot|can't)"
ASK_USER = re.compile(NEGATION + r"[^.\n]{0,100}?(?:ask[_ -]?user|ask(?:ing)?(?:\s+(?:the\s+)?user|\s+questions))")
DELEGATE = re.compile(NEGATION + r"[^.\n]{0,100}?(?:delegat|sub-?agents?\b)")
COMMAND_SPAN = re.compile(r"```[^`]+```|`[^`\n]+ [^`\n]+`")


def findings_for(text, kind, allow_ask_user, allow_delegation):
    findings = []
    if not DONE.search(text):
        findings.append({"check": "done_criteria", "severity": "error",
                         "message": "no `done means`/`done when` or acceptance criteria"})
    return_lines = [line for line in text.splitlines() if RETURN_LINE.search(line)]
    if not any(PATH_TOKEN.search(line) or NATIVE_CHANNEL.search(line) for line in return_lines):
        findings.append({"check": "return_path", "severity": "error",
                         "message": "no file path or native result channel where the worker returns results/report"})
    if not allow_ask_user and not ASK_USER.search(text):
        findings.append({"check": "ask_user_clause", "severity": "error",
                         "message": "no clause forbidding worker `ask_user` calls "
                                    "(pass --allow-ask-user only when explicitly authorized)"})
    if not allow_delegation and not DELEGATE.search(text):
        findings.append({"check": "delegation_clause", "severity": "error",
                         "message": "no clause forbidding worker delegation "
                                    "(pass --allow-delegation only when explicitly authorized)"})
    if kind == "build" and not COMMAND_SPAN.search(text):
        findings.append({"check": "verification_command", "severity": "error",
                         "message": "no runnable verification command for a build assignment"})
    return findings


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
    lint = sub.add_parser("lint", help="reject a brief that drops a contract clause")
    lint.add_argument("--brief", required=True, help="brief file to check")
    lint.add_argument("--kind", default="build", choices=["build", "research", "review"])
    lint.add_argument("--allow-ask-user", action="store_true",
                      help="brief explicitly authorizes worker ask_user")
    lint.add_argument("--allow-delegation", action="store_true",
                      help="brief explicitly authorizes worker delegation")
    lint.set_defaults(func=cmd_lint)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
