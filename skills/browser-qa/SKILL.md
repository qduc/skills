---
name: browser-qa
description: Verify scoped user journeys and actual rendered behavior in a real browser. Use for UI acceptance checks, reproducing interface defects, or verifying a changed interaction, including relevant error, empty, loading, and accessibility behavior. Supply browser evidence to a larger workflow; exclude implementation, deployment, broad test-suite ownership, and a full accessibility audit.
---

# Browser QA

Produce current, reproducible evidence of what a user can actually do and observe. Contribute journey selection, browser observation, and acceptance verdicts to the caller's workflow; leave overall progression and completion to that workflow.

## Scope the check

Take the target URL or artifact, requested behavior, acceptance criteria, relevant changes, available data/account, and authorized effects from context. Define a small set of journeys: starting state, actions, expected visible result, and recovery. Distinguish specified requirements from reasonable assumptions. Ask only when a missing answer materially changes the check; perform useful authorized work first.

Prioritize the changed journey and affected adjacent behavior. Include happy, error, empty, and loading states where meaningful; record why a state is inapplicable or inaccessible. Select viewport, browser, and keyboard coverage by requirements and concrete risk. Do not expand into every page, browser, or test suite by default.

## Establish environment and authority

Record the current URL/environment, build or revision if available, browser/tool version if exposed, viewport, account role, fixtures, and observation time. Label unknown versions explicitly. Distinguish local, preview, staging, and production; verify that the intended build is served.

Follow the host's browser, API, connector, plugin, and authentication policies. Read the chosen tool's documentation before using it. Prefer supported connectors where required, but do not claim UI verification from connector responses alone. If a permitted browser is unavailable, report the missing evidence. Do not install another tool, probe sessions, bypass a sign-in wall, or invent APIs to evade host restrictions.

Verification grants no authority to send, purchase, delete, publish, or change another person's data. Use already authorized reversible test data and safe reads without needless approval. For an unauthorized consequential step, verify the reachable pre-submit behavior and identify the exact remaining gate.

## Observe, interact, and verify

Inspect the live rendered state before choosing a target. Prefer observed roles, accessible names, labels, or stable explicit identifiers; resolve ambiguous matches. When the host offers only visual interaction, use fresh observations and re-observe after layout changes. Avoid stale coordinates or selectors.

Use the host's supported readiness mechanism and bounded waits for the specific condition: actionable control, completed results, visible validation, or navigation. A fixed delay or network quiet alone does not prove readiness. Reinspect after a timeout; distinguish an obscuring overlay, wrong target, unavailable dependency, and product failure. Do not force interaction through disabled or covered controls to manufacture success.

Execute the journey through the UI. Check the actual result after each meaningful transition: displayed content, validation, selection, navigation, dismissal, or retained state. For relevant loading states, observe pending feedback and the eventual result. Exercise error recovery and empty-state next actions with permitted fixtures or controlled conditions. Never break a live service just to induce an error.

Pair screenshots for layout and visual defects with behavioral evidence such as an action/observation sequence, rendered text/state checks, or a supported trace. Screenshots alone cannot establish click behavior or persistence. Inspect relevant browser errors when available; correlate them with the observed journey rather than treating every console warning as a defect.

Check accessibility basics on touched controls: meaningful labels, keyboard reachability and operation, visible focus, dialog focus behavior, and understandable error feedback. Record checks that the tool cannot support. Do not infer full accessibility compliance from these checks or an automated scan.

## Return evidence and limits

Report PASS, FAIL, or UNCERTAIN per criterion with observed versus expected results. Include reproducible starting conditions, minimal steps, environment/time, and evidence references. Describe user impact; separate an observed symptom from an unproven cause.

Label mocked responses and fixtures. Mocked UI checks do not establish live integration; live observations do not establish all data conditions. Mark skipped coverage and access/tool limits explicitly. Invalidate affected evidence after changes to the build, configuration, data, or session and rerun only the necessary checks.

Do not silently fix code. Hand reproducible failures to debugging or implementation when authorized; stop once scoped criteria have current evidence or a specific blocker. Read [sources.md](references/sources.md) only for provenance and rationale.
