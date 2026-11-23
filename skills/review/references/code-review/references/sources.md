# Source provenance

Inspected on 2026-10-05. These are design inputs, not evidence that this skill is effective. Instructions are an original synthesis; source names, adoption, and popularity do not establish review quality.

| Primary source | Ideas adapted | Boundaries |
| --- | --- | --- |
| [Anthropic Claude Code code-review command](https://github.com/anthropics/claude-code/blob/main/plugins/code-review/commands/code-review.md) ([plain text](https://raw.githubusercontent.com/anthropics/claude-code/main/plugins/code-review/commands/code-review.md)) | Validate candidate bugs, filter false positives, avoid duplicate findings, locate evidence, and separate reporting from posting. | Do not copy mandatory agent counts, model choices, tool-success assumptions, draft-PR exclusion, or the rejection of all input-dependent failures. Prove realistic conditional failures instead. |
| [Google Engineering Practices: What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html) | Inspect behavior in system context, reason about concurrency and edge cases, assess whether test assertions detect failures, declare partial scope, and label optional style comments. | Scale the method to the caller's scope and risk. Do not impose Google's internal process, exhaustive style review, or mandatory tests for every change. |

The phase mapping and input/evidence/authorization boundary follow the local agentic-loop supplemental-skill contract. This review skill remains usable independently; it does not require that framework or add tool permissions.
