#!/usr/bin/env python3
"""Harvest coordination lessons into a Markdown retro digest. Read-only."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import sys

from coord_state import root_path

LESSON_KINDS = {'incident', 'lesson', 'coordination_failure', 'tooling'}
TEXT_FIELDS = ('what', 'text', 'description')
MARKER = re.compile(r'<!--\s*lesson:\s*([a-z0-9][a-z0-9-]*)\s+promoted\s+(\d{4}-\d{2}-\d{2})\s*-->')
STOP = set('''about after again also always because before being both could does doing done each even every from
have into just keep like made make more most must never only other over same should since still such than
that their them then there these they this those through under until very were what when where which while
with without would your worker workers task tasks'''.split())


def day(value):
    if not isinstance(value, str):
        return None
    match = re.search(r'\d{4}-\d{2}-\d{2}', value)
    return date.fromisoformat(match.group()) if match else None


def lesson(source, document, where, text, **fields):
    # One document (task record, log, handoff, memory file) counts as one source.
    return {'source': source, 'document': str(document), 'where': where, 'text': ' '.join(text.split()),
            'key': fields.get('key'), 'scope': fields.get('scope'), 'rule': fields.get('rule'),
            'cost': fields.get('cost'), 'outcome': fields.get('outcome'), 'date': fields.get('date')}


def task_lessons(root, warnings):
    found = []
    for path in sorted((root / 'tasks').glob('*/state.json')):
        try:
            state = json.loads(path.read_text())
            notes = state['details']['notes']
        except (OSError, ValueError, KeyError, TypeError) as error:
            warnings.append(f'{path}: {error}')
            continue
        fallback = day(state.get('updated_at'))
        for index, note in enumerate(notes):
            # String notes and planning kinds (intent, contract, ...) are task facts, not lessons.
            if not isinstance(note, dict) or note.get('kind') not in LESSON_KINDS:
                continue
            text = next((note[k] for k in TEXT_FIELDS if isinstance(note.get(k), str)), '')
            found.append(lesson(f"task {state.get('id', path.parent.name)[:8]} ({state.get('title', '')})",
                                path, f'notes[{index}]', text,
                                key=note.get('key'), scope=note.get('scope'), rule=note.get('rule'),
                                cost=note.get('cost'), outcome=note.get('outcome'),
                                date=day(note.get('at')) or fallback))
    return found


def friction_lessons(root):
    path = root / 'friction-log.md'
    if not path.exists():
        return []
    text = path.read_text()
    status = dict(re.findall(r'^\|\s*(\d+)\s*\|[^|]*\|\s*([^|]*?)\s*\|', text, re.M))
    logged = day(text)
    found = []
    for number, title, body in re.findall(r'^## (\d+)\. ([^\n]+)\n(.*?)(?=^## |\Z)', text, re.M | re.S):
        if status.get(number, '').startswith('withdrawn'):
            continue
        happened = re.search(r'\*\*What happened:\*\*(.*?)(?=\n- \*\*|\Z)', body, re.S)
        suggestion = re.search(r'\*\*Suggestion:\*\*(.*?)(?=\n- \*\*|\Z)', body, re.S)
        found.append(lesson('friction-log', path, f'#{number}',
                            title + ': ' + (happened.group(1) if happened else body[:400].lstrip('- ')),
                            rule=' '.join(suggestion.group(1).split()) if suggestion else None, date=logged))
    return found


def handoff_lessons(root):
    found = []
    for path in sorted(root.glob('handoff-*.md')):
        lines = path.read_text().splitlines()
        inside, start, bullet = False, 0, []
        def flush():
            if bullet:
                found.append(lesson('handoff', path, f'line {start}', ' '.join(bullet), date=day(path.name)))
        for number, line in enumerate(lines, 1):
            if line.startswith('#'):
                flush()
                bullet = []
                inside = 'hard-won' in line.lower() or 'lesson' in line.lower()
            elif inside and line.startswith('- '):
                flush()
                start, bullet = number, [line[2:]]
            elif inside and bullet and line.startswith(' '):
                bullet.append(line.strip())
        flush()
    return found


def memory_lessons(directory, warnings):
    found = []
    for path in sorted(Path(directory).expanduser().glob('*.md')):
        text = path.read_text()
        head = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
        if not head or not re.search(r'^\s*type:\s*feedback\s*$', head.group(1), re.M):
            continue
        description = re.search(r'^description:\s*"?(.*?)"?\s*$', head.group(1), re.M)
        body = head.group(2).strip().split('\n\n')[0]
        found.append(lesson('memory', path, '', (description.group(1) + '. ' if description else '') + body,
                            date=day(next(iter(re.findall(r'modified:.*', head.group(1))), None))))
    if not found and not Path(directory).expanduser().is_dir():
        warnings.append(f'memory directory not found: {directory}')
    return found


def words(text):
    tokens = set()
    for token in re.findall(r'[a-z][a-z0-9_]{3,}', text.lower()):
        if token not in STOP:
            tokens.add(re.sub(r'(ing|ed|es|s)$', '', token) if len(token) > 5 else token)
    return tokens


def group(lessons, threshold):
    """Exact grouping by key; keyless lessons join by word overlap (a hint, not a verdict)."""
    groups = {}
    for item in lessons:
        if item['key']:
            groups.setdefault('key:' + item['key'], []).append(item)
    keyed = list(groups.values())
    loose = [[item] for item in lessons if not item['key']]
    merged = True
    while merged:
        merged = False
        for i in range(len(loose)):
            for j in range(i + 1, len(loose)):
                if any(similar(a, b, threshold) for a in loose[i] for b in loose[j]):
                    loose[i].extend(loose.pop(j))
                    merged = True
                    break
            if merged:
                break
    for cluster in loose:
        # Attach a keyless cluster to a keyed group it resembles so recurrences are counted together.
        home = next((g for g in keyed if any(similar(a, b, threshold) for a in g for b in cluster)), None)
        if home is not None:
            home.extend(cluster)
        else:
            keyed.append(cluster)
    return keyed


def similar(a, b, threshold):
    left, right = words(a['text']), words(b['text'])
    return bool(left and right) and len(left & right) / len(left | right) >= threshold


def promoted_rules(directories):
    rules = []
    for directory in directories:
        for path in sorted(Path(directory).rglob('*.md')):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                for key, promoted in MARKER.findall(line):
                    rules.append({'key': key, 'promoted': date.fromisoformat(promoted), 'locator': f'{path}:{number}'})
    return rules


def digest(lessons, rules, threshold, prune_days, today, warnings):
    groups = group(lessons, threshold)
    def weight(g):
        return (len({i['document'] for i in g}), len(g), any(i['cost'] for i in g))
    groups.sort(key=weight, reverse=True)
    out = [f'# Coordinator retro digest ({today.isoformat()})', '',
           f'{len(lessons)} candidate lessons from {len({i["document"] for i in lessons})} sources. '
           'Groups are ordered by distinct sources, then mentions. Keyless grouping is a word-overlap hint: '
           'confirm recurrence from the citations; one event retold in a task note, handoff, and memory is one occurrence.', '']
    def entry(item):
        text = item['text'][:300] + ('…' if len(item['text']) > 300 else '')
        extras = ''.join(f'; {k}: {item[k]}' for k in ('key', 'scope', 'cost', 'rule', 'outcome') if item[k])
        where = f" {item['where']}" if item['where'] else ''
        return [f'- {text}{extras}', f"  — {item['source']}, {item['date'] or 'undated'}: `{item['document']}`{where}"]
    out.extend(['## Recurring candidates', ''])
    recurring = [g for g in groups if len(g) > 1]
    for number, g in enumerate(recurring, 1):
        keys = sorted({i['key'] for i in g if i['key']})
        scopes = sorted({i['scope'] for i in g if i['scope']})
        dates = sorted(i['date'] for i in g if i['date'])
        span = f'{dates[0]}..{dates[-1]}' if dates else 'undated'
        out.extend([f"### {number}. {', '.join(keys) or 'unkeyed'}: {len(g)} mentions in "
                    f"{len({i['document'] for i in g})} sources, {span}, scope {'/'.join(scopes) or 'unclassified'}", ''])
        for item in g:
            out.extend(entry(item))
        out.append('')
    if not recurring:
        out.extend(['None.', ''])
    out.extend(['## Single mentions', '', 'Entries with a recorded cost come first; promote one only if it caused real damage.', ''])
    for g in groups:
        if len(g) == 1:
            out.extend(entry(g[0]))
    out.append('')
    out.extend(['## Promoted rules', ''])
    if not rules:
        out.extend(['No `lesson:` markers found.', ''])
    for rule in rules:
        cited = sorted(i['date'] for i in lessons if i['key'] == rule['key'] and i['date'] and i['date'] >= rule['promoted'])
        last = cited[-1] if cited else None
        stale = last is None and today - rule['promoted'] > timedelta(days=prune_days)
        out.append(f"- `{rule['key']}` promoted {rule['promoted']} (`{rule['locator']}`): "
                   + (f'{len(cited)} citations since, last {last}' if cited else 'no citations since')
                   + (f' — prune candidate (>{prune_days} days)' if stale else ''))
    out.append('')
    if warnings:
        out.extend(['## Warnings', ''] + [f'- {w}' for w in warnings] + [''])
    return '\n'.join(out)


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument('--root', help='override the coordinator state directory')
    command.add_argument('--memory-dir', action='append', default=[], help='feedback-memory directory (repeatable)')
    command.add_argument('--rules-dir', action='append', default=[],
                         help='directory scanned for lesson markers (default: this skill package; repeatable)')
    command.add_argument('--threshold', type=float, default=0.2, help='word-overlap ratio for keyless grouping')
    command.add_argument('--prune-days', type=int, default=90)
    command.add_argument('--today', type=date.fromisoformat, default=date.today())
    return command


def main():
    args = parser().parse_args()
    root = root_path(args.root)
    warnings = []
    lessons = task_lessons(root, warnings) + friction_lessons(root) + handoff_lessons(root)
    for directory in args.memory_dir:
        lessons += memory_lessons(directory, warnings)
    rules = promoted_rules(args.rules_dir or [Path(__file__).resolve().parents[1]])
    print(digest(lessons, rules, args.threshold, args.prune_days, args.today, warnings))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
