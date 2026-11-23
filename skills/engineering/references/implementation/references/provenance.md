# Source influences

Inspected on 2026-10-05. These are design inputs, not runtime dependencies or
claims about popularity. The core is an original synthesis adapted to a
composable editing method.

| Primary source | Ideas adapted | Boundaries retained here |
| --- | --- | --- |
| [obra/superpowers: executing-plans](https://raw.githubusercontent.com/obra/superpowers/main/skills/executing-plans/SKILL.md) | Compare actual outputs with intended results; distinguish implementation errors from defects in supplied directions; support completion claims with observed evidence. | Do not inherit its mandatory TDD, worktree setup, ledger format, subagent review, branch finishing, or fixed execution workflow. The caller owns orchestration. |
| [Google Engineering Practices: Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) | Limit each change to a coherent purpose; include necessary consumers and related validation; separate unrelated restructuring; judge scope by comprehensibility rather than just size. | Do not impose numeric change-size rules or Google's test policy. Choose proportionate checks under the host's actual gates. |

The contract and phase mapping follow the existing local agentic-loop adapter
contract. Workspace preservation, authorization, and tool availability remain
governed by the host and current user task. No source is loaded automatically
when applying this skill.
