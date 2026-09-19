#!/usr/bin/env python3
"""Run one benchmark candidate through a herdr-managed interactive pane.

Many harnesses are painful to drive non-interactively (no headless mode, or a
headless mode that behaves differently from the TUI the user actually uses).
Herdr gives us the real TUI plus a lifecycle we can wait on, so harness
comparisons measure the thing people run.

Usage:
  herdr-run.py --benchmark-dir DIR --candidate NAME --registry FILE
               [--timeout SECS] [--keep-pane] [--workspace WS_ID]

Writes control/<candidate>.{seconds,run.status,run.log,herdr.json}.
Exit codes: 0 ok, 1 error, 2 not herdr-drivable, 3 blocked, 4 timeout.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time

SETTLED = {"idle", "done"}
POLL_SECONDS = 5
ADMISSION_GRACE = 30  # seconds to allow a submitted prompt to reach "working"


def herdr(*args, check=True):
    """Run a herdr CLI command and return its parsed JSON result."""
    proc = subprocess.run(["herdr", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(
            "herdr %s failed (%d): %s" % (" ".join(args), proc.returncode, proc.stderr.strip())
        )
    out = proc.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"_raw": out}


def slug(text):
    text = re.sub(r"[^a-z0-9_-]+", "-", text.lower()).strip("-")
    if not text or not text[0].isalpha():
        text = "b-" + text
    return text[:32]


def agent_state(target):
    got = herdr("agent", "get", target, check=False)
    result = got.get("result", got)
    agent = result.get("agent", result)
    if isinstance(agent, str):  # `agent` also names the kind on some responses
        agent = result
    return agent.get("agent_status") or agent.get("status") or "unknown"


def read_transcript(target, skill_root):
    """Prefer the herdr skill's extractor; fall back to a raw pane read."""
    extractor = os.path.join(
        skill_root, "..", "herdr", "scripts", "extract-agent-response.py"
    )
    extractor = os.path.normpath(extractor)
    if os.path.exists(extractor):
        proc = subprocess.run(
            [sys.executable, extractor, target, "--lines", "400"],
            capture_output=True, text=True,
        )
        if proc.stdout.strip():
            return proc.stdout
    got = herdr("agent", "read", target, "--source", "recent-unwrapped",
                "--lines", "400", "--format", "text", check=False)
    result = got.get("result", got)
    return result.get("text") or result.get("_raw") or json.dumps(got)[:4000]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark-dir", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep-pane", action="store_true")
    ap.add_argument("--workspace")
    args = ap.parse_args()

    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bench = os.path.abspath(args.benchmark_dir)
    control = os.path.join(bench, "control")
    cand = args.candidate
    workspace_dir = os.path.join(bench, cand)

    with open(os.path.join(control, "meta.json")) as f:
        meta = json.load(f)
    with open(args.registry) as f:
        registry = json.load(f)["harnesses"]

    spec = meta.get("candidate_specs", {}).get(cand)
    if not spec:
        sys.exit("Error: no candidate_spec for '%s'" % cand)
    harness = registry.get(spec["harness"], {})
    hcfg = harness.get("herdr")
    if not hcfg:
        sys.exit(2)

    model = harness.get("model_template", "{model_id}").format(
        provider=spec.get("provider") or "", model_id=spec.get("model_id") or ""
    )
    fields = {"model": model, "provider": spec.get("provider") or "",
              "model_id": spec.get("model_id") or "", "workspace": workspace_dir}
    start_args = [a.format(**fields) for a in hcfg.get("start_args", [])]

    with open(os.path.join(control, "prompt.txt")) as f:
        prompt = f.read().strip()

    workspace_id = args.workspace
    if not workspace_id:
        listing = herdr("workspace", "list")
        spaces = listing.get("result", {}).get("workspaces") or listing.get("workspaces") or []
        if not spaces:
            sys.exit("Error: no herdr workspace available")
        workspace_id = spaces[0].get("workspace_id") or spaces[0].get("id")

    name = slug("bench-" + cand)
    tab = herdr("tab", "create", "--workspace", workspace_id, "--cwd", workspace_dir,
                "--label", name, "--no-focus")
    tab_result = tab.get("result", tab)
    tab_id = (tab_result.get("tab") or {}).get("tab_id")
    pane_id = (tab_result.get("root_pane") or {}).get("pane_id")
    if not pane_id:
        sys.exit("Error: could not read root pane from tab create response: %s" % json.dumps(tab))

    record = {"candidate": cand, "harness": spec["harness"], "model": model,
              "tab_id": tab_id, "pane_id": pane_id, "agent": name,
              "start_args": start_args, "driver": "herdr"}
    status, elapsed = "ERROR", 0
    try:
        if hcfg["kind"] == "term2":
            cmd = "term2 " + " ".join(shlex.quote(a) for a in start_args)
            herdr("pane", "run", pane_id, cmd)
            time.sleep(3)
            herdr("agent", "rename", pane_id, name, check=False)
            started = time.time()
            clean_prompt = " ".join(prompt.splitlines())
            herdr("pane", "run", pane_id, clean_prompt)
            time.sleep(1)
            herdr("pane", "send-keys", pane_id, "enter")
        else:
            herdr("agent", "start", name, "--kind", hcfg["kind"], "--pane", pane_id,
                  "--timeout", "60000", "--", *start_args)

            started = time.time()
            # Bounded admission observation only; the real wait is the poll below.
            herdr("agent", "prompt", name, prompt, "--wait", "--until", "working",
                  "--timeout", "15000", check=False)

        deadline = started + args.timeout
        status = "TIMEOUT"
        saw_working = False
        while time.time() < deadline:
            state = agent_state(name)
            if state == "blocked":
                # An approval prompt is a harness result, not something to
                # auto-accept: record it and let the operator decide.
                status = "BLOCKED"
                break
            if state == "working":
                saw_working = True
            elif state in SETTLED:
                # A settled state before any observed work usually means the
                # prompt has not been admitted yet; allow a short grace window.
                if saw_working or time.time() - started > ADMISSION_GRACE:
                    status = "OK"
                    break
            time.sleep(POLL_SECONDS)
        elapsed = int(time.time() - started)

        transcript = read_transcript(name, skill_root)
        with open(os.path.join(control, cand + ".run.log"), "w") as f:
            f.write(transcript)
    finally:
        record["status"] = status
        record["seconds"] = elapsed
        with open(os.path.join(control, cand + ".herdr.json"), "w") as f:
            json.dump(record, f, indent=2)
        with open(os.path.join(control, cand + ".seconds"), "w") as f:
            f.write(str(elapsed) + "\n")
        with open(os.path.join(control, cand + ".run.status"), "w") as f:
            f.write(status + "\n")
        if not args.keep_pane and tab_id:
            herdr("tab", "close", tab_id, check=False)

    print("%s: %s in %ds (agent %s, pane %s)" % (cand, status, elapsed, name, pane_id))
    sys.exit({"OK": 0, "BLOCKED": 3, "TIMEOUT": 4}.get(status, 1))


if __name__ == "__main__":
    main()
