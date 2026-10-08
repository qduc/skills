## Answer

The evidence that autonomous research agents beat a single model is strong when the baseline is a single non-agentic model. OpenAI's Deep Research scored 51.5% on BrowseComp against 9.9% for o1, and 26.6% on Humanity's Last Exam against 13.0% for o3-mini-high. Anthropic reports its multi-agent system beat a single-agent Opus 4 by 90.2% on an internal research eval. The evidence is weak, and partly negative, when the comparison is a single well-prompted model given the same tools and compute. Token usage alone explains 80% of BrowseComp variance. Compute-matched studies find single agents match or beat multi-agent systems. Simple baselines match complex agents on coding benchmarks. On long-horizon research-engineering tasks, agents still trail human experts once humans get more than a few hours. Overall confidence: medium. The headline gains are real, but they come mostly from extra compute and tool access, not from autonomy or architecture itself.

## Findings

**C1 (supported, medium).** Anthropic's multi-agent system (Opus 4 lead with Sonnet 4 subagents) beat single-agent Opus 4 by 90.2% on an internal research eval. That eval is not public. The comparison is also not compute-matched: multi-agent uses about 15x the tokens of a chat, against about 4x for a single agent, so roughly 3.75x more per task. Kim et al. found gains of up to +80.8% on decomposable tasks, which fits breadth-heavy research benefiting from parallelism. Compute-matched studies point the other way.

**C2 (supported, high).** On public hard benchmarks, agentic deep research scores far above the same vendor's non-agentic models. On BrowseComp it is 5.2x o1 and 27x GPT-4o with browsing. On HLE it is 2x o3-mini-high. The caveats: the vendor ran these evals itself, the agent had tools the baselines lacked, and the HLE baselines were partly scored on a text-only subset. DeepTRACE adds that deep-research outputs still contain many unsupported statements, with citation accuracy of 40-80% depending on the system.

**C3 (supported, medium).** Much of the measured advantage tracks compute. Anthropic attributes 80% of BrowseComp variance to token usage alone, and the BrowseComp paper shows smooth scaling with test-time compute. Tran & Kiela (2026) find the reported advantages of multi-agent systems "better explained by unaccounted computation". An equal-inference-cost preprint finds no significant multi-agent benefit. A counter-search turned up no compute-matched study showing architecture gains on hard research tasks.

**C4 (supported, medium).** When cost is controlled, simple baselines often match complex agents. AI Agents That Matter found that "SOTA" HumanEval agents do not beat simple baselines, and its escalation strategy beat LDB at under half the cost. Agentless beat open-source SWE agents on SWE-bench Lite at $0.70 per issue. Single agents match multi-agent systems on multi-hop reasoning at equal thinking tokens. All of this comes from coding and QA tasks, not open-ended research.

**C5 (supported, high).** Agents do not yet beat skilled humans on longer research tasks. On RE-Bench, agents scored 4x humans at a 2-hour budget, but humans edged ahead at 8 hours and scored 2x the agents at 32 hours. On PaperBench, the best agent reached 21.0% replication and did not beat ML PhDs. Both results come from 2024-2025 models.

**C6 (supported, medium).** Multi-agent gains are often minimal and fail in systematic ways. MAST catalogs 14 failure modes across more than 1,600 traces from 7 frameworks. Kim et al. measured anywhere from -70% to +80.8% versus a single agent, depending on whether the task is sequential or decomposable.

## Judgment calls for the human

- What counts as a "single well-prompted model"? The answer flips depending on whether the baseline gets the same tools and token budget. Vendor headline numbers do not give it either.
- How much weight to put on vendor-run and internal evals (Anthropic's internal eval, OpenAI's BrowseComp and HLE runs) compared with independent, compute-matched academic studies, which mostly use smaller tasks.
- Whether higher accuracy bought with 4-15x more tokens counts as "outperforming" for your use case, given cost, latency and the citation-reliability problems DeepTRACE found.
- Two of the compute-matched sources (arXiv 2604.02460 and 2609.04217) are recent preprints and were only checked at abstract level.

## Follow-up questions

- Is there an independent, compute-matched comparison of a deep-research agent against a single model with the same search tools and token budget on BrowseComp or HLE?
- Do newer (2026) agents close the human gap on RE-Bench or PaperBench at 8-32 hour budgets?
- Which task properties (decomposability, breadth, sequential dependency) predict when agent architecture helps beyond extra compute?
- How does citation and claim faithfulness compare between deep-research agents and a single model with retrieval at equal cost?
