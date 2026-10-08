# Verification record

Final implementation checks:

- `python -m unittest discover -s examples/research-lab -p 'test*.py' -v`: **22 probes passed**, 2.451 seconds in this environment. No network or paid API calls.
- The recorded real protocol replays offline to `completed` with the same 4 request steps, 5 web calls, 5 queries, 12 page operations, 1 experiment and three identical claim dispositions. Replay is not fresh source verification.
- The aggregate-analysis script runs independently and reproduces its committed numerical results.
- A subsequent local investigation imported the real completed ledger and retrieved two reviewed knowledge entries, with source provenance, as hints. It asserted no new findings automatically.
- Independent model adjudication opened primary originals and supported 6/6 baseline and 3/3 autonomous scoped top-level claims; both rubric ratings tied. Model source appraisal is not a guarantee of correctness or scientific reproducibility.
- Local code inspection traced transaction rollback, stable pending request IDs, budget reservation, observation replay rejection, challenge coverage, knowledge promotion and stopped states. No changes to existing skills or other project code.

Boundary evidence: probes cover unsupported/unknown citations, snippets presented as originals, omitted challenges, disputed knowledge, failed tools retained against budget, stale responses, unknown/replayed observations, deadline recovery, negative/paid reservations, bounded refinement, adapter nonzero exit, missing executable, malformed/oversize output and process timeout. The timestamp-compatibility regression surfaced in the live run and is directly covered.

Limits: the live host is cooperative and does not expose token billing; authoritative tool permissions, paid-budget enforcement and cancellation require its trusted gateway. The optional unattended executable adapter has only fixture-level end-to-end evidence. No service was deployed, paid API invoked, or branch merged. The first real run needed one automated compatibility repair; the elapsed result includes it.
