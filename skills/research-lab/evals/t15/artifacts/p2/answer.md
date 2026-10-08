# What evidence shows that autonomous research agents outperform a single well-prompted model on difficult technical research tasks?

## Answer
On hard, multi-step information-seeking and tool-using research tasks (BrowseComp, GAIA, Humanity’s Last Exam with retrieval), autonomous research agents clearly beat single models that lack comparable tools and multi-step loops—often by large absolute margins. Confidence is **medium**: the gains are real in primary vendor and open reports, but many comparisons confound scaffolding with tools, specialized training, and far higher token budgets. On end-to-end scientific rediscovery with both sides given tool access, full agents barely beat (or lose to) lighter harnesses, so “agent > well-prompted model” is not a general law.

## Key findings
- On BrowseComp (1,266 hard web-finding questions), OpenAI Deep Research scored **51.5%** versus **1.9%** for GPT-4o with browsing and **9.9%** for o1 without browsing; enabling browsing alone barely helped GPT-4o (0.6%→1.9%). [1][2] (confidence: high for the numbers; medium for fairness—Deep Research was trained specifically for BrowseComp-style tasks)
- On Humanity’s Last Exam, OpenAI’s deep-research model scored **26.6%** with browsing and Python tools versus **9.1%** for o1 and **13.0%** for o3-mini (high) without that agentic tool loop. [3] (confidence: high for reported table; medium that the gap is “agent vs prompt” rather than “tools + specialized training”)
- On GAIA, a single model without an agentic setup is reported near floor (GPT-4 **<7%** on validation), while Deep Research reached **67.36%** pass@1 (prior SOTA ~63.64%); open reproductions also show large lifts from agent scaffolding (e.g., code-agent setup ~55% vs JSON-action agent ~33% in one Hugging Face report). [3][4] (confidence: medium—GAIA leaderboard/vendor numbers; HF is secondary for the &lt;7% GPT-4 claim)
- Controlled scaffold comparisons on GAIA show that **scaffold choice alone** can move accuracy by **up to ~28 percentage points** within one model (Opus on Level 2), confirming that agent loop design is a first-order driver of measured research-assistant performance—not just the base model. [5] (confidence: high)
- Anthropic reports a multi-agent research system (Opus lead + Sonnet subagents) **outperformed single-agent Opus 4 by 90.2%** on an internal research eval, but also that **token usage alone explained ~80%** of BrowseComp variance and that multi-agent systems use ~**15×** more tokens than chat. [6] (confidence: medium—primary vendor engineering post; internal eval not public)
- On ResearchClawBench (40 real-paper rediscovery tasks), the strongest full agent (Claude Code) averaged **21.5** versus **20.7** for Claude-Opus-4.7 under ResearchHarness—a lightweight ReAct tool loop—so heavy autonomous agents do **not** clearly dominate lightly harnessed frontier models when both can search, read files, and execute code. [7] (confidence: high)
- On AARRI-Bench research-intern tasks, **Mini-SWE-Agent + Claude Opus 4.7 (68.3%)** beat the same model in Claude Code (**62.2%**) and Hermes (**64.6%**), indicating that more complex research harnesses can underperform minimal ones; model quality dominates harness complexity. [8] (confidence: high)
- Under matched thinking-token budgets on multi-hop reasoning (FRAMES, MuSiQue), single-agent systems **match or outperform** multi-agent architectures once compute is normalized; many MAS “wins” appear to be unaccounted tokens. [9] (confidence: high for that setting; lower relevance to tool-heavy web research)
- PaperBench shows non-trivial agent research-replication ability (best BasicAgent ~**21%**; o1 IterativeAgent up to **26%** at 36h) but still far below expert humans on a subset (**41.4%** after 48h)—agents help, yet absolute competence on hard research remains limited. [10] (confidence: high)

## Contradictions and counter-evidence
- **Tools and training, not “agentness” alone:** BrowseComp and HLE gaps contrast Deep Research (tools + specialized training) with chat/reasoning models that often lack the same browsing/Python loop; GPT-4o *with* browsing still fails BrowseComp, so persistence/strategy matter, but baselines are not “same model, same tools, single well-crafted prompt.” [1][2][3]
- **End-to-end science rediscovery:** ResearchClawBench shows nearly tied scores for a full coding research agent and a frontier LLM in a light tool harness; neither approaches the 50-point “target-paper-level” bar. [7]
- **Complex ≠ better:** AARRI-Bench and budget-controlled MAS studies show minimal single-agent or light harnesses can beat heavier multi-agent research scaffolds, especially when tokens are equalized. [8][9]
- **Cost and compute:** Anthropic’s own analysis ties much BrowseComp performance to token spend; multi-agent research is ~15× chat token cost, so outperformance may be purchased compute rather than architecture. [6]
- Searched for contrary evidence in equal-budget and harness papers; disagreement is mainly about *what is held fixed* (tools, tokens, training), not about raw BrowseComp/GAIA/HLE tables.

## Uncertainty and gaps
- No fully public, same-model comparison of “one carefully engineered single-shot prompt with no tools” versus “identical model in a deep-research agent” on a shared hard research suite with matched dollar/token budgets.
- OpenAI’s live Introducing Deep Research HTML was blocked (CDN PDF used); GAIA “GPT-4 <7%” rests partly on secondary reporting. [3][4]
- ResearchClawBench’s “LLM” baseline is already agentic (ResearchHarness), so it understates any gap versus a true non-agent prompt.
- Humanity’s Last Exam and BrowseComp mix retrieval with reasoning; gains may not transfer to novel wet-lab or closed-world discovery.
- Independent replications of Anthropic’s +90.2% internal multi-agent result were not found.

## Follow-up questions
- Holding model, tools, and total tokens fixed, how large is the gap between a single ReAct loop and a multi-agent deep-research orchestrator on BrowseComp/GAIA?
- On ResearchClawBench-style rediscovery, does a true no-tool single prompt score near zero, and where do light versus heavy harnesses diverge by domain?
- What is the accuracy–$/token Pareto frontier for deep research agents versus long-context single-model reasoning with retrieved corpora pasted in?

## References
[1] BrowseComp: a benchmark for browsing agents — OpenAI, 10 Apr 2025. https://openai.com/index/browsecomp/
    > "Deep research* | 51.5" … "GPT‑4o w/ browsing | 1.9" … "OpenAI o1 | 9.9" … "Note that the Deep Research model is trained on data that specifically teaches the model to be good at BrowseComp tasks."

[2] BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents — Wei et al. (OpenAI), arXiv:2504.12516. https://arxiv.org/html/2504.12516
    > "Enabling browsing for GPT-4o led to a modest improvement in accuracy (from 0.6% to 1.9%), but performance remained low. … Deep Research significantly outperforms all other models, solving around half of the problems."

[3] Introducing deep research — OpenAI, 2 Feb 2025. https://cdn.openai.com/API/docs/deep_research_blog.pdf
    > "the model powering deep research scores a new high at 26.6% accuracy" … "OpenAI o1 | 9.1" … "**with browsing + python tools" … "Deep Research (pass@1) | … | 67.36"

[4] Open-source DeepResearch – Freeing our search agents — Hugging Face (m-ric et al.). https://raw.githubusercontent.com/huggingface/blog/main/open-deep-research.md
    > "GPT-4 does not even reach 7% on the validation set when used without any agentic setup. … with Deep Research, OpenAI reached 67.36% score on the validation set"

[5] Scaffold Effects on GAIA: A Controlled Comparison — Jason Starace, arXiv:2606.08529. https://arxiv.org/html/2606.08529
    > "Scaffold choice alone moves measured accuracy by as much as 28 percentage points within a single model (Opus, Level 2, robust slice)"

[6] How we built our multi-agent research system — Anthropic, 13 Jun 2025. https://www.anthropic.com/engineering/multi-agent-research-system
    > "a multi-agent system with Claude Opus 4 as the lead agent and Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval." … "token usage by itself explains 80% of the variance" … "multi-agent systems use about 15× more tokens than chats."

[7] ResearchClawBench: A Benchmark for End-to-End Autonomous Scientific Research — Shanghai AI Laboratory et al., arXiv:2606.07591. https://arxiv.org/html/2606.07591v4
    > "the strongest autonomous agent, Claude Code, averages 21.5, and the strongest ResearchHarness LLM, Claude-Opus-4.7, averages 20.7"

[8] Act As a Real Researcher: A Suite of Benchmarks… (AARRI-Bench) — Wang et al., arXiv:2606.07462. https://arxiv.org/html/2606.07462v1
    > "the highest-performing configuration is the combination of Mini-SWE-Agent and Claude-Opus-4.7, achieving an overall success rate of 68.3%. This outperforms more complex, feature-rich harnesses, such as Hermes Agent (64.6%) and Claude Code (62.2%), when paired with the same state-of-the-art model."

[9] Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets — Tran & Kiela, arXiv:2604.02460. https://arxiv.org/html/2604.02460
    > "We find that SAS consistently match or outperform MAS on multi-hop reasoning tasks when reasoning tokens are held constant." … "many reported advantages of multi-agent systems are better explained by unaccounted computation and context effects"

[10] PaperBench: Evaluating AI’s Ability to Replicate AI Research — Starace et al. (OpenAI), arXiv:2504.01848. https://arxiv.org/html/2504.01848v2
    > "Claude 3.5 Sonnet (New) with open-source scaffolding, achieves an average replication score of 21.0%." … "our human baseline of ML PhDs (best of 3 attempts) achieved 41.4% after 48 hours of effort, compared to 26.6% achieved by o1 on the same subset."
