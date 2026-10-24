#!/usr/bin/env python3
"""Check that skill-router covers every skill and every route has a real exit. Read-only.

usage: check_router.py [SKILLS_DIR]

SKILLS_DIR defaults to the directory that contains skill-router. A skill is any
subdirectory with a SKILL.md. The router "names" a skill when the skill's slug
appears in backticks in skill-router/SKILL.md (for example `debugging`).

Fails (exit 1, problems listed) when:
  - a skill other than skill-router is missing from the router;
  - the router names a slug that is neither a skill nor a built-in exit;
  - the router does not define the built-in exit `none`;
  - an eval's expected_exit or also_ok entry is not `none`, a skill, or
    `a → b` of skills;
  - the evals have no `none` case (the fast exit must stay tested);
  - a route row or an eval exits to a user-only skill (frontmatter
    `disable-model-invocation: true`): the model cannot load it, so the route
    dead-ends;
  - a route row's exit has no eval expecting it. Untested rows are where
    shadowing hides: a row whose case is answered by an earlier, more general
    row. Whether rows actually shadow each other needs a model reading them in
    order; run_router_evals.py does that.

A route row is a table row under "## Route"; its exit is the first slug in its
second cell (in a chain, the first skill of the chain).
"""

import json
import re
import sys
from pathlib import Path

ROUTER = "skill-router"
BUILTIN_EXITS = {"none"}
SLUG = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")
CHAIN = re.compile(r"\s*(?:→|->)\s*")


def skills_in(skills_dir: Path) -> set[str]:
    return {p.parent.name for p in skills_dir.glob("*/SKILL.md")}


def user_only(skills_dir: Path) -> set[str]:
    """Skills only the user can invoke: the harness never lets the model load them."""
    flag = re.compile(r"^disable-model-invocation:\s*(true|yes|on|1)\s*$", re.M | re.I)
    found = set()
    for md in skills_dir.glob("*/SKILL.md"):
        front = re.match(r"---\n(.*?)\n---", md.read_text(encoding="utf-8"), re.S)
        if front and flag.search(front.group(1)):
            found.add(md.parent.name)
    return found


def named_in(router_md: Path) -> set[str]:
    return set(SLUG.findall(router_md.read_text(encoding="utf-8")))


def route_exits(router_md: Path, every: bool = False) -> list[str]:
    """Primary exit of each table row in the Route section, in order; with every, all skills in the exit cell."""
    text = router_md.read_text(encoding="utf-8")
    section = re.search(r"^## Route\b.*?(?=^## |\Z)", text, re.M | re.S)
    if not section:
        return []
    exits = []
    for line in section.group(0).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.lstrip().startswith("|") or len(cells) < 2:
            continue
        found = SLUG.findall(cells[1])
        for slug in found if every else found[:1]:
            if slug not in exits:
                exits.append(slug)
    return exits


def check_evals(evals_path: Path, existing: set[str], routed: list[str] = (),
                manual: set[str] = frozenset()) -> list[str]:
    if not evals_path.is_file():
        return [f"evals not found: {evals_path}"]
    problems, exits = [], []
    for case in json.loads(evals_path.read_text(encoding="utf-8")).get("evals", []):
        exit_ = case.get("expected_exit", "")
        exits.append(exit_)
        for field, value in [("expected_exit", exit_)] + [("also_ok", a) for a in case.get("also_ok", [])]:
            parts = CHAIN.split(value.strip())
            if value in BUILTIN_EXITS:
                continue
            if len(parts) > 2 or not all(p in existing for p in parts):
                problems.append(f"eval {case.get('id')}: invalid {field}: {value!r}")
            problems += [f"eval {case.get('id')}: {field} is user-only: {p}" for p in parts if p in manual]
    if "none" not in exits:
        problems.append("evals have no `none` case")
    tested = {p for e in exits for p in CHAIN.split(e.strip())}
    problems += [f"route exit has no eval: {e}"
                 for e in routed if e not in tested and e not in BUILTIN_EXITS]
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
    manual = user_only(skills_dir)
    problems += [f"route exits to user-only skill: {s}" for s in route_exits(router_md, every=True) if s in manual]
    problems += check_evals(router_dir / "evals" / "evals.json", existing, route_exits(router_md), manual)
    return problems


def main(argv: list[str]) -> int:
    default = Path(__file__).resolve().parents[2]
    skills_dir = Path(argv[1]) if len(argv) > 1 else default
    problems = check(skills_dir)
    for p in problems:
        print(p)
    if not problems:
        print(f"ok: router covers {len(skills_in(skills_dir)) - 1} skills; every eval exit is real; every route exit is tested")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
