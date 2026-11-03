---
name: parity-rewrite
description: Run a rewrite, port, engine swap or large refactor that must keep user-visible behaviour identical to an existing system. Use when replacing an implementation behind an unchanged product, planning its verification and cutover, writing its acceptance criteria, or judging whether it is ready to replace the old one. Not for redesigns that intentionally change behaviour.
---

# Parity rewrite

**Goal:** the new implementation replaces the old one, and an end user sees no difference. Only the internals change.

The failure mode this skill exists for: weeks of green checks while the user-visible product drifted. In the term2 rewrite, a 98/98 e2e suite and 9/9 parity goldens stayed green while menus lost their styling, ten slash commands were invented, steering changed behaviour, and every keystroke read a 465 MB store. The owner found all of it within an hour of real use. Every check had compared the new system against itself.

## The oracle is the old system, bugs included

- **The old system's observable behaviour is the spec.** Design notes, contracts and tests written for the new system are not. Measure the old system directly, under identical conditions, before you port, match or remove anything.
- **A check that doesn't run the old system is a regression guard, not parity evidence.** Label it that way in every report.
- **Keep a closed list of accepted differences,** each with its source. "Better", "polish", "P3" or a tester's preference never adds to it. The only additions are differences forced by a scope decision the owner already made.
- **Any user-visible difference is at least P2.** Never file one as polish that doesn't block.
- **No new user-facing surface:** no command, key, flag, message or screen the old system lacks. Builders tend to expose their own internals (wire operations, debug commands) as user surface. Flag these for removal.

## Make parity executable, early

Build the differential harness before most porting, not at the end:
1. **Screens.** Drive both binaries with the same keystroke scripts, fake provider, fixture data and terminal size. Diff the rendered cells *including colours and attributes* (pyte works well for TUIs). Mask only volatile values, from one documented list.
2. **Surfaces.** Diff commands, keys, flags and help text in both directions. A one-way inventory taken from the old code can't see invented items.
3. **Effects.** For the same scripts, diff the files written, exit codes, stdout, persisted data and outbound requests.
4. **Speed.** Measure latency, CPU and output volume against the old system, never against an earlier build of the new one.
5. **Self-check.** The old system against itself must show zero differences, and the harness must catch a known injected difference.

The corpus is a walk of **every** reachable branch (each command, tab, picker, dialog, prompt and key), not a handful of named workflows.

## Test under real conditions

- **Realistic data.** Use a copy of real-sized stores and long sessions, not an empty temp dir. A per-render scan of the store was invisible with empty fixtures and caused 1 s key lag on the real one.
- **A real terminal or browser,** not just a pty. Have the new build used side by side with the old one by someone with no context: a fresh agent if the owner must not be a bottleneck. Agents doing their normal jobs on the new build count only as stability soak; they don't notice styling or lag.
- **The exact shipped artifact,** confirmed by its binary path and build identity in every report.

## Close work on evidence against the old system

- A user-visible job closes only on side-by-side evidence (screenshot pairs or a harness diff, with paths). "Shipped", a structural metric (for example "zero allowlist edges") or the builder's own e2e doesn't close it.
- Verifiers compare against the old system, not against the builder's claim.
- Hand reviewers the artifact and the old system first. Give them the builder's conclusions only afterwards.

## Keep verification continuous

Deferring checks to a late milestone was the costliest decision in the term2 rewrite. Cross-file bugs and parity drift piled up unseen. Compile and run the cheap guards on every commit. Run the differential harness on every candidate, and track its difference count like a burn-down.

## Supporting engineering rules

These came from the same rewrite; see references/evidence.md for the incidents.
- Tie every result to the exact commit and binary it ran on, and re-run after any move.
- Classify each red as product, fixture, harness or environment before changing product code.
- Make oracles able to fail: show red on the unfixed base, then green on the fix.
- Never weaken an assertion, golden or guard to reach green.
- When the new system can't do something yet, refuse explicitly ("unavailable"). Never fake success, zero or an invented value.
- Before a long-diverged merge, review every main-only change for fixes it would drop.
- Migrate user data copy-first with checksums. Never write the old store.

## Done

The new system is ready to replace the old one when all of these hold on one build:
- the harness shows zero differences outside the closed list;
- the effects and speed checks pass;
- a context-free side-by-side use in a real terminal or browser finds nothing new;
- the regression guards are green.
