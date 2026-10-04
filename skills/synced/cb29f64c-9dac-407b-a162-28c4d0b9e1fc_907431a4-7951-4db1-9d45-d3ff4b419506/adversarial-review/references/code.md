# Code & Diffs — review profile

Applies when the artifact is source code, a diff/PR, a script, or configuration-as-code. Use alongside SKILL.md; do not restate its rules.

## Reading order

1. Entry points and public surfaces first (exports, handlers, CLI args, config keys).
2. State: what is mutated, shared, persisted, cached.
3. Only then internals. For diffs, also read enough surrounding unchanged code to know what the change interacts with — a diff reviewed in isolation is a top source of false negatives and false positives.

## Persona focus adjustments

- **P1 Assumption Challenger:** input validity (null/empty/huge/malformed/duplicate), encoding and locale, clock and timezone, filesystem/network availability, library behavior assumed but not pinned, "this is only called with X" claims. Check whether assumptions are enforced (validated/typed/asserted) or merely hoped.
- **P2 Failure-Path Prober:** every `throw`/`error` return path — who catches it and what state is left behind; partial writes; retries without idempotency; resource leaks on early return; concurrency (shared mutable state, check-then-act races, lock ordering); timeouts absent on external calls.
- **P3 Consistency Auditor:** signature vs. call sites; docstring/comment vs. behavior; type says non-null but code branches on null (or vice versa); error contract of the function vs. what callers handle; config default vs. documented default; test asserts behavior the code doesn't have.
- **P4 Scope & Omission Detector:** stated purpose of the change vs. what the diff covers (the fix applied in one place but the same bug exists in a sibling path); missing migration for schema/format changes; no test for the specific behavior the change claims to add; feature flags/rollback absent for risky changes.
- **P5 Adversary:** every input crossing a trust boundary (user input, network, file contents, env vars, deserialization); injection (SQL/shell/path/template); authz checks present at every entry, not just the main one; secrets in code/logs; resource exhaustion (unbounded loops, allocations, recursion driven by input); TOCTOU on files and permissions.

## Evidence norms

A code finding needs a **constructible trigger**: a specific input value, call sequence, or environmental event ("dependency returns 503 mid-loop") — not "if something goes wrong." For concurrency findings, name the two interleaved operations and the shared state. If you can write the failing input in one line, include it in the finding's evidence.

## Severity anchors

- **critical:** data loss/corruption; security breach reachable from an untrusted input; crash-loop of the whole service on realistic input; silent wrong results on the main path.
- **high:** wrong results or crashes on realistic edge inputs; unhandled failure of a dependency the code calls on the main path; race with plausible timing; authz gap on a secondary entry point.
- **medium:** resource leak needing sustained conditions; wrong behavior in a rare-but-real configuration; misleading error handling that will burn debugging time when it fires.
- **low:** defect on a path with strong existing mitigation elsewhere; harm limited to degraded logs/metrics.

Reject as nitpicks regardless of temptation: naming, formatting, "could be simplified", micro-perf on cold paths, missing comments, style-guide deviations — unless they are the direct cause of an accepted defect (e.g., copy-paste error hidden by misleading names, where the defect itself is the finding).

## Type-specific notes

- **Low-yield persona:** none — all five earn their keep on code. Under Light budget the SKILL.md default (P1–P3) still applies, but if the code touches a trust boundary, promote P5 into the Light set and say so.
- **Diffs:** P4 must explicitly check "same defect elsewhere" — grep the codebase (if available) for the pattern the diff fixes.
- **Config-as-code:** P3's main axis is config vs. the code that reads it; a key rename in one and not the other is a classic critical.
- **Tests included in the artifact:** a test that passes while asserting the wrong thing is a finding against the code artifact, filed by P3.
