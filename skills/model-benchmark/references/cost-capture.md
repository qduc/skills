# Cost capture

`scripts/collect-cost.py` recovers what a candidate actually consumed. Cost is
the second half of the question a benchmark answers — a ranking without it says
which candidate is best, not which one you should run.

## Where each harness keeps its usage

| Harness | Source | Requirement |
| --- | --- | --- |
| `codex` | `turn.completed.usage` in the JSONL stream | `codex exec --json` |
| `pi` | `usage` on each assistant `message_end` | `pi --mode json` |
| `term2` | provider-traffic log on disk | `logging.debugLogging = true` |

term2 is the awkward one: it writes no usage to stdout at all. The collector
reads `~/.local/state/term2-nodejs/logs/provider-traffic/` and attributes each
response file to a candidate by mtime, using the `.start_epoch` / `.end_epoch`
that `run-candidates.sh` records.

Two consequences follow, and both bite silently:

- **term2 candidates must run serially.** Attribution is a time window over a
  shared directory. Running term2 cells in parallel mixes their usage together
  and nothing in the output looks wrong. The runner is serial by default; do
  not pass `--parallel` with term2 in the grid.
- **Debug logging must be on before the run, not after.** There is no way to
  recover usage for a run that already happened. Verify the setting first, and
  restore it afterwards if the user had it off.

## Normalisation

All three are folded into the same five numbers. The one that matters is
`input`, which is always *uncached* input: every wire format reports cached
tokens inside the input total, and cached tokens are an order of magnitude
cheaper. Charging them at the full rate overstates every long agentic run,
which is exactly the kind of run a benchmark measures.

## The dollar figure is a proxy

`PRICES` in the collector comes from pi's model catalog. These models are
normally reached over a ChatGPT subscription rather than metered API billing,
so the dollar column is a comparable measure of consumption, not an invoice.
It is still the right column to compare on: it weights output tokens against
input tokens the way the provider does, which a raw token count does not.

When the price table and the model set drift apart, the collector prints `--`
for that candidate rather than guessing. Add the model to `PRICES` rather than
letting a run report a blank cost column.
