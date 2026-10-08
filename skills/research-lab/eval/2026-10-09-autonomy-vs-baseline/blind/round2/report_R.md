# Report

## Answer

The evidence that autonomous research agents beat a single well-prompted model on hard technical research is real but weaker than it is often presented. The strongest positive results are not compute-matched, and they come from vendors or from agent-vs-less-agentic comparisons: Anthropic's internal eval reports a 90.2% gain for multi-agent research over single-agent Opus 4 (C1); dedicated deep-research agents lead LLM+search on DeepResearch Bench (C4); and iterative scaffolds roughly double the same model's scores on PaperBench and MLE-bench (C6). Much of this gain tracks extra tokens, tool calls and time (C2). Controlled equal-budget studies find that a single agent matches or beats multi-agent setups on multi-hop reasoning and agentic tasks. The one large controlled study (180/260 configurations) finds the multi-agent edge appears only on decomposable work and turns into a loss on sequential tasks (C3, contested). On the hardest research tasks, agents of every kind still trail human experts over long horizons (C5), and end-to-end "AI scientist" systems show major quality failures (C7). Overall confidence: medium. "Agentic beats non-agentic at higher spend" is well supported. "Agent architecture beats a single well-prompted model at equal budget on difficult research" is not established.

## Findings

**C1 (supported, medium).** Anthropic reports that a multi-agent system (Opus 4 lead, Sonnet 4 subagents) "outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval." The eval is internal and unpublished, and not cost-matched: multi-agent runs use about 15x the tokens of a chat. No independent replication was found.

**C2 (supported, medium).** In Anthropic's own BrowseComp analysis, token usage alone explains 80% of performance variance. Tran & Kiela argue that reported multi-agent gains "are often confounded by increased test-time computation." MLE-bench shows that pure compute (pass@8 vs pass@1) doubles scores, a gain as large as the scaffold gains. Variance explained is not proof of cause, so confidence is medium.

**C3 (contested, medium).** Under matched reasoning-token budgets, single agents "consistently match or outperform" multi-agent systems on multi-hop reasoning (Tran & Kiela). At equal inference cost, an evolved multi-agent team is not statistically better than a single agent (0.769 vs 0.754 on ALFWorld/WebShop; the experiment re-analysis gives a 1.02x ratio). Google's controlled study (with tools, prompts and compute standardized) finds +80.8% for centralized coordination on decomposable financial reasoning but -39 to -70% on sequential planning. Resolution: a matched-budget multi-agent advantage exists only for parallelizable or decomposable tasks. None of these studies tests difficult technical research directly.

**C4 (supported, medium).** On DeepResearch Bench (100 PhD-level tasks across 22 fields), the top deep-research agent (Gemini-2.5-Pro Deep Research, RACE 48.88) beats the top LLM with search (Claude-3.7-Sonnet w/Search, 40.67). The ranking does not split cleanly by category, since Claude w/Search beats Grok Deeper Search. DeepTRACE finds that deep-research configurations reduce overconfidence but "still exhibit large fractions of unsupported statements." Scoring is by an LLM judge and budgets are not matched.

**C5 (supported, high).** On PaperBench the best agent averages 21.0% replication (o1 with IterativeAgent reaches 24.4%), against 41.4% for ML PhDs given 48 hours. Humans overtake agents after 24 hours, and o1 plateaus after the first hour. On MLE-bench the best setup reaches bronze or better in 16.9% of competitions. RE-Bench partly contradicts this at short horizons (agents score 4x humans at 2 hours) but reverses at long horizons (humans score 2x agents at 32 hours).

**C6 (supported, medium).** Holding the model fixed, more agentic scaffolds help: o1 scores 13.2 with BasicAgent and 24.4 with IterativeAgent on PaperBench; GPT-4o with AIDE scores 8.7% against 4.4% (OpenHands) and 0.8% (MLAB) on MLE-bench. Two caveats. Scaffold effects depend on the model (Claude 3.5 Sonnet does better with BasicAgent than o1, worse with IterativeAgent), and an unscaffolded long-context model matched tuned scaffolds on SWE-bench Verified (38% vs 32%). Some of the scaffold gain is also more time and compute.

**C7 (supported, medium).** An independent evaluation of Sakana's AI Scientist found that 42% of its experiments failed from coding errors, that its novelty assessments were poor, and that its manuscripts were poorly substantiated. In Sakana's own AI Scientist-v2 trial, 1 of 3 workshop submissions cleared the reviewer threshold and none met their internal main-track bar. This shows progress but not research-level reliability. Neither evaluation compares the system with a single well-prompted model.

## Judgment calls for the human

- Which comparison matters to you: agent vs single model at the same cost, or agent vs single model at whatever cost the agent needs? The answer flips between them (C2, C3).
- Whether to trust vendor-internal evals (Anthropic's 90.2%) that have no public benchmark or compute matching.
- Whether your research tasks are decomposable and breadth-heavy, where multi-agent setups can help, or sequential and deep, where they hurt (C3).
- Whether LLM-judged report quality (RACE) is an acceptable proxy for research correctness, given the high rates of unsupported statements (C4).

## Follow-up questions

- Is there a compute-matched comparison of a deep-research agent against a single long-context model with the same tools on PhD-level technical research (DeepResearch Bench or similar)?
- How much of PaperBench's IterativeAgent gain persists when BasicAgent gets the same wall-clock time and token budget?
- Do 2026 frontier models (with longer effective context) erase the multi-agent advantage on decomposable research tasks, as the capability-saturation finding predicts?
- Has anyone independently replicated Anthropic's multi-agent vs single-agent result on a public benchmark such as BrowseComp?

## Sources
- How we built our multi-agent research system (Anthropic Engineering): https://www.anthropic.com/engineering/multi-agent-research-system
- At Equal Inference Cost, Multi-Agent Structure Does Not Beat a Single Frozen Agent (arXiv 2609.04217; ALFWorld/WebShop, 7B backbone): https://arxiv.org/abs/2609.04217
- Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets (Tran & Kiela, arXiv 2604.02460): https://arxiv.org/abs/2604.02460
- DeepResearch Bench: A Comprehensive Benchmark for Deep Research Agents (Du et al., ICLR 2026): https://arxiv.org/html/2506.11763
- PaperBench: Evaluating AI's Ability to Replicate AI Research (OpenAI, 2025): https://arxiv.org/abs/2504.01848
- PaperBench full text (Sections 5.3-5.4, Tables 4-5): https://arxiv.org/html/2504.01848
- MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering (OpenAI, 2024): https://arxiv.org/abs/2410.07095
- MLE-bench full text (scaffold comparison, pass@k, time scaling): https://arxiv.org/html/2410.07095
- Towards a science of scaling agent systems: When and why agent systems work (Google Research blog; arXiv 2512.08296): https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Towards a Science of Scaling Agent Systems (arXiv 2512.08296, abstract): https://arxiv.org/abs/2512.08296
- DeepTRACE: Auditing Deep Research AI Systems for Tracking Reliability Across Citations and Evidence (arXiv 2509.04499): https://arxiv.org/abs/2509.04499
- RE-Bench: Evaluating frontier AI R&D capabilities of language model agents against human experts (METR, ICML 2025): https://arxiv.org/abs/2411.15114
- Putting It All into Context: Simplifying Agents with LCLMs (arXiv 2505.08120): https://arxiv.org/abs/2505.08120
- Evaluating Sakana's AI Scientist: Bold Claims, Mixed Results, and a Promising Future? (Beel, Kan, Baumgart): https://arxiv.org/abs/2502.14297
- The AI Scientist Generates its First Peer-Reviewed Scientific Publication (Sakana AI): https://sakana.ai/ai-scientist-first-publication/
