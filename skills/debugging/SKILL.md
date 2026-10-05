---
name: debugging
description: Test causal explanations for unexpected behavior through hypotheses, discriminating experiments, and model updates. Use when a failure, contradiction, intermittent symptom, or ineffective change needs an explanation, or when selecting the next diagnostic experiment. Supply a bounded reasoning primitive within a larger task; do not substitute for broad investigation, implementation, regression testing, or incident management.
---

# Debugging

Turn an unexplained observation into a better causal model. Contribute to **PLAN** by choosing a discriminating experiment, **ACT** by running it within authority, **OBSERVE/VERIFY** by evaluating its actual effect, and **ADAPT** by revising explanations. Let the caller own task progression and completion.

## Establish the local question

Take the expected behavior, observed deviation, relevant artifacts, available explanations, and task limits as inputs. Reuse the caller's evidence and working record. Identify the exact uncertainty this invocation should reduce; for example, whether a stale value originates before or after a cache boundary.

Check whether the observations actually support the reported symptom. Record a reproducible trigger when available: input, commands or actions, version, configuration, relevant initial state, and observed output. For intermittent behavior, record conditions, frequency, and observation window rather than inventing a deterministic reproducer. Keep sensitive material protected under host policy.

If the expected behavior is ambiguous or the symptom lacks usable evidence, return the specific missing observation to investigation. Gather a small prerequisite observation directly when practical; avoid turning this primitive into an unrestricted search.

## Form an explanation and prediction

State a falsifiable mechanism: **under conditions C, factor X produces deviation Y through mechanism M**. Separate observed facts from assumptions. Consider the strongest plausible alternative, including a faulty observation or experimental setup when relevant; avoid padding a list with implausible possibilities.

Before acting, write what each explanation predicts and what outcome would weaken it. Prefer a probe whose possible results separate explanations. A result every candidate predicts teaches little. Rank probes by expected information, cost, risk, and relevance; use a cheap observation before an invasive intervention when it answers the same question.

## Run a bounded experiment

Choose a read-only probe, controlled input, boundary trace, working/failing comparison, bisection, or reversible intervention appropriate to the question. Keep other relevant conditions stable where feasible. If several factors must vary, make their effects distinguishable and record the confounding limits.

Specify the measured signal, baseline or control, and interpretation before running. Confirm the probe reaches the suspected path and can detect the predicted effect. Bound duration, resources, and affected scope to the task. Honor existing authorization and host policy; this skill supplies no new permissions.

Record what actually ran, any changed state, and enough setup to repeat it. Inspect actual outputs and side effects. A successful command, log marker, or changed configuration alone does not show that the intended experimental condition occurred. Restore temporary interventions when appropriate; preserve useful evidence and identify anything left changed.

## Update the model

Compare observations with the predictions. Label the explanation **supported**, **weakened**, or **unresolved**, with the reason and limits. Treat a negative result as evidence only if the probe was valid and exercised the relevant conditions. Do not reinterpret the prediction after seeing the result; record a revised hypothesis explicitly.

Distinguish evidence for a cause from evidence that a workaround suppresses its symptom. Improvement after a change may reflect timing, another changed factor, or bypassed behavior. Strengthen causal claims through a mechanism trace, counterexample, control, or safe reversal when needed and proportionate. Preserve uncertainty about interacting causes and untested conditions.

## Return or continue deliberately

Return a compact handoff: question, hypothesis and alternative, predicted versus observed result, evidence location and reproduction details, model update, residual uncertainty, and next useful step. Use the existing record rather than requiring a new file or rigid template.

Stop when this question is sufficiently resolved for the next decision, or when authority, access, observability, or the caller's budget prevents a useful experiment. Continue only when another probe has a concrete reason to reduce uncertainty; change the method if results remain non-discriminating. Do not impose a universal retry count or claim that the overall bug is fixed.

Pass broader evidence collection to investigation, corrective changes to implementation, and acceptance or regression checks to testing. Keep necessary experimental edits bounded. Read [experiment examples and sources](references/experiments.md) only for help choosing a probe or reviewing methodological provenance.
