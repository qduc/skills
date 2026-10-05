# Escalation and handoff

Spend human attention on decisions that cannot responsibly be made within the
delegated authority. Treat the user's existing instruction and preferences as
authorization where applicable; do not ask again just because a method describes
an approval step. Preserve higher-priority requirements.

## Decide whether to escalate

| Situation | Response |
| --- | --- |
| Equivalent technical choices or reversible low-impact assumptions | Choose and proceed |
| First failure, missing adapter, or harder-than-expected task | Investigate and adapt |
| Material subjective choice with no usable preference | Present the concrete alternatives and ask for the choice |
| Conflicting requirements | Explain the conflict and ask which constraint may change |
| Necessary action outside granted authority | Prepare a reviewable result, then request that exact authorization |
| Missing access, credentials, or unavailable capability | Identify the prerequisite; complete independent work |
| Reasonable approaches exhausted or budget boundary reached | Present evidence, remaining options, and the recommended next decision |

Keep authorized independent work moving before returning a blocker. Do not ask
the user to perform investigation the agent can still do. Never substitute
fabricated observations when a required check is unavailable.

## Ask a bounded question

Present:

- **Current result:** completed parts and the unmet requirement.
- **Blocker:** the exact missing decision, access, or resource.
- **Evidence:** relevant observations and approaches already attempted.
- **Options:** realistic choices with meaningful tradeoffs.
- **Recommendation:** the preferred next step and why.
- **Needed from you:** one specific answer or authorization.

Include only fields that help the decision. Preserve the resumable next action
and remaining risk in working state. Do not label blocked work complete, imply
background work continues without a running mechanism, or broaden the requested
authorization to unrelated future actions.

After the answer arrives, update the contract and resume from the blocker.
Recheck only assumptions and evidence affected by the new decision.
