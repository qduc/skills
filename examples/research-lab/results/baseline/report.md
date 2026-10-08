# Independent single-model baseline

Question: What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?

**Evidence supports conditional gains, not a general claim that autonomous research agents beat a well-prompted single model at equal cost.** The relevant comparator is a strong model allowed to search, run experiments, maintain memory and revise its answer. Beating one unassisted response is a substantially weaker result.

| Inspected primary evidence | Finding | What it establishes |
|---|---|---|
| [AutoScientists](https://arxiv.org/html/2605.28655v1) | 74.40 versus 66.07 mean leaderboard percentile across 24 biomedical ML tasks: **+8.33 percentile points**. Same backend, task interface and experimental hardware. | The strongest directly relevant comparison found. Teams improve experimental search, but use more LLM tokens; equal total cost remains untested. Aggregate standard errors are 6.20 and 7.38, so paired significance requires further analysis. |
| [ST-Bench](https://arxiv.org/html/2610.07763v1) | Strongest workflow scores 32.0 versus 11.0 across 100 scientific data-analysis tasks, using approximately 4.5 times the inference time. | Same GPT-5 backbone, but single comparator is explicitly **one-turn**. Gains chiefly reflect reaching computable output; conditional metric quality is similar. |
| [Anthropic research system](https://www.anthropic.com/engineering/multi-agent-research-system) | Vendor reports **90.2% relative improvement** over single Opus 4 on internal research evaluation. | Evidence for broad parallel information gathering. Public task-level data and equal-resource controls are unavailable; approximately 15× chat token use is **not** 15× single-agent use (single agents are approximately 4× chat). |

AutoScientists also supplies component ablations on four tasks, which strengthen the case that coordination affects results. Nonetheless, matching experimental hardware does not match reasoning expenditure, and comparisons against some published agents use different hardware protocols. It remains an author-reported preprint result.

Contrary evidence is substantial. The inspected third version of [Scaling Agent Systems](https://arxiv.org/html/2512.08296v3) evaluates 260 configurations with matched reasoning budgets and tools. Gains range from +80.8% on Finance Agent to −70.0% on sequential PlanCraft. Coordination returns diminish around 45% single-agent success within these tested domains. This threshold is an empirical observation, not a universal rule; technical benchmark extensions use small 20-instance subsets.

[Equal-thinking-budget multi-hop research](https://arxiv.org/html/2604.02460v1) likewise favors single agents in many conditions. At a requested 2,000-token budget, mean accuracy is .421 for single agents, .389 for sequential teams and .403 for debate. However, teams win some low-budget cells, and Gemini's requested budget does not perfectly control actual thought tokens. These are world-knowledge questions rather than autonomous science experiments. The title should not be read as universal dominance.

A narrow [automated-ML study](https://arxiv.org/html/2603.29632v1) reports faster early improvement from parallel subagents and more diverse changes from teams, alongside crashes and deliberation overhead. Its mixed roles, limited task scope and training-time controls leave causal uncertainty. [ResearchClawBench](https://arxiv.org/abs/2606.07591) reports strongest agent and lightweight model-harness scores of 21.5 and 20.7; these unmatched maxima and abstract-only inspection establish neither a reliable advantage nor high overall capability.

My inference is that independent exploration, context management and experiment selection can improve results when tasks decompose well. The evidence is considerably weaker that adding agents inherently improves deep technical reasoning, novel discovery or reliability. Gains conflate architecture, prompting, tools, memory, selection and additional compute.

A decisive follow-up would run paired repeated trials on fresh technical research tasks, with a tuned iterative single agent, single-agent self-critique, independent sampling plus selection, and coordinated teams. Keep model and tools fixed; compare both equal total cost and equal wall-clock regimes. Blind experts should grade correctness, novelty, reproducibility and evidence-to-claim alignment, alongside completion, human interventions and paired confidence intervals. Publish prompts, tuning budgets, failures and runnable artifacts.

Research budget: 8 web calls, 6 submitted search queries, 12 open operations (including repeat reads and one failure); no delegation, interventions or paid API. Subscription token cost is unavailable.
