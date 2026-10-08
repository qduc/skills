#!/usr/bin/env python3
"""Run-directory helper for the autonomy contract. Python stdlib only; no services.

A run directory holds one bounded, unattended run as plain files:

  goal.md         the goal, verbatim
  budget.json     frozen limits, start time, and the knowledge-store path
  ledger.jsonl    hash-chained budget charges and refusals (append-only)
  log.jsonl       structured events, one per line (append-only)
  claims.jsonl, sources.jsonl, findings.jsonl
                  records, append-only; the last line for an id wins
  brief.md        the human-facing conclusions, written by the agent

The knowledge store (a .jsonl file) lives outside the run directory and
outlives it. `recall` reads it back; `add RUN knowledge` writes to it.

Exit codes: 0 ok/continue, 2 usage or schema error, 3 budget refused,
4 validation failed, 5 audit failed, 10 the stop rule says stop.

Enforcement is cooperative. An agent can skip this script entirely; `audit`
re-checks the ledger after the run against counts observed elsewhere (for
example, tool calls counted from the transcript).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTRACT = "autonomy-contract/1"
PHASES = {"observe", "decide", "act", "verify", "learn", "repeat"}
CLAIM_STATUS = {"open", "supported", "contradicted", "unresolved"}
RESOLVED = CLAIM_STATUS - {"open"}
DECIDED = {"supported", "contradicted"}  # progress for the stall rule; "unresolved" is not
CONFIDENCE = {"high", "medium", "low"}
URL = re.compile(r"^(https?://\S+|file:\S+)$")
URL_IN_TEXT = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
STOPWORDS = set("""about after again also because been before being between both does doing
from have into more most only other over same should such than that their them then there
these they this those through under very what when where which while with would your""".split())


class Fail(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise Fail(2, f"ERROR {path.name}:{number} is not JSON: {exc}")
    return rows


def append_jsonl(path: Path, record: dict) -> str:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return line


def latest(rows: list[dict]) -> dict[str, dict]:
    return {row["id"]: row for row in rows if "id" in row}


class Run:
    def __init__(self, path: str):
        self.dir = Path(path)
        if not (self.dir / "budget.json").exists():
            raise Fail(2, f"ERROR {self.dir} is not a run directory (no budget.json)")
        self.budget_bytes = (self.dir / "budget.json").read_bytes()
        self.budget = json.loads(self.budget_bytes)
        self.limits = self.budget["limits"]
        self.store = (self.dir / self.budget["store"]).resolve()

    def file(self, name: str) -> Path:
        return self.dir / name

    def elapsed_min(self) -> float:
        start = datetime.fromisoformat(self.budget["started_at"])
        return round((now() - start).total_seconds() / 60, 2)

    def records(self, kind: str) -> dict[str, dict]:
        return latest(read_jsonl(self.file(f"{kind}s.jsonl")))

    def decided_count(self) -> int:
        return sum(1 for c in self.records("claim").values() if c.get("status") in DECIDED)

    def log(self, phase: str, event: str, data: dict | None = None) -> None:
        append_jsonl(self.file("log.jsonl"), {"ts": now().isoformat(timespec="seconds"),
                                              "phase": phase, "event": event, "data": data or {}})

    def ledger(self) -> list[dict]:
        """Return ledger entries after checking the hash chain back to budget.json."""
        path = self.file("ledger.jsonl")
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        prev = sha(self.budget_bytes)
        entries = []
        for index, line in enumerate(lines):
            entry = json.loads(line)
            if entry.get("prev") != prev or entry.get("seq") != index:
                raise Fail(5, f"ERROR ledger.jsonl line {index + 1} breaks the hash chain "
                              "(edited, reordered, or budget.json changed)")
            prev = sha(line.encode("utf-8"))
            entries.append(entry)
        return entries

    def used(self, entries: list[dict]) -> dict[str, int]:
        used = {"cycle": 0, "web": 0}
        for entry in entries:
            if entry["kind"] == "charge":
                used[entry["what"]] += entry["n"]
        return used

    def append_ledger(self, entries: list[dict], record: dict) -> str:
        """Append a chained entry and return its hash (the new ledger head)."""
        if entries:
            last = self.file("ledger.jsonl").read_text(encoding="utf-8").splitlines()[-1]
            prev = sha(last.encode("utf-8"))
        else:
            prev = sha(self.budget_bytes)
        record.update(seq=len(entries), prev=prev, ts=now().isoformat(timespec="seconds"))
        return sha(append_jsonl(self.file("ledger.jsonl"), record).encode("utf-8"))


# ---------------------------------------------------------------- schemas

def require(record: dict, field: str, kind: str, check=None, why: str = "") -> None:
    value = record.get(field)
    ok = value not in (None, "", []) and (check is None or check(value))
    if not ok:
        raise Fail(2, f"ERROR {kind} {record.get('id', '?')}: field '{field}' {why or 'is required'}")


def check_schema(kind: str, record: dict) -> None:
    if kind in ("claim", "source", "finding"):
        require(record, "id", kind, lambda v: isinstance(v, str))
    if kind == "claim":
        require(record, "text", kind)
        require(record, "status", kind, lambda v: v in CLAIM_STATUS, f"must be one of {sorted(CLAIM_STATUS)}")
    elif kind == "source":
        require(record, "url", kind, lambda v: isinstance(v, str) and URL.match(v), "must be an http(s) or file: URL")
        require(record, "excerpt", kind, lambda v: isinstance(v, str) and len(v.strip()) >= 8,
                "must quote the supporting passage (8+ chars)")
    elif kind == "finding":
        require(record, "statement", kind)
        require(record, "claim_ids", kind, lambda v: isinstance(v, list))
        require(record, "source_ids", kind, lambda v: isinstance(v, list))
        require(record, "confidence", kind, lambda v: v in CONFIDENCE, f"must be one of {sorted(CONFIDENCE)}")
        require(record, "uncertainty", kind, lambda v: isinstance(v, str), "must state what is uncertain")
    elif kind == "knowledge":
        require(record, "kind", kind, lambda v: v in ("finding", "lesson", "question"),
                "must be 'finding', 'lesson', or 'question'")
        require(record, "statement", kind)
        require(record, "tags", kind, lambda v: isinstance(v, list))
        if record["kind"] == "finding":
            require(record, "finding_ids", kind, lambda v: isinstance(v, list))
            require(record, "confidence", kind, lambda v: v in CONFIDENCE)
        elif record["kind"] == "lesson":
            require(record, "evidence", kind, why="must say what happened that taught this lesson")
    else:
        raise Fail(2, f"ERROR unknown record kind '{kind}'")


# ---------------------------------------------------------------- commands

def cmd_init(args) -> int:
    run_dir = Path(args.run)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise Fail(2, f"ERROR {run_dir} already exists and is not empty")
    goal = args.goal if args.goal is not None else Path(args.goal_file).read_text(encoding="utf-8")
    if not goal.strip():
        raise Fail(2, "ERROR goal is empty")
    for name in ("max_cycles", "max_web", "max_minutes"):
        if getattr(args, name) <= 0:
            raise Fail(2, f"ERROR --{name.replace('_', '-')} must be positive")
    run_dir.mkdir(parents=True, exist_ok=True)
    store = Path(args.store).resolve()
    if store == run_dir.resolve() or run_dir.resolve() in store.parents:
        raise Fail(2, "ERROR the knowledge store must live outside the run directory")
    store.parent.mkdir(parents=True, exist_ok=True)
    store.touch(exist_ok=True)
    started = now()
    (run_dir / "goal.md").write_text(goal.rstrip() + "\n", encoding="utf-8")
    budget = {
        "contract": CONTRACT,
        "run_id": f"{run_dir.resolve().name}-{started.strftime('%Y%m%dT%H%M%S')}",
        "goal_sha256": sha((run_dir / "goal.md").read_bytes()),
        "started_at": started.isoformat(timespec="seconds"),
        "limits": {"cycles": args.max_cycles, "web": args.max_web, "minutes": args.max_minutes,
                   "stall_cycles": args.max_stall, "reserve_minutes": args.reserve_minutes},
        "store": os.path.relpath(store, run_dir.resolve()),
    }
    (run_dir / "budget.json").write_text(json.dumps(budget, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name in ("claims.jsonl", "sources.jsonl", "findings.jsonl", "log.jsonl", "ledger.jsonl"):
        (run_dir / name).touch()
    run = Run(args.run)
    head = run.append_ledger([], {"kind": "init", "limits": budget["limits"]})
    run.log("observe", "run_initialized", {"run_id": budget["run_id"], "limits": budget["limits"],
                                           "store": str(store), "ledger_head": head})
    print(json.dumps({"run_id": budget["run_id"], "limits": budget["limits"], "store": str(store)}))
    return 0


def cmd_charge(args) -> int:
    if args.n < 1:
        raise Fail(2, f"ERROR --n must be at least 1 (got {args.n}); charges cannot refund budget")
    run = Run(args.run)
    entries = run.ledger()
    used = run.used(entries)
    elapsed = run.elapsed_min()
    limit = run.limits["cycles" if args.what == "cycle" else "web"]
    reason = None
    if elapsed >= run.limits["minutes"]:
        reason = f"wall clock {elapsed}/{run.limits['minutes']} min reached"
    elif used[args.what] + args.n > limit:
        reason = f"{args.what} limit reached: {used[args.what]} used + {args.n} requested > {limit}"
    record = {"what": args.what, "n": args.n, "note": args.note, "elapsed_min": elapsed}
    if args.what == "cycle":
        record["decided_claims"] = run.decided_count()
    if reason:
        record.update(kind="refused", reason=reason)
        head = run.append_ledger(entries, record)
        run.log("act", "budget_refused", {"what": args.what, "reason": reason, "note": args.note,
                                          "ledger_head": head})
        print(f"REFUSED {args.what}: {reason}", file=sys.stderr)
        return 3
    record["kind"] = "charge"
    head = run.append_ledger(entries, record)
    used[args.what] += args.n
    run.log("act", "budget_charged", {"what": args.what, "n": args.n, "note": args.note, "used": used,
                                      "ledger_head": head})
    print(f"OK {args.what} charged. used: cycles {used['cycle']}/{run.limits['cycles']}, "
          f"web {used['web']}/{run.limits['web']}, minutes {elapsed}/{run.limits['minutes']}")
    return 0


def cmd_log(args) -> int:
    run = Run(args.run)
    if args.phase not in PHASES:
        raise Fail(2, f"ERROR phase must be one of {sorted(PHASES)}")
    data = json.loads(args.data) if args.data else {}
    run.log(args.phase, args.event, data)
    return 0


def cmd_add(args) -> int:
    run = Run(args.run)
    raw = sys.stdin.read() if args.json == "-" else args.json
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Fail(2, f"ERROR record is not JSON: {exc}")
    check_schema(args.kind, record)
    record["ts"] = now().isoformat(timespec="seconds")
    if args.kind != "knowledge":
        append_jsonl(run.file(f"{args.kind}s.jsonl"), record)
        run.log("act" if args.kind == "source" else "verify" if args.kind == "finding" else "decide",
                f"{args.kind}_recorded", {"id": record["id"]})
        print(f"OK {args.kind} {record['id']}")
        return 0
    # Knowledge goes to the durable store, with provenance back to this run.
    # Sources are copied from the cited findings; relative file: URLs are
    # rewritten to be relative to the store's directory.
    findings, sources = run.records("finding"), run.records("source")
    missing = [f for f in record.get("finding_ids", []) if f not in findings]
    if missing:
        raise Fail(2, f"ERROR knowledge cites unknown finding(s) {missing}")
    if "sources" not in record:
        copied = []
        for sid in (s for f in record.get("finding_ids", []) for s in findings[f]["source_ids"]):
            if sid not in sources:
                continue
            url = sources[sid]["url"]
            if url.startswith("file:") and not url.startswith("file:/"):
                url = "file:" + os.path.relpath(run.dir.resolve() / url[5:], run.store.parent)
            item = {"url": url, "excerpt": sources[sid]["excerpt"]}
            if item not in copied:
                copied.append(item)
        record["sources"] = copied
    if record["kind"] == "finding" and not record["sources"]:
        raise Fail(2, "ERROR knowledge finding has no traceable sources")
    record["run_id"] = run.budget["run_id"]
    record["id"] = "K-" + sha((record["run_id"] + record["statement"]).encode("utf-8"))[:8]
    if record["id"] in latest(read_jsonl(run.store)):
        print(f"SKIP knowledge {record['id']} already stored")
        return 0
    append_jsonl(run.store, record)
    run.log("learn", "knowledge_written", {"id": record["id"], "kind": record["kind"], "store": str(run.store)})
    print(f"OK knowledge {record['id']} -> {run.store}")
    return 0


def terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9_.-]{3,}", text.lower()) if w not in STOPWORDS}


def cmd_recall(args) -> int:
    run = Run(args.run)
    query = args.query or run.file("goal.md").read_text(encoding="utf-8")
    wanted = terms(query)
    entries = list(latest(read_jsonl(run.store)).values())
    scored = []
    for entry in entries:
        score = len(wanted & terms(entry["statement"] + " " + " ".join(entry.get("tags", []))))
        if entry["kind"] == "lesson" or score > 0:
            scored.append((entry["kind"] != "lesson", -score, entry["id"], entry))
    surfaced = [e for *_, e in sorted(scored)][: args.limit]
    run.log("observe", "knowledge_recalled", {"store": str(run.store), "store_entries": len(entries),
                                              "query_terms": sorted(wanted)[:40],
                                              "surfaced": [e["id"] for e in surfaced]})
    print(json.dumps(surfaced, indent=2, ensure_ascii=False))
    return 0


def stop_status(run: Run) -> dict:
    entries = run.ledger()
    used = run.used(entries)
    elapsed = run.elapsed_min()
    claims = run.records("claim")
    open_claims = [c for c, r in claims.items() if r["status"] == "open"]
    unresolved = sum(1 for r in claims.values() if r["status"] == "unresolved")
    resolved = len(claims) - len(open_claims) - unresolved  # supported or contradicted
    reasons = []
    if used["cycle"] >= run.limits["cycles"]:
        reasons.append(f"cycle budget spent ({used['cycle']}/{run.limits['cycles']})")
    if used["web"] >= run.limits["web"]:
        reasons.append(f"web budget spent ({used['web']}/{run.limits['web']})")
    if elapsed >= run.limits["minutes"] - run.limits["reserve_minutes"]:
        reasons.append(f"time spent ({elapsed}/{run.limits['minutes']} min, "
                       f"{run.limits['reserve_minutes']} reserved to finish)")
    if claims and not open_claims:
        reasons.append(f"no open claims left ({resolved} resolved, {unresolved} unresolved)")
    cycles = [e for e in entries if e["kind"] == "charge" and e["what"] == "cycle"]
    stall = run.limits["stall_cycles"]
    # Ledgers written before "decided_claims" stored "resolved_claims" (which counted "unresolved").
    if stall and len(cycles) >= stall and resolved <= cycles[-stall].get(
            "decided_claims", cycles[-stall].get("resolved_claims", 0)):
        reasons.append(f"stalled: no claim newly supported or contradicted in the last {stall} cycles")
    return {"decision": "stop" if reasons else "continue", "reasons": reasons, "used": used,
            "limits": run.limits, "elapsed_min": elapsed,
            "claims": {"open": len(open_claims), "resolved": resolved, "unresolved": unresolved}}


def cmd_check(args) -> int:
    run = Run(args.run)
    status = stop_status(run)
    run.log("repeat", "stop_check", status)
    print(json.dumps(status))
    if status["decision"] == "stop":
        print("STOP " + "; ".join(status["reasons"]), file=sys.stderr)
        return 10
    return 0


def norm_url(url: str) -> str:
    return url.rstrip(".,;:").rstrip("/").lower()


def validation_errors(run: Run) -> list[str]:
    errors = []
    raw = {k: read_jsonl(run.file(f"{k}s.jsonl")) for k in ("claim", "source", "finding")}
    for kind, rows in raw.items():
        for row in rows:
            try:
                check_schema(kind, row)
            except Fail as exc:
                errors.append(str(exc))
    claims, sources, findings = (latest(raw[k]) for k in ("claim", "source", "finding"))
    if not findings:
        errors.append("ERROR no findings recorded")
    cited_claims = set()
    for fid, finding in findings.items():
        for cid in finding.get("claim_ids", []):
            cited_claims.add(cid)
            if cid not in claims:
                errors.append(f"ERROR finding {fid} cites unknown claim {cid}")
        for sid in finding.get("source_ids", []):
            if sid not in sources:
                errors.append(f"ERROR finding {fid} cites unknown source {sid}")
    for cid, claim in claims.items():
        if claim.get("status") in ("supported", "contradicted") and cid not in cited_claims:
            errors.append(f"ERROR claim {cid} is '{claim['status']}' but no finding cites it")
    store_ids = set(latest(read_jsonl(run.store)))
    surfaced = {i for e in read_jsonl(run.file("log.jsonl")) if e["event"] == "knowledge_recalled"
                for i in e["data"].get("surfaced", [])}
    for sid, source in sources.items():
        via = source.get("via")
        if via and via not in store_ids:
            errors.append(f"ERROR source {sid} claims to come from knowledge {via}, which is not in the store")
        elif via and via not in surfaced:
            errors.append(f"ERROR source {sid} uses knowledge {via}, but no recall in this run surfaced it")
    brief = run.file("brief.md")
    if brief.exists():
        known = {norm_url(s["url"]) for s in sources.values() if "url" in s}
        for url in sorted(set(URL_IN_TEXT.findall(brief.read_text(encoding="utf-8")))):
            if norm_url(url) not in known:
                errors.append(f"ERROR brief.md cites {url}, which is not a recorded source")
    return errors


def cmd_validate(args) -> int:
    run = Run(args.run)
    errors = validation_errors(run)
    run.log("verify", "validation", {"ok": not errors, "errors": errors})
    if errors:
        print("\n".join(errors))
        return 4
    print("VALID " + json.dumps({k: len(run.records(k)) for k in ("claim", "source", "finding")}))
    return 0


def cmd_audit(args) -> int:
    run = Run(args.run)
    problems = []
    try:
        entries = run.ledger()
    except Fail as exc:
        print(str(exc).replace("ERROR", "AUDIT FAIL", 1))
        return 5
    used = {"cycle": 0, "web": 0}
    for entry in entries[1:]:
        if entry["kind"] != "charge":
            continue
        if not isinstance(entry["n"], int) or entry["n"] < 1:
            problems.append(f"charge seq {entry['seq']} has n={entry['n']} (must be a positive integer)")
        used[entry["what"]] += entry["n"]
        limit = run.limits["cycles" if entry["what"] == "cycle" else "web"]
        if used[entry["what"]] > limit:
            problems.append(f"charge seq {entry['seq']} exceeded the {entry['what']} limit {limit}")
        if entry["elapsed_min"] >= run.limits["minutes"]:
            problems.append(f"charge seq {entry['seq']} was accepted after the wall-clock limit")
    for what, observed in (("web", args.observed_web), ("cycle", args.observed_cycles)):
        if observed is not None and observed != used[what]:
            problems.append(f"{what}: ledger records {used[what]} but {observed} were observed")
    if run.budget["goal_sha256"] != sha(run.file("goal.md").read_bytes()):
        problems.append("goal.md changed after init")
    log = read_jsonl(run.file("log.jsonl"))
    heads = [e["data"]["ledger_head"] for e in log if "ledger_head" in e.get("data", {})]
    last_line = run.file("ledger.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    if not heads or heads[-1] != sha(last_line.encode("utf-8")):
        problems.append("ledger.jsonl tail does not match the last ledger head in log.jsonl "
                        "(hash chain edited or truncated)")
    stops = [e for e in log if e["event"] == "stop_check" and e["data"]["decision"] == "stop"]
    summary = {"run_id": run.budget["run_id"], "limits": run.limits, "used": used,
               "refusals": sum(1 for e in entries if e["kind"] == "refused"),
               "terminated_by_stop_rule": bool(stops),
               "stop_reasons": stops[-1]["data"]["reasons"] if stops else [],
               "last_event_at": log[-1]["ts"] if log else None}
    print(json.dumps(summary, indent=2))
    for problem in problems:
        print(f"AUDIT FAIL {problem}")
    if problems:
        return 5
    print("AUDIT OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="create a run directory from a goal and a budget")
    p.add_argument("run")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--goal")
    g.add_argument("--goal-file")
    p.add_argument("--store", required=True, help="knowledge store .jsonl, outside the run dir")
    p.add_argument("--max-cycles", type=int, required=True)
    p.add_argument("--max-web", type=int, required=True, help="web search/fetch calls")
    p.add_argument("--max-minutes", type=float, required=True, help="wall clock from init")
    p.add_argument("--max-stall", type=int, default=2, help="stop after N cycles that newly support or contradict no claim (0=off)")
    p.add_argument("--reserve-minutes", type=float, default=0, help="stop this early to leave time to finish")
    p = sub.add_parser("charge", help="charge the budget before a cycle or a web call; exit 3 if refused")
    p.add_argument("run")
    p.add_argument("what", choices=["cycle", "web"])
    p.add_argument("--n", type=int, default=1, help="units to charge (at least 1)")
    p.add_argument("--note", default="")
    p = sub.add_parser("log", help="append a structured event")
    p.add_argument("run")
    p.add_argument("phase")
    p.add_argument("event")
    p.add_argument("--data", help="JSON object")
    p = sub.add_parser("add", help="append a claim, source, finding, or knowledge entry ('-' reads stdin)")
    p.add_argument("run")
    p.add_argument("kind", choices=["claim", "source", "finding", "knowledge"])
    p.add_argument("json")
    p = sub.add_parser("recall", help="read the knowledge store back and log what was surfaced")
    p.add_argument("run")
    p.add_argument("--query")
    p.add_argument("--limit", type=int, default=8)
    p = sub.add_parser("check", help="apply the stop rule; exit 10 means stop")
    p.add_argument("run")
    p = sub.add_parser("validate", help="check findings cite recorded sources; exit 4 on errors")
    p.add_argument("run")
    p = sub.add_parser("audit", help="re-check the ledger after the run; exit 5 on problems")
    p.add_argument("run")
    p.add_argument("--observed-web", type=int)
    p.add_argument("--observed-cycles", type=int)
    args = parser.parse_args(argv)
    try:
        return globals()[f"cmd_{args.cmd}"](args)
    except Fail as exc:
        print(str(exc), file=sys.stderr if exc.code != 4 else sys.stdout)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
