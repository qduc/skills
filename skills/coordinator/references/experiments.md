# Candidate experiments

Not applied. Each item is one workflow-evolution candidate: freeze the
incumbent skill, change one behavior, run the same tasks, and promote only on
an external signal. Coordinator prose is not the score. Preservation gate:
`evals/evals.json` entries 1–3 still pass. The wake-sweep, live-worktree, and
pre-existing-gate evals are preservation checks for rules already in the skill,
not scores for the mutations below.

## Dispatch pre-mortem

- **Hypothesis:** A brief pre-mortem before a large dispatch surfaces shared
  assumptions and failure paths early enough to reduce rework.
- **Mutation:** Before the first large wave, ask "assume this failed; why?"
  Record the strongest plausible causes, evidence needed, and any resulting
  change to sequencing or verification in task state.
- **Metric:** Invalidating surprises found before dependent work starts, and
  avoidable rework versus comparable dispatches without the pre-mortem.
- **Comparable tasks:** Similar multi-outcome tasks, with and without a recorded
  pre-mortem.

## Paired coordination indicators

- **Hypothesis:** Pairing a speed indicator with a quality indicator prevents
  optimizing dispatch or integration speed at the expense of a working result.
- **Mutation:** For a coordination change, record one flow measure (for example
  dispatch-to-report time) and one quality measure (for example first-pass
  acceptance or post-merge defects); evaluate them together.
- **Metric:** Flow improvement with no quality regression on matched tasks.
- **Comparable tasks:** The same task class under incumbent and candidate
  workflow, with both indicators collected.

## Task-relevant brief detail

- **Hypothesis:** Matching brief detail to demonstrated task-specific worker
  capability reduces clarification without overconstraining capable workers.
- **Mutation:** For workers within one demonstrated capability tier on a task
  type, compare a detailed procedural brief with a concise outcome brief; keep
  scope, criteria, and authority explicit in both.
- **Metric:** Rework and clarification rate, plus deviations from the contract.
- **Comparable tasks:** Matched repetitions of one task type with detailed and
  concise briefs at the same capability tier; capability evidence is recorded
  before dispatch so brief detail, not worker capability, is the only difference.

## Constraint-aware dispatch

- **Hypothesis:** Identifying the current coordination constraint before a wave
  reduces queued work that cannot be reviewed, merged, or admitted in time.
- **Mutation:** Record the binding capacity or serial gate (such as review
  attention, quota, or merge access), its available throughput, and the next
  work admitted only as capacity frees. Track the visible queue.
- **Metric:** Queue age and work waiting at the constraint, alongside total
  completion time and unutilized worker capacity.
- **Comparable tasks:** Similar multi-worker tasks with and without explicit
  constraint and queue tracking.

## Cost-of-delay ordering

- **Hypothesis:** Ordering otherwise-ready outcomes by the cost of delay delivers
  more value than treating every independent item as equally urgent.
- **Mutation:** Before a wave, estimate each ready outcome's delay cost and rank
  it alongside dependencies and risk; record the rationale and compare the
  resulting order with the incumbent priority method.
- **Metric:** Value delivered earlier and total completion time, with priority
  reversals and missed dependencies tracked.
- **Comparable tasks:** Matched multi-outcome plans with different delay costs
  and identical dependency constraints.

## Stall ledger

- **Hypothesis:** Three identical supervision snapshots are a stall, and
  replanning then beats another steer of the same brief.
- **Mutation:** At each fallback, resume, or inbox wake, record UTC time,
  lifecycle status, `approval_suspected`, newest report id, and artifact mtimes
  per worker. Increment `stall_count` when that tuple is unchanged. Above 2,
  replan with a new method or a fresh worker.
- **Metric:** Stalls caught before a person notices, and false stalls on a
  fixture whose artifact mtime changes.
- **Comparable tasks:** A tabletop where `agent_status` stays `working` and the
  pane shows an approval menu for three fallbacks.

## Follow-up command

- **Hypothesis:** A delivered worker can take a correction without a new pane
  and without marking the original dispatch not-delivered.
- **Mutation:** Add `follow-up` on `coord_lifecycle.py` for a settled or
  working worker whose dispatch is `delivered` and not retired. Store the new
  brief on the existing assignment, record `followup_id`, and steer with
  `--message-file`. The brief starts with the failed criterion, the evidence
  path, and one coordinator-written reflection.
- **Metric:** The correction round finishes without a new pane, and false
  `not-delivered` resolutions stay at zero.
- **Comparable tasks:** A lifecycle unit test where `follow-up` succeeds and a
  second `dispatch` still fails. Eval 2 names `follow-up` rather than
  `resolve-dispatch not-delivered`.

## Route card

- **Hypothesis:** A short per-harness card in the dispatch prompt cuts failure
  modes that today live only in the host inventory.
- **Mutation:** Keep a card of at most 15 lines per worker kind in the host
  inventory, dated with that file. `dispatch` appends the matching card to
  `dispatch.txt`.
- **Metric:** Hidden-test pass rate, and how often a trace calls a failing gate
  unrelated, on the same model with and without the card.
- **Comparable tasks:** model-benchmark `f-security-002-symlink-traversal`.
  A tabletop whose candidate dispatch text contains the card.

## Boundary smoke

- **Hypothesis:** Changes to processes, sockets, packaging, or persistence need
  a coordinator-run seam command before integration. Unit tests have passed on
  defects that command would catch.
- **Mutation:** Tag those work items `boundary`. Acceptance records a command
  the coordinator ran under `verification`, with exit status, distinct from the
  worker's unit tests. The pre-existing-gate rule already compares a red gate
  to the base branch; this mutation adds the seam command.
- **Metric:** On a fixture where unit tests pass, a hidden socket smoke fails,
  and the base branch is green, the smoke is recorded and the bad merge does
  not land.
- **Comparable tasks:** model-benchmark `r-ws-session-lifetime`.

## WIP cap

- **Hypothesis:** A cap of 2 concurrent modifying workers and 1 read-only
  reviewer per artifact cuts quota deaths without stretching integration by
  more than one item's duration.
- **Mutation:** Record `wip_limit` on the task before the first wave. Start the
  next wave when a slot frees.
- **Metric:** Max simultaneous modifying workers, and time-to-last-integration
  on a four-item board versus an uncapped run.
- **Comparable tasks:** A tabletop with four independent items and quota
  headroom for two.

## Mergeable stages

- **Hypothesis:** Requiring every stage of a staged plan to name an independent
  merge point that can land on main on its own limits branch bloat; when a new
  unknown blocks the final merge, splitting at the last green point delivers
  value early instead of widening the branch. Motivating incident: Henshin phase
  2 (`henshin-run-code`) accumulated 19 unmerged commits and 3.6k lines with a
  single end-merge before hitting an invalidating discovery.
- **Mutation:** Every stage of a staged plan names a merge point that can land
  on main on its own. When an unexpected blocker halts the active stage, split at
  the last green milestone instead of widening the branch.
- **Metric:** Unmerged commits/lines and age of the longest-lived branch per
  task; value that reaches main before the hardest step.
- **Comparable tasks:** A multi-stage feature task where the final stage hits a
  design blocker after earlier slices pass tests.

## Riskiest boundary first

- **Hypothesis:** Spiking the assumption most likely to invalidate the design
  against the real runtime before building dependent slices prevents compounding
  rework; stub-only green tests must be treated as "not proven". Motivating
  incident: Henshin phase 2 built six slices against a stub manager before a
  real-runner check showed foreground child approval returns `interrupted` and
  drops continuation.
- **Mutation:** Before building dependent slices, spike the assumption most
  likely to invalidate the design against the real runtime (not stubs), and
  treat stub-only green tests as "not proven".
- **Metric:** Slices built before the invalidating finding; rework after it.
- **Comparable tasks:** A multi-agent orchestration task with external harness
  boundaries where a stubbed harness masks runtime approval or interruption
  behavior.

## Outcome-independent decision review

- **Hypothesis:** When a result fails, reviewing the recorded decision against
  its contemporaneous evidence separates sound decisions with bad outcomes from
  process mistakes, so failed outcomes are not automatically judged errors.
- **Mutation:** When an outcome that depended on a recorded assumption or
  decision fails, review that decision against the evidence, alternatives, and
  uncertainty recorded at decision time before calling it a mistake, and record
  whether the process was sound.
- **Metric:** Proportion of failed-outcome decisions whose review distinguishes
  process-sound from process-error, and reversals of outcome-based verdicts on
  replay with the recorded rationale.
- **Comparable tasks:** Tasks with recorded material assumptions whose outcome
  later failed, with and without the review step.

## Recorded work-item DAG

- **Hypothesis:** When a staged task records its work items with `needs` edges
  at planning time (coord_state already validates `work_items.needs`), a shared
  root risk and the real done/total become visible early. Motivating incident:
  Henshin task e6b817b0 kept 4 flat, stale work items and no edges while about
  13 workers ran; six slices depended on one unproven approval assumption, and
  progress reports were estimates.
- **Mutation:** At planning and at each checkpoint, keep work_items as nodes
  with `needs` edges and real statuses; `coord_progress.py` renders done/total
  from them.
- **Metric:** How early a single-root risk is visible (nodes built on an
  unproven node); how often the progress % is a guess rather than a computed
  count.
- **Comparable tasks:** A staged coordination task with dependent work items
  where downstream slices depend on an unproven root node and progress is
  computed from the DAG.
