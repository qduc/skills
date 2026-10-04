# Skills

These are agent skills: procedures an agent can follow for a particular kind of work.

There is no installer. A skill is a directory under `skills/<name>/` with a `SKILL.md` file. Read that file. The `name` and `description` in the frontmatter say when the skill applies. The rest of the file is the procedure. A skill may also keep notes, scripts, or other files next to `SKILL.md`. Use those only when the procedure tells you to.

## Setup

The skills in this repository do not need to be installed. If you want the coordinator to look for outside engineering skills as well, run this once from the repository root:

```sh
python3 scripts/setup-protocols.py
```

That downloads two public collections into `.external/`, which git ignores. They are not part of the skills published here:

- [mattpocock/skills](https://github.com/mattpocock/skills) lands in `.external/mattpocock-skills/skills`
- [cursor/plugins](https://github.com/cursor/plugins) (`pstack/skills`) lands in `.external/cursor-plugins/pstack/skills`

The script records both directories in `.external/catalog.env`. If you skip the download, or remove `.external/`, the coordinator still works without them.

## Skills

- **adversarial-review** — Looks at one change or document, such as a pull request, spec, design, or plan, and reports concrete defects and gaps that the evidence supports.
- **bug-retro** — After a bug is fixed, turns that single fix into a lasting improvement for the whole class of bug.
- **coordinator** — Splits substantial work across bounded workers, then tracks dependencies, checks the results, and integrates them.
- **deep-module-review** — Judges one module or API for cohesion, what it hides, how heavy its interface is, what leaks out, and how much callers have to carry.
- **finding-triage** — Decides which review findings must be fixed, what each fix would cost, and whether to route, narrow, accept, or reject it.
- **herdr** — Inspects and coordinates Herdr workspaces, tabs, panes, terminals, and agents from the command line without disrupting work already running.
- **invariant-reviewer** — Looks for reachable failures and broken invariants in a design or implementation, and weighs how much complexity a proposed fix would add.
- **model-benchmark** — Measures coding models and agent harnesses on real engineering tasks from the term2 repository, including solve rates and blind grading of candidate diffs.
- **playwright-cli** — Drives a browser to interact with web pages and to run or work with Playwright tests.
- **proportionality-review** — Judges whether a proposal or design is more complex than the problem needs.
- **simplicity-architect** — Proposes software designs built on strong invariants and a small complexity budget, keeping edge cases from growing into extra defensive machinery.
- **skill-creator** — Creates and revises agent skills, and measures how well they perform, including tests and how accurately a description gets the skill selected.
- **slop-audit** — Surveys a whole repository for piled-up problems in design, correctness, tests, duplication, security, dependencies, and overbuilding, then ranks what to repair.
- **term2** — Starts, configures, and runs term2 for interactive coding sessions or one-shot command-line tasks.
- **workflow-evolution** — Improves an agent workflow by revising its skills through experiments backed by evidence, leaving the harness unchanged.
