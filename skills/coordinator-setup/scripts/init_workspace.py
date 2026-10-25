#!/usr/bin/env python3
"""Create a coordinator project workspace from the bundled template.

Copies ../assets/workspace-template to a new or empty directory, fills in
{{PROJECT}}, {{SOURCE_CHECKOUT}} and {{DATE}}, then initializes git and makes
the first commit. It never overwrites an existing non-empty directory.
"""
import argparse
from datetime import date
from pathlib import Path
import shutil
import subprocess
import sys

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "workspace-template"


def create(target, project, source_checkout, today=None, git=True):
    target = Path(target).expanduser().resolve()
    source = Path(source_checkout).expanduser()
    if not source.is_absolute():
        raise ValueError("--source-checkout must be an absolute path")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError(f"{target} exists and is not empty; refusing to overwrite")
    values = {
        "{{PROJECT}}": project,
        "{{SOURCE_CHECKOUT}}": str(source),
        "{{DATE}}": (today or date.today()).isoformat(),
    }
    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True)
    for path in target.rglob("*"):
        if path.is_file():
            text = path.read_text()
            for key, value in values.items():
                text = text.replace(key, value)
            path.write_text(text)
    committed = False
    if git:
        run = lambda *args: subprocess.run(["git", *args], cwd=target, check=True,
                                           capture_output=True, text=True)
        try:
            run("init", "-q")
            run("add", "-A")
            run("commit", "-q", "-m", f"Initialize {project} coordination workspace")
            committed = True
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(error, "stderr", None) or str(error)
            print(f"warning: git setup incomplete; files were created, finish git manually: "
                  f"{detail.strip()}", file=sys.stderr)
    return target, committed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="new workspace directory, e.g. ~/coord/<project>")
    parser.add_argument("--project", required=True, help="project name used in the notes")
    parser.add_argument("--source-checkout", required=True,
                        help="absolute path of the project's source checkout")
    parser.add_argument("--no-git", action="store_true", help="skip git init and commit")
    args = parser.parse_args(argv)
    try:
        target, committed = create(args.target, args.project, args.source_checkout,
                                   git=not args.no_git)
    except ValueError as error:
        parser.error(str(error))
    print(f"created {target}" + (" (git initialized, first commit made)" if committed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
