---
name: skill-development
description: Create, revise, evaluate, and optimize agent skills, or improve agent workflows through evidence-backed experiments.
---

# Skill Development

Choose the workflow that fits the task and read its file before following it. Load additional workflows only when their distinct methods are needed; simple requests may not need a workflow. Paths in each workflow are relative to that workflow’s directory. The former skill names below identify workflows, not separately installed skills.

| Need | Workflow |
| --- | --- |
| Create, revise, evaluate, or optimize a skill. | [skill-creator](references/skill-creator/workflow.md) |
| Improve an agent workflow through evidence-backed experiments. | [workflow-evolution](references/workflow-evolution/workflow.md) |

Names of related methods may appear in the workflow text: `engineering` contains investigation, debugging, implementation, testing, profiling, and bug-retro; `review` contains code-review, adversarial-review, deep-module-review, invariant-reviewer, proportionality-review, slop-audit, and finding-triage; `browser` contains browser-qa and playwright-cli; `skill-development` contains skill-creator and workflow-evolution. Load the named parent and method when needed.
