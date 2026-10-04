#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Generate benchmark comparison report")
    parser.add_argument("--benchmark-dir", required=True, help="Path to benchmark run directory")
    parser.add_argument("--output", help="Output markdown file path (defaults to <benchmark-dir>/BENCH-REPORT.md)")
    return parser.parse_args()

def get_file_content(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return default

def get_diff_stats(diff_path):
    if not os.path.exists(diff_path):
        return {"files": 0, "additions": 0, "deletions": 0}
    
    touched = set()
    additions = 0
    deletions = 0
    with open(diff_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("+++ "):
                # Unified diff header; tolerate a/ b/ prefixes, absolute paths,
                # and trailing timestamps.
                path = line[4:].split("\t")[0].strip()
                if path and path != "/dev/null":
                    if path.startswith(("a/", "b/")):
                        path = path[2:]
                    touched.add(path)
            elif line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
    return {"files": len(touched), "additions": additions, "deletions": deletions}

def main():
    args = parse_args()
    bench_dir = Path(args.benchmark_dir).resolve()
    control_dir = bench_dir / "control"
    
    if not control_dir.exists():
        print(f"Error: Control directory not found: {control_dir}", file=sys.stderr)
        sys.exit(1)
        
    meta_path = control_dir / "meta.json"
    if not meta_path.exists():
        print(f"Error: Missing meta.json in {control_dir}", file=sys.stderr)
        sys.exit(1)
        
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    task_id = meta.get("task_id", "unknown-task")
    specs = meta.get("candidate_specs", {})
    comparison_mode = meta.get("comparison_mode", "mixed")
    candidates = meta.get("candidates", [])
    created_at = meta.get("created_at", "")
    
    mapping_path = control_dir / "mapping.json"
    mapping = {}
    reverse_mapping = {}
    if mapping_path.exists():
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
                reverse_mapping = {v: k for k, v in mapping.items()}
        except Exception:
            pass

    judge_verdict = get_file_content(control_dir / "claude-verdict.txt") or get_file_content(control_dir / "judge-verdict.txt")

    # Gather candidate stats
    rows = []
    for cand in candidates:
        status_path = control_dir / f"{cand}.evaluator.status"
        status = get_file_content(status_path, default="PENDING")
        
        seconds_path = control_dir / f"{cand}.seconds"
        seconds = get_file_content(seconds_path, default="--")
        
        diff_path = control_dir / f"{cand}.diff"
        stats = get_diff_stats(diff_path)
        diff_summary = f"{stats['files']} files (+{stats['additions']}/-{stats['deletions']})"
        
        label = reverse_mapping.get(cand, "--")
        spec = specs.get(cand, {})
        run_status = get_file_content(control_dir / f"{cand}.run.status", default="--")

        rows.append({
            "candidate": cand,
            "label": label,
            "harness": spec.get("harness") or "--",
            "model": spec.get("model_id") or "--",
            "run_status": run_status,
            "status": status,
            "seconds": seconds,
            "diff_summary": diff_summary
        })

    out_file = args.output or (bench_dir / "BENCH-REPORT.md")
    
    report_lines = [
        f"# Model Benchmark Report: {task_id}",
        "",
        f"- **Benchmark Directory**: `{bench_dir}`",
        f"- **Task ID**: `{task_id}`",
        f"- **Date**: {created_at}",
        f"- **Comparison Mode**: `{comparison_mode}`" + (
            "  (model held constant across harnesses)" if comparison_mode == "harness-comparison"
            else "  (harness held constant across models)" if comparison_mode == "model-comparison"
            else ""),
        "",
        "## Summary Matrix",
        "",
        "| Candidate | Harness | Model | Blind Label | Run | Deterministic Result | Duration (s) | Diff Size |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for r in rows:
        status_badge = "✅ PASS" if r["status"] == "PASS" else ("❌ FAIL" if r["status"] == "FAIL" else r["status"])
        report_lines.append(
            f"| `{r['candidate']}` | `{r['harness']}` | `{r['model']}` | `{r['label']}` | "
            f"{r['run_status']} | {status_badge} | {r['seconds']} | {r['diff_summary']} |"
        )

    if comparison_mode == "harness-comparison":
        report_lines.extend([
            "",
            "> Same model, different harnesses. Differences here are attributable to the",
            "> harness: system prompt, tool set, context management, and approval policy.",
            "> Note any candidate whose `Run` column is `BLOCKED` or `TIMEOUT` — that is a",
            "> harness outcome, not a model outcome.",
        ])
        
    report_lines.extend([
        "",
        "## Detailed Candidate Evaluations",
        ""
    ])
    
    for cand in candidates:
        eval_out = get_file_content(control_dir / f"{cand}.evaluator.txt", "No evaluator output recorded.")
        # Truncate if long
        eval_lines = eval_out.splitlines()
        truncated = "\n".join(eval_lines[-25:]) if len(eval_lines) > 25 else eval_out
        
        report_lines.extend([
            f"### Candidate: `{cand}`",
            "",
            "```text",
            truncated,
            "```",
            ""
        ])

    if judge_verdict:
        report_lines.extend([
            "## Blind LLM Judge Verdict",
            "",
            judge_verdict,
            ""
        ])

    final_report = "\n".join(report_lines)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(final_report)
        
    print(f"Benchmark report generated successfully at: {out_file}")

if __name__ == "__main__":
    main()
