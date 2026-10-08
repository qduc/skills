# First paired experiment — 8 October 2026 UTC

**The lab completed the task and retained reusable evidence, but this trial does not demonstrate a research-quality advantage over the simpler baseline.** Both answers were careful about confounds. The baseline found more directly relevant technical-research comparisons; the lab added a reproducible aggregate audit and a durable claim/evidence ledger.

Question: *What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?*

## Protocol

Two isolated agent contexts used the same inherited model and question. Neither saw the other's answer. The baseline received a strong evidence-oriented prompt and could use search without delegated workers or mandated critic stages. The lab followed plan → research → challenge → report through the ledger; it could refine within two cycles. The baseline was deliberately allowed to think carefully and consider counterevidence; a weak one-shot straw man would not answer the question.

Each arm had a cap of eight web calls, twelve submitted search queries, twelve page-open operations, ten minutes and no paid API. Calls can batch queries/pages; page operations include repeat reads and failed opens. The lab additionally allowed two local experiments and twelve request steps. Its actual experiment recomputed published arithmetic; it did not independently replicate an agent study. Reasoning tokens, temperature, host context overhead and billable inference costs were unavailable. Thus this is an equal-retrieval-cap comparison, **not an equal-token or equal-dollar experiment**.

[The rubric](evaluation-rubric.json) was frozen before the coordinator read either final answer. A separate model evaluator opened primary originals and adjudicated each submitted top-level claim. It was not blinded to arm labels; this is a provisional model audit rather than expert human ground truth. Detailed dispositions are in [adjudication.md](results/adjudication.md).

## Measured resources

| Measure | Single-model baseline | Autonomous lab |
|---|---:|---:|
| Completed | Yes | Yes |
| Elapsed seconds | 203.000 | 233.709 |
| Web calls | 8 | 5 |
| Search queries | 6 | 5 |
| Page-open operations | 12 | 12 |
| Original source URLs retained | 7 | 5 |
| Local aggregate experiments | 0 | 1 |
| User interventions after goal | 0 | 0 |
| Automated engineering repairs during arm | 0 | 1 |
| Paid API calls | 0 | 0 |
| Total inference cost in USD | Unavailable | Unavailable |

The lab was 30.709 seconds (15.1%) slower, with three fewer web calls. Its timestamp compatibility repair contributed a recovery span of at least 81.7 seconds while other work continued; subtracting that entire span would invent a clean-run time, so the measured time remains unchanged. Setup, baseline/lab launch, independent adjudication and engineering probes are outside per-arm elapsed metrics. Tool usage is not a proxy for dollar cost.

## Quality and useful findings

Both arms concluded that positive evidence is task-specific and does not establish universal equal-resource superiority of autonomous orchestration. They distinguished model/tool capability, training and inference expenditure from agent multiplicity. Neither treated an internal relative gain as an absolute percentage-point improvement.

The baseline's strongest addition was AutoScientists: a directly relevant biomedical-ML comparison with matched experimental hardware but unmatched model-token expense. It also found a controlled study of task-dependent scaling. The lab omitted those sources and emphasized BrowseComp, text-only equal-thinking-cap counterevidence and difficult scientific-literature retrieval. Its report and arithmetic audit add useful reliability cautions, but more process did not automatically find the strongest technical comparison.

| Audited measure | Baseline | Lab |
|---|---:|---:|
| Top-level claims supported in stated scope | 6/6 | 3/3 |
| Top-level claims contradicted | 0 | 0 |
| Contradiction rubric | 3/3 | 3/3 |
| Useful-findings rubric | 6/6 | 6/6 |
| Retained primary originals | 7 | 5 |

These are provisional source-audit ratings, not accuracy estimates for all possible claims. One baseline source was abstract-only: primary attribution without method verification.

Final rubric ratings and audited claim verdicts are recorded in [adjudication.json](results/adjudication.json). Top-level claim counts differ because the lab groups several observations into three claims; do not interpret a supported fraction or a larger claim count as a normalized quality score. Coarse rubric ties can conceal meaningful differences in coverage.

The autonomous aggregate audit checks published differences, a Wilson interval and paired table arithmetic. It does not establish causal architecture benefit, global statistical significance or a new scientific result. Source-level sampling, ground-truth errors, inference accounting and multiple comparisons remain limitations.

## Acceptance evidence

| Requirement | Outcome and evidence |
|---|---|
| Complete a real research task with minimal supervision | Completed both arms; zero additional user instructions; one lab engineering repair disclosed |
| Trace important factual claims | Claim/source mappings, opened-URL reservations, source locators, semantic review and independent source audit |
| Expose contradictions and uncertainty | Both reports distinguish positive findings, contrary results and resource/task mismatch |
| Respect budget and terminate | Lab recorded 4 requests, 5 web calls, 5 queries, 12 pages, 1 experiment within caps; probes reject exceeding, stale, negative and paid requests and expired runs |
| Reuse useful knowledge | Two reviewed supported claims promoted; real subsequent-run retrieval returns both as hints with provenance, without asserting new claims ([probe](results/knowledge-reuse.json)) |
| Measure whether autonomy improves outcomes | Working paired protocol and rubric; no demonstrated quality advantage in this trial; quality per dollar remains unmeasurable |

The budgets are enforced for protocol-mediated calls. The existing host is cooperative; this is not an OS sandbox or authoritative billing gate. The optional local driver adds bounded execution and process-group timeout for a preapproved executable, but only fixture adapters were available for that path.

## Reproducibility and artifacts

- [Baseline answer and metadata](results/baseline/final.json), [readable baseline](results/baseline/report.md).
- [Autonomous accepted event export](results/autonomous/final.json), [metrics](results/autonomous/metrics.json), [readable report](results/autonomous/report.md).
- [Reproducible arithmetic](results/autonomous/analysis.py), [outputs](results/autonomous/analysis-results.json).
- [Frozen rubric](evaluation-rubric.json), independent adjudication and [knowledge retrieval evidence](results/knowledge-reuse.json).

Use `replay.py` to reconstruct the accepted protocol offline. This checks serialization, gates and reuse; it is not a fresh research run. The live database and raw retrieval text remain local; the committed JSON records accepted evidence and actions without copying entire remote articles.

## Next discriminating experiment

Use several fresh technical tasks and repeated paired runs, with a frozen corpus/retriever where feasible. Compare a tuned single agent, single-agent self-critique, independent sampling plus selection, and the bounded lab. Keep model and tools fixed. Report both equal-total-cost and equal-wall-time analyses; include setup and tuning costs. Blind expert adjudicators should score evidence entailment, contradiction resolution, task completion and useful decisions. Do not add more workers until they show measurable benefit on independently decomposable tasks.
