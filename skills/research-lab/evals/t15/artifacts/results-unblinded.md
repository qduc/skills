# T15 result (unblinded 2026-10-09 ~02:55 ICT, after blind/scores.md existed)

scores.md sha256 at unblinding: d404fdd5da9156f37b7bb113f2a35392d5e6eae4f0a1b4f8b317af6b4a2c158c (copy: blind/scores.pre-blinding-check.md)
Mapping (key.txt): X = Arm A (autonomy contract), Y = Arm B (single well-prompted baseline).

| Criterion | A (X) | B (Y) |
|---|---|---|
| Factual correctness | 3 | 4 |
| Source quality | 4 | 3 |
| Contradictions and uncertainty | 4 | 4 |
| Useful findings | 4 | 3 |
| Q (0-16) | 15 | 14 |
| Citation integrity | 0.92 (1 Partial of 6) | 1.00 (6 of 6) |

Decision rule (frozen at 54d86025):
- Q_A - Q_B = 1, which is < 2, so the result is not "autonomy helped".
- Q_B - Q_A = -1, which is < 2, so the result is not "did worse".
- Label: **INCONCLUSIVE**. (A is at most 1 below B on every criterion; A's citation integrity 0.92 >= 1.00 - 0.10. Only the margin failed.)
- Cost check: A used 13 web calls vs B's 20 (0.65x) and 4.60 vs 3.81 min (1.21x). The "costlier" flag does not apply.
- A's one Partial (pair #17): "shrink or reverse" under matched controls overstated; Kim et al. [8] shows +80.8% on Finance Agent under matched compute.

## Blinding check (asked after scores were recorded)
Sol guessed X (= Arm A, correct) was the more elaborate workflow, medium confidence. Tell: X's contradictions bullet "Challenge review of this synthesis (sequential [redacted] in one context ...)" — the residual stage description plus the visible redaction. Sol: without that line, "can't tell". Blinding partially failed; scores were already written before the question was asked, but Sol may have inferred the arm while scoring. Lesson for the protocol: scrub stage descriptions from run outputs (or forbid them in the arm prompt), not just tokens.
