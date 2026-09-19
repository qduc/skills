#!/usr/bin/env python3
"""Recover per-candidate token usage and dollar cost from a benchmark run.

Each harness reports usage differently, and one of them does not report it on
stdout at all:

  codex  --json      JSONL; sum `usage` on every `turn.completed` event. A run
                     killed by the timeout never emits one, so the session
                     rollout under ~/.codex/sessions is preferred: it carries a
                     running `total_token_usage` and survives a kill.
  pi     --mode json JSONL; sum `usage` on every assistant `message_end`.
  term2              nothing on stdout. Usage is read from the provider-traffic
                     log, matched to the run by mtime window. This requires
                     `logging.debugLogging = true` in term2's settings.

All three are normalised to the same five numbers so a dollar figure can be
computed from one price table, making the cost column comparable across
harnesses. `input` is always *uncached* input: the wire formats report cached
tokens inside the input total, and charging them at the full rate would
overstate every long run.

Writes <candidate>.cost.json into control/ and prints a summary table.
"""
import argparse
import glob
import json
import os
import sys

# USD per 1M tokens. Source: pi's model catalog (~/.pi/agent/models-store.json),
# openai-codex provider entries, read 2026-08-27. These models are reached over
# a ChatGPT subscription rather than metered API billing, so the dollar column
# is a comparable *proxy* for consumption, not an invoice.
PRICES = {
    "gpt-5.6-luna":  {"input": 0.20, "output": 1.20, "cache_read": 0.02, "cache_write": 0.25},
    "gpt-5.6-terra": {"input": 2.00, "output": 12.00, "cache_read": 0.20, "cache_write": 2.50},
    "gpt-5.6-sol":   {"input": 5.00, "output": 30.00, "cache_read": 0.50, "cache_write": 6.25},
    # deepseek-v4-flash is cheaper direct than via opencode-go ($0.22/$0.66);
    # these are the direct api.deepseek.com rates, which is how both harnesses
    # reach it here. Re-check this row if a run routes it through opencode.
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28, "cache_read": 0.0028, "cache_write": 0.0},
    "glm-5.3":       {"input": 1.40, "output": 4.40, "cache_read": 0.26, "cache_write": 0.0},
    # glm-5.3-flash list rates (models.dev still 404s for it; taken from the
    # provider pricing table, 2026-08-27). A 50% launch promo was running at
    # $0.075/$0.25/$0.015 — real spend right now is half this. List is used
    # here because every other row in this table is a list rate, and promos
    # expire while the benchmark record does not.
    "glm-5.3-flash": {"input": 0.15, "output": 0.50, "cache_read": 0.03, "cache_write": 0.0},
}

ZERO = {"input": 0, "cached_input": 0, "cache_write": 0, "output": 0, "reasoning": 0}


def add(acc, **kw):
    for k, v in kw.items():
        acc[k] += int(v or 0)


def usage_codex_rollout(sessions_root, workspace):
    """Read codex's own session rollouts, which survive a killed run.

    Rollouts are matched on `session_meta.cwd`, which is exactly the candidate
    workspace. An earlier attempt matched on file mtime instead and silently
    swept in a *previous* candidate's threads, inflating one cell roughly
    eightfold — codex keeps touching older rollout files, so a time window is
    not a safe key here. Matching on cwd also picks up sub-threads for free,
    since they inherit the workspace.
    """
    if not os.path.isdir(sessions_root):
        return None, 0
    acc, files = dict(ZERO), 0
    for path in glob.glob(os.path.join(sessions_root, "**", "rollout-*.jsonl"), recursive=True):
        cwd, last = None, None
        try:
            with open(path, errors="replace") as f:
                for line in f:
                    if cwd is None and '"cwd"' in line:
                        try:
                            cwd = _find_value(json.loads(line), "cwd")
                        except json.JSONDecodeError:
                            pass
                        if cwd is not None and cwd != workspace:
                            break
                    if '"total_token_usage"' in line:
                        last = line
        except OSError:
            continue
        if cwd != workspace or last is None:
            continue
        try:
            u = _find_key(json.loads(last), "total_token_usage")
        except json.JSONDecodeError:
            continue
        if not u:
            continue
        cached = u.get("cached_input_tokens", 0) or 0
        add(acc,
            input=(u.get("input_tokens", 0) or 0) - cached,
            cached_input=cached,
            cache_write=u.get("cache_write_input_tokens", 0) or 0,
            output=u.get("output_tokens", 0) or 0,
            reasoning=u.get("reasoning_output_tokens", 0) or 0)
        files += 1
    return (acc, files) if files else (None, 0)


def _find_value(obj, key):
    if isinstance(obj, dict):
        if isinstance(obj.get(key), str):
            return obj[key]
        for v in obj.values():
            found = _find_value(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_value(v, key)
            if found is not None:
                return found
    return None


def _find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], dict):
            return obj[key]
        for v in obj.values():
            found = _find_key(v, key)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key(v, key)
            if found:
                return found
    return None


def usage_codex(log_path):
    acc = dict(ZERO)
    calls = 0
    with open(log_path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") != "turn.completed":
                continue
            u = ev.get("usage") or {}
            cached = u.get("cached_input_tokens", 0) or 0
            add(acc,
                input=(u.get("input_tokens", 0) or 0) - cached,
                cached_input=cached,
                cache_write=u.get("cache_write_input_tokens", 0) or 0,
                output=u.get("output_tokens", 0) or 0,
                reasoning=u.get("reasoning_output_tokens", 0) or 0)
            calls += 1
    return acc, calls


def usage_pi(log_path):
    acc = dict(ZERO)
    calls = 0
    with open(log_path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") != "message_end":
                continue
            msg = ev.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            u = msg.get("usage") or {}
            if not u.get("totalTokens"):
                continue
            add(acc,
                input=u.get("input", 0),
                cached_input=u.get("cacheRead", 0),
                cache_write=u.get("cacheWrite", 0),
                output=u.get("output", 0))
            calls += 1
    return acc, calls


def usage_term2(traffic_root, start_epoch, end_epoch):
    """term2 writes no usage to stdout; recover it from the traffic log.

    Attribution keys on the *session directory*, not on file mtime. term2 keeps
    touching a finished session's files after the next candidate has started,
    so an mtime window silently absorbs the previous candidate's tokens — the
    same trap codex's rollouts set. A session directory is named for the moment
    the process started (`HH-MM-SS_...` under a `YYYY-MM-DD` day directory), so
    a directory whose start falls inside the window belongs to this candidate,
    and every file in it does too.
    """
    acc = dict(ZERO)
    calls = 0
    if not traffic_root or not os.path.isdir(traffic_root):
        return acc, 0
    for day in sorted(os.listdir(traffic_root)):
        day_dir = os.path.join(traffic_root, day)
        if not os.path.isdir(day_dir):
            continue
        for session in sorted(os.listdir(day_dir)):
            session_dir = os.path.join(day_dir, session)
            if not os.path.isdir(session_dir):
                continue
            started = _session_start_epoch(day, session)
            if started is None or not (start_epoch - 2 <= started <= end_epoch):
                continue
            for name in sorted(os.listdir(session_dir)):
                if not name.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(session_dir, name)) as f:
                        rec = json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
                summary = (rec.get("received") or {}).get("summary") or {}
                u = (summary.get("payload") or {}).get("usage") or {}
                if not u:
                    continue
                add(acc, **_normalise_term2_usage(u))
                calls += 1
    return acc, calls


def _normalise_term2_usage(u):
    """term2 logs whatever shape the provider speaks; both appear in one grid.

    Responses uses `input_tokens` / `output_tokens`; Chat Completions uses
    `prompt_tokens` / `completion_tokens`. Reading only the first shape returns
    a silent zero for every Chat Completions provider, which looks like a free
    run rather than a broken parser.
    """
    if "input_tokens" in u or "output_tokens" in u:
        details = u.get("input_tokens_details") or {}
        cached = details.get("cached_tokens", 0) or 0
        return {
            "input": (u.get("input_tokens", 0) or 0) - cached,
            "cached_input": cached,
            "cache_write": details.get("cache_write_tokens", 0) or 0,
            "output": u.get("output_tokens", 0) or 0,
            "reasoning": ((u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)) or 0,
        }
    details = u.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens", 0) or 0
    return {
        "input": (u.get("prompt_tokens", 0) or 0) - cached,
        "cached_input": cached,
        "cache_write": 0,
        "output": u.get("completion_tokens", 0) or 0,
        "reasoning": ((u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)) or 0,
    }


def _session_start_epoch(day, session):
    """Turn `2026-08-27` + `04-29-38_non-i` into an epoch. Names are UTC."""
    import calendar
    import time
    stamp = session.split("_", 1)[0]
    try:
        parsed = time.strptime(day + " " + stamp, "%Y-%m-%d %H-%M-%S")
    except ValueError:
        return None
    return calendar.timegm(parsed)


def price(acc, model_id):
    p = PRICES.get(model_id)
    if not p:
        return None
    return round(
        acc["input"] * p["input"] / 1e6
        + acc["cached_input"] * p["cache_read"] / 1e6
        + acc["cache_write"] * p["cache_write"] / 1e6
        + acc["output"] * p["output"] / 1e6,
        6,
    )


def read_epoch(control, candidate, which, default):
    path = os.path.join(control, "%s.%s_epoch" % (candidate, which))
    try:
        with open(path) as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark-dir", required=True)
    ap.add_argument("--term2-traffic-root",
                    default=os.path.expanduser("~/.local/state/term2-nodejs/logs/provider-traffic"))
    ap.add_argument("--codex-sessions-root",
                    default=os.path.expanduser("~/.codex/sessions"))
    args = ap.parse_args()

    control = os.path.join(args.benchmark_dir, "control")
    with open(os.path.join(control, "meta.json")) as f:
        meta = json.load(f)

    rows = []
    for cand in meta["candidates"]:
        spec = meta["candidate_specs"][cand]
        harness, model_id = spec["harness"], spec.get("model_id") or ""
        log = os.path.join(control, "%s.run.log" % cand)
        acc, calls, source = dict(ZERO), 0, "none"

        if harness.startswith("term2"):
            acc, calls = usage_term2(
                args.term2_traffic_root,
                read_epoch(control, cand, "start", 0),
                read_epoch(control, cand, "end", 0),
            )
            source = "provider-traffic"
        elif os.path.exists(log):
            if harness == "codex":
                acc, calls = usage_codex(log)
                source = "codex --json"
                roll, nfiles = usage_codex_rollout(
                    args.codex_sessions_root,
                    os.path.join(args.benchmark_dir, cand))
                # The rollout is authoritative: it includes sub-threads and is
                # the only source at all when the run was killed mid-turn.
                if roll and (calls == 0 or roll["output"] >= acc["output"]):
                    acc, calls, source = roll, max(calls, nfiles), "codex rollout"
            elif harness == "pi":
                acc, calls = usage_pi(log)
                source = "pi --mode json"

        total = acc["input"] + acc["cached_input"] + acc["output"]
        rec = {
            "candidate": cand, "harness": harness, "model_id": model_id,
            "effort": spec.get("effort"), "usage": acc, "total_tokens": total,
            "model_calls": calls, "usd": price(acc, model_id), "source": source,
        }
        with open(os.path.join(control, "%s.cost.json" % cand), "w") as f:
            json.dump(rec, f, indent=2)
        rows.append(rec)

    w = max(len(r["candidate"]) for r in rows) + 2
    print("%-*s %10s %10s %10s %8s %10s" % (w, "candidate", "in(new)", "cached", "out", "calls", "usd"))
    for r in rows:
        u = r["usage"]
        print("%-*s %10d %10d %10d %8d %10s"
              % (w, r["candidate"], u["input"], u["cached_input"], u["output"],
                 r["model_calls"], "--" if r["usd"] is None else "%.4f" % r["usd"]))
    missing = [r["candidate"] for r in rows if r["model_calls"] == 0]
    if missing:
        print("\nWARNING: no usage recovered for: %s" % ", ".join(missing), file=sys.stderr)


if __name__ == "__main__":
    main()
