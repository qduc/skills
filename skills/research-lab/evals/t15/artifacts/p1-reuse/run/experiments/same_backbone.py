# Same-backbone deltas from ResearchClawBench Table (arXiv 2606.07591v4), overall scores
harness={'GPT-5.4':15.3,'Claude-Opus-4.6':19.9}
agents={'EvoScientist v0.1.1 (multi-agent, GPT-5.4)':('GPT-5.4',18.8),'Codex CLI (single agent, GPT-5.4)':('GPT-5.4',18.4),
'OpenClaw (GPT-5.4)':('GPT-5.4',16.6),'ResearchClaw (GPT-5.4)':('GPT-5.4',16.3),'EvoScientist v0.0.4 (multi-agent, GPT-5.4)':('GPT-5.4',15.5),
'ARIS Codex (adversarial multi-agent, GPT-5.4)':('GPT-5.4',13.6),'Nanobot (GPT-5.4)':('GPT-5.4',12.8),'Claude Code (Claude-Opus-4.6)':('Claude-Opus-4.6',21.5)}
for k,(m,s) in agents.items(): print(f"{k}: {s} vs ResearchHarness {m} {harness[m]} -> delta {s-harness[m]:+.1f}")
