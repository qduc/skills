---
name: coordinator-setup
description: Discover and configure the host for the coordinator skill. Use on first coordinator use, when its host profile is missing, or when changing machines, harnesses, adapters, or installed method catalogs.
---

# Coordinator setup

Configure the host, not the coordinator's instructions. Keep machine facts in
one external host profile; never generate or rewrite a host-specific base skill.
Discovery does not grant authority to use a model, install software, publish,
or change system settings.

## 1. Discover

Run `python3 <setup-skill-dir>/scripts/host_profile.py discover`. This read-only
probe reports platform, Python, executable locations, and platform prerequisites.
An executable on PATH is not proof of a working adapter or available provider.
Inspect the current harness's native worker tools separately: dispatch, return
channel, observation, correction, and stop support. Mark unexposed operations
unavailable rather than inventing commands.

The helper's executable list is a starting point, not a supported-product list.
Discover unfamiliar harnesses, aliases, and catalog locations from the current
host's tool definitions, installed help, and configuration. Judge routes by
capabilities and evidence rather than product names.

The base's bundled task state requires Unix `fcntl`. Its process runtime requires
Linux `/proc` and process groups. On unsupported platforms, record the limitation;
do not run that runtime. Native host tools do not remove the task-state requirement.

## 2. Configure selected capabilities

Read [Adapters](references/adapters.md) only for the selected branch. Probe its
installed help and a bounded read-only operation before recording it as verified.
For native tools, record exposed operation names and evidence from this session;
their availability must be rediscovered in a different harness session.

When standard discovery does not establish a usable route, adapt:

1. Name the missing capability and the evidence needed to establish it.
2. Inspect supported host interfaces and identify the simplest existing route.
   Prefer native tools or a configured adapter over inventing a new abstraction.
3. Run the smallest reversible, bounded probe that can resolve the uncertainty.
   Start with read-only checks. A live worker probe needs an authorized selected
   model, a narrow assignment, an observable return channel, and owned cleanup.
   If that authority is absent, record execution as unverified rather than launch.
4. Record observed capabilities, limitations, and the next revalidation trigger.
   If the route needs new adapter code or changed coordinator semantics, separate
   that implementation from configuration and report the prerequisite.

Executable discovery, transport acceptance, worker admission, completion, and
verified output are distinct evidence. Verify required observation, recovery,
and cleanup operations before calling a route usable. Missing optional correction
support can be recorded as a limitation; missing a capability required by the
requested task blocks that route. Preserve `unknown` when a bounded probe is
inconclusive; timeouts do not prove non-delivery or authorize replacement workers.
Use the evidence to settle observable questions; ask the user only for a material
preference or authority decision that inspection cannot resolve.

Record catalog directories only when they exist. Download optional catalogs with
the package's `scripts/setup-protocols.sh` when installation is requested; otherwise
leave absent catalogs unavailable. Keep shell startup files unchanged unless
explicitly requested. Generate environment configuration per installation.

Keep credentials, account details, model selections, and task authority out of
the profile. Record available model information as discovery evidence only;
the coordinator's per-task selection gate still applies. Keep the memory sidecar
disabled: the shipped implementation is not a safe portable integration.

## 3. Save and verify

Read [Host profile](../coordinator/references/host-profile.md) for the location and
schema. Construct a JSON profile from the discovery result, adding verified
adapters and catalogs. Write it through the editing tool outside the skill package.
Review an existing profile before replacing it; preserve valid unrelated adapter
entries and explain changed or retired capabilities. Re-run probes after tool,
platform, or harness changes. Configuration is evidence, not executable code.

Run `host_profile.py show` to validate and read the saved profile. Smoke-test the
selected coordinator route without launching an unsolicited worker. Report the
profile path, verified capabilities, unavailable capabilities, and limitations.
Setup is complete when the requested route has supported operations and verified
prerequisites. Otherwise report setup as blocked or partial with an exact unresolved
prerequisite; recording a blocker is not successful setup. Retain concise results,
not speculative commands or an investigation transcript, in the profile.
