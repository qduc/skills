# Autonomous Research Lab — working vertical slice

A human supplies a question and a budget. An existing agent host researches it, checks competing evidence, records feasible experiments, and delivers a decision brief. A small standard-library Python ledger retains the evidence and enforces protocol gates. No server, paid API, new agent framework or deployed service.

**Start:** read [HOST.md](HOST.md), give its host task to your existing agent, and use [experiment.json](experiment.json) as the question/budget input. Python 3.10+ and SQLite are sufficient. The live experiment uses the current Codex host's existing browser/search tools; no separate model provider is configured.

## What runs

| Autonomy contract | Concrete mechanism |
|---|---|
| Observe | Goal, inspected-source notes, actual tool observations and previous reviewed knowledge |
| Decide | Persisted request with bounded remaining resources and stage-specific schema |
| Act | Pre-reserved search/open/experiment operations through the existing host |
| Verify | Evidence references, observed opens, complete claim challenge; host semantic review |
| Learn | Reviewed supported claims with provenance in SQLite; recurring failure lessons |
| Repeat | At most two research cycles; deadline, step cap, final brief or explicit stopped state |

One agent can do every phase. Separate contexts for the baseline and lab prevent answer leakage. Parallel source workers are unnecessary for this first slice. The stages are semantic seams, not a cast of specialized agents.

The application deliberately uses a predictable plan → research → challenge → report sequence, with bounded refinement. It does not promise a general scheduler. Other domains are not implemented.

## Output and reuse

The database stores transactional state, reservations, append-only events and promoted knowledge. The current model context is disposable. A restarted host receives the same pending request without another step charge. A subsequent investigation can import the previous knowledge database and retrieve up to five relevant hints. It must revalidate them before asserting a new finding.

The human report contains conclusions, source-linked claims, uncertainty, contradictions and follow-ups. Detailed actions remain in the ledger. Supported claims need evidence, every claim needs a challenge, and disputed claims cannot enter durable knowledge. These checks ensure traceability, **not semantic truth**: the model's source-to-claim judgment remains fallible.

## Verification

```sh
python -m unittest discover -s . -p 'test*.py' -v
```

Probes exercise complete delivery, restart recovery, stale replies, failed tools, source fabrication, unsupported claims, paid/negative reservations, budgets, deadlines, refinement limits, knowledge reuse and adapter failure boundaries. They make no network or paid API calls. Live research provides separate evidence of host compatibility.

Read [EVALUATION.md](EVALUATION.md) for measured results and [DESIGN.md](DESIGN.md) for alternatives, lessons and remaining limitations.
