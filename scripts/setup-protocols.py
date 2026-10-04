#!/usr/bin/env python3
"""Download optional external skills into a gitignored directory.

Run from anywhere:

    python3 scripts/setup-protocols.py

The coordinator can resolve installed protocols from the catalogs this writes.
Nothing here is imported by the coordinator, and the published skills stay
usable when these downloads are absent. Running the script again updates the
same checkouts.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / ".external"

MATT_URL = "https://github.com/mattpocock/skills.git"
MATT_DIR = DEST / "mattpocock-skills"
MATT_CATALOG = MATT_DIR / "skills"

PLUGINS_URL = "https://github.com/cursor/plugins.git"
PLUGINS_DIR = DEST / "cursor-plugins"
# SKILL.md files live at pstack/skills in cursor/plugins.
PSTACK_SPARSE = "pstack/skills"
PSTACK_CATALOG = PLUGINS_DIR / "pstack" / "skills"

CATALOG_ENV = DEST / "catalog.env"


def run(args):
    print("+", " ".join(args), flush=True)
    subprocess.run(args, check=True)


def ensure_clone(url, dest, sparse):
    git_dir = dest / ".git"
    if git_dir.is_dir():
        run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin"])
        if sparse:
            run(["git", "-C", str(dest), "sparse-checkout", "set", sparse])
        run(["git", "-C", str(dest), "reset", "--hard", "FETCH_HEAD"])
        return
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if sparse:
        cmd.extend(["--filter=blob:none", "--sparse"])
    cmd.extend([url, str(dest)])
    run(cmd)
    if sparse:
        run(["git", "-C", str(dest), "sparse-checkout", "set", sparse])


def write_catalog_env(catalogs):
    value = os.pathsep.join(str(path.resolve()) for path in catalogs)
    CATALOG_ENV.write_text(
        "export COORDINATOR_PROTOCOL_CATALOG=" + value + "\n",
        encoding="utf-8",
    )
    return value


def main():
    if shutil.which("git") is None:
        print("git is required", file=sys.stderr)
        return 1
    ensure_clone(PLUGINS_URL, PLUGINS_DIR, PSTACK_SPARSE)
    ensure_clone(MATT_URL, MATT_DIR, None)
    missing = [path for path in (PSTACK_CATALOG, MATT_CATALOG) if not path.is_dir()]
    if missing:
        print("expected catalog directory was not created:", file=sys.stderr)
        for path in missing:
            print(" ", path, file=sys.stderr)
        return 1
    # pstack first: its skill names are the protocols the coordinator looks up.
    value = write_catalog_env([PSTACK_CATALOG, MATT_CATALOG])
    print()
    print("Downloaded skills are in:")
    print(" ", PSTACK_CATALOG.resolve())
    print(" ", MATT_CATALOG.resolve())
    print("Catalog list written to", CATALOG_ENV.resolve())
    print("COORDINATOR_PROTOCOL_CATALOG=" + value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
