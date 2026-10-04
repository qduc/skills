---
name: deep-module-review
description: Evaluate or improve the design of one software module or API, focusing on cohesion, information hiding, interface complexity, leakage, side effects, and caller burden. Use adversarial-review when reviewing a change to that module, slop-audit for repo-wide health audits, and proportionality-review only when the specific question is whether the design is overbuilt.
---

# Deep Module Review

## Objective

Design modules that hide substantial implementation complexity behind a clear, predictable interface.

A good deep module lets callers understand:

- what the module does;
- when and how to use it;
- its important inputs, outputs, errors, and side effects;

without requiring them to understand its internal mechanisms.

Do not optimize merely for fewer methods or fewer lines of public API. Optimize for lower cognitive load, strong information hiding, coherent responsibility, and predictable behavior.

## Core distinction

Treat module depth as the relationship between interface complexity and useful functionality.

- A **deep module** provides substantial, coherent functionality through a comparatively simple interface.
- A **shallow module** adds an interface but hides little complexity.
- A **bad deep-looking module** has a tiny interface but obscures unrelated responsibilities, surprising side effects, or essential operational behavior.

The goal is not the smallest possible interface. The goal is the simplest interface that communicates all information callers need.

## Review workflow

When reviewing a module, proceed in this order.

### 1. State the module's responsibility

Describe its responsibility in one sentence.

If the sentence requires “and” to connect unrelated jobs, flag a possible responsibility problem. Do not split a module automatically; first determine whether the operations form one coherent abstraction.

### 2. Identify the caller's required knowledge

List what a caller must know to use the module correctly:

- domain concepts;
- configuration choices;
- ordering requirements;
- lifecycle or state rules;
- failure modes;
- performance constraints;
- external effects.

Classify each item as either essential contract information or an implementation detail that should be hidden.

### 3. Inspect the interface

Evaluate whether names, parameters, return values, and errors express domain intent.

Prefer:

```python
invoice_service.issue(invoice)
```

over mechanism-oriented interfaces such as:

```python
invoice_db.insert(row, table, shard)
```

unless the module is intentionally a low-level database abstraction.

Flag:

- generic verbs such as `run`, `execute`, `handle`, or `process` without a precise domain meaning;
- mode flags that radically change behavior;
- parameters exposing storage, caching, retry, sharding, or transport internals;
- catch-all payloads and action strings;
- required call sequences that callers must orchestrate manually.

### 4. Inspect hidden behavior

Determine all important consequences of a call.

A module may hide implementation mechanics, but it must not conceal contract-relevant behavior such as:

- charging money;
- deleting or irreversibly changing data;
- sending messages;
- making remote calls;
- starting background work;
- mutating shared state;
- acquiring long-lived resources;
- making expensive operations;
- changing transactional boundaries.

Require these consequences to be clear from naming, types, documentation, or the surrounding API design.

### 5. Check information hiding

Look for design decisions duplicated across callers, including:

- retry policy;
- cache invalidation;
- transaction management;
- serialization;
- storage layout;
- connection lifecycle;
- default configuration;
- sequencing of internal operations.

Move coherent, repeated decisions behind the module boundary when the module can own them safely.

### 6. Check abstraction leakage

Ask whether callers still need implementation knowledge to achieve correctness or acceptable performance.

Examples include requiring callers to know:

- database indexes;
- cache keys;
- internal partitions;
- connection-pool behavior;
- undocumented ordering rules;
- internal state transitions.

Not every performance characteristic can be hidden. Expose constraints that callers genuinely need, but avoid exposing the mechanism that creates them when a stable conceptual contract is possible.

### 7. Check cohesion

A simple interface does not justify unrelated behavior.

Flag modules that combine unrelated responsibilities merely to reduce method count. Distinguish a genuinely unified abstraction from a god object.

A module can be large internally and still be cohesive when all complexity serves one well-defined purpose.

### 8. Evaluate common operations

Common tasks should require minimal setup, sequencing, and policy decisions.

Prefer safe defaults and high-level operations. Keep advanced control available only when callers truly need it. Do not force every caller through a verbose builder or configuration surface for routine cases.

### 9. Propose improvements

Recommend the smallest useful design change first. Possible changes include:

- rename operations around domain intent;
- remove mechanism-oriented parameters;
- internalize repeated orchestration;
- make side effects explicit;
- replace boolean mode flags with separate operations or types;
- add safe defaults;
- split unrelated responsibilities;
- combine shallow pass-through layers;
- document unavoidable constraints.

Do not recommend splitting solely to make classes smaller. Splitting can create more shallow modules and increase total interface complexity.

## Do

- Hide decisions that callers should not need to make.
- Expose domain concepts rather than internal mechanisms.
- Make common operations straightforward.
- Use precise names that communicate intent.
- Keep the module's responsibility coherent.
- Make important side effects and failures predictable.
- Centralize repeated policy and orchestration.
- Provide safe defaults while allowing justified advanced use.
- Preserve invariants inside the module whenever possible.
- Prefer a few general-purpose operations over many special-case methods when the general operations remain clear.

## Don't

- Do not equate a one-method API with depth.
- Do not use a catch-all `execute(action, payload)` interface to conceal many unrelated operations.
- Do not hide destructive, expensive, remote, or externally visible effects.
- Do not leak storage, cache, transport, or deployment details without necessity.
- Do not make callers coordinate the module's internal workflow.
- Do not create pass-through wrappers that add naming and navigation cost without hiding complexity.
- Do not split cohesive logic into many tiny classes merely to reduce class size.
- Do not combine unrelated responsibilities into a god object.
- Do not make correctness depend on undocumented call ordering.
- Do not claim an abstraction is good merely because its implementation is complicated.

## Scoring rubric

Score each category from 1 to 5.

1. **Interface simplicity** — How much must callers learn?
2. **Functionality leverage** — How much coherent work does the module perform?
3. **Information hiding** — How many internal decisions remain internal?
4. **Predictability** — Are effects, failures, and costs understandable?
5. **Cohesion** — Does the module serve one recognizable purpose?
6. **Caller autonomy** — Can callers use it without manual orchestration?
7. **Leak resistance** — Can callers avoid depending on implementation details?

Interpret scores cautiously. A module is not good simply because its average is high. A score of 1 or 2 in predictability or cohesion is a serious design warning.

## Response format

When asked to review a module, return:

### Verdict

Choose one:

- Good deep module
- Promising but leaky
- Shallow module
- Deep-looking but misleading
- God module
- Insufficient context

Give a two- or three-sentence explanation.

### What callers must know

Separate essential contract knowledge from leaked implementation knowledge.

### Main risks

Identify the highest-impact issues, prioritizing correctness and predictability over style.

### Recommended boundary

Describe what the module should own and what should remain outside it.

### Suggested interface

Provide a concise code sketch when useful.

### Trade-offs

Note any complexity, flexibility, performance, migration, or testing costs introduced by the recommendation.

## Final checks

Before completing the review, verify:

- Can a new caller predict the important consequences without reading the implementation?
- Does the module hide mechanisms rather than hide meaning?
- Does every public operation belong to the same abstraction?
- Are common cases easy and safe?
- Are implementation decisions centralized rather than repeated by callers?
- Would splitting or merging reduce total cognitive load, not merely change file size?
