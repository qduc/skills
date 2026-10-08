# T15 artifacts

These are the raw records behind [../results.md](../results.md), copied from `/workspace/lab-runs/t15/` on 2026-10-09 ICT.
They keep the original layout, so relative paths in the runs still resolve. For example, `budget.json` points to
`../../p1-store/knowledge.jsonl`, and the reuse run's `file:experiments/...` source is included.

| Path | What it is |
| --- | --- |
| `p1/answer.md` | Arm A (autonomy contract) answer, a copy of `p1/run/brief.md` |
| `p1/run/` | Arm A run directory: `goal.md`, `budget.json`, `ledger.jsonl`, `log.jsonl`, `claims.jsonl`, `sources.jsonl`, `findings.jsonl`, `brief.md` |
| `p2/answer.md` | Arm B (single well-prompted baseline) answer |
| `p2/calls.log` | Arm B's self-kept web-call tally. Unreliable: it over-counts by 2 (see results) |
| `blind/X.md`, `blind/Y.md` | What the scorer saw (X = Arm A with one redaction, Y = Arm B unchanged) |
| `blind/scores.md` | Sol's scores, citation spot-check, and blinding check |
| `blind/scores.pre-blinding-check.md` | Sol's scores before the blinding question was asked (sha256 recorded in `results-unblinded.md`) |
| `key.txt` | Coin flip, X/Y mapping, leak-scan hits, and the one redaction |
| `measurements.md` | Phase 2 measurements, including the authoritative "Addendum: transcript-based counts" |
| `dispatch.log` | Dispatch times, worker type, and scorer and reuse dispatch notes |
| `results-unblinded.md` | Conductor's unblinding note: score table and decision-rule arithmetic |
| `p1-reuse/run/` | Optional reuse run (outside the A/B comparison): run files plus `experiments/same_backbone.{py,out}` |
| `p1-store/knowledge.pre-reuse.jsonl` | Arm A's knowledge store after Arm A, before the reuse run (5 entries) |
| `p1-store/knowledge.jsonl` | The same store after the reuse run (12 entries) |

**Not copied:**

- `p2/openai-deep-research.html`: a Cloudflare/JS challenge page that Arm B's curl got instead of the article.
- `p1-reuse/run/experiments/{rcb.html, rcb.txt, sab.html}`: about 3 MB of raw third-party arXiv pages that the reuse run
  fetched and parsed locally. The `same_backbone.*` files keep the table values that were extracted.
- `p1-run-snapshot-pre-measurement.tar`: a backup of `p1/run`. The copy here is the live run directory.
- The scorer's private pairs list `/workspace/review-scratch/t15/pairs.md`. The sampled pairs are already in `blind/scores.md`.

**Re-verifying:** `lab.py validate` appends a `validation` event to the run's `log.jsonl`, so run it on a copy.
`audit` only reads. On these files, both runs give VALID and AUDIT OK:
`audit p1/run --observed-web 13` and `audit p1-reuse/run --observed-web 9 --observed-cycles 4`.
Arm A's `log.jsonl` has two `validation` events. The one at 02:48:16 is Arm A's own. The one at 02:49:39 came from
the measuring worker's phase 2 check.

The files were scanned for credentials and tokens before commit and none were found. They do contain box paths and
the subagent ids of the two arms.
