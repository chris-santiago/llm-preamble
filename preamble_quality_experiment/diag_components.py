# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
"""Diagnostic: which CQS component (if any) separates preamble conditions?

Reads experiment2_results/full_results.jsonl and reports, per component:
  - mean by condition (main conditions only)
  - Kruskal-Wallis across main conditions
Also audits whether static sub-metrics are degenerate (zero-variance).

This is a read-only post-hoc diagnostic; it does not mutate experiment artifacts.
"""
import json
from pathlib import Path

import numpy as np
from scipy import stats

RESULTS = Path("experiment2_results/full_results.jsonl")
MAIN_CONDITIONS = [
    "none", "minimal", "generic_coding", "real_agent",
    "negative_control", "persona_only", "long_directive",
]
COMPONENTS = ["static_score", "ast_score", "llm_idiom_score", "llm_comment_score", "cqs"]

rows = [json.loads(l) for l in RESULTS.read_text().splitlines() if l.strip()]
print(f"Loaded {len(rows)} scored rows")
print(f"Models present: {sorted({r['model'].split('/')[-1] for r in rows})}")
counts = {c: sum(1 for r in rows if r["preamble"] == c) for c in MAIN_CONDITIONS + ["trivial_baseline"]}
print(f"Rows per condition: {counts}")

print("\n=== Component separation across main conditions ===")
print(f"{'component':<20} {'KW H':>8} {'KW p':>9}   per-condition means")
for comp in COMPONENTS:
    groups = []
    means = []
    for c in MAIN_CONDITIONS:
        vals = [r[comp] for r in rows if r["preamble"] == c and r.get(comp) is not None]
        if vals:
            groups.append(vals)
            means.append(f"{c[:4]}={np.mean(vals):.3f}")
    if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
        H, p = stats.kruskal(*groups)
    else:
        H, p = float("nan"), float("nan")
    flag = "  <-- SEPARATES" if p < 0.05 else ""
    print(f"{comp:<20} {H:>8.3f} {p:>9.4f}   {' '.join(means)}{flag}")

print("\n=== Static sub-metric variance audit (raw_* fields) ===")
raw_keys = [
    "raw_maintainability_index", "raw_avg_cyclomatic", "raw_halstead_difficulty",
    "raw_pylint_penalty", "raw_cognitive_complexity_violations",
    "raw_bare_except_count", "raw_max_nesting_depth",
]
for k in raw_keys:
    vals = [r[k] for r in rows if r.get(k) is not None]
    if vals:
        arr = np.array(vals, dtype=float)
        nonzero = int((arr != 0).sum())
        print(f"  {k:<40} min={arr.min():.2f} max={arr.max():.2f} mean={arr.mean():.3f} nonzero={nonzero}/{len(arr)}")
    else:
        print(f"  {k:<40} MISSING")

print("\n=== Separation within refactoring vs creation tasks (cqs) ===")
creation = {"task_lru_ttl_cache", "task_recursive_parser", "task_async_conn_pool"}
for group_name, task_filter in [("creation", lambda t: t in creation),
                                 ("refactoring", lambda t: t not in creation)]:
    sub = [r for r in rows if task_filter(r["task_id"])]
    groups = [[r["cqs"] for r in sub if r["preamble"] == c] for c in MAIN_CONDITIONS]
    groups = [g for g in groups if len(g) >= 2]
    if len(groups) >= 2:
        H, p = stats.kruskal(*groups)
        print(f"  {group_name:<12} n={len(sub):<4} KW H={H:.3f} p={p:.4f}")
