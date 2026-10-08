| Criterion | X | Y | One-line reason per answer |
| --- | --- | --- | --- |
| Factual correctness | 3 | 4 | X: all 6 checked pairs found on page and numbers right, but the synthesis line "where that control exists, agent advantages shrink or reverse [2][5][8]" overstates: Kim et al. ([8]) report +80.8% MAS gains (Finance Agent) under matched compute, and [5] has no matched control; the Kim quote also joins two separate sentences without an ellipsis (minor). Y: all 6 checked pairs right, and every extra claim checked was right too (HF 55%/33%, AARRI 68.3/64.6/62.2, PaperBench 21.0/26.0/41.4); one small caveat left unstated: o3-mini (high) HLE 13.0 is on the text-only subset. |
| Source quality | 4 | 3 | X: the decisive claims rest on primary papers (arXiv, Nature MI) plus Anthropic's first-party engineering post, and every reference is dated. Y: mostly primary (OpenAI benchmark paper and post, arXiv papers), but the GAIA "GPT-4 <7%" no-agent baseline rests on a secondary Hugging Face blog (Y says so itself), HLE/GAIA numbers come from a vendor launch post, and most references have no dates. |
| Contradiction detection and uncertainty | 4 | 4 | X: three cited conflicts with reasons (task type, unmatched tokens, scaffold vs agent count, baseline control) plus clear gaps and follow-ups that would change the answer. Y: four cited conflicts with reasons (tools and training confound, near-tie on rediscovery, complex ≠ better, token cost), says the dispute is about "what is held fixed", and lists concrete unknowns. |
| Useful findings | 4 | 3 | X: specific task/metric/effect/cost findings tied to technical research (re-discovery, scientific coding, literature QA, research optimization, paper replication), with confidence labels and decision-relevant follow-ups. Y: specific and well hedged, but the large headline lifts are web-finding QA (BrowseComp/HLE/GAIA) against baselines without tools, and the PaperBench item is not an agent-vs-single-model comparison, so the link to "difficult technical research" and to a well-prompted baseline is weaker. |
| Total (0–16) | 15 | 14 | |

## Citation spot-check
| Answer | # | Statement (short) | URL | Label | Note |
| --- | --- | --- | --- | --- | --- |
| X | 2 | Under matched thinking-token budgets, SAS match or beat MAS on multi-hop reasoning; MAS gains track unaccounted compute/context | https://arxiv.org/abs/2604.02460 | Supported | Quote is verbatim in the abstract (Tran & Kiela, Stanford); scope is FRAMES/MuSiQue, text-only, no tools |
| X | 5 | Anthropic multi-agent beat single-agent Opus 4 by 90.2% on an internal eval (breadth-first); tokens explain 80% of BrowseComp variance; ~15× tokens vs chat | https://www.anthropic.com/engineering/multi-agent-research-system | Supported | All three numbers are on the page (published 2025-06-13) |
| X | 8 | 260 configs; MAS gains domain-dependent (+80% to −70%); baseline ≳45% → no further gains | https://www.nature.com/articles/s42256-026-01268-y | Supported | +80.8% / −70.0% / ~45% threshold all on the page (published 2026-07-24); the quote joins abstract and contributions sentences without an ellipsis |
| X | 9 | ResearchClawBench shows almost no agent advantage over a harnessed LLM | https://arxiv.org/abs/2606.07591 | Supported | 21.5 (Claude Code) vs 20.7 (Opus-4.7 via ResearchHarness) is verbatim in the abstract |
| X | 10 | Anthropic reports a large multi-agent lift on an internal eval | https://www.anthropic.com/engineering/multi-agent-research-system | Supported | 90.2% on internal research eval |
| X | 17 | Where the equal-tools/tokens control exists, agent advantages shrink or reverse | https://www.nature.com/articles/s42256-026-01268-y | Partial | Kim et al. hold prompts, tools and compute fixed: mean MAS change 0.0%, reversals on PlanCraft/SWE-bench, but large gains on Finance Agent (+80.8%); it compares MAS with a single tool-using agent, not a "single well-prompted model" |
| Y | 1 | BrowseComp: Deep Research 51.5% vs GPT-4o+browsing 1.9%, o1 9.9%; browsing 0.6→1.9 | https://openai.com/index/browsecomp/ | Supported | Table and the "trained on data that specifically teaches..." note are on the page (Apr 10, 2025) |
| Y | 2 | Same BrowseComp claim (paper) | https://arxiv.org/html/2504.12516 | Supported | "Enabling browsing for GPT-4o led to a modest improvement (from 0.6% to 1.9%)" and "solving around half" are verbatim |
| Y | 3 | HLE: deep research 26.6% (browsing + python) vs o1 9.1%, o3-mini (high) 13.0% | https://cdn.openai.com/API/docs/deep_research_blog.pdf | Supported | Table matches; o3-mini rows are marked "evaluated on text-only subset", which Y leaves out |
| Y | 4 | GAIA: Deep Research 67.36% pass@1, prior SOTA 63.64% | https://cdn.openai.com/API/docs/deep_research_blog.pdf | Supported | 67.36 / 63.64 are in the GAIA table; the "GPT-4 <7%" part is attributed to [4] (HF), which Y flags and I checked as correct |
| Y | 6 | Scaffold choice alone moves GAIA accuracy up to ~28 pp within one model (Opus L2) | https://arxiv.org/html/2606.08529 | Supported | Verbatim in the abstract (Jason Starace); spread is Opus L2 best 0.84 vs worst 0.56 |
| Y | 15 | ResearchClawBench near-tie; neither near the 50-point bar | https://arxiv.org/html/2606.07591v4 | Supported | 21.5 vs 20.7; 50 = target-paper level |

Citation integrity: X = 0.92 (5.5/6), Y = 1.00 (6/6)   (Unreachable: X = 0, Y = 0)

## Notes
- N: X = 17 pairs, Y = 18 pairs (Y's last contradictions bullet has no citation). Full numbered lists: /workspace/review-scratch/t15/pairs.md.
- Seeds: S = int("54d86025",16) = 1423466533; X seed = S, Y seed = S+1. Random picks: X [5, 9, 10, 17]; Y [1, 3, 6, 15].
- Decisive picks: X #2 and #8. X's headline caveat ("when compute, tools, and base models are carefully matched, multi-agent systems frequently fail to beat a strong single agent") rests on these two controlled studies. The near-tie claim (#1) is the same statement and source as random pick #9. Y #2 and #4. After the random BrowseComp pick #1 and HLE pick #3, these are the next most decisive pairs for Y's main "agents clearly beat single models" claim: the BrowseComp paper and the GAIA number.
- Every URL was reachable with WebFetch or curl. No browser was needed.
- Outside the sample, a careful read also checked these pairs against their sources and found them correct: X: PaperQA2 t(3.7)=3.41 and WikiCrow 13.5% vs 24.9%; Arbor >2.5× quote; STORM 74.1/68.7 and per-paper best-of being top; ScienceAgentBench 16.7→32.4, +10.8 pts vs OpenHands at 17× lower cost. Y: HF 7%/67.36/55.15/33; AARRI 68.3/64.6/62.2; PaperBench 21.0, o1-high IterativeAgent 36h 26.0, humans 41.4 vs o1 26.6.
- Start 2026-10-09 02:51 ICT; end 2026-10-09 02:53 ICT.

## Blinding check
(Added after the scores above were written. No score was changed.)

- **Guess:** X came from the more elaborate, multi-step workflow. Confidence: **medium**.
- **What gave it away:**
  - X's third contradictions bullet says "Challenge review of this synthesis (sequential [redacted] in one context, not independent reviewers) flagged a load-bearing assumption…". That describes a separate review stage, and the redaction looks like a workflow term that was scrubbed out. This is the main tell, and the redaction itself leaks it.
  - X also has "Local reproduction of these frontier benchmarks was not feasible here", which suggests a step where reproduction was attempted or planned.
  - X reads as a reconciled synthesis: it is shorter and tighter than Y. That is weak evidence, though, since both answers label each finding with a confidence level.
- **Why only medium:**
  - Y also shows traces of its process: "Searched for contrary evidence in equal-budget and harness papers", and the note that the live HTML was blocked so the CDN PDF was used.
  - Y is longer and has more references (10 vs 8). Neither of those separates a single careful pass from a pipeline.
  - Without X's review line I would say "can't tell", leaning low.
