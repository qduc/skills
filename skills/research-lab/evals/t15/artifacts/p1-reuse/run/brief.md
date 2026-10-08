# On open-ended scientific research tasks, when tools and token budgets are matched, does a multi-agent or autonomous research scaffold beat a single tool-using frontier model?

## Answer
Not reliably, and nobody has yet run the clean test. No study I inspected matches both tools and LLM-token budgets on open-ended science. When compute is controlled on other tasks, the single agent usually matches or beats the multi-agent system, except on tasks that split into independent parallel lookups [1][2]. On a science benchmark built from real published papers, holding the model fixed, the choice of scaffold moves scores by only about ±3 points out of 100. The best multi-agent scaffold ties a single-agent coding CLI, and every system stays far below the level of the original papers [4]. The strongest pro-multi-agent science result matches GPU compute but not tokens [5]. The famous large gains come from spending more compute [3][6]. **Confidence: medium** that matched budgets would erase most of the advantage, with possible exceptions for breadth-heavy literature search and long experiment loops where a single agent stalls.

## Key findings
- **Matched-budget reasoning:** with thinking tokens held equal, a single agent matched or beat five multi-agent designs across three model families on multi-hop QA. Multi-agent only caught up when the single agent's context was heavily corrupted [1]. (confidence: high)
- **Matched tools and compute on agentic tasks:** across 260 configurations with the same prompts, tools and compute ceilings, the mean multi-agent effect was 0.0% (CI −59% to +77%). It ranged from +81% on decomposable financial research to large losses on sequential planning. Gains disappear once the single agent scores above ~45% [2]. None of the six benchmarks is a science benchmark. (confidence: high)
- **The headline "90% better" result isn't matched:** the multi-agent setup beat single-agent Opus 4 by 90.2% on an internal research eval. But the same authors say token usage alone explains 80% of BrowseComp variance, and multi-agent runs use ~15× chat tokens [3]. (confidence: high)
- **Open-ended science benchmark, same model:** on ResearchClawBench (40 tasks taken from published papers), GPT-5.4 in a minimal ReAct harness scored 15.3. Scaffolds on the same model scored 12.8–18.8. The multi-agent EvoScientist scored 18.8, about the same as the single-agent Codex CLI (18.4), and the adversarial multi-agent ARIS scored 13.6, below the plain harness. Score tracks cost or runtime only weakly [4]. Budgets were not matched, and scores come from single runs with no confidence intervals. (confidence: medium)
- **Best pro-multi-agent science result:** AutoScientists beat single-agent Autoresearch on BioML-Bench, 74.4 vs 66.1 leaderboard percentile, with the same model backend and hardware budget. It also kept finding improvements after the single agent had plateaued. However, it used more LLM tokens than the single agent [5]. (confidence: medium)
- **Hypothesis generation:** Co-Scientist beat single frontier models in its own Elo tournament by scaling test-time compute. Its authors note that single reasoning models were competitive at much lower compute [6]. (confidence: medium)
- **The feedback loop is what helps, not the scaffold's complexity:** on scientific coding, a simple execute-and-fix loop nearly doubled one-shot success. A heavier agent framework solved 10.8% fewer tasks at 17× the cost [7]. (confidence: medium)

## Contradictions and counter-evidence
- **Single agent wins one study, multi-agent wins another:** a single agent dominated multi-hop QA under matched budgets [1], yet centralized multi-agent coordination gained +81% on Finance Agent with tools and compute matched [2]. The likely reason is task structure. Multi-agent helps when work splits into parallel information streams and hurts when reasoning must stay in one sequential context [2]. Open-ended science contains both kinds of work, so the net effect probably depends on the task.
- **AutoScientists headline vs. its own appendix:** the headline says the team hit a target loss 1.9× faster than the single agent. But in the appendix runs from the same starting point, the single agent ended slightly better (0.9773 vs 0.9777 val_bpb, lower is better) after more experiments [5]. The team's edge is clearest only after the single agent stalls.
- **What I searched for:** a direct counter-search for science-specific multi-agent systems beating single agents under the same compute. It turned up AutoScientists, Co-Scientist and an idea-generation system (EvoSci). None of them matched LLM-token budgets.

## Uncertainty and gaps
- **"Matched budget" means different things in each source:** thinking tokens [1], per-system compute ceilings [2], GPU/experiment budget [5], or nothing at all [3][4][6]. The question's exact condition (tools and tokens both matched, on open-ended science) has no inspected direct test. Absence after a limited search does not prove no such study exists.
- **Small and noisy science evidence:** 40 single-run tasks [4], 24 tasks with overlapping standard errors [5], and evaluation mostly by LLM judges or the system's own scores.
- **Baselines differ in strength:** a "single tool-using frontier model" might be a bare ReAct loop or a mature coding agent. That choice moves results about as much as adding agents does [4].
- **Not covered by evidence I re-checked:** literature question answering, and whether human experts prefer multi-agent or single-agent outputs under matched budgets.
- **Weak self-review:** the self-challenge checks (unstated assumptions, internal consistency, scope) ran one after another by the same reviewer, not as independent reviews.
- **What would change the answer:** a token-matched rerun on ResearchClawBench or BioML-Bench showing multi-agent gains that clear run-to-run noise.

## Follow-up questions
- On ResearchClawBench or BioML-Bench, does a multi-agent scaffold beat a single ReAct agent when both get the same LLM-token budget and the same tools?
- Does the ~45% saturation threshold predict where multi-agent gains appear on science benchmarks, where current baselines score about 15–25/100?
- Do blinded domain experts prefer multi-agent research outputs over single-agent outputs when token budgets are matched?
- Do AutoScientists' BioML-Bench gains hold across repeated runs with token budgets equalized?

## References
[1] Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets — Dat Tran, Douwe Kiela (Stanford), 2026-04. https://arxiv.org/abs/2604.02460
    > "SAS consistently match or outperform MAS on multi-hop reasoning tasks when reasoning tokens are held constant. Overall, our results suggest that, for multi-hop reasoning tasks, many reported advantages of multi-agent systems are better explained by unaccounted computation and context effects rather than inherent architectural benefits"

[2] Capable language models can outgrow the benefits of collaboration — Kim et al., Nature Machine Intelligence, 2026-07-24. https://www.nature.com/articles/s42256-026-01268-y
    > "Here we conduct a controlled experiment that holds task prompts, tools and compute budgets constant while varying only coordination structure and model capability."
    > "Aggregating across all six benchmarks and architectures, the overall mean MAS improvement is 0.0% (95% confidence interval (CI) −58.7% to 77.2%)"
    > "On Finance Agent, MAS achieve substantial improvements: centralized reaches +80.8% (mean 0.631 versus SAS 0.349)"
    > "baselines above approximately 45% predict zero-to-negative multi-agent gains"

[3] How we built our multi-agent research system — Anthropic, 2025-06-13. https://www.anthropic.com/engineering/multi-agent-research-system
    > "We found that a multi-agent system with Claude Opus 4 as the lead agent and Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval."
    > "Multi-agent systems work mainly because they help spend enough tokens to solve the problem. In our analysis, three factors explained 95% of the performance variance in the BrowseComp evaluation"

[4] ResearchClawBench: A Benchmark for End-to-End Autonomous Scientific Research — InternScience, 2026-06. https://arxiv.org/html/2606.07591v4
    > "Current systems remain far from reliable re-discovery: the strongest autonomous agent, Claude Code, averages 21.5, and the strongest ResearchHarness LLM, Claude-Opus-4.7, averages 20.7, with an LLM frontier mean of only 26.5."
    > "Overall, score appears to have only a weak positive relationship with resource investment, and this relationship is largely elevated by Claude Code, which combines a high score with high cost and long runtime."

[5] AutoScientists: Self-Organizing Agent Teams for Long-Running Scientific Experimentation — Gao, Fang, Zitnik (Harvard), 2026-05. https://arxiv.org/abs/2605.28655
    > "reaching 74.40% across 24 biomedical ML tasks compared with 66.07% for Autoresearch under the same task interface, model backend, and hardware budget"
    > "AutoScientists is not designed to be more LLM-call efficient than single-agent baselines. As shown in Table S8, AutoScientists uses more LLM tokens than Autoresearch, though within the same order of magnitude"
    > "Final values: autoresearch 0.9773 (15 KEEPs / 83 exps), full AutoScientists 0.9777 (11 KEEPs / 71 exps), abl-no-self-org 0.9833 (5 KEEPs / 47 exps)."

[6] Accelerating scientific discovery with Co-Scientist — Gottweis et al., Nature, 2026-05-19. https://www.nature.com/articles/s41586-026-10644-y
    > "Co-Scientist eventually substantially surpassed the other frontier LLMs and reasoning models in Elo rating with iterative improvement. Notably, newer reasoning models, such as OpenAI o3-mini-high and DeepSeek R1, demonstrated competitive performance while requiring much less compute and reasoning time."

[7] ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery — Chen et al., 2024-10. https://arxiv.org/html/2410.05080v2
    > "Claude-3.5-Sonnet using self-debug can successfully solve 10.8% more tasks than using OpenHands CodeAct while costing 17 times less API fees."
