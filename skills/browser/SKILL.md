---
name: browser
description: Verify user journeys and rendered browser behavior, or use the Playwright CLI to automate a browser and run or debug Playwright tests. Choose the relevant workflow and driver.
---

# Browser

Choose the workflow that fits the task and read its file before following it. Load additional workflows only when their distinct methods are needed; simple requests may not need a workflow. Paths in each workflow are relative to that workflow’s directory. The former skill names below identify workflows, not separately installed skills.

| Need | Workflow |
| --- | --- |
| Verify a user journey or rendered behavior in a real browser. | [browser-qa](references/browser-qa/workflow.md) |
| Drive Playwright from the CLI or run and debug Playwright tests. | [playwright-cli](references/playwright-cli/workflow.md) |

Browser QA defines the verification; Playwright CLI is an optional driver when suitable and available. Load both when needed. Respect the host’s browser and tool policies.

Names of related methods may appear in the workflow text: `engineering` contains investigation, debugging, implementation, testing, profiling, and bug-retro; `review` contains code-review, adversarial-review, deep-module-review, invariant-reviewer, proportionality-review, slop-audit, and finding-triage; `browser` contains browser-qa and playwright-cli; `skill-development` contains skill-creator and workflow-evolution. Load the named parent and method when needed.
