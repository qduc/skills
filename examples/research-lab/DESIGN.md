# Design, tradeoffs and failure record

## Reuse before building

Existing `agentic-loop` owns the delegated goal, `research` supplies source appraisal, `testing` and `code-review` supply engineering verification. The current Codex host already has model reasoning, isolated worker contexts, search and file tools. Reuse those. Term2 would be a plausible later host adapter, but changing its backend is unnecessary to answer this first question.

Compared alternatives:

| Option | Decision and tradeoff |
|---|---|
| A well-prompted single model with tools | Keep as the real baseline; already strong, cheapest operational path |
| Existing Agents SDK / managed hosted agents | Useful infrastructure, but adds deployment/provider configuration and billing to this experiment; not invoked |
| Coordinator with many research workers | Independent exploration can help, but context/compute grow and coordination can mask a weak comparator; defer |
| Existing host plus local transactional ledger | Chosen: source/claim mapping, observable progress, bounded passes, durable knowledge and minimal dependencies |
| A new general autonomy framework | Rejected: no demonstrated need; reusable observe/decide/act/verify/learn seams already exist in the skill |

A phase can include several contract operations. No six-agent bureaucracy. `run.py` is an optional local protocol driver, not an agent engine or billing gateway.

## Lessons applied

| Original source | Mechanism used here | Limit of the evidence |
|---|---|---|
| [OpenAI Harness Engineering, Feb 11 2026](https://openai.com/index/harness-engineering/) | Compact navigation, explicit evidence, inspectable logs, repository artifacts as durable knowledge | Engineering experience; not a controlled research-quality comparison |
| [OpenAI Agent Improvement Loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop) | Preserve failures and connect them to a reproducible regression probe and a bounded change | Proposed improvements must be verified; no automatic self-modification or permission expansion |
| [Anthropic Parallel Claudes, Feb 5 2026](https://www.anthropic.com/engineering/building-c-compiler) | Isolate independent experiment arms; use checks an agent can inspect; keep logs out of the decision brief | Shared bottlenecks do not become parallelizable by adding workers; compiler work is not evidence of equal-cost research superiority |
| [Anthropic Managed Agents, Apr 8 2026](https://www.anthropic.com/engineering/managed-agents) | Keep session storage independent of model context and tool execution; resume pending requests from durable state | Hosted production infrastructure is not recreated; local disk is durable only as far as its storage is durable |

## Failed approaches and observed defects

- **Repository destination discovery:** `qduc/skills` is accessible and contains the needed primitives, but its README says standalone publishing is retired and points to an agents repository. `qduc/agents` returned 404 and is absent from accessible repositories. Prepare an isolated draft PR in the accessible skills repository; do not merge or revive its publishing workflow. It can be moved to the canonical repo when access is supplied.
- **Timestamp hot edit during the live run:** observations recorded under the initial prototype lacked `observed_at`. A subsequent validator expected it and blocked a real research submission. The host reported the exact error; the transaction rolled back without losing its request or evidence. The fix recovers the original timestamp from the append-only observation event. A regression probe exercises the legacy shape. The lab run includes this delay and one engineering intervention; it must not be represented as untouched production software.
- **Whole-page logs in model context:** retrieval outputs are noisy. The live arm keeps compact inspected paraphrases and locators in results, with raw retrieval logs outside committed deliverables. Notes carry a digest for integrity; this is not proof of source authenticity or semantic support.
- **Limited retrieval budget:** inaccessible originals and repeated passage opens still consume budget. Retain their observation and downgrade missing evidence instead of manufacturing a citation or expanding limits.
- **Missing dollar accounting:** the current host exposes no token usage or billed cost. Quality per dollar cannot be calculated. No paid API was invoked; that is not a claim of zero total inference cost.

## Remaining limitations

This is a working host-driven vertical slice. It needs an existing tool-using agent; Python alone does not reason or search. The optional unattended driver is tested with local fixtures, not a real external model CLI. Research quality depends on semantic appraisal, which remains model-generated. The ledger verifies structure and provenance references, not truth.

Permissions/tool budgets are cooperative at this layer. Production enforcement needs the existing host's trusted gateway, accurate token/tool accounting and cancellation. No payment-capable adapter exists; nonzero paid budgets and reservations are rejected. External experiment code is never executed by the ledger. A host's local calculation is recorded with method and observed result; it is not a reproduction of all published research.

Each investigation uses a separate SQLite database; cross-investigation knowledge is explicitly imported and retrieved as hints. Knowledge remains dated and scoped; semantic similarity ranking and automatic refreshing are deferred. No publishing, business-discovery or development applications are built. Failure lessons are proposals plus regression evidence, not self-granted permission to modify arbitrary infrastructure.

One live paired question is exploratory. Equal query/open caps do not imply equal thinking tokens, search corpus, or total cost. Scores are model-judged, not an independent human ground truth. Repeated blinded tasks with matched models, retrievers and resource envelopes are needed before claiming superiority.
