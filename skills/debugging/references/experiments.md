# Experiment selection and provenance

## Original examples

**Stale response:** A caller suspects either client caching or stale server state. Repeating the normal request does not distinguish them. Compare normal and cache-bypassing requests while checking the server's actual response and keeping identity and input stable. If both responses are stale, weaken the client-only explanation. If only the normal request is stale, support it, subject to whether the bypass changes routing or authentication. Check those confounders before attributing causality.

**Connection failure:** A successful network reachability check does not establish that application credentials work. Probe the relevant connection using the application's route and identity, with permitted diagnostic tools. Record which layer the result exercises; avoid declaring unrelated layers healthy.

**Intermittent slowdown:** One fast run after a change cannot establish a cause. Compare equivalent workloads and initial states over an observation window appropriate to the known variability. Check that diagnostic instrumentation does not materially alter timing. Report unresolved evidence when the available window is too short.

**Ineffective edit:** An unchanged symptom can weaken a hypothesis only if the changed artifact was loaded and the relevant path executed. First inspect those conditions. Distinguish an invalid experiment from a valid disconfirming result.

## Sources inspected

Inspected public source content on 2026-10-05. These are optional background sources; using this skill does not require loading them or importing their surrounding workflows.

- [obra/superpowers: systematic-debugging](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md), also inspected through its [raw source](https://raw.githubusercontent.com/obra/superpowers/main/skills/systematic-debugging/SKILL.md). Adapted explicit hypotheses, minimal diagnostic changes, and checking results before stacking changes. Omitted its complete fix workflow, universal sequencing, neighboring-skill requirements, and fixed failed-fix threshold.
- [Google SRE: Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/), Chris Jones, with the negative-results section by Randall Bosetti. Adapted observation versus controlled intervention, useful disconfirmation, probe relevance, and the distinction between probable causal factors and definitive causal proof. Retained room for authorized mitigation before full diagnosis.
- [The Debugging Book: Introduction to Debugging](https://www.debuggingbook.org/html/Intro_Debugging.html). Adapted predictions that distinguish likely explanations, explicit observation records, and hypothesis refinement or refutation. Kept this primitive separate from the chapter's subsequent repair process.

The core and examples are an original synthesis for composition with an outcome-owning caller. They are methodological guidance, not evidence that any particular diagnosis or intervention will succeed.
