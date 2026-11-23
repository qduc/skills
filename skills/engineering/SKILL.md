---
name: engineering
description: Investigate engineering systems, diagnose failures, implement changes, test behavior, and profile performance. Use for a bug retrospective when a bug is found, diagnosed, or fixed; after a non-trivial fix; or when an agent's defective behavior is corrected, to prevent recurrence. Select only the methods needed.
---

# Engineering

Choose the workflow that fits the task and read its file before following it. Load additional workflows only when their distinct methods are needed; simple requests may not need a workflow. Paths in each workflow are relative to that workflow’s directory. The former skill names below identify workflows, not separately installed skills.

| Need | Workflow |
| --- | --- |
| Gather traceable evidence about a system or repository. | [investigation](references/investigation/workflow.md) |
| Diagnose unexpected behavior with hypotheses and experiments. | [debugging](references/debugging/workflow.md) |
| Make an understood, bounded code change. | [implementation](references/implementation/workflow.md) |
| Choose or write proportionate automated behavioral tests. | [testing](references/testing/workflow.md) |
| Measure performance and verify optimizations. | [profiling](references/profiling/workflow.md) |
| Examine a found, diagnosed, or fixed bug, or corrected agent defect, and prevent its recurrence. | [bug-retro](references/bug-retro/workflow.md) |

Compose methods as needed: for example, investigate and debug before implementation, then test; use bug-retro when its conditions apply.

Names of related methods may appear in the workflow text: `engineering` contains investigation, debugging, implementation, testing, profiling, and bug-retro; `review` contains code-review, adversarial-review, deep-module-review, invariant-reviewer, proportionality-review, slop-audit, and finding-triage; `browser` contains browser-qa and playwright-cli; `skill-development` contains skill-creator and workflow-evolution. Load the named parent and method when needed.
