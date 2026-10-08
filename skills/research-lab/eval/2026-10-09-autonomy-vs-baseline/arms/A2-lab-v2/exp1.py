rows = {
 "PaperBench o1-high Iterative vs Basic": (24.4, 13.2),
 "PaperBench o3-mini-high Iterative vs Basic": (8.5, 2.6),
 "MLE-bench GPT-4o AIDE vs OpenHands": (8.7, 4.4),
 "MLE-bench GPT-4o AIDE vs MLAB": (8.7, 0.8),
 "MLE-bench o1-preview pass@8 vs pass@1 (compute, not structure)": (34.1, 16.9),
 "MLE-bench GPT-4o 100h vs 24h (time)": (11.8, 8.7),
 "DeepResearch Bench Gemini DR vs best LLM+search (RACE)": (48.88, 40.67),
 "LCLM no-scaffold Gemini-1.5 vs tuned scaffold (SWE-V)": (38.0, 32.0),
 "MA-Evolve team vs single (equal cost)": (0.769, 0.754),
}
for k,(a,b) in rows.items():
    print(f"{k}: {a} vs {b} -> ratio {a/b:.2f}x, abs diff {a-b:+.2f}")
print("PaperBench best agent (o1 Iterative 36h 26.0) as fraction of human 41.4:", round(26.0/41.4,2))
