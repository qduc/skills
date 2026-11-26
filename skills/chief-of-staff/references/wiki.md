# Project wiki

The wiki carries durable knowledge across sessions so future workers start
with the context earlier ones had to discover. It is a dated historical
record, not a live mirror of the codebase and not a task tracker — current
task state belongs in the run ledger.

## Find it before writing

1. Look for an existing shared wiki or knowledge base and follow its
   conventions.
2. Read its index and the pages relevant to the current goal, subsystem,
   decisions, and prior failures.
3. Give workers pointers to relevant pages, files, issues, and commits rather
   than pasting large context into every brief.

If none exists, agree on a location with the user before the first write.

## Structure

A compact, interlinked Markdown wiki. At minimum:

```text
wiki/
  index.md
  decisions/
  projects/
  systems/
  problems/
  preferences/
```

`index.md` lists each page with a one-line description, grouped by category.
Each page covers one durable topic — a decision, subsystem, recurring problem,
project, or preference — and links related pages.

## Evidence and history

- **Date claims.** For code behavior, include the repository and commit when
  available. For external facts, link the source and its date.
- **Label confidence:** **verified**, **inferred**, or **assumption**. A
  worker's finding is accurate within its view, but may not hold project-wide;
  record it as inferred until checked against the wider context, then
  promote it.
- **Supersede, don't rewrite.** When a fact changes, append a new dated claim
  and mark the old one **superseded**, preserving the history.
- **Reference sources, don't copy them.** Issues, PRs, transcripts, logs, and
  worker reports are linked, not pasted in or edited as if they were the
  original.
- **Update every affected page** and the index when a decision or correction
  touches more than one topic.
- No secrets, credentials, or unnecessary personal data.

## Three operations

- **Ingest:** after useful work, capture durable findings, verified facts,
  decisions, user corrections, and reusable lessons, linked to evidence.
  Context gaps that assumption checks repeatedly caught are high-value
  entries — they are exactly what the next worker would otherwise lack.
  Keep one `systems/verification.md` page for the verify layer: where the
  `verify-<app>` skill lives, its Isolate answer, and dead ends with their
  exact reason (or that the user declined one). Later runs read it before
  trying to create a skill again.
- **Query:** before deciding or briefing a worker, retrieve relevant pages and
  put the useful pointers in the brief.
- **Lint:** look for contradictions, orphan pages, missing links, stale
  claims, and newer evidence that supersedes older conclusions. Run it after
  failed or unusually difficult work, and periodically otherwise.
