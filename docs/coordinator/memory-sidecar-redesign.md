# Memory sidecar redesign: transcript watcher + deterministic filter

**Status: proposal.** [Memory sidecar](memory-sidecar.md) now documents this
watcher design, but the integration stays disabled per
[Operational status](../../skills/supervise-panes/references/operational-status.md) until the work below is implemented
and independently verified. Nothing here changes that policy.

**Implemented so far** (branch `sidecar-v2`): the deterministic, profile-driven
filter (`scripts/coord_memory_filter.py`) wired into `_events`; the transcript
watcher (`scripts/coord_memory_watch.py`) with launcher markers and idempotent
binding; the induction tooling (`scripts/coord_memory_induct.py`: a payload-free
census, profile shape and reduction gates, and an induction entry point); and
removal of the hook path (`install_memory_hooks.py`, `capture()`, `session_nonce`,
`_find_transcript`, the `session-nonce` command, and the PreCompact/SessionEnd
triggers). The efficacy eval is recorded in
[the efficacy result](../../skills/delegate/evals/memory-sidecar-efficacy.md).

Sources are harness-agnostic through the profile seam. A profile names the path
to the record's type token and maps each conversational record type to a channel
(its text path and block specs), so one declarative shape covers structurally
different harnesses. Two hand-written profiles ship: `CLAUDE_CODE` (types
`user`/`assistant`, text at `message.content`) and `TERM2` (envelope
`event.type`, user text at `event.message.text`, assistant text in
`event.turn.items`). Sessions carry their harness in the launcher marker and the
binding key (`<harness>:<session_id>`); the judge selects the profile by that
harness and falls back to `CLAUDE_CODE` for an unknown one.

Independent verification is recorded below. The real-use gate remains. The judge
is no longer driven by a hook.

**Verification status (2026-10-09).** Corpus measurement recorded; efficacy
eval recorded in [the efficacy result](../../skills/delegate/evals/memory-sidecar-efficacy.md)
(5/5 labeled decisions captured, 0 noise). The full skill suite passes (284
tests). An independent verifier inspected claims 1, 2, 5, 6, and 8 against the
artifact; it confirmed claims 6 and 8 by inspection and found claim 2 had no
prompt-level assertion, which is now closed by
`test_injection_never_reaches_the_judge_prompt`. Two further independent verifiers
did not implement the change: one inspected the artifact and quoted the exact
claim-2 assertion `assertNotIn(sentinel, prompt)` and the claim-8 payload-free
assertions, and one ran the full suite on a byte-identical snapshot of commit
2362b8e — 284 tests in 37.7s, OK. Read-only subagents cannot execute tests (the
harness restricts a non-write agent's shell to GREEN commands), so the runtime
run used a write-capable agent against a disposable copy. Claims 1, 2, 5, 6, and
8 are covered by this combination. The Term2 profile was measured on the six newest real Term2
conversation logs (7,511,942 bytes in, 52,363 kept-text bytes out, 99.3%
reduction, 25 kept records) and keeps genuine user/assistant text. The real-use
gate is left pending by explicit user choice. The sidecar stays disabled.

## Why change

The previous integration installed Claude Code hooks (`PreCompact`,
`SessionEnd`) that fork a judge. The hook coupling is brittle:

- Requires writing into `~/.claude/settings.json`; hook ownership is matched by
  exact command string, so an interpreter path change orphans the entry.
- Fires only at boundaries: a session that never compacts or is killed loses
  everything; `PreCompact` fires at an arbitrary point.
- Binding needs a nonce planted in-session, then `_find_transcript` guesses among
  the newest 50 transcripts by scanning their last 256 KB each.
- Detached `Popen` judge, unsupervised.
- Invokes `term2 -p codex ...` for a Claude workflow: a cross-harness dependency.

Separately, the judge currently ingests tool output. `record_text` feeds a
`tool_result` block's `content` straight into the prompt, and tool results are
the largest block class in real transcripts.

## Measured basis

12 newest `~/.claude/projects/-home-qduc-term2/*.jsonl`:

| block type | bytes | note |
| --- | ---: | --- |
| `tool_result` | 1,855,626 | largest class; conversion + injection vector |
| `thinking` | 1,048,574 | already dropped by `record_text` |
| `tool_use` (inputs) | 763,431 | currently included |
| `user` text | 390,897 | signal |
| assistant `text` | 253,815 | signal |
| `image` | 263,434 | |
| total records | 14,948,877 | |

Conversational signal (`user` + assistant `text`) is ~4% of transcript bytes. A
deterministic filter recovers it without a model in the loop.

### Filter measurement (2026-10-09, branch `sidecar-v2`)

Re-ran the census over the same 12 newest
`~/.claude/projects/-home-qduc-term2/*.jsonl`, offline and with no model,
comparing the deleted `record_text` judge input with the profile-driven filter:

| metric | value |
| --- | ---: |
| transcript record bytes | 14,948,877 |
| old judge-input bytes | 3,134,248 |
| new judge-input bytes | 689,356 |
| reduction vs old | 78.0% |
| kept records | 481 |
| dropped records | 6,156 |

Dropped records by type: `no-text` 2487, `attachment` 1700, `last-prompt` 333,
`atis-latch` 332, `mode` 289, `queue-operation` 270, `ai-title` 207, `system` 175,
`bridge-session` 127, `permission-mode` 120, `file-history-snapshot` 74,
`cost-state` 17, `file-history-delta` 13, `dev-mods` 12.

Method: total counts every accepted JSONL line's raw bytes; `old` sums the bytes
`record_text` would have emitted (tool_use inputs included, thinking dropped);
`new` sums the filter's retained text. Kept/total record ratio is 7.2%; the new
judge input is 4.6% of transcript bytes, observed against the ~4% target.

## Decisions

- **Trigger:** a continuous watcher daemon tails transcript files and classifies
  incrementally. No harness lifecycle events.
- **Association:** launcher-mediated. The coordinator owns the session launch and
  pins a deterministic marker; no nonce search, no heuristic guessing.
- **Judge input:** text only — user and assistant natural-language text. No tool
  names, inputs, results, thinking, or images.
- **Sources:** harness-agnostic through a normalization layer. Claude Code
  transcripts and term2 conversation logs ship hand-written profiles first; a
  source with no profile is onboarded by schema induction (see below).

## Target architecture

```
watcher daemon
  discovery  watch <source-root>/<project>/<session>.<ext>
  binding    transcript file -> task, via launcher marker
  collector  read new bytes from stored offset; complete JSONL lines only
  filter     deterministic; no LLM
  judge      existing prompt, validator, and byte budget (unchanged core)
  apply      coord_state.py memory-apply (unchanged)
```

The offset + `memory.audit` dedup core already makes the pipeline idempotent and
resumable; keep it.

## Filter stages (no model)

1. **Record gate.** Keep conversational records; drop the rest. Real transcripts
   carry non-conversational types (`attachment`, `system`, `mode`,
   `permission-mode`, `queue-operation`, `file-history-snapshot`,
   `file-history-delta`, `ai-title`, `last-prompt`, `cost-state`,
   `atis-latch`, `bridge-session`, `dev-mods`). Count and log each unrecognized
   type once so schema drift is visible rather than silently ingested.
2. **Block gate.** Keep `text` blocks from `user`/assistant records. Drop
   `tool_result`, `tool_use`, `thinking`, `image`, `document`.
3. **Caps.** Per-event byte cap (~2 KB) and a batch budget smaller than the
   current 12 KB, so one paste cannot dominate.
4. **Redact.** Keep existing `redact()`.

## Collector

- Parse only complete lines; hold a trailing partial line until its newline
  arrives (a tailer sees torn writes).
- Reset the offset to 0 when the file is truncated or replaced (offset > size).
- Reuse `transcript_offset` in the binding record.

## Association (launcher-mediated)

- The coordinator launches the session and pins a marker: a wrapper writes
  `{session_id, task_id}` at launch, or the session runs under a unique cwd that
  maps to the task.
- The watcher reads markers to bind a transcript file to a task. No nonce, no
  "newest 50" search.

## Removed by this change

- `install_memory_hooks.py` and the settings hook entries.
- `capture()` boundary handling and the hook entrypoint.
- `session_nonce`, `_find_transcript`, and nonce-based `bind_session --session-id auto`.
- PreCompact / SessionEnd triggers.

### Concrete removal checklist (completed)

- Delete `scripts/install_memory_hooks.py`.
- `coord_memory.py`: delete `capture()` and the stdin hook branch of `main()`.
  Keep `flush`, the `--judge` CLI, `_hook_log`, `_child_env`, and `_runner`; the
  judge CLI is retained as the single-session debug entry point.
- `coord_state.py`: delete `session_nonce()`, `_find_transcript()`, the `auto`
  branch of `bind_session`, the `session-nonce` subparser and its dispatch, and
  the `--nonce` / `--projects-dir` args. Keep `--transcript`.
- `test_coord_memory.py`: drop `import install_memory_hooks`, `InstallerTest`,
  and the capture tests (`test_non_boundary_does_not_read`,
  `test_missing_binding_and_child_marker_do_not_read`,
  `test_missing_transcript_is_deferred`, `test_changed_task_owner_is_ignored`).
  Keep the `_child_env` / `_runner` / `_hook_log` tests.
- `test_coord_state.py`: drop the nonce and `auto` bind tests (~lines 100-145).
- `references/memory-sidecar.md`: rewrite around the watcher and launcher marker;
  keep it disabled per operational-status.md.

## Security

Dropping tool output removes the primary prompt-injection channel, but user and
assistant text can still carry injected instructions. The data frame, strict
action validator, and provenance rules stay. This narrows the "judge acts on
transcript content" objection; it does not remove it.

## Implementation surface

- `coord_memory.py`: add the filter and watcher loop; keep `prompt`, `_batches`,
  `_proposal`, `_map_event_ids`, `redact`; drop the hook path.
- New watcher entrypoint (a `watch` subcommand or `coord_memory_watch.py`).
- New per-source normalization adapters.
- Update `test_coord_memory.py` for the filter and collector; remove
  `install_memory_hooks` coverage.
- Update `memory-sidecar.md` and `operational-status.md` at implementation time,
  not before.

## Schema induction for unseen harnesses

A harness-agnostic adapter written by hand is work repeated for every new
harness. Use the judge LLM for the onboarding step only, never at runtime. Two
distinct uses, only the first is wanted:

- **Onboarding (one per harness, per schema version):** the LLM reads a
  *structural census* of a sample and emits a declarative profile; deterministic
  code interprets that profile at runtime.
- **Per-record runtime classification (rejected):** it reads every record
  including tool output, is nondeterministic, costs tokens proportional to
  transcript size, and reintroduces exactly the injection channel the filter
  removes.

Induction input is a census, not content: for a sample of records, the set of
top-level types, each type's key set, nested container and block types, byte-size
distributions, and at most a few truncated, redacted sample values. The model
sees shapes, not payloads: near-zero injection surface and tiny token cost, while
still enough to infer which field holds the human text.

Induction output is a **declarative profile**, not generated code: which record
types carry conversational text, which field holds text, which block types are
noise, and how meta or sidechain records are detected. A small deterministic
interpreter applies the profile. It is committed, reviewed once by a human, and
versioned.

Deterministic gates before a profile is trusted:

- it yields non-empty text for the records the census says carry text;
- its byte reduction on the sample clears a threshold;
- unknown record types are dropped and logged, never silently ingested.

Re-induction fires on the drift signal the record gate already requires (a record
type absent from the profile's known set). A hand-written Claude Code profile
ships as the default; induction runs only for a source with no profile.

Cost honesty: for one or two harnesses a hand-written adapter is cheaper than an
induction pipeline. Induction earns its keep only for genuinely unseen harnesses,
which is why it is an onboarding tool, not a runtime dependency.

**Implemented** (`scripts/coord_memory_induct.py`): `census_records` emits only
identifier-shaped schema tokens, so a secret or injection string in the sample
cannot appear in the census (asserted in `test_coord_memory_induct.py`);
`validate_profile` and `evaluate_profile` are the deterministic gates;
`induce` runs the onboarding model once (injected runner) and returns the
validated profile. Held-out records are checked for coverage and the reduction
threshold (the test uses a synthetic second-harness shape, distinct from Claude
Code's).

A real induction run over an unseen harness, and a committed frozen profile from
it, remain. The census reports record types from a top-level discriminator; an
envelope-style source (a type token nested under `event.type`, as Term2 uses)
is not yet reported by the census, so such a harness ships a hand-written profile
first. This is why Term2 ships a hand-written profile rather than an induced one.

## Verification

Nothing here is claimed until it has evidence. This is a high-risk change: it
writes into authoritative task state, it is a security boundary, and it adds a
long-lived process. So it needs tests plus an independent verifier plus the
[Real-use verification](../../skills/supervise-panes/references/real-use-verification.md) gate before the sidecar is
enabled. The policy in [Operational status](../../skills/supervise-panes/references/operational-status.md) stands until
then.

### Claims and their evidence

Ordered cheapest first; stop and fix before paying for the next tier.

1. **Filter selects the signal.** Given a record, the filter emits exactly its
   conversational text and drops the noise. Tests in
   `scripts/test_coord_memory_filter.py`, over committed JSONL fixtures for both
   harnesses: user text, assistant text, string content, `tool_use`, `tool_result`,
   `thinking`, `image`, each known noise type, and an unknown type.
2. **Tool output cannot reach the judge.** Feed a record whose `tool_result`
   contains a sentinel injection string; assert the string never appears in the
   judge prompt. This is the injection-containment claim, and it is deterministic.
3. **Redaction still holds** on retained text. Extend the existing secret-form
   test to the new filter path.
4. **Byte reduction meets the target** on a real corpus. Re-run the census over
   the local transcripts, offline and with no model, and record bytes-in,
   bytes-out, and per-type drop counts. This is a measurement, not a pass/fail
   test; the acceptance target is the ~4% keeper ratio, reported as observed.
5. **Collector is tail-safe and idempotent.** Unit tests: a torn trailing line is
   not parsed and is parsed once completed; truncation or replacement resets the
   offset; running the collector twice over the same file yields no duplicate
   memory items (offset + `memory.audit` dedup).
6. **Watcher works end to end without a live model.** Bind a synthetic transcript
   in a temporary source tree to a task, run the watcher with an injected stub
   `runner` returning canned actions, and assert the resulting `memory`. The
   judge already accepts an injected runner, so this needs no LLM.
7. **Binding is deterministic.** Unit-test the launcher-marker lookup, including
   the ambiguous case (two sessions, same project) that the old nonce search
   handled by guessing.
8. **Induction is payload-free and its profile passes the gates.** Assert the
   census built from a record containing a secret or injection string carries no
   payload bytes; then, on held-out records, assert the frozen induced profile
   yields non-empty text where text exists and clears the reduction threshold.
   The induction *run* is nondeterministic; the profile it produces is frozen,
   reviewed, and interpreted deterministically.
9. **Judge/apply contract is unchanged.** The existing `coord_memory` tests
   (prompt frame, event-id mapping, batching, oversize retention, apply
   validators) still pass. Run the skill's test suite as the regression gate.

### Efficacy — does it capture the right things

Mechanical tests prove containment, not usefulness. Take a few completed
sessions, hand-label their real decisions and discoveries, run the sidecar, and
report captured versus missed and the noise rate. This is the claim the user
actually cares about: that the memory reflects reality. Record it as an eval in
`evals/` with stated criteria, not as prose.

### Independent verification

A separate agent that did not implement the change verifies claims 1, 2, 5, 6,
and 8 by running the tests and the measurement against the artifact, and inspects
the injection test and the frozen profiles rather than trusting the report.

### Real-use gate

Before enabling, satisfy [Real-use verification](../../skills/supervise-panes/references/real-use-verification.md): a
fresh agent, the shipped skill, a representative real task, retained evidence,
and independent inspection of the captured memory. The user may waive this;
record the waiver and its limits with the result.

### What stays uncertain

- Absolute injection containment is not provable; only that the known channels
  (tool output, tool input, thinking, images) are closed and that retained text
  is redacted.
- Long-run watcher stability (silent death, duplicate watchers, lock contention)
  is only observable over real use, not in a test.
- Induction correctness for harnesses not in the sample.

## Open risks

- **Transcript schema drift.** Observed record types are harness/version
  specific; monitoring trades hook brittleness for schema brittleness. Mitigate
  with fail-soft unknown-type telemetry plus re-induction (see above).
- **Induced profile correctness.** An induction step can produce a wrong profile;
  the deterministic gates above are the only thing standing between it and silent
  loss or ingestion. An induced profile must be reviewed before it is committed.
- **Watcher lifecycle.** Who starts it, supervises it, and guarantees one per
  host. Needs an explicit ownership and restart story.
- **Watch portability.** inotify vs a poll fallback for non-Linux hosts.
- **Partial-turn classification.** A watcher can classify a turn mid-stream; the
  judge should prefer settled turns or tolerate revision, since later actions can
  supersede earlier ones.
