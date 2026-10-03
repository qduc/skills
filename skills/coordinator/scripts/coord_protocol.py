#!/usr/bin/env python3
"""Resolve an installed execution protocol, or fall back to a bounded worker.

The coordinator owns outcome, scope, ownership, dependencies, authority,
acceptance, and integration. A protocol, when one is installed, owns only the
task-specific engineering method and local verification. This helper does not
route worker pools, read or write task state, or accept results. Protocol
output is worker evidence.

Usage:
  coord_protocol.py resolve --protocol NAME [--catalog DIR ...]
  coord_protocol.py admit --protocol NAME --report FILE

Catalogs come from repeated --catalog flags, then from
COORDINATOR_PROTOCOL_CATALOG (path-separator-separated) when that variable is
set. A catalog path that was supplied but does not exist prints
{"error":"missing_catalog","catalog":"..."} and exits 1. Unknown protocol
names and protocols with no installed match print a fallback and exit 0.

Prints one JSON line.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


PROTOCOLS = (
    "bug-fix",
    "architect",
    "refactor",
    "arena",
    "swarm",
    "interrogate",
)

PROTOCOL_OWNS = ["engineering_method", "local_verification"]
COORDINATOR_OWNS = [
    "outcome",
    "scope",
    "ownership",
    "dependencies",
    "authority",
    "acceptance",
    "integration",
]


def error_line(code, **extra):
    return json.dumps({"error": code, **extra})


def unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_simple_yaml(lines):
    """Parse the small frontmatter subset this resolver needs. No PyYAML."""
    data = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if stripped.startswith("- "):
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw in {"", "|", ">", "|-", ">-", "|+", ">+"}:
            items = []
            index += 1
            while index < len(lines):
                nxt = lines[index]
                nxt_stripped = nxt.strip()
                if nxt_stripped.startswith("- "):
                    items.append(unquote(nxt_stripped[2:].strip()))
                    index += 1
                    continue
                if nxt.startswith((" ", "\t")):
                    index += 1
                    continue
                break
            data[key] = items
            continue
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            data[key] = [] if not inner else [unquote(part.strip()) for part in inner.split(",")]
            index += 1
            continue
        data[key] = unquote(raw)
        index += 1
    return data


def parse_frontmatter(text):
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return parse_simple_yaml(lines[1:index])
    return {}


def declared_protocols(frontmatter):
    found = []
    for key in ("execution-protocol", "execution-protocols"):
        if key not in frontmatter:
            continue
        value = frontmatter[key]
        if isinstance(value, list):
            parts = value
        else:
            parts = str(value).split(",")
        for part in parts:
            name = str(part).strip()
            if name:
                found.append(name)
    return found


def skill_name(frontmatter):
    name = frontmatter.get("name")
    if not isinstance(name, str):
        return None
    name = name.strip()
    return name or None


def ownership_fields():
    return {
        "protocol_owns": list(PROTOCOL_OWNS),
        "coordinator_owns": list(COORDINATOR_OWNS),
        "disposition": "worker_evidence",
        "accepted": False,
    }


def resolve_payload(protocol, *, event, reason, skill, skill_name_value, workflow):
    payload = {
        "event": event,
        "protocol": protocol,
        "reason": reason,
        "skill": skill,
        "skill_name": skill_name_value,
        "workflow": workflow,
    }
    payload.update(ownership_fields())
    return payload


def catalog_args(cli_catalogs):
    catalogs = list(cli_catalogs or [])
    raw = os.environ.get("COORDINATOR_PROTOCOL_CATALOG")
    if raw:
        catalogs.extend(part for part in raw.split(os.pathsep) if part)
    return catalogs


def compatible_skills(protocol, catalogs):
    matches = []
    for catalog_index, raw in enumerate(catalogs):
        root = Path(raw).resolve()
        for skill in sorted(root.rglob("SKILL.md")):
            if not skill.is_file():
                continue
            try:
                frontmatter = parse_frontmatter(skill.read_text(encoding="utf-8"))
            except OSError:
                continue
            name = skill_name(frontmatter)
            name_match = name == protocol
            declared = protocol in declared_protocols(frontmatter)
            if not name_match and not declared:
                continue
            relative = skill.resolve().relative_to(root).as_posix()
            matches.append((
                0 if name_match else 1,
                catalog_index,
                len(relative),
                relative,
                str(skill.resolve()),
                name,
            ))
    matches.sort()
    return matches


def cmd_resolve(args):
    catalogs = catalog_args(args.catalog)
    for catalog in catalogs:
        if not Path(catalog).is_dir():
            print(error_line("missing_catalog", catalog=catalog))
            return 1
    if args.protocol not in PROTOCOLS:
        print(json.dumps(resolve_payload(
            args.protocol,
            event="protocol_fallback",
            reason="unknown_protocol",
            skill=None,
            skill_name_value=None,
            workflow="bounded_worker",
        )))
        return 0
    matches = compatible_skills(args.protocol, catalogs)
    if not matches:
        print(json.dumps(resolve_payload(
            args.protocol,
            event="protocol_fallback",
            reason="not_installed",
            skill=None,
            skill_name_value=None,
            workflow="bounded_worker",
        )))
        return 0
    _rank, _index, _length, _relative, skill, name = matches[0]
    print(json.dumps(resolve_payload(
        args.protocol,
        event="protocol_selected",
        reason=None,
        skill=skill,
        skill_name_value=name,
        workflow="execution_protocol",
    )))
    return 0


def cmd_admit(args):
    report = Path(args.report)
    try:
        raw = report.read_bytes()
    except OSError:
        print(error_line("missing_report", report=args.report))
        return 1
    payload = {
        "event": "worker_evidence",
        "protocol": args.protocol,
        "accepted": False,
        "disposition": "worker_evidence",
        "coordinator_owns": list(COORDINATOR_OWNS),
        "protocol_owns": list(PROTOCOL_OWNS),
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "note": "protocol output is evidence for coordinator inspection, not acceptance",
    }
    print(json.dumps(payload))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    resolve = sub.add_parser("resolve", help="select an installed protocol or fall back")
    resolve.add_argument("--protocol", required=True, help="generic protocol name")
    resolve.add_argument(
        "--catalog",
        action="append",
        default=[],
        help="directory of installed skills; repeat to search several",
    )
    resolve.set_defaults(func=cmd_resolve)

    admit = sub.add_parser("admit", help="record protocol output as worker evidence")
    admit.add_argument("--protocol", required=True, help="protocol that produced the report")
    admit.add_argument("--report", required=True, help="report file to hash and admit as evidence")
    admit.set_defaults(func=cmd_admit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
