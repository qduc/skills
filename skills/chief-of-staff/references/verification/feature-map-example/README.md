# Notes verification map

This directory is the maintained source for verifying the user-facing behavior of Notes. Read the index before driving the app, then use the matching feature file as the recipe.

## Baseline preconditions

- Launch Notes at `http://127.0.0.1:4173` with a disposable data directory.
- Set `NOTES_DATA_DIR=/tmp/notes-verify-$RUN_ID` so concurrent runs do not share state.
- Seed notes titled `Quarterly plan` and `Grocery list`.
- Put `control-notes` and the `notes` CLI on `PATH`.
- Run `control-notes doctor` and require the expected URL, data directory, and build revision.
- Never drive an instance that was not started by this verification run.

## Driving conventions

- Start every recipe from the baseline state unless its preconditions say otherwise.
- Prefer ARIA roles and accessible names over CSS selectors or DOM position.
- Treat every command as literal. Keep quoted names and flags unchanged.
- Run browser actions through `control-notes browser`.
- Run terminal actions through `control-notes cli -- <command>`.
- Restore seeded data after a mutation. Do not remove proof artifacts during cleanup.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final screen.
- UI proof includes an ARIA snapshot and a screenshot with the app identity visible.
- CLI proof includes the command, stdout, stderr, and exit code.
- Mutation proof includes a read-only second view of the stored value.
- Record the feature ID and entry point used with every artifact.
- Report an unreachable path with the attempted command and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.
- Report one verdict per sub-feature and entry point: `verified`, `failed`, `verified-unreachable`, or `skipped`.
- Classify every failure as `product`, `map-drift`, or `environment`, and append map drift to [`DRIFT.md`](./DRIFT.md).

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with <harness>` starts with `Preconditions:`, then a `Smoke:` line naming the one or two steps that prove the feature is basically alive, then labeled bullets that pair each user action with an exact command and observable result. Steps that reproduce a fixed bug are labeled `Regression (<date>, <ref>)` and stay in the feature they belong to.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of feature files. Name only user paths, stable handles, required state, commands, and observable proof. Source paths live only in the Change selection table below.

## Features

Entries marked `(unproven)` have never been driven end to end. Treat their recipes as drafts.

- [Create a note](./create-note.md) covers browser and CLI creation, cancellation, persistence, and cleanup.
- [Search notes](./search.md) covers toolbar, keyboard, and CLI search with matching, empty, and clear states.

## Change selection

Match a change's paths against this table to pick features. A path that matches one or two rows: drive those features in full. A path in a shared row: drive the smoke steps of every listed feature. A user-facing path that matches nothing: the map is missing a feature.

| Feature | Source paths |
| --- | --- |
| [create-note](./create-note.md) | `src/notes/editor/**`, `src/api/notes/create.ts`, `cli/commands/create.ts` |
| [search](./search.md) | `src/search/**`, `src/api/notes/search.ts`, `cli/commands/search.ts` |
| shared: create-note, search | `src/notes/store/**`, `src/ui/toolbar/**` |

