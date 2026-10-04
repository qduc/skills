---
name: adversarial-review
description: Multi-persona adversarial review for software artifacts — code changes, specifications, plans, and architecture/designs. Use whenever the user asks to review, critique, red-team, sanity-check, find problems in, or poke holes in a PR, diff, spec, design doc, RFC, project plan, or architecture — even if they don't say "adversarial" or "review" (e.g. "what's wrong with this plan", "would this survive production", "tear this apart"). Also use before approving or finalizing any such artifact when the user asks for a go/no-go opinion. Do NOT use for style-only feedback requests or writing improvement; this skill hunts real defects.
---

# Adversarial Review

A structured multi-persona review that finds **real defects** in software artifacts. It optimizes for true positives, not volume of criticism. A review that finds nothing material and says so clearly is a successful review.

## Non-negotiable principles

1. **No performative hostility.** Personas are lenses, not characters. Never manufacture outrage, snark, or concern-for-its-own-sake.
2. **No fabricated or speculative findings.** Every finding must trace to concrete evidence in the artifact (a line, a requirement, a stated assumption, or a provable omission). "This might have issues" is not a finding.
3. **No stylistic nitpicks.** Naming, formatting, phrasing, and taste are out of scope unless they cause a real defect (e.g., a misleading name that already caused a contradiction elsewhere in the artifact).
4. **Smallest practical correction.** Every accepted finding proposes the minimal change that removes the failure scenario — never a rewrite when a one-line fix works.
5. **The null result is legitimate.** If the review finds no material issues, say exactly that, list what was checked, and stop. Do not pad.

## Workflow

### Stage 0 — Intake and routing

1. Identify the target artifact(s) and classify each as one of: **code**, **spec**, **plan**, **architecture**.
   - Mixed targets (e.g., a PR containing both code and a design doc change): treat as separate artifacts, each reviewed with its own reference profile. Pick the dominant one first if budget is tight, and say which one you deprioritized.
2. Read the matching reference file **before** running personas:
   - Code → `references/code.md`
   - Specification / requirements → `references/spec.md`
   - Plan / roadmap / migration plan → `references/plan.md`
   - Architecture / system design → `references/architecture.md`
   Load only the file(s) for the artifact type(s) actually present.
3. Gather required inputs (see Inputs below). If a critical input is missing, ask for it or state the assumption you are forced to make — assumptions made at intake must be listed in the final report.
4. Set the review budget (see Depth/cost/risk below) and state it in one line at the top of your work.

### Stage 1 — Independent persona passes

Run each persona as a separate, self-contained pass over the artifact.

- **If subagents are available** (Claude Code / Cowork): spawn one subagent per persona. Give each subagent ONLY: the artifact, the persona's charter from this file, the relevant reference file's section for that persona, and the output schema for raw findings. Do **not** share other personas' findings, the implementer's rationale beyond the artifact itself, or your own preliminary opinions. This is the strongest anchoring defense available — use it when you can.
- **If subagents are not available** (claude.ai chat): run the passes sequentially in one context, but enforce discipline: complete each persona's pass and record its raw findings **before** starting the next; do not revise an earlier persona's findings while running a later one; when starting a persona, re-read its charter and deliberately set aside prior passes' conclusions. Acknowledge in the final report that passes were sequential, not independent.

**Anti-anchoring rules (all modes):**
- Personas review the artifact, not the author's narrative. Commit messages, PR descriptions, and doc intros are claims to be verified, not context to be inherited. Where the artifact asserts "X is handled," the persona must find where and how, or file a finding.
- Each persona must, before scanning, write down the top 3 unstated assumptions the implementer appears to be making, then test the artifact against the negation of each.
- Personas stop at their stopping condition (below), not when they "feel done" and not when they hit a target finding count. Zero raw findings from a persona is an acceptable outcome.

### Stage 2 — Judge: merge, dedupe, filter

A final judge pass (you, wearing only this hat) processes all raw findings:

1. **Deduplicate.** Findings pointing at the same root cause merge into one, keeping the strongest evidence and the union of affected locations.
2. **Reject** any finding that fails an acceptance rule (below). Rejections are silent — do not pad the report with a list of rejected findings unless the user asks.
3. **Assign severity and confidence** using the rubric below plus the artifact-type anchors in the reference file.
4. **Resolve disagreements.** When two personas conflict:
   - Prefer the finding with stronger evidence (direct citation beats inference; demonstrated failure scenario beats hypothetical).
   - If evidence is equal and the conflict is severity, report the lower severity and note the disagreement in one sentence.
   - If evidence is equal and the conflict is substance (one says defect, one says intended behavior), report it as a single finding at confidence "low", framed as a question to the author, only if it would be at least severity "medium" if true. Otherwise drop it.
5. **Rank** accepted findings by severity, then confidence.

### Stage 3 — Report

Emit the output schema below. Then stop. Do not append general advice, praise padding, or "other things you might consider" unless asked.

## Inputs

Required:
- The artifact itself (diff, file(s), document, or plan text).

Strongly recommended (ask if absent, proceed with stated assumptions if unavailable):
- The artifact's purpose or the requirement it serves (one sentence is enough).
- Constraints: runtime environment, scale, deadline, compliance requirements — whichever apply.
- For code: how it is invoked and by what.
- For plans/architecture: what failure would be most expensive to the owner.

Never required: the author's self-assessment. If provided, treat as claims to verify.

## Reviewer personas

Each persona has a **charter** (what it examines), an **evidence standard** (what it must produce to file a finding), and a **stopping condition** (when its pass is complete). Reference files adjust the charter's focus per artifact type; the standards and stopping conditions below always apply.

### P1 — Assumption Challenger
- **Charter:** Hunt unstated assumptions and test their negations. Inputs assumed valid, ordering assumed stable, resources assumed available, terms assumed defined, dependencies assumed reliable.
- **Evidence standard:** Must name the specific assumption, cite where the artifact depends on it, and describe one realistic circumstance where it fails.
- **Stopping condition:** The top-3 assumption list is exhausted and one systematic scan for further load-bearing assumptions found no new ones.

### P2 — Failure-Path Prober
- **Charter:** Error paths, edge inputs, partial failures, concurrency/timing, rollback and recovery. What happens when step N fails halfway.
- **Evidence standard:** A concrete triggering scenario (specific input, specific event sequence, or specific failure of a named dependency) plus the resulting observable damage.
- **Stopping condition:** Every externally-triggered operation and every stateful transition in the artifact has been walked through at least one failure scenario.

### P3 — Consistency Auditor
- **Charter:** Internal contradictions. Statement A vs statement B, interface vs implementation, plan step vs stated constraint, diagram vs text, declared invariant vs code path that violates it.
- **Evidence standard:** Both conflicting locations cited verbatim-adjacent (paraphrased with pointers), plus why they cannot both hold.
- **Stopping condition:** All declared invariants, interfaces, and constraints have been cross-checked against their usages.

### P4 — Scope & Omission Detector
- **Charter:** What's missing that the stated purpose requires. Unhandled requirements, absent migration/rollout steps, missing test or verification strategy, unaddressed stakeholders or integration points.
- **Evidence standard:** Must tie the omission to a stated purpose, requirement, or constraint of the artifact — not to the persona's personal wishlist. "It doesn't do X" is only a finding if the artifact's purpose implies X.
- **Stopping condition:** Every stated requirement/goal has been mapped to the part of the artifact that satisfies it (or filed as an omission).

### P5 — Adversary
- **Charter:** Deliberate misuse. Security, abuse, gaming of incentives, malicious or merely careless actors. For plans: how a rational actor's incentives break the plan. For code: untrusted input, privilege, injection, resource exhaustion.
- **Evidence standard:** A named attacker/actor class, their capability, the concrete action, and the harm. No "could be a security issue" without a path.
- **Stopping condition:** Every trust boundary and every external input surface in the artifact has been examined once.

**Persona selection:** All five run by default. Under a Light budget (below), run P1–P3 only and say so. The reference file may mark a persona as low-yield for that artifact type; you may then time-box it rather than skip it.

## Acceptance rules (judge applies to every finding)

A finding is accepted only if ALL hold:

1. **Located.** Names the affected file/line, section, requirement ID, step, or component. "Somewhere in the error handling" fails.
2. **Realistic failure scenario.** Describes a concrete, plausible sequence ending in observable harm (wrong output, data loss, outage, missed deadline, cost overrun, security breach, unbuildable design). Plausible means it can occur under the artifact's stated constraints — not "if the laws of the deployment environment were different."
3. **Material.** The harm matters at the artifact's stated scale and purpose. Theoretical perf issues on cold paths, style preferences, and harms below the owner's stated risk floor are rejected.
4. **Smallest fix proposed.** One suggested correction, sized to the defect.
5. **Not duplicate.** Root-cause distinct from every other accepted finding.
6. **Evidence-backed per the filing persona's standard.**

## Severity and confidence

Severity (use the artifact-type anchors in the reference file to calibrate; these are the generic tiers):
- **critical** — harm is severe and likely under normal operation: data loss/corruption, security breach, plan cannot succeed as written, system cannot meet a stated hard requirement.
- **high** — severe harm under realistic-but-not-guaranteed conditions, or moderate harm under normal operation.
- **medium** — real harm, but recoverable, rare, or limited in blast radius.
- **low** — genuine defect with minor consequence. (If you're reaching for "low" and it smells like a nitpick, reject it instead.)

Confidence:
- **high** — evidence is directly demonstrable from the artifact (the contradiction is on the page; the failing input is constructible).
- **medium** — requires one reasonable inference about unstated behavior or environment.
- **low** — depends on facts the review couldn't verify; must be phrased as a verification question to the author. Low-confidence findings below medium severity are dropped.

## Depth, cost, and risk

Choose and state one budget at intake:

- **Light** (small change, low blast radius, reversible): P1–P3, single pass each, judge inline. Target: minutes of work.
- **Standard** (default): all five personas, full workflow.
- **Deep** (irreversible decisions, security-sensitive, high cost of failure, pre-launch): all personas + a second P2/P5 pass focused on the top-3 highest-risk components identified in the first pass.

Escalate one level if the artifact is irreversible after adoption (public API, data migration, published commitment). De-escalate only if the user says the stakes are low.

## When to conclude "no material issue"

Conclude a clean pass when: every persona reached its stopping condition, the judge accepted zero findings at medium or above, and any low findings were rejected as immaterial. Report format for this case: state the conclusion in one sentence, list the personas run and their coverage (what was checked), list intake assumptions, and stop. Never invent a finding to avoid an empty report.

## Output schema

```
# Adversarial Review: <artifact name>

**Artifact type:** code | spec | plan | architecture (one per artifact)
**Budget:** light | standard | deep — <one-line justification>
**Intake assumptions:** <bulleted, or "none">
**Verdict:** <one sentence: approve / approve-with-fixes / needs-rework / no material issues found>

## Findings
(ordered by severity desc, then confidence desc; omit section entirely if none)

### [SEV-<n>] <short title> — severity: <tier>, confidence: <tier>
- **Location:** <file:line / section / step / requirement>
- **Found by:** <persona(s)>
- **Failure scenario:** <concrete sequence → observable harm>
- **Evidence:** <citation/pointer into the artifact>
- **Smallest fix:** <minimal correction>
- **Disagreement note:** <only if personas conflicted>

## Coverage
<one line per persona: what it examined, stopping condition met or time-boxed>

## Open questions for the author
<only low-confidence, ≥medium-severity items phrased as questions; omit if none>
```

## Reference files

- `references/code.md` — persona focus, severity anchors, and evidence norms for code and diffs
- `references/spec.md` — same, for specifications and requirements docs
- `references/plan.md` — same, for project/migration/rollout plans
- `references/architecture.md` — same, for system designs and architecture docs

Schema and acceptance rules live only in this file. Reference files must never restate them.
