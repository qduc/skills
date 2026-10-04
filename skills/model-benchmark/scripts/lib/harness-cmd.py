#!/usr/bin/env python3
"""Render a harness invocation from the registry.

Usage: harness-cmd.py <registry> <benchmark_dir> <candidate>
Prints NUL-separated: <cwd> <argv...>
Exits 2 if the candidate has no runnable harness (e.g. "manual").
"""
import json
import sys


def main():
    registry_path, bench_dir, candidate = sys.argv[1:4]
    with open(registry_path) as f:
        registry = json.load(f)["harnesses"]
    with open(bench_dir + "/control/meta.json") as f:
        meta = json.load(f)

    spec = meta.get("candidate_specs", {}).get(candidate)
    if not spec:
        sys.exit("Error: no candidate_spec for '%s' (re-run prepare-benchmark.sh)" % candidate)

    harness = registry.get(spec["harness"])
    if harness is None:
        sys.exit("Error: harness '%s' missing from registry" % spec["harness"])
    if not harness.get("bin"):
        sys.exit(2)

    workspace = "%s/%s" % (bench_dir, candidate)
    prompt_file = bench_dir + "/control/prompt.txt"
    with open(prompt_file) as f:
        prompt = f.read().strip()

    model_template = harness.get("model_template", "{model_id}")
    model = model_template.format(
        provider=spec.get("provider") or "", model_id=spec.get("model_id") or ""
    )
    if "{model}" in json.dumps(harness.get("args", [])) and not (spec.get("model_id") or ""):
        sys.exit("Error: candidate '%s' needs a model but its spec has none" % candidate)

    fields = {
        "workspace": workspace,
        "prompt": prompt,
        "prompt_file": prompt_file,
        "model": model,
        "provider": spec.get("provider") or "",
        "model_id": spec.get("model_id") or "",
        "effort": spec.get("effort") or "medium",
    }
    argv = [harness["bin"]] + [a.format(**fields) for a in harness.get("args", [])]
    # Every harness runs with the candidate workspace as cwd; registry entries
    # that also take an explicit dir flag get it filled from {workspace}.
    sys.stdout.write("\0".join([workspace] + argv))


if __name__ == "__main__":
    main()
