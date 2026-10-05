# Supplemental skill contract

Use a skill as methodology for one or several phases. Interpret its existing
instructions; do not require code entry points, custom metadata, or a wrapper.
The loop owns progression and completion; the adapter supplies domain methods.

## Establish fit

Resolve these questions from the skill and task context. A short task-local
note is enough when the mapping is not obvious.

| Concern | What to establish |
| --- | --- |
| Applicability | Capability supplied, intended situations, and exclusions |
| Phase contribution | PLAN, ACT, OBSERVE, VERIFY, and/or ADAPT |
| Inputs | Required artifacts, known state, assumptions, tools, and access |
| Method | Useful steps and decisions, scaled to this task |
| Evidence | Observable outputs, checks, and their limitations |
| Failure | Signals that require changing method, stopping, or escalating |
| Effects | Writes, external effects, and authorization needed |

For example, debugging may span all phases, while visual inspection may mainly
support OBSERVE and VERIFY. These are mappings, not a mandatory installed bundle.

## Select and compose

Search the available catalog by the capability gap, inspect candidates, and
prefer an existing applicable method. A matching name is insufficient; check
its prerequisites and evidence coverage. Search beyond the local catalog only
when an available discovery mechanism and task scope support doing so.

Assign each chosen method a purpose and useful output. Feed observed outputs
into the next method without promoting assumptions to facts. Load relevant
reference sections as needed rather than loading entire skill collections.

If methods disagree, follow governing instructions and user constraints. Resolve
ordinary methodological differences using task evidence. If mandatory gates
conflict and cannot be reconciled, stop the affected action and describe the
specific conflict. Do not use a new skill to route around permissions.

## Fill a real methodology gap

Invoke the separate skill creator with this brief:

```text
Missing capability:
Current task and phase(s):
Available inputs, tools, and authority:
Existing methods checked and why insufficient:
Required outputs and evidence:
Known failure modes and stopping conditions:
Scope: smallest useful method; provisional/task-local unless persistence is authorized.
```

Require the method to specify applicability, steps, observations, verification,
and adaptation/stop conditions. Do not embed task secrets or entire transcripts
in reusable instructions. Generated methodology is a hypothesis, not evidence.

Before use, inspect internal consistency, tool availability, constraints, and
reference integrity. Try it on a bounded part of the actual task or a reversible
representative case. Evaluate its output against independently defined acceptance
criteria, not just its own assertion of success. Refine if it fails.

If the creator is unavailable, record a short explicit method in working state
when the task is within competence. If method creation stalls, return to the
original task and assess what can be done directly; never recurse into creating
creators or let adapter development consume the delegated task.

Record demonstrated usefulness and limitations. Promote to a reusable installed
skill only when persistence is appropriate, authorized, and supported by the
host's management workflow. A single generated method is not automatically
approved for future unrelated tasks.

Before promotion, require successful use on several distinct occasions and a
recurring need beyond the original task. Retain brief evidence of which uses
worked, failures and revisions, and the method's applicability limits. Check for
overlap with existing skills; improve or merge an existing primitive when that
serves the need better. An agent may recognize recurring value without gaining
new authority to install it. Favor a small set of strong, composable methods;
do not promote duplicates, one-off task recipes, or success claims unsupported
by observed outcomes. The explicitly requested initial seed set bootstraps the
ecosystem; do not describe these new seeds as already proven by repeated use.
