#!/usr/bin/env python3
"""Parse --candidates specs into candidate records.

Spec grammar (comma-separated):
    <harness>:<provider>/<model_id>[#effort][=<alias>]  full harness comparison entry
    <harness>:<model_id>[=<alias>]              provider defaults to the harness name
    <name>                                      opaque candidate, harness "manual"

Emits JSON: {"candidates": [names...], "candidate_specs": {name: {...}}}
"""
import json
import re
import sys


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")


def parse(specs, registry):
    names, records = [], {}
    for raw in [s.strip() for s in specs.split(",") if s.strip()]:
        spec, _, alias = raw.partition("=")
        spec, _, effort = spec.partition("#")
        harness, sep, model = spec.partition(":")
        bare = not sep
        if bare:
            # Opaque candidate name: the operator drives this one by hand.
            harness, model, alias = "manual", "", alias or spec
        if harness not in registry:
            known = ", ".join(sorted(k for k in registry if not k.startswith("_")))
            raise SystemExit(
                "Error: unknown harness '%s' in candidate spec '%s'.\nKnown harnesses: %s"
                % (harness, raw, known)
            )
        provider, _, model_id = model.partition("/")
        if not model_id:
            provider, model_id = harness, provider
        default = harness + "-" + model_id + ("-" + effort if effort else "") if model_id else harness
        name = slug(alias or default)

        if name in records:
            raise SystemExit(
                "Error: duplicate candidate name '%s'. Use =<alias> to disambiguate." % name
            )
        names.append(name)
        records[name] = {
            "harness": harness,
            "provider": provider if model_id else None,
            "model_id": model_id or None,
            "effort": effort or None,
            "spec": raw,
        }
    if not names:
        raise SystemExit("Error: no candidates parsed from --candidates")
    return {"candidates": names, "candidate_specs": records}


def main():
    specs, registry_path = sys.argv[1], sys.argv[2]
    with open(registry_path) as f:
        registry = json.load(f)["harnesses"]
    json.dump(parse(specs, registry), sys.stdout, indent=2)


if __name__ == "__main__":
    main()
