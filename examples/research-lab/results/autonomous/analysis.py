"""Reproduce arithmetic from inspected primary-source aggregates; no model/API calls."""
import json, math
from pathlib import Path
out = {}
out['browsecomp'] = {'deep_research_percent':51.5,'gpt4o_browsing_percent':1.9,'absolute_difference_percentage_points':51.5-1.9,'ratio':51.5/1.9,'interpretation':'Different models/training and inference settings; arithmetic is not a causal estimate.'}
n,k,z=50,11,1.96
ph=k/n
den=1+z*z/n
center=(ph+z*z/(2*n))/den
half=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
out['autoresearchbench']={'deep_research_correct':k,'sample_n':n,'accuracy_percent':100*ph,'wilson95_percent':[100*(center-half),100*(center+half)],'interpretation':'Sampling interval only; excludes ground-truth uncertainty, tool mismatch and benchmark selection effects.'}
paired=[]
for model,mas_only,sas_only,both,both_wrong in [('Gemini-2.5-Flash',72,124,265,714),('Qwen3-30B-A3B',60,96,209,810)]:
    n=mas_only+sas_only+both+both_wrong
    discordant=mas_only+sas_only
    p=min(1.0,2*sum(math.comb(discordant,i) for i in range(min(mas_only,sas_only)+1))/2**discordant)
    paired.append({'model':model,'n':n,'mas_only':mas_only,'sas_only':sas_only,'both_correct':both,'both_wrong':both_wrong,'sas_accuracy_percent':100*(sas_only+both)/n,'mas_accuracy_percent':100*(mas_only+both)/n,'sas_minus_mas_percentage_points':100*(sas_only-mas_only)/n,'exact_two_sided_mcnemar_p':p,'interpretation':'Post-hoc paired aggregate audit; not independent replication or global significance proof. Requested cap matched, realized reasoning and total costs differ.'})
out['musique_table2']=paired
Path(__file__).with_name('analysis-results.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
