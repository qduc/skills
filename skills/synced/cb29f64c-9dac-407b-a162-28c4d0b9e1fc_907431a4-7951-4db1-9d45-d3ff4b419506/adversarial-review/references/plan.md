# Plans — review profile

Applies when the artifact is a project plan, migration plan, rollout/launch plan, incident remediation plan, or roadmap. Use alongside SKILL.md; do not restate its rules.

A plan's defects are steps that can't be executed as written, orderings that trap you, dependencies nobody controls, and missing answers to "what do we do when step N slips or fails."

## Reading order

1. The goal and the deadline/constraints.
2. The dependency structure: build the actual DAG of steps from the text, because the written order and the real order often differ — divergences between them are P3 findings.
3. Ownership: who does each step, and do they know.

## Persona focus adjustments

- **P1 Assumption Challenger:** availability of named people/teams (vacations, competing priorities); external parties assumed to respond on schedule; estimates assumed accurate with zero slack; environments/access assumed to exist ("deploy to staging" — is there a staging?); approvals assumed instant. Negate each: which single assumption failing sinks the deadline?
- **P2 Failure-Path Prober:** for each step: what if it slips 2x, fails outright, or half-completes? Is there a rollback, and is the rollback itself planned (a "revert the migration" step with no procedure is not a rollback)? Points of no return — are they marked, and is everything verified before crossing them? What is the plan's behavior on discovering mid-flight that a premise was wrong?
- **P3 Consistency Auditor:** step ordering vs. actual dependencies (step 4 needs step 6's output); resource totals vs. per-step allocations; deadline vs. sum of estimates on the critical path; plan text vs. any embedded timeline/Gantt; success criteria of the plan vs. what the final step actually delivers.
- **P4 Scope & Omission Detector:** goals with no step that produces them; missing verification steps (the plan ships but never checks it worked); missing communication steps (who tells customers/on-call/dependent teams); no owner on a step; missing "decide/check" gates before expensive commitments; absent contingency for the risk the owner said was most expensive (from intake).
- **P5 Adversary:** incentive analysis — which actor benefits from slipping, gaming a milestone metric, or quietly descoping? Milestones satisfiable in letter while defeating intent ("demo works" via hardcoding). External parties whose rational behavior differs from the plan's hopes. For migration plans: who is hurt by the change and what will they do about it?

## Evidence norms

Cite the step number/name for every finding. **Sequencing findings** must name both steps and the dependency direction. **Slack findings** must show the arithmetic (critical path sum vs. deadline). **Assumption findings** must name the assumption's owner — the person/team whose non-cooperation breaks it. Do not file "estimates might be wrong" without identifying a specific estimate and why it's implausible (comparable prior work, missing sub-tasks it must contain, etc.).

## Severity anchors

- **critical:** an unmarked point of no return with no rollback and no pre-verification; a circular or inverted dependency on the critical path; the critical path arithmetically exceeds a hard deadline; the plan as written cannot produce its stated goal.
- **high:** single point of failure (one person/party) on the critical path with no contingency; a rollback that is named but not actually executable; a step nobody owns on the critical path.
- **medium:** zero slack on a path with historically volatile estimates; missing verification after a risky step (recoverable, but late discovery is costly); communication gap likely to cause rework.
- **low:** off-critical-path step with a fixable gap and cheap recovery.

Reject: preferences about planning methodology or tooling, granularity opinions ("break this into smaller tasks") without a demonstrated failure the granularity causes, and demands for contingencies against risks below the owner's stated risk floor.

## Type-specific notes

- **Low-yield persona:** P5 can be low-yield on small internal plans with aligned actors — time-box it to a single incentive scan rather than skipping, since it's also the persona that catches metric gaming.
- **Migration plans:** P2 is the star. Insist on: dual-run or comparison verification, an executable rollback per phase, and an explicit point-of-no-return marker. Absence of any of these on a data migration is at least high.
- **Roadmaps** (low-detail, long-horizon): drop step-level P2 probing; focus P1 (assumptions about the future) and P3 (goal vs. sequencing contradictions). Say in Coverage that step-level analysis wasn't applicable.
