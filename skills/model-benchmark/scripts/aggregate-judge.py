#!/usr/bin/env python3
"""De-anonymise judge samples and average each candidate's score.

Each sample used its own label shuffle, so scores are joined back through that
sample's mapping-<i>.json before averaging. Reporting the spread alongside the
mean matters here: a one-point mean gap between candidates means nothing if the
judge's own samples disagree by two.
"""
import argparse
import json
import math
import os
import re
import statistics
import sys

DIMS = ("correctness", "scope", "compatibility", "tests", "total")
LIMITS = {"correctness": 4, "scope": 2, "compatibility": 2, "tests": 2}
# The plain run-judge.sh prompt historically asked the judge to also report a
# "total"; the aggregator recomputes it, so that one extra key is tolerated.
# Any other key is prompt/contract drift and must be named, not guessed.


def extract_json(text):
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    blocks = re.findall(r"```json\s*(.*?)```", text, re.S)
    for b in reversed(blocks):
        try:
            return json.loads(b)
        except json.JSONDecodeError:
            continue
    # Fall back to the last brace-balanced object in the reply.
    for m in reversed(list(re.finditer(r"\{", text))):
        depth, i = 0, m.start()
        for j in range(m.start(), len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[m.start():j + 1])
                    except json.JSONDecodeError:
                        break
        del i
    return None


def main():
    ap = argparse.ArgumentParser()
    location = ap.add_mutually_exclusive_group(required=True)
    location.add_argument("--benchmark-dir")
    location.add_argument("--control-dir")
    args = ap.parse_args()
    control = args.control_dir or os.path.join(args.benchmark_dir, "control")

    per_candidate = {}
    mechanical_path = os.path.join(control, "mechanical-scores.json")
    mechanical = {}
    if os.path.exists(mechanical_path):
        with open(mechanical_path) as f:
            mechanical = json.load(f)
    samples_used = 0
    for i in range(1, 21):
        jpath = os.path.join(control, "judge-%d.txt" % i)
        mpath = os.path.join(control, "mapping-%d.json" % i)
        if not (os.path.exists(jpath) and os.path.exists(mpath)):
            continue
        with open(jpath) as f:
            parsed = extract_json(f.read())
        if not parsed or "scores" not in parsed:
            print("  sample %d: no parsable score block, skipped" % i)
            continue
        with open(mpath) as f:
            mapping = json.load(f)
        expected = set(mapping)
        scores = parsed["scores"]
        if set(scores) != expected:
            print("  sample %d: candidate set mismatch, skipped" % i)
            continue
        normalized = {}
        valid = True
        reject_reason = ""
        for label, sc in scores.items():
            if not isinstance(sc, dict):
                reject_reason = "%s: score is not an object" % label
                valid = False
                break
            unknown = sorted(set(sc) - set(LIMITS) - {"total"})
            missing = sorted(d for d in LIMITS if d not in sc)
            if unknown:
                reject_reason = "%s: unknown keys %s" % (label, unknown)
                valid = False
                break
            if missing:
                reject_reason = "%s: missing dimensions %s" % (label, missing)
                valid = False
                break
            dimensions = {}
            for dimension, maximum in LIMITS.items():
                value = sc[dimension]
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
                    reject_reason = "%s: %s out of range" % (label, dimension)
                    valid = False
                    break
                dimensions[dimension] = float(value)
            if not valid:
                break
            dimensions["total"] = sum(dimensions.values())
            normalized[label] = dimensions
        if not valid:
            print("  sample %d: invalid dimension score (%s), skipped" % (i, reject_reason))
            continue
        samples_used += 1
        for label, dimensions in normalized.items():
            candidates = mapping[label]
            if isinstance(candidates, str):
                candidates = [candidates]
            for cand in candidates:
                slot = per_candidate.setdefault(cand, {d: [] for d in DIMS})
                for dimension, value in dimensions.items():
                    slot[dimension].append(value)

    out = {
        candidate: {
            "samples": 0,
            "score_source": "mechanical-empty",
            "total_mean": 0.0,
            "total_stdev": 0.0,
            "total_scores": [0.0],
            **{dimension: float(score[dimension]) for dimension in DIMS if dimension != "total"},
        }
        for candidate, score in mechanical.items()
    }
    for cand, dims in per_candidate.items():
        totals = dims["total"]
        out[cand] = {
            "samples": len(totals),
            "score_source": "judge",
            "total_mean": round(statistics.mean(totals), 2) if totals else None,
            "total_stdev": round(statistics.stdev(totals), 2) if len(totals) > 1 else 0.0,
            "total_scores": totals,
            **{d: (round(statistics.mean(v), 2) if v else None)
               for d, v in dims.items() if d != "total"},
        }

    ranking = sorted(out, key=lambda candidate: (-(out[candidate]["total_mean"] or 0), candidate))
    with open(os.path.join(control, "judge-summary.json"), "w") as f:
        json.dump({"samples_used": samples_used, "ranking": ranking, "candidates": out}, f, indent=2)

    print("\nJudge summary (%d sample(s))" % samples_used)
    print("%-14s %7s %7s   %s" % ("candidate", "mean", "stdev", "samples"))
    for cand, r in sorted(out.items(), key=lambda kv: -(kv[1]["total_mean"] or 0)):
        print("%-14s %7s %7s   %s" % (cand, r["total_mean"], r["total_stdev"],
                                      r["total_scores"]))
    if samples_used == 0 and any(name.startswith("mapping-") for name in os.listdir(control)):
        print("Error: no valid judge samples", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
