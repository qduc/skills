---
name: deep-module-review
description: Evaluate or improve the design of one software module or API, focusing on cohesion, information hiding, interface complexity, leakage, side effects, and caller burden. Use adversarial-review when reviewing a change to that module, slop-audit for repo-wide health audits, and proportionality-review only when the specific question is whether the design is overbuilt.
---

# Deep Module Review

**Goal:** a located verdict on whether one module hides substantial implementation complexity behind a clear, predictable interface, with the smallest useful boundary change.

A good deep module lets callers understand what it does, when and how to use it, and its important inputs, outputs, errors, and side effects, without understanding its internal mechanisms. Do not optimize merely for fewer methods or fewer lines of public API. Optimize for lower cognitive load, strong information hiding, coherent responsibility, and predictable behavior. The goal is not the smallest possible interface. The goal is the simplest interface that communicates all information callers need.

## Phases

Load [references/review-checklist.md](references/review-checklist.md) before phase 2. It holds the core distinction (deep / shallow / bad deep-looking), the full per-step lists, the Do/Don't lists, the 1–5 rubric, and the final checks. Every list item there must be considered.

1. **Responsibility.** State it in one sentence. If the sentence needs "and" to join unrelated jobs, flag a possible responsibility problem; do not split automatically.
2. **Caller knowledge.** List what a caller must know (checklist step 2) and classify each item as essential contract or hidden-worthy implementation detail.
3. **Inspect.** Work checklist steps 3–8: interface naming and flags, hidden behavior (money, deletion, messages, remote calls, background work, shared state, resources, expense, transactions), information hiding, leakage, cohesion, common operations. Record each issue with file:line.
4. **Propose and check.** Recommend the smallest useful design change first (checklist step 9). Do not recommend splitting solely to make classes smaller. Score the seven rubric categories and run the final checks. A score of 1 or 2 in predictability or cohesion is a serious design warning.

## Stop rules

- Do not equate a one-method API with depth, and do not hide destructive, expensive, remote, or externally visible effects.
- Do not review a change or diff here; that is adversarial-review. Do not audit the whole repo; that is slop-audit.
- If the module's source or callers are not available, stop and return `Insufficient context` with what is needed.
- Stop once all four phases are recorded; do not keep generating speculative redesigns.

**Done when** the verdict is chosen, every main risk cites file:line, all seven rubric scores are given, and the six final checks have yes/no answers.

## Evidence to report

Each risk and each "callers must know" item cites file:line in the module or a caller. Rubric scores cite the finding that justifies any score of 1–2. Self-assessment without a location is not evidence.

## Response format

```
### Verdict
Good deep module | Promising but leaky | Shallow module | Deep-looking but misleading | God module | Insufficient context
<two or three sentences>
### What callers must know
Essential contract: <items, file:line>
Leaked implementation knowledge: <items, file:line | none>
### Main risks
<highest impact first; correctness and predictability over style; file:line each | none>
### Recommended boundary
<what the module owns / what stays outside>
### Suggested interface
<concise code sketch when useful | not needed>
### Trade-offs
<complexity, flexibility, performance, migration, testing costs>
### Scores (1–5)
interface simplicity, functionality leverage, information hiding, predictability, cohesion, caller autonomy, leak resistance
### Final checks
<six yes/no answers>
```

Null case: verdict `Good deep module`, `Main risks: none material`, `Recommended boundary: unchanged`.
