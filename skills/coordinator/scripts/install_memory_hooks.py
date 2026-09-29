#!/usr/bin/env python3
"""Install only the coordinator memory boundary hooks in a Claude settings file."""
import argparse
import json
from pathlib import Path
import sys

COMMAND = f'{sys.executable} {Path(__file__).resolve().with_name("coord_memory.py")}'
EVENTS = ('PreCompact', 'SessionEnd')


def own(entry):
    if not isinstance(entry, dict):
        return False
    return any(isinstance(hook, dict) and hook.get('command') == COMMAND
               for hook in entry.get('hooks', []))


def install(path):
    data = json.loads(path.read_text()) if path.exists() else {}
    hooks = data.setdefault('hooks', {})
    for event in EVENTS:
        entries = hooks.setdefault(event, [])
        hooks[event] = [entry for entry in entries if not own(entry)]
        hooks[event].append({'hooks': [{'type': 'command', 'command': COMMAND}]})
    path.write_text(json.dumps(data, indent=2) + '\n')


def uninstall(path):
    if not path.exists():
        return
    data = json.loads(path.read_text())
    hooks = data.get('hooks', {})
    for event in EVENTS:
        if event in hooks:
            hooks[event] = [entry for entry in hooks[event] if not own(entry)]
            if not hooks[event]:
                del hooks[event]
    path.write_text(json.dumps(data, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('install', 'uninstall'))
    parser.add_argument('--settings', required=True)
    args = parser.parse_args()
    path = Path(args.settings)
    (install if args.action == 'install' else uninstall)(path)


if __name__ == '__main__':
    main()
