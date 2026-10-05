# Source provenance

Inspected on 2026-10-05. Use these links for background, not as runtime
prerequisites. The core is an original synthesis; no scripts or workflow were
copied. Source publication does not establish that this skill is proven effective.

- [Anthropic webapp-testing skill](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md): Actual existing agent skill with local application inspection, server lifecycle handling, browser actions, screenshots, and logs. Adapted the separation of observable interaction evidence from setup and lifecycle responsibilities. Kept browser-specific tooling out of this framework-neutral primitive; did not adopt its blanket network-idle or fixed-wait guidance.
- [Google Testing Blog: Test Behaviors, Not Methods](https://testing.googleblog.com/2014/04/testing-on-toilet-test-behaviors-not.html): Adapted focused behavior-oriented assertions rather than one test per method. Independent expected values and criterion mapping are synthesis choices.
- [Google Testing Blog: Hermetic Servers](https://testing.googleblog.com/2012/10/hermetic-servers.html): Adapted isolation, injected external boundaries, local fixtures, and useful tracing. Preserved the distinction between local evidence and production fidelity; did not prescribe an entire server stack for every test.
- [Playwright best practices](https://playwright.dev/docs/best-practices): Adapted independent test state, user-visible assertions, controlled third-party responses, and bounded condition waiting. Generalized these ideas beyond Playwright without asserting browser compatibility from unit tests.

Risk-based scope, stale-evidence handling, negative controls, mock limitations,
and the compact criterion handoff combine these ideas with the host's existing
verification contract. No universal test-level ratio or TDD requirement is
claimed by this synthesis.
