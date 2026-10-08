# T15 measurements (phase 2) and blind prep (phase 3)

Protocol: `skills/research-lab/evals/t15/protocol.md` at freeze `54d86025aa213040592cd082b5b07146451e0dd6`
(frozen checkout `/workspace/lab-runs/t15/skills`, HEAD confirmed at the freeze SHA, `git status` clean).
Measured 2026-10-09 02:49–02:53 ICT. All times ICT (UTC+7).
This file holds no blinding mapping. The mapping is only in `/workspace/lab-runs/t15/key.txt`.

## Transcript availability (read first)

**Neither arm's transcript could be read.** No transcript-reading tool was available to the measuring worker:
`GetDynamicTools` lists only `cursor-github`, `cursor-origin`, `x` (and `user-Finance-xai`, needsAuth). There is no
`cursor` namespace and no ReadTranscript tool. On the box, `/home/box/agent-data/agent-transcripts/` holds one
unrelated transcript, and a filesystem search for either subagent id (`2958ea10-...`, `d0150782-...`) found nothing.

Every count below therefore comes from the **arms' own artifacts and self-reports**, labeled as such. None is an
independent transcript count. The protocol's "observed" web count for the Arm A audit is not available independently.

## Per-arm table

| Measure | Arm A (p1, autonomous) | Arm B (p2, baseline) |
| --- | --- | --- |
| Worker | knowledgeWork `sand-subagent-2958ea10-2768-7253-0783-bb4cac341fe7` | knowledgeWork `sand-subagent-d0150782-be41-b2bf-f787-e866e74607c1` |
| Model | Unknown (not visible; transcripts unreadable) | Unknown (same) |
| Web calls, self-report (final message) | 13 | 20 |
| Web calls, from arm's own log | 13 (ledger: 5 search, 8 fetch) | 22 call lines in `calls.log` (8 WebSearch, 13 WebFetch, 1 curl), plus 2 correction annotations |
| Web calls, transcript | Not available | Not available |
| Other tool calls | Not measurable (transcript unreadable). Artifact lower bound for `lab.py`: 1 init, 15 charges (13 web + 2 cycle), plus claim/source/finding/knowledge adds, 2 stop checks, recall, validate | Not measurable (transcript unreadable) |
| Elapsed, window start 02:44:03 → answer.md mtime | 4.60 min (02:48:38.97) | 3.81 min (02:47:51.42) |
| Elapsed, window start 02:44:03 → final message | ~4.92 min (~02:48:58) | ~4.27 min (~02:48:19) |
| (for reference) per-arm dispatch ~02:44:15 → mtime / final | 4.40 / ~4.72 min | 3.61 / ~4.07 min |
| First own action (artifact) | 02:44:26 (`init`, budget.json `started_at`) | 02:44:18 (calls.log line 1) |
| Last web call (artifact) | 02:46:43 (ledger seq 15) | 02:46:39 (calls.log line 24) |
| Tokens and money | Not measurable with our tools: no per-worker token usage is exposed, and no API is billed per run. | Same |
| Human interventions | 0 (see below) | 0 (see below) |
| Budget: web ≤ 40 | Within (13) | Within (20 self-report; 22 by log; at most 24 even if the 2 annotation lines were separate calls) |
| Budget: ≤ 60 min | Within (~4.9 min) | Within (~4.3 min) |
| Budget: cycles ≤ 8 (A only) | Within (2/8); 0 refusals in ledger | n/a |
| Contamination hits | 0 in artifacts; transcript grep not possible | 0 in artifacts; transcript grep not possible |
| Answer words (`wc -w`) | 1,142 | 1,382 |
| Leak-scan regex hits | 15, all non-revealing | 9, all non-revealing |
| Redactions | 1 (outside the regex; see Blinding) | 0 |

## Arm A process checks

Commands run by the measuring worker. A tar snapshot of `p1/run` was taken first:
`/workspace/lab-runs/t15/p1-run-snapshot-pre-measurement.tar`, sha256 `079cd0d71a16539475c12687631484b359deae0851cd422db55f210e3ec9a1ed`.

```
$ python3 .../autonomy-contract/scripts/lab.py validate /workspace/lab-runs/t15/p1/run
VALID {"claim": 5, "source": 8, "finding": 10}
[exit 0]

$ python3 .../autonomy-contract/scripts/lab.py audit /workspace/lab-runs/t15/p1/run --observed-web 13
{ "run_id": "run-20261009T024426", "limits": {cycles 8, minutes 60.0, reserve_minutes 10.0, stall_cycles 2, web 40},
  "used": {"cycle": 2, "web": 13}, "refusals": 0, "terminated_by_stop_rule": true,
  "stop_reasons": ["no open claims left (5 recorded)"], "last_event_at": "2026-10-09T02:49:39+07:00" }
AUDIT OK
[exit 0]

$ ... audit /workspace/lab-runs/t15/p1/run --observed-web 13 --observed-cycles 2
AUDIT OK
[exit 0]
```

- **Caveat:** `--observed-web 13` is Arm A's self-reported count, not a transcript count. The audit confirms that the
  hash chain and ledger head are intact and that the ledger agrees with the self-report. It cannot show that no web
  call went uncharged. Supporting signal: the 8 recorded sources map one-to-one onto the 8 ledger fetches.
- `validate` appends a `verify/validation` event to `log.jsonl`. That is the 02:49:39 `last_event_at` above, from
  this measurement. Arm A's own validation event is at 02:48:16. The pre-measurement snapshot keeps the original.
- Stop rule: `stop_check` at 02:47:30 → `decision: stop`, reason "no open claims left (5 recorded)", used cycle 2, web 13,
  3.08 min. Final claim statuses: C1–C4 supported, C5 unresolved.
- Knowledge: 5 entries written to `p1-store/knowledge.jsonl` (2 finding, 1 lesson, 2 question).
- `knowledge_recalled` was logged at start (02:44:26). The store was empty, so it surfaced nothing, as expected.
- Challenge pass logged: `adversarial_challenge` on F10, personas P1/P3/P4, mode `sequential_one_context`.
  Experiment step: `experiment_not_feasible` logged for C1.
- `p1/answer.md` is byte-identical to `p1/run/brief.md`.

## Arm B tally comparison

`p2/calls.log`: line 1 is the start time (02:44:18), line 2 is `---`, lines 3–24 are 22 call entries, and lines 25–26
(02:47:51) are annotations saying lines 13 and 23 were actually fetched as arxiv HTML, not the PDF URLs logged.
Read as annotations, the log shows **22** calls. The final message reported **20**. Without a transcript, this
2-call discrepancy cannot be resolved. The count is under the cap under every reading.
Arm B also saved the curl output as `p2/openai-deep-research.html`. It is a JS challenge page, not article content,
and its answer says that page was blocked. It is an extra file in p2, not a read outside allowed paths.

## Contamination

- The protocol method (grep both transcripts) **could not be performed**, because the transcripts are unreadable.
- Substitute (weaker) check: `rg -i "workspace/research|review-scratch|design-notes|evals/t15|bdv-critique|orchestrator-ai"`
  over `p1/`, `p2/`, `p1-store/` → **no hits** (exit 1). Arm A's sources are 8 public https URLs (arxiv, anthropic.com, nature.com).
  Arm B's calls.log lists only public URLs.
- File atimes were checked and are **inconclusive**. The mount is `relatime`. The forbidden files' atimes are either
  before dispatch (design-notes.md 02:43:41 and evals/t15/* 02:43:46, from the conductor's reads) or less than 24 h
  old, so a later read would not have updated them.
- Result: no contamination evidence found, but contamination **cannot be ruled out** without transcripts.

## Human interventions

0 for both arms, per the conductor: no messages were sent to either arm after dispatch. This could not be
cross-checked against transcripts. Recorded deviation (from `dispatch.log`): both arms ran as fresh knowledgeWork
workers instead of the "fresh executor worker" in protocol step 3, because a new executor would inherit the
dispatcher's conversation, which contains the protocol, rubric, and prompts. Dispatch mode: concurrent.

## Blinding (phase 3)

- Coin flip run with the exact protocol command. Output, time, and mapping are recorded only in `/workspace/lab-runs/t15/key.txt`
  (mode 600, outside `blind/`).
- Leak scan: the protocol regex was run on both answers. All 24 hits (15 + 9) are subject-matter words ("token budget",
  "resource budget", "single-agent baseline", "human baseline", quoted "autonomy") or a URL fragment (`s42256` in the
  Nature URL). None was redacted.
- **Redactions: 1 total**, found by manual read outside the regex. That is a **deviation to log**: one revealing token
  in Arm A's answer was replaced with `[redacted]`. The reason is that the scorer can read protocol.md at the freeze SHA,
  and protocol.md ties that token to Arm A's method. Details and the residual wording are in `key.txt`. To revert,
  regenerate the blind file from `p1/answer.md` unchanged.
- Blind files: `/workspace/lab-runs/t15/blind/X.md`, `/workspace/lab-runs/t15/blind/Y.md`. No other edits. Both
  mtimes are set to the same instant. `blind/` contains only these two files. File sizes differ by content, which is unavoidable.
- Not done: no contact with Sol, no PR, no push.

## Reuse run

The protocol's optional follow-up run that reuses Arm A's store has **not** been done.

> **Correction (2026-10-09 03:09 ICT, added to this repo copy after evaluation):** the line above was true when this
> file was written (~02:51 ICT). The reuse run was dispatched later, at 02:51:49 ICT (`dispatch.log`), and has been
> done. See `p1-reuse/run/` and the "Reuse run" section of `../results.md`.

## Addendum: transcript-based counts (coder, 2026-10-09 ~02:55 ICT)

The executor could not read transcripts; the dispatcher (coder) can. Counts below come from ReadTranscript of each arm, full transcript paged to the start, classified by tool name per tool_use.

| | Arm A (p1) | Arm B (p2) |
|---|---|---|
| Total tool calls | 30 | 35 |
| Web calls | 13 (5 WebSearch, 8 WebFetch, 0 curl) | 20 (8 WebSearch, 11 WebFetch, 1 curl via Shell) |
| Other tool calls | 17 (6 Read, 11 Shell) | 15 (2 Read, 13 non-web Shell) |

- Arm A: transcript web count 13 equals ledger web charges 13. Independent re-audit: `audit --observed-web 13` from the transcript count gives the same result as the arm's own self-reported run. Every web call was preceded by a matching `charge web` in a prior Shell call.
- Arm B: transcript web count 20 equals its final message. `calls.log` has 22 call lines + 2 correction notes because it pre-logged 2 fetches it never made (`cdn.openai.com/deep-research-faq.pdf`, `github.com/huggingface/blog/blob/...`) and logged pdf URLs where it fetched the html versions. Tally over-counted; budget not exceeded.
- Contamination (transcript grep): Arm A read only autonomy-contract/SKILL.md, research-lab/SKILL.md, research/SKILL.md, adversarial-review/SKILL.md, adversarial-review/references/spec.md (the one allowed reference), and its own dirs. Arm B read only research/SKILL.md and its own p2 files. No reads of /workspace/research, /workspace/review-scratch, references/design-notes.md, or evals/t15. **Clean.**
- Human interventions: 0 for both. Each transcript has exactly one user message (the frozen prompt).
- Models: not visible in transcripts.
- Cost ratio check (protocol "better but costlier" rule): A used 0.65x B's web calls and 1.21x B's time to answer.md. Neither exceeds 1.5x.
- Note: Arm A's own audit passed `--observed-web 13` from its self-tally; the transcript confirms that number independently.
