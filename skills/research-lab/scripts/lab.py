#!/usr/bin/env python3
"""Research-lab harness: a durable, observable environment for one research run.

The agent (any host: Claude Code, term2, Pi, Codex) does the thinking and the
web access. This script owns the parts that must not live in model context:

  * budget meter with a predictable stop (exit code 3 once exhausted)
  * append-only event log            -> events.jsonl
  * claim ledger                     -> claims.json
  * source snapshots                 -> sources/S<n>.txt
  * evidence linked to claims        -> evidence.jsonl
  * deterministic verifier           -> verify.json
  * report renderer                  -> findings.md
  * knowledge base promotion/search  -> <kb>/claims.jsonl, questions.jsonl, lessons.md

Stdlib only. Output is short and greppable on purpose: every problem line
starts with "ISSUE" so a host can surface it without reading whole files.

Exit codes: 0 ok, 1 usage/data error, 2 verify failed, 3 budget exhausted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

BUDGET_KINDS = ("search", "fetch", "experiment")
CLAIM_STATUSES = ("open", "supported", "refuted", "contested", "unresolved")
CONFIDENCE = ("low", "medium", "high")
STANCES = ("supports", "contradicts", "context")
SOURCE_TYPES = ("primary", "secondary", "tertiary")
EXIT_VERIFY = 2
EXIT_BUDGET = 3


# ---------------------------------------------------------------- storage --

def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR {msg}", file=sys.stderr)
    sys.exit(code)


def read_json(p: Path, default):
    return json.loads(p.read_text()) if p.exists() else default


def write_json(p: Path, data) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(p)


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def append_jsonl(p: Path, rec: dict) -> None:
    with p.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class Run:
    def __init__(self, root: str):
        self.root = Path(root)
        if not (self.root / "run.json").exists():
            die(f"no run at {self.root} (run `init` first)")
        self.meta = read_json(self.root / "run.json", {})

    # files
    @property
    def claims_p(self): return self.root / "claims.json"
    @property
    def evidence_p(self): return self.root / "evidence.jsonl"
    @property
    def events_p(self): return self.root / "events.jsonl"
    @property
    def sources_d(self): return self.root / "sources"

    def claims(self) -> list[dict]: return read_json(self.claims_p, [])
    def evidence(self) -> list[dict]: return read_jsonl(self.evidence_p)

    def save_meta(self): write_json(self.root / "run.json", self.meta)

    def log(self, event: str, **data) -> None:
        append_jsonl(self.events_p, {"t": now(), "event": event, **data})

    def elapsed_minutes(self) -> float:
        start = dt.datetime.fromisoformat(self.meta["created"])
        end = dt.datetime.fromisoformat(self.meta["ended"]) if self.meta.get("ended") \
            else dt.datetime.now(dt.timezone.utc)
        return (end - start).total_seconds() / 60

    def require_active(self) -> None:
        if self.meta["status"] != "ACTIVE":
            die(f"run is {self.meta['status']} ({self.meta.get('stop_reason')}); "
                "only verify/report/learn/status are allowed", EXIT_BUDGET)


def next_id(prefix: str, items: list[dict]) -> str:
    return f"{prefix}{len(items) + 1}"


# ---------------------------------------------------------------- budget ---

def cmd_init(a) -> None:
    root = Path(a.run)
    if (root / "run.json").exists():
        die(f"run already exists at {root}")
    (root / "sources").mkdir(parents=True, exist_ok=True)
    meta = {
        "id": root.name, "goal": a.goal, "created": now(), "status": "ACTIVE",
        "stop_reason": None, "kb": a.kb,
        "budget": {"search": a.max_searches, "fetch": a.max_fetches,
                   "experiment": a.max_experiments, "minutes": a.max_minutes},
        "spent": {k: 0 for k in BUDGET_KINDS},
    }
    write_json(root / "run.json", meta)
    write_json(root / "claims.json", [])
    r = Run(a.run)
    r.log("init", goal=a.goal, budget=meta["budget"])
    print(f"OK run {root} budget={meta['budget']}")


def stop(r: Run, reason: str, status: str = "STOPPED") -> None:
    r.meta["status"], r.meta["stop_reason"], r.meta["ended"] = status, reason, now()
    r.save_meta()
    r.log("stop", status=status, reason=reason)


def cmd_charge(a) -> None:
    """Call BEFORE each paid action. Exit 3 means: do not perform it; finish up."""
    r = Run(a.run)
    r.require_active()
    b, s = r.meta["budget"], r.meta["spent"]
    if r.elapsed_minutes() > b["minutes"]:
        stop(r, f"time budget {b['minutes']}m exhausted")
        die("BUDGET time exhausted: stop acting, run verify/report", EXIT_BUDGET)
    if s[a.kind] + a.n > b[a.kind]:
        stop(r, f"{a.kind} budget {b[a.kind]} exhausted")
        die(f"BUDGET {a.kind} exhausted ({s[a.kind]}/{b[a.kind]}): stop acting, "
            "run verify/report", EXIT_BUDGET)
    s[a.kind] += a.n
    r.save_meta()
    r.log("charge", kind=a.kind, n=a.n, note=a.note)
    print(f"OK {a.kind} {s[a.kind]}/{b[a.kind]}")


def cmd_finish(a) -> None:
    r = Run(a.run)
    if r.meta["status"] == "ACTIVE":
        stop(r, a.reason, "FINISHED")
    print(f"OK {r.meta['status']}: {r.meta['stop_reason']}")


def cmd_status(a) -> None:
    r = Run(a.run)
    b, s = r.meta["budget"], r.meta["spent"]
    claims = r.claims()
    open_key = [c["id"] for c in claims if c["key"] and c["status"] == "open"]
    print(f"status={r.meta['status']} elapsed={r.elapsed_minutes():.1f}/{b['minutes']}m "
          + " ".join(f"{k}={s[k]}/{b[k]}" for k in BUDGET_KINDS))
    print(f"claims={len(claims)} key_open={','.join(open_key) or '-'} "
          f"evidence={len(r.evidence())} sources={len(list(r.sources_d.glob('S*.txt')))}")


# ---------------------------------------------------------------- ledger ---

def cmd_claim_add(a) -> None:
    r = Run(a.run)
    r.require_active()
    claims = r.claims()
    c = {"id": next_id("C", claims), "text": a.text, "key": a.key,
         "parent": a.parent, "status": "open", "confidence": None,
         "note": "", "challenges": []}
    claims.append(c)
    write_json(r.claims_p, claims)
    r.log("claim_add", id=c["id"], text=a.text, key=a.key)
    print(f"OK {c['id']}")


def find_claim(claims: list[dict], cid: str) -> dict:
    for c in claims:
        if c["id"] == cid:
            return c
    die(f"unknown claim {cid}")


def cmd_claim_set(a) -> None:
    r = Run(a.run)
    claims = r.claims()
    c = find_claim(claims, a.id)
    if a.status:
        c["status"] = a.status
    if a.confidence:
        c["confidence"] = a.confidence
    if a.note:
        c["note"] = a.note
    write_json(r.claims_p, claims)
    r.log("claim_set", id=a.id, status=c["status"], confidence=c["confidence"])
    print(f"OK {a.id} {c['status']}/{c['confidence']}")


def cmd_challenge(a) -> None:
    """Record a deliberate attempt to find evidence AGAINST a claim."""
    r = Run(a.run)
    claims = r.claims()
    c = find_claim(claims, a.claim)
    c["challenges"].append({"query": a.query, "found": a.found, "t": now()})
    write_json(r.claims_p, claims)
    r.log("challenge", claim=a.claim, query=a.query, found=a.found)
    print(f"OK {a.claim} challenges={len(c['challenges'])}")


def cmd_scan(a) -> None:
    """Record a breadth search: which evidence lineages exist for the goal.

    Required before decomposing into key claims, and again as a final gap check
    after the last key claim is added (see verify: breadth)."""
    r = Run(a.run)
    lineages = [x.strip() for x in a.lineages.split(";") if x.strip()]
    rec = {"t": now(), "query": a.query, "lineages": lineages, "new": a.new}
    append_jsonl(r.root / "scans.jsonl", rec)
    r.log("scan", query=a.query, lineages=lineages, new=a.new)
    print(f"OK scan lineages={len(lineages)}")


def cmd_snapshot(a) -> None:
    r = Run(a.run)
    text = Path(a.file).read_text() if a.file else sys.stdin.read()
    if not text.strip():
        die("empty snapshot")
    n = len(list(r.sources_d.glob("S*.txt"))) + 1
    sid = f"S{n}"
    header = (f"url: {a.url}\ntitle: {a.title}\ntype: {a.type}\n"
              f"year: {a.year or ''}\nfetched: {now()}\nvia: {a.via}\n---\n")
    (r.sources_d / f"{sid}.txt").write_text(header + text)
    r.log("snapshot", id=sid, url=a.url, type=a.type, chars=len(text))
    print(f"OK {sid}")


def snapshot_meta(path: Path) -> tuple[dict, str]:
    raw = path.read_text()
    head, _, body = raw.partition("\n---\n")
    meta = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
    return meta, body


def cmd_evidence(a) -> None:
    r = Run(a.run)
    find_claim(r.claims(), a.claim)
    sp = r.sources_d / f"{a.snapshot}.txt"
    if not sp.exists():
        die(f"unknown snapshot {a.snapshot}")
    ev = r.evidence()
    rec = {"id": next_id("E", ev), "claim": a.claim, "stance": a.stance,
           "snapshot": a.snapshot, "quote": a.quote, "locator": a.locator}
    append_jsonl(r.evidence_p, rec)
    r.log("evidence", **rec)
    ok = quote_in(a.quote, snapshot_meta(sp)[1])
    print(f"OK {rec['id']}" + ("" if ok else " ISSUE quote not found in snapshot"))


def cmd_experiment(a) -> None:
    r = Run(a.run)
    find_claim(r.claims(), a.claim)
    rec = {"claim": a.claim, "hypothesis": a.hypothesis, "command": a.command,
           "result": a.result, "artifact": a.artifact, "t": now()}
    append_jsonl(r.root / "experiments.jsonl", rec)
    r.log("experiment", **rec)
    print("OK experiment recorded")


# -------------------------------------------------------------- verifier ---

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"',
                                   "”": '"', "–": "-", "—": "-"}))
    s = re.sub(r"[*_`#>\[\]]", "", s)  # markdown noise from fetch tools
    return re.sub(r"\s+", " ", s).strip()


def quote_in(quote: str, body: str) -> bool:
    q = norm(quote)
    if not q:
        return False
    if q in norm(body):
        return True
    # allow "..." elisions: every fragment must appear, in order
    parts = [p.strip() for p in re.split(r"\.\.\.|…", q) if p.strip()]
    if len(parts) < 2:
        return False
    b, pos = norm(body), 0
    for p in parts:
        pos = b.find(p, pos)
        if pos < 0:
            return False
        pos += len(p)
    return True


def verify(r: Run) -> dict:
    claims, ev = r.claims(), r.evidence()
    checks: dict[str, list[str]] = {k: [] for k in
                                    ("breadth", "quotes", "coverage", "challenge", "primary",
                                     "contradictions", "budget")}
    # order by position in the append-only log (timestamps tie within a second)
    events = read_jsonl(r.events_p)
    scans = [i for i, e in enumerate(events) if e["event"] == "scan"]
    key_added = [i for i, e in enumerate(events) if e["event"] == "claim_add" and e.get("key")]
    if key_added:
        if not any(i < min(key_added) for i in scans):
            checks["breadth"].append("key claims were written before any breadth scan")
        if not any(i > max(key_added) for i in scans):
            checks["breadth"].append("no final gap-check scan after the last key claim")
    snaps = {p.stem: snapshot_meta(p) for p in r.sources_d.glob("S*.txt")}
    good_ev = []
    for e in ev:
        meta, body = snaps.get(e["snapshot"], ({}, ""))
        if quote_in(e["quote"], body):
            good_ev.append(e)
        else:
            checks["quotes"].append(f"{e['id']} ({e['claim']}) quote not found in {e['snapshot']}")
    by_claim: dict[str, list[dict]] = {}
    for e in good_ev:
        by_claim.setdefault(e["claim"], []).append(e)

    for c in claims:
        cev = by_claim.get(c["id"], [])
        sup = [e for e in cev if e["stance"] == "supports"]
        con = [e for e in cev if e["stance"] == "contradicts"]
        if c["key"]:
            if c["status"] == "open":
                checks["coverage"].append(f"{c['id']} key claim still open")
            elif c["status"] != "unresolved" and not cev:
                checks["coverage"].append(f"{c['id']} {c['status']} without verified evidence")
            if not c["confidence"] and c["status"] != "open":
                checks["coverage"].append(f"{c['id']} has no confidence")
            if not c["challenges"]:
                checks["challenge"].append(f"{c['id']} key claim never challenged")
        if c["status"] == "supported" and c["confidence"] == "high":
            if not any(snaps[e["snapshot"]][0].get("type") == "primary" for e in sup):
                checks["primary"].append(f"{c['id']} high confidence without primary source")
        if con and c["status"] == "supported" and not c["note"]:
            checks["contradictions"].append(
                f"{c['id']} supported despite contradicting {','.join(e['id'] for e in con)}"
                " with no resolution note")
        if c["status"] == "refuted" and not con:
            checks["contradictions"].append(f"{c['id']} refuted without contradicting evidence")
    b, s = r.meta["budget"], r.meta["spent"]
    for k in BUDGET_KINDS:
        if s[k] > b[k]:
            checks["budget"].append(f"{k} overspent {s[k]}/{b[k]}")
    return {"t": now(), "pass": not any(checks.values()),
            "checks": {k: {"pass": not v, "issues": v} for k, v in checks.items()},
            "verified_evidence": len(good_ev), "evidence": len(ev)}


def cmd_verify(a) -> None:
    r = Run(a.run)
    res = verify(r)
    write_json(r.root / "verify.json", res)
    r.log("verify", passed=res["pass"],
          failed=[k for k, v in res["checks"].items() if not v["pass"]])
    for k, v in res["checks"].items():
        print(f"{'PASS' if v['pass'] else 'FAIL'} {k}")
        for i in v["issues"]:
            print(f"ISSUE {k}: {i}")
    print(f"evidence verified {res['verified_evidence']}/{res['evidence']}")
    sys.exit(0 if res["pass"] else EXIT_VERIFY)


# ---------------------------------------------------------------- report ---

def cmd_report(a) -> None:
    r = Run(a.run)
    res = verify(r)
    claims, ev = r.claims(), r.evidence()
    snaps = {p.stem: snapshot_meta(p)[0] for p in r.sources_d.glob("S*.txt")}
    synth_p = r.root / "synthesis.md"
    synthesis = synth_p.read_text().strip() if synth_p.exists() else \
        "_No synthesis.md written: the agent must write the judgment-level answer._"
    b, s = r.meta["budget"], r.meta["spent"]
    out = [f"# {r.meta['goal']}", ""]
    if not res["pass"]:
        failed = [k for k, v in res["checks"].items() if not v["pass"]]
        out += [f"> **DRAFT — verification failed: {', '.join(failed)}.** "
                "Treat affected claims as unverified.", ""]
    out += [synthesis, "", "## Claim ledger", "",
            "| Claim | Status | Confidence | Evidence (verified quote → source) |",
            "|---|---|---|---|"]
    good = {e["id"] for e in ev if quote_in(e["quote"], snapshot_meta(
        r.sources_d / f"{e['snapshot']}.txt")[1])}
    for c in claims:
        refs = []
        for e in ev:
            if e["claim"] != c["id"]:
                continue
            m = snaps.get(e["snapshot"], {})
            mark = "" if e["id"] in good else " ⚠unverified"
            sign = {"supports": "+", "contradicts": "−", "context": "~"}[e["stance"]]
            refs.append(f"{sign} [{m.get('title', e['snapshot'])}]({m.get('url', '')})"
                        f" ({m.get('type', '?')}){mark}")
        key = "**" if c["key"] else ""
        out.append(f"| {key}{c['id']}{key}: {c['text']} | {c['status']} | "
                   f"{c['confidence'] or '-'} | {'<br>'.join(refs) or '-'} |")
    contested = [c for c in claims if c["status"] in ("contested", "unresolved", "refuted")
                 or any(e["claim"] == c["id"] and e["stance"] == "contradicts" for e in ev)]
    out += ["", "## Contradictions and open uncertainty", ""]
    out += [f"- **{c['id']}** ({c['status']}): {c['text']}"
            + (f" — {c['note']}" if c["note"] else "") for c in contested] or ["- none recorded"]
    out += ["", "## Run accounting", "",
            f"- Status: {r.meta['status']} ({r.meta.get('stop_reason') or 'active'})",
            f"- Elapsed: {r.elapsed_minutes():.1f} min (budget {b['minutes']})",
            "- Spent: " + ", ".join(f"{k} {s[k]}/{b[k]}" for k in BUDGET_KINDS),
            f"- Verification: {'PASS' if res['pass'] else 'FAIL'}; "
            f"{res['verified_evidence']}/{res['evidence']} quotes matched snapshots",
            f"- Sources snapshotted: {len(snaps)} "
            f"({sum(1 for m in snaps.values() if m.get('type') == 'primary')} primary)"]
    (r.root / "findings.md").write_text("\n".join(out) + "\n")
    r.log("report", verified=res["pass"])
    print(f"OK {r.root / 'findings.md'} verified={res['pass']}")


# ------------------------------------------------------------- knowledge ---

def cmd_learn(a) -> None:
    """Promote verified, settled claims and follow-ups into the knowledge base."""
    r = Run(a.run)
    kb = Path(a.kb or r.meta.get("kb") or die("no --kb given"))
    kb.mkdir(parents=True, exist_ok=True)
    res = verify(r)
    good = [e for e in r.evidence() if quote_in(e["quote"], snapshot_meta(
        r.sources_d / f"{e['snapshot']}.txt")[1])]
    promoted = 0
    existing = {(k["run"], k["claim_id"]) for k in read_jsonl(kb / "claims.jsonl")}
    for c in r.claims():
        if c["status"] not in ("supported", "refuted", "contested"):
            continue
        cev = [e for e in good if e["claim"] == c["id"]]
        if not cev or (r.meta["id"], c["id"]) in existing:
            continue
        srcs = []
        for e in cev:
            m, _ = snapshot_meta(r.sources_d / f"{e['snapshot']}.txt")
            srcs.append({"url": m.get("url"), "title": m.get("title"),
                         "type": m.get("type"), "stance": e["stance"], "quote": e["quote"]})
        append_jsonl(kb / "claims.jsonl", {
            "run": r.meta["id"], "claim_id": c["id"], "learned": now(),
            "text": c["text"], "status": c["status"], "confidence": c["confidence"],
            "note": c["note"], "sources": srcs, "run_verified": res["pass"]})
        promoted += 1
    qs = 0
    synth = r.root / "synthesis.md"
    if synth.exists():
        m = re.search(r"^##\s*Follow-up questions\s*$(.*?)(?=^##\s|\Z)",
                      synth.read_text(), re.M | re.S)
        for line in (m.group(1).splitlines() if m else []):
            q = re.sub(r"^\s*[-*\d.]+\s*", "", line).strip()
            if q:
                append_jsonl(kb / "questions.jsonl",
                             {"run": r.meta["id"], "question": q, "t": now()})
                qs += 1
    lessons = r.root / "lessons.md"
    if lessons.exists() and lessons.read_text().strip():
        with (kb / "lessons.md").open("a") as f:
            f.write(f"\n## {r.meta['id']} ({now()[:10]})\n\n{lessons.read_text().strip()}\n")
    r.log("learn", kb=str(kb), promoted=promoted, questions=qs)
    print(f"OK promoted={promoted} questions={qs} kb={kb}")


def cmd_kb_search(a) -> None:
    kb = Path(a.kb)
    terms = [t.lower() for t in a.terms]
    rows = []
    for k in read_jsonl(kb / "claims.jsonl"):
        hay = norm(k["text"] + " " + k.get("note", ""))
        score = sum(hay.count(t) for t in terms)
        if score:
            rows.append((score, k))
    for score, k in sorted(rows, key=lambda x: -x[0])[: a.limit]:
        urls = ", ".join(s["url"] for s in k["sources"][:3])
        print(f"[{k['status']}/{k['confidence']}] {k['text']}  <{k['run']}:{k['claim_id']}> {urls}")
    if not rows:
        print("no matches")
    for line in (kb / "lessons.md").read_text().splitlines()[-15:] if (kb / "lessons.md").exists() and a.lessons else []:
        print(f"LESSON {line}")


# ------------------------------------------------------------------- cli ---

def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("run"); s.add_argument("--goal", required=True)
    s.add_argument("--max-searches", type=int, default=20)
    s.add_argument("--max-fetches", type=int, default=20)
    s.add_argument("--max-experiments", type=int, default=3)
    s.add_argument("--max-minutes", type=float, default=45)
    s.add_argument("--kb"); s.set_defaults(f=cmd_init)

    s = sub.add_parser("charge"); s.add_argument("run"); s.add_argument("kind", choices=BUDGET_KINDS)
    s.add_argument("-n", type=int, default=1); s.add_argument("--note", default="")
    s.set_defaults(f=cmd_charge)

    s = sub.add_parser("status"); s.add_argument("run"); s.set_defaults(f=cmd_status)
    s = sub.add_parser("finish"); s.add_argument("run"); s.add_argument("--reason", default="goal answered")
    s.set_defaults(f=cmd_finish)

    s = sub.add_parser("claim-add"); s.add_argument("run"); s.add_argument("text")
    s.add_argument("--key", action="store_true"); s.add_argument("--parent")
    s.set_defaults(f=cmd_claim_add)
    s = sub.add_parser("claim-set"); s.add_argument("run"); s.add_argument("id")
    s.add_argument("--status", choices=CLAIM_STATUSES); s.add_argument("--confidence", choices=CONFIDENCE)
    s.add_argument("--note"); s.set_defaults(f=cmd_claim_set)
    s = sub.add_parser("challenge"); s.add_argument("run"); s.add_argument("claim")
    s.add_argument("--query", required=True); s.add_argument("--found", choices=("yes", "no"), required=True)
    s.set_defaults(f=cmd_challenge)

    s = sub.add_parser("scan"); s.add_argument("run"); s.add_argument("--query", required=True)
    s.add_argument("--lineages", required=True, help="';'-separated evidence families found")
    s.add_argument("--new", choices=("yes", "no"), default="yes",
                   help="did this scan reveal lineages not yet covered by key claims?")
    s.set_defaults(f=cmd_scan)
    s = sub.add_parser("snapshot"); s.add_argument("run"); s.add_argument("--url", required=True)
    s.add_argument("--title", required=True); s.add_argument("--type", choices=SOURCE_TYPES, required=True)
    s.add_argument("--year"); s.add_argument("--via", default="fetch")
    s.add_argument("--file", help="text file; default stdin"); s.set_defaults(f=cmd_snapshot)
    s = sub.add_parser("evidence"); s.add_argument("run"); s.add_argument("claim")
    s.add_argument("--snapshot", required=True); s.add_argument("--stance", choices=STANCES, required=True)
    s.add_argument("--quote", required=True); s.add_argument("--locator", default="")
    s.set_defaults(f=cmd_evidence)
    s = sub.add_parser("experiment"); s.add_argument("run"); s.add_argument("claim")
    for f in ("hypothesis", "command", "result"):
        s.add_argument(f"--{f}", required=True)
    s.add_argument("--artifact", default=""); s.set_defaults(f=cmd_experiment)

    s = sub.add_parser("verify"); s.add_argument("run"); s.set_defaults(f=cmd_verify)
    s = sub.add_parser("report"); s.add_argument("run"); s.set_defaults(f=cmd_report)
    s = sub.add_parser("learn"); s.add_argument("run"); s.add_argument("--kb"); s.set_defaults(f=cmd_learn)
    s = sub.add_parser("kb-search"); s.add_argument("kb"); s.add_argument("terms", nargs="+")
    s.add_argument("--limit", type=int, default=10); s.add_argument("--lessons", action="store_true")
    s.set_defaults(f=cmd_kb_search)

    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
