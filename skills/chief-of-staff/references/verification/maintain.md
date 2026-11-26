# Maintain a project verification skill

Adapted from pstack's `maintain-verification-skill` (MIT, © 2026 Lauren Tan —
see `LICENSE-pstack`). Changes: harness-neutral worker and path wording; a
scoped mode that runs automatically on logged drift; the drift log as an
input; selection-table upkeep; pruning removed features; chief-of-staff's
run ledger and authorization rules for shipping.

A feature map rots the moment the app changes. This is the upkeep loop for a
verification skill made by `create.md`, or any project-local verification
skill with a feature map. The unit of rigor is the feature, not every
sentence: cover each in-scope feature file from source and exercise it live,
without turning every bullet into a test.

## Modes

| Mode | Covers | Runs |
| --- | --- | --- |
| **Scoped** | Features with entries in `features/DRIFT.md`, plus any selection rows whose paths no longer exist | Automatically at the end of a run that left drift (`lifecycle.md`). Edits only the verify skill's directory, on the work branch, so no approval is needed. |
| **Full** | Every feature, plus pruning and a sweep for unmapped surfaces | Periodically. Offer it when the user asks, after a large change to user-facing behavior, or when scoped passes keep turning up drift in neighboring features. |

Track the pass in the run ledger (`assets/progress.md`, one task per
feature).

## Outcomes

Pick one, and say which:

- **clean** — every in-scope feature got source and live coverage; nothing
  to change.
- **changed** — proven map, harness, or doc corrections committed to the
  work branch.
- **blocked** — coverage couldn't finish or a proven fix couldn't be made
  safely. Say exactly what blocked it.

## Edit scope

Only edit the verification skill's own directory: its SKILL.md, `features/`,
and any harness scripts it owns. Never edit product code during this pass. A
behavior the map describes that the app no longer does is either map drift
(fix the map) or a product regression (report it — don't paper over it in the
docs).

## Pass

0. **Locate the target.** Find the project-local skill with Launch/Drive
   sections and a feature map (usually `verify-*/` in the harness's project
   skill directory). Several candidates → ask which; none → hand back to
   `lifecycle.md`.

1. **Index hygiene and drift log.** Read the feature map README and list its
   sibling files. Fix missing, extra, duplicate, or dead entries. Check every
   Change selection glob against the repo and note those that match nothing.
   Read `features/DRIFT.md`; in scoped mode, those features (plus features
   with dead globs) are the whole scope.

2. **Source wave.** One read-only worker per in-scope feature file,
   dispatched together where the harness allows. Use read-only workers if it
   has them. Either way, the brief says "do not edit files", and you check
   version-control status afterwards. Each worker explains how the
   user-facing feature works from source, flags likely drift with file
   citations, lists the feature's **current source paths**, and returns one
   concise live-verification recipe. Workers never drive the app and never
   edit files. Return shape: feature summary / source paths / likely drift or
   none / one recipe.

3. **Reconcile.** Every in-scope feature has a returned summary. Merge
   overlapping recipes into as few app states as practical. Spot-check cited
   drift; don't re-prove clean claims. Update the Change selection rows from
   the returned source paths, keeping globs tight. **Full mode only:** sweep
   recent churn for user-facing surfaces missing from the map (require a
   concrete source path before calling one missing), and find features whose
   entry points no longer exist in the source.

4. **Live pass.** Required even when source looks clean. The coordinator does
   all driving itself, because the instance is shared state. Follow the
   verification skill's own launch model: one long-lived instance driven
   serially for servers and UIs, or a fresh isolated session per drive for
   short-lived CLIs. Exercise every in-scope feature at least once (including
   its regression steps), and hold three invariants the whole pass:
   1. Never drive an instance you haven't health-checked since it last did
      something surprising — doctor before the first drive, on each fresh
      session where sessions are the unit, and again after any failed drive.
      Where doctor can't see the failure (a wedged UI on a healthy process),
      reset to a known state or relaunch rather than hoping.
   2. Evidence captured so far survives every cleanup — checked at its named
      location, not assumed.
   3. Nothing a drive started outlives its usefulness. Failed-iteration
      residue is cleaned whether the session is stuck, exited, or shared (for
      a shared instance, clean the residue, not the instance).

   A doctor failure caused by skill drift is drift: fix it within edit scope
   and retry once — restarting only what the fix invalidated — before calling
   the pass blocked. A feature that can't be reached is
   `verified-unreachable` only with the concrete prerequisite (auth,
   entitlement, OS, external state) and the route attempted; if the map omits
   that prerequisite, that's drift. Any harness fix gets re-driven live before
   it is committed. Final teardown comes after the last drive, re-proofs
   included.

5. **Triage.**
   - Wrong or missing user-POV description, stale expected result, or stale
     selection path → map drift; fix it.
   - Working behavior the harness can't drive → harness gap; fix it, with
     the same helper rules as generation (executable, invocation documented).
   - App behavior that's actually broken → product regression; record it for
     the user and keep it out of this change.
   - **Full mode:** a feature whose entry points are gone from both the
     source and the live app → prune it. Delete the feature file and its
     selection row, and note the removal in the outcome. Absent from the
     source but still reachable live means the selection paths are wrong,
     not that the feature is gone.

   Clear the `DRIFT.md` lines this pass resolved; leave unresolved ones with a
   note. Remove `(unproven)` from features you proved.

6. **Commit or stop.** For **changed**: commit the proven corrections to the
   work branch, re-reading every changed file first. Pushing or opening a PR
   is an authorization boundary — it travels with the rest of the run's work,
   or, for a standalone audit, ask before pushing. For **clean** or
   **blocked**: no commit; report the outcome and the coverage honestly.

Keep run notes (features covered, unreachable prerequisites, confirmed drift,
pruned features, product regressions, outcome) in the run ledger, not in the
repo.
