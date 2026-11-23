# Methodology provenance

Inspect these sources when revisiting the method's rationale. Accessed 2026-10-05; these are mutable upstream documents. This skill is an original synthesis and an initial seed, not a claim of demonstrated effectiveness across repeated uses.

- [Anthropic webapp-testing skill](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md): adapted the reconnaissance-before-action pattern and browser observations. Did not adopt its mandatory Python/Playwright, server helper, headless Chromium, fixed-delay, or universal network-idle instructions; host capabilities and policy govern execution.
- [Playwright best practices](https://playwright.dev/docs/best-practices): adapted checks against rendered user outcomes, stable user-facing targets, scoped/reproducible conditions, and evidence beyond screenshots. Kept framework syntax and cross-browser expansion optional.
- [Playwright auto-waiting](https://playwright.dev/docs/actionability): adapted attention to unique, visible, stable, enabled, unobscured targets and bounded readiness checks. Do not assume every host supplies these checks automatically; use only its documented mechanisms.
- [Playwright Page API: waitForLoadState](https://playwright.dev/docs/api/class-page#page-wait-for-load-state): used its explicit warning against treating network-idle as testing readiness to resolve the conflict with the public skill's universal network-idle advice.
- [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing): adapted the limits of automated scans and the need to check interaction states; retained a small accessibility check rather than claiming a complete audit.

The scoped contract, authority boundaries, freshness rules, criterion verdicts, and handoff structure follow the existing agentic-loop supplemental-skill contract. Keep those boundaries when composing this primitive with another method.
