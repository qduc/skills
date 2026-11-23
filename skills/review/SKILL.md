---
name: review
description: Review pull requests, code changes, specifications, designs, modules, and whole repositories for defects, risks, complexity, or broken invariants; or triage review findings. Select the appropriate review method for the scope.
---

# Review

Choose the workflow that fits the task and read its file before following it. Load additional workflows only when their distinct methods are needed; simple requests may not need a workflow. Paths in each workflow are relative to that workflow’s directory. The former skill names below identify workflows, not separately installed skills.

| Need | Workflow |
| --- | --- |
| Review code changes, diffs, commits, and pull requests. | [code-review](references/code-review/workflow.md) |
| Find defects in a specific artifact, specification, design, or plan. | [adversarial-review](references/adversarial-review/workflow.md) |
| Evaluate one module or API for cohesion and interface design. | [deep-module-review](references/deep-module-review/workflow.md) |
| Stress-test reachable failures and broken invariants. | [invariant-reviewer](references/invariant-reviewer/workflow.md) |
| Assess whether a proposal is overbuilt or too complex. | [proportionality-review](references/proportionality-review/workflow.md) |
| Audit an entire repository and prioritize repairs. | [slop-audit](references/slop-audit/workflow.md) |
| Decide which review findings to fix, narrow, accept, or reject. | [finding-triage](references/finding-triage/workflow.md) |

Keep the scope of each method distinct. Triage can follow any review; load both when needed.

Names of related methods may appear in the workflow text: `engineering` contains investigation, debugging, implementation, testing, profiling, and bug-retro; `review` contains code-review, adversarial-review, deep-module-review, invariant-reviewer, proportionality-review, slop-audit, and finding-triage; `browser` contains browser-qa and playwright-cli; `skill-development` contains skill-creator and workflow-evolution. Load the named parent and method when needed.
