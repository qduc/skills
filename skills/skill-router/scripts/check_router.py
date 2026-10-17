#!/usr/bin/env python3
"""Check that skill-router covers every skill and every route has a real exit. Read-only.

usage: check_router.py [SKILLS_DIR]

SKILLS_DIR defaults to the directory that contains skill-router. A skill is any
subdirectory with a SKILL.md. The router "names" a skill when the skill's slug
appears in backticks in skill-router/SKILL.md (for example `debugging`).

Fails (exit 1, problems listed) when:
  - a skill other than skill-router is missing from the router;
  - the router names a slug that is neither a skill nor a built-in exit;
  - the router does not define the built-in exits `none` and `gap`;
  - an eval's expected_exit is not `none`, `gap`, a skill, or `a → b` of skills;
  - the evals have no `none` case (the fast exit must stay tested).
"""

import json
import re
import sys
from pathlib import Path

ROUTER = "skill-router"
BUILTIN_EXITS = {"none", "gap"}
SLUG = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")
CHAIN = re.compile(r"\s*(?:→|->)\s*")


def skills_in(skills_dir: Path) -> set[str]:
    return {p.parent.name for p in skills_dir.glob("*/SKILL.md")}


def named_in(router_md: Path) -> set[str]:
    return set(SLUG.findall(router_md.read_text(encoding="utf-8")))


def check_evals(evals_path: Path, existing: set[str]) -> list[str]:
    if not evals_path.is_file():
        return [f"evals not found: {evals_path}"]
    problems, exits = [], []
    for case in json.loads(evals_path.read_text(encoding="utf-8")).get("evals", []):
        exit_ = case.get("expected_exit", "")
        exits.append(exit_)
        parts = CHAIN.split(exit_.strip())
        if exit_ in BUILTIN_EXITS:
            continue
        if len(parts) > 2 or not all(p in existing for p in parts):
            problems.append(f"eval {case.get('id')}: invalid expected_exit: {exit_!r}")
    if "none" not in exits:
        problems.append("evals have no `none` case")
    return problems


def check(skills_dir: Path) -> list[str]:
    router_dir = skills_dir / ROUTER
    router_md = router_dir / "SKILL.md"
    if not router_md.is_file():
        return [f"router file not found: {router_md}"]
    existing = skills_in(skills_dir) - {ROUTER}
    named = named_in(router_md) - {ROUTER}
    problems = [f"missing from router: {s}" for s in sorted(existing - named)]
    problems += [f"router names unknown skill: {s}"
                 for s in sorted(named - existing - BUILTIN_EXITS)]
    problems += [f"router does not define exit: {e}" for e in sorted(BUILTIN_EXITS - named)]
    problems += check_evals(router_dir / "evals" / "evals.json", existing)
    return problems


def main(argv: list[str]) -> int:
    default = Path(__file__).resolve().parents[2]
    skills_dir = Path(argv[1]) if len(argv) > 1 else default
    problems = check(skills_dir)
    for p in problems:
        print(p)
    if not problems:
        print(f"ok: router covers {len(skills_in(skills_dir)) - 1} skills; every eval exit is real")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
