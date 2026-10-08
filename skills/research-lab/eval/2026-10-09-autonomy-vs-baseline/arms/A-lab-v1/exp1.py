bc = {"GPT-4o":0.6,"GPT-4o w/ browsing":1.9,"GPT-4.5":0.9,"o1":9.9,"Deep Research":51.5,"Human trainers (solved)":29.2}
hle = {"GPT-4o":3.3,"o1":9.1,"DeepSeek-R1":9.4,"o3-mini-medium":10.5,"o3-mini-high":13.0,"Deep research":26.6}
print("BrowseComp DR/o1 = %.1fx, abs gap = %.1f pts"%(bc["Deep Research"]/bc["o1"], bc["Deep Research"]-bc["o1"]))
print("BrowseComp DR/GPT-4o+browse = %.1fx"%(bc["Deep Research"]/bc["GPT-4o w/ browsing"]))
print("HLE DR/o3-mini-high = %.2fx, abs gap = %.1f pts"%(hle["Deep research"]/hle["o3-mini-high"], hle["Deep research"]-hle["o3-mini-high"]))
print("Anthropic: multi-agent ~15x tokens of chat vs agent ~4x -> multi-agent/single-agent token ratio = %.2fx; reported gain 90.2%% (1.90x)"%(15/4))
