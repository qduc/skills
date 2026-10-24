# Memory sidecar efficacy eval

**Status: result (2026-10-09, branch `sidecar-v2`).** The sidecar remains disabled
per Operational status (the manual-coordination skill's `references/operational-status.md`); this measures the
judge offline, it does not enable anything.

## Question

Mechanical tests prove containment, not usefulness. Does the judge, run with the
production runner (`term2 -p codex -m gpt-6-luna -r low`), capture the real
decisions and discoveries in a completed session, and how much noise does it
record?

## Method

Session `33e284ec-7148-4795-addc-b1ceaf303f54` (a real debugging task) was
hand-labeled before the run. A temporary coordinator root created a task, bound
the transcript, and ran `coord_memory.judge` with the production runner. The
captured `memory.cold` and `memory.journal` items were compared to the labels.

Labels (5):

1. decision — treat WebSocket close code 1000 as retryable.
2. decision — `retry-tool` must place the latest turn's calls at the end, not by
   user-message position.
3. discovery — turn IDs diverge from the user-message count (`beginTurn()`
   increments on replays; `import()` resets to the highest turn in the ledger).
4. decision — wire the recorded user-message count into the ledger, including
   pruning.
5. state — committed to local `main` as `5184cd74`.

## Result

Judge: `{"status": "applied", "events": 18}`; 4 cold items, 0 journal items.

| metric | value |
| --- | ---: |
| labeled items | 5 |
| captured | 5 (labels 1 and 2 combined into one item) |
| missed | 0 |
| recorded noise | 0 |
| noise rate | 0 of 4 items |

The four items map to: discovery (labels 1+2), discovery (label 3), decision
(label 4), state (label 5). No recorded item lacked a label.

Filter-level noise observed but not ingested: command-wrapper records
(`<command-name>`, `<local-caveat>`), a pasted skill body, and a context-usage
table are retained by the deterministic filter as user text and judged `ignore`.
This is filter-level noise, not judge-level.

## Limits

One session (n=1) and a nondeterministic model run; re-running can shift wording
and the 1+2 merge. This measures the judge, not the watcher under sustained load.
The temporary root lives under the OS temp dir and is not retained.

## Reproduction

The harness below is the exact one used; point `--transcript` at any session and
compare its output to hand labels.

```python
import json, sys, tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0, '<skill-dir>/scripts')
import coord_state
import coord_memory

transcript = sys.argv[1]
root = Path(tempfile.mkdtemp(prefix='efficacy-'))
created = coord_state.create(mock.Mock(title='efficacy', objective='measure capture',
                                       project=str(root), conversation=None, owner='eval'), root)
task_id = created['state']['id']
args = mock.Mock(task=task_id, owner='eval', revision=1, session_id='eval', transcript=str(transcript))
coord_state.bind_session(args, root)
result = coord_memory.judge(root, 'eval')
print('JUDGE_RESULT', json.dumps(result))
mem = coord_state.load(coord_state.task_path(root, task_id))['memory']
for item in mem['cold']:
    print('COLD\t%s\t%s' % (item['category'], item['text']))
for item in mem['journal']:
    print('JOURNAL\t%s\t%s' % (item['category'], item['text']))
```
