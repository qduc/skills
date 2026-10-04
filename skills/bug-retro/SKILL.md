---
name: bug-retro
description: Post-fix retrospective that turns a single bug fix into a durable improvement for the whole class of bug. Use this whenever a bug has been found, diagnosed, or fixed — when a failing test goes green, a hotfix lands, a regression is resolved, or the user says "fixed it", "that was the bug", "ok it works now", "why did this happen", "post-mortem", "root cause", or asks how to stop a bug recurring. Also run it after YOU fix any non-trivial bug, even if the user only asked for the fix — the fix is the floor, not the deliverable. Do NOT use for feature requests or pure style refactors with no defect involved.
---

# Bug Retro

A fix removes one bug. A retro removes the *category*. The key question is not "why did this bug happen?" but **"why was this bug *possible*, and why wasn't it *caught*?"** — and then to leave behind an artifact (a type, a test, an assertion, a single source of truth) so the same shape of bug is measurably harder to write next time.

Don't teach every future contributor (human or agent) about every old bug. Change the environment so the old mistake stops being easy to make.

Keep it proportional. A one-line typo gets a three-line retro. A bug that took a day to find gets the full treatment. Never write more retro than the investigation deserved.

Not a blame exercise. The question is always "what about the system let this through", never "who let this through".

## Inputs

Gather these before triaging. If they're already in the conversation, don't re-ask; if a key one is missing, ask in one short message.

- What broke: observed vs expected behaviour, trigger, blast radius
- What the fix was (the diff, or a summary)
- How it was found (user report, test, monitoring, accident, review)
- How long it existed and how long it took to find — rough is fine
- **Where it came from**, if findable cheaply: the commit or PR that introduced it, or "latent — wrong since it was written". Use `git log -S`, `git blame`, or `git bisect` (bisect only if there's a reproducible failing test). Cap the effort at a few minutes; for a trivial bug, skip it.

## Step 1 — Triage: was this preventable?

Default to **preventable**. "Unpreventable" is a high bar and should be rare; most bugs that feel like bad luck are a missing invariant.

**Genuinely unpreventable** (or not worth preventing) — write a short note and stop:
- An external dependency changed behaviour without notice and there was no reasonable way to detect it in advance
- The requirement itself was wrong or changed after the code was written, and the code correctly implemented the old requirement
- Hardware / environment faults with no software signal
- The cost of preventing this class clearly exceeds the cost of it recurring — say this explicitly, with the reasoning

**Preventable** — continue. Signals:
- The bug lives entirely in code we control
- A test, type, lint rule, or assertion *could* have caught it, whether or not one existed
- This shape of bug has happened before in this codebase
- There was an invariant everyone "knew" but nothing enforced

Borderline → treat as preventable and let Step 3 decide whether prevention is worth the work.

## Step 2 — Root cause: what made it possible, what made it invisible

Work through three levels, in order:

```
Level 1 — Bug:             What broke? (symptom, trigger, blast radius)
Level 2 — Root cause:      Why did it break? (the local mechanism)
Level 3 — System weakness: What ALLOWED this class of breakage to exist,
                           and what let it go unnoticed?
```

Level 3 is where the leverage is. Stopping at Level 2 ("the null check was missing") is the most common failure of this skill.

### Level 3 checklist

Ask each of these about the root cause. **Skip none — write the answer down even if it's "N/A".** The point of writing N/A is that you had to actually check.

1. **Representability** — Why was the invalid state representable at all? Could a type, enum, newtype, non-nullable field, or constructor make it impossible to write?
2. **Single source of truth** — Did the same fact live in two places and drift (config vs code, cache vs DB, a duplicated constant, denormalised state)? Could one be derived from the other instead of copied?
3. **Boundary contract** — Did this cross a module/API/process boundary without an explicit contract (assertion, schema, validation, normalisation)?
4. **Implicit coupling** — Did a change in one place silently require a change in another, with nothing linking them (magic strings, ordering dependencies, "remember to also update X")?
5. **Wrong assumption** — What did the code assume about timing, ordering, uniqueness, encoding, timezone, concurrency, or environment that isn't actually guaranteed?
6. **Detection gap** — Why did no test catch it? Be specific about which of these it was:
   - no test covered this path at all
   - a test existed but mocked away exactly the thing that broke
   - a test existed but asserted the wrong thing, or too loosely
   - the suite doesn't run in the environment where the bug shows (integration gap, wrong config, wrong data shape)
   - the class isn't unit-testable and there's no integration/e2e/property layer for it
   Then: is the gap this one path, or a whole category of paths (all retry paths, all error paths, all concurrent paths)?
7. **Automation gap** — Could a lint rule, static check, type-checker setting, CI gate, or property test have flagged this mechanically instead of relying on a human noticing?
8. **Sibling paths** — Where else does the same pattern appear? **Grep for it.** List every sibling site. Each one gets checked *now*, not filed for later.
9. **Knowledge gap** — Did this survive review because nobody knew the invariant existed? Was it written down anywhere a reviewer would see it? If a careful reviewer genuinely couldn't have spotted it, say so — that's a signal the problem is structural, not attentional.
10. **Observability** — How long did it live undetected, and what would have surfaced it in minutes instead?
11. **Origin** — Is this a regression or a latent bug? They have different lessons:
    - **Regression** (the invariant held, then a change broke it): read that commit/PR. What was it *trying* to do — refactor, hotfix, rename, agent-written change? Did the tests pass at that commit? (If yes, the detection gap has a timestamp.) Did it touch some sibling sites but not others? Did the PR description or diff give a reviewer any realistic chance of catching it? Was the invariant stated anywhere the author would have seen it?
    - **Latent** (wrong from day one, or the invariant was never established): there's no change to learn from. The lesson is that this was never protected at all — the prevention is about establishing the invariant, not restoring it.
    The origin commit is evidence about what the *system* let through, not about the author. If a careful reviewer couldn't have caught it, say so — that's the finding.

Keep asking "and why was *that* the case?" until you hit something structural or the next "why" would be speculation. Usually two or three levels.

## Step 3 — Prevention: ship an artifact

The bar is a concrete artifact, not a resolution to be more careful. "Be careful" and "remember to check X" are not preventions. If the only honest answer is "be careful", say so plainly and mark the class as effectively unprevented.

Produce these, in priority order, going as deep as the codebase allows:

1. **The fix** for the immediate defect.
2. **A regression test** that fails without the fix and passes with it. This is the *floor*, not the finish line — it protects this exact bug, not the class.
3. **The sibling audit** from checklist item 8: every site checked, each one fixed or filed.
4. **At least one structural artifact** that makes the *class* harder to repeat. Prefer higher on this list — more leverage, less reliance on anyone remembering anything:
   - a type / schema / invariant that makes the invalid state unrepresentable
   - collapsing to a single source of truth (delete the duplicate, derive instead of copy)
   - a runtime assertion or schema check at the boundary that fails loudly
   - a lint rule, static check, or CI gate for the pattern
   - a property-based or category-covering test (all retry paths, not just this one)
   - observability so the next instance is found fast
   - if none of the above is feasible: the invariant written where the next person will actually see it (the module's docs or CLAUDE.md), stated as a rule — "X must survive Y" — so the knowledge doesn't live only in one head or one PR. This is a last resort and should usually accompany something above, not replace it.

If item 4 genuinely isn't worth it (trivial one-off, throwaway code), say so explicitly and why. Don't silently skip it.

Then be honest about scope. If the real fix is a refactor that's out of scope right now, say so, size it roughly, and separate "now" from "later". Don't let a big correct answer crowd out a small good one that can ship today.

If the codebase is available, *write* the test and the artifact as part of the retro rather than describing them. A retro that ends with a red-then-green test is worth ten that end with recommendations.

## Output

Report back in this shape, scaled to the bug:

```
## Retro: <one-line bug description>

Preventable:      yes / no / borderline — <one sentence why>
Bug:              <what broke, trigger, blast radius>
Origin:           regression in <commit/PR + what it was for> / latent / unknown
Root cause:       <the local mechanism>
System weakness:  <what made it possible + what made it invisible>
Fixed:            <patch + regression test>
Siblings:         <n sites checked, m fixed / filed>
Hardened:         <the structural artifact added, or why none>
Later:            <out-of-scope structural work, with rough size, if any>
```

For a trivial bug this collapses to three or four lines. For a serious one each line can be a paragraph. Never pad.

## Anti-patterns

- Stopping at Level 2 ("the null check was missing") when the real cause is Level 3 ("nothing guarantees this field is set")
- Recommending process ("add a checklist item") when a mechanism (type, test, assertion) is available
- Skipping checklist items instead of writing N/A
- Listing sibling sites without checking them
- Writing a long retro for a small bug
- Marking a bug unpreventable to skip the work
- Naming the origin commit's author as the finding, or spending twenty minutes bisecting a typo
- Producing only a regression test and calling the class handled
