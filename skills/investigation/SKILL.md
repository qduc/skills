---
name: investigation
description: Gather traceable evidence to reduce uncertainty about an engineering system, repository, artifact, or reported behavior. Use for bounded unknowns such as locating ownership, mapping a data path, establishing actual configuration, assessing change scope, reconciling conflicting observations, or determining what evidence is missing before a decision. Supply evidence to debugging when a causal diagnosis is needed; leave external-source discovery and appraisal to research methods. Do not impose an investigation on a simple edit or already answered question.
---

# Investigation

Resolve the smallest engineering unknown that changes the next decision. Treat an investigation as an evidence-producing step, not a commitment to repair, explain every cause, or explore the whole system.

## Establish the question

Extract the decision being supported, the bounded question, relevant artifacts or systems, known observations, access, constraints, and an adequate answer threshold. Reuse existing task state. For example, establish which service writes a field before deciding where to modify it; do not expand automatically into why every downstream consumer behaves differently.

Identify what would change the decision and which uncertainties can remain. If context is incomplete, inspect available evidence and make reversible assumptions. Ask only when a missing answer materially determines scope or access; do not require a separate investigation approval.

Contribute to PLAN by selecting informative checks, ACT and OBSERVE by acquiring evidence, VERIFY by assessing the bounded answer, and ADAPT by identifying remaining gaps. Let the surrounding task own progression and overall completion.

## Acquire useful evidence

1. **Inventory the evidence already available.** Separate direct observations, reported observations, interpretations, and unknowns. Locate the relevant code, configuration, history, runtime state, logs, traces, or artifacts. Prefer the narrowest authoritative entry point for the question over broad repository exploration. Record source identity, version or revision, environment, identifier, and time window where these affect interpretation.
2. **Check that observations are comparable.** Verify paths, accounts, regions, deployments, units, clocks, filters, and versions before interpreting disagreement. Treat configuration as intended behavior until corroborated against actual state when runtime behavior matters. A command's output can still be incomplete, stale, sampled, or from the wrong target.
3. **Choose a discriminating check.** List the plausible answers or interpretations only as far as needed. State which observation would distinguish them and how the outcome would affect the next decision. Prefer a cheap targeted read or comparison with meaningful coverage. A search returning no matches establishes absence only within the searched scope and method.
4. **Observe and record.** Run the permitted check, retain a useful locator or reproducible query, and capture actual results separately from expectations. Record empty results, contradictions, and failed access attempts. Before an active probe, assess effects and preserve relevant evidence. Respect host tool policies and existing authority; the skill grants neither access nor permission to alter live systems.
5. **Update the answer.** Compare findings with alternatives, assess coverage and freshness, and identify the strongest supported conclusion. Look for one material counterexample or missing context that could overturn it. Use an independent source or targeted repeat only when it resolves a concrete reliability concern; duplicated reports of one observation are not independent corroboration.

## Return a usable handoff

Provide the bounded answer and its status: **supported**, **contradicted**, or **unresolved** relative to the stated question. Include decisive evidence locators, relevant observation conditions, what was inferred, coverage limitations, and the next useful check if needed. Use a small claim/evidence/limitation table for several findings; use prose for one. Extend an existing task record rather than creating a mandatory report.

Stop when evidence meets the answer threshold, even if unrelated unknowns remain. Reframe when checks cease reducing uncertainty or all listed alternatives fail. Stop the affected line when access, authority, capability, or the agreed budget prevents a useful check; preserve partial evidence and identify the specific missing input. Never turn an inaccessible source into a negative finding or manufacture certainty to close the task.

## Compose at a concrete gap

Pass observations to debugging for causal reproduction and isolation; to research for external knowledge or source appraisal; or to implementation and verification for corrective action and acceptance checks. Load another skill only when its capability is needed. Keep exploratory observations distinct from acceptance evidence unless their conditions satisfy the actual criterion.

Read [method provenance](references/sources.md) only for attribution or deeper rationale.
