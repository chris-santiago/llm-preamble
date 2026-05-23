# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai",
#   "matplotlib",
#   "scipy",
#   "numpy",
# ]
# ///
"""Checklist-rubric re-analysis of saved generations.

Tests whether preambles move *specific* python-coder-agent quality dimensions
(the 9-item lite-review gate, restricted to the 8 items measurable in a
single-file setting). Reads the existing generation_results.jsonl — no new
code generation. ~822 LLM judge calls (3-judge panel × 274 samples).

For each (sample, judge) pair, the judge returns a binary {0=smell absent,
1=smell present} for each of 8 smells plus a one-sentence rationale. Per-item
smell rate is then tested across preamble conditions via Kruskal-Wallis.

Per the F3 result (self-preference bias was negligible but real, d=0.16),
self-judgments are excluded from the primary analysis.
"""
import asyncio
import json
from pathlib import Path

import numpy as np
from scipy import stats
from openai import AsyncOpenAI

import preamble_quality_experiment2 as exp

RESULTS_DIR = exp.RESULTS_DIR
MAIN_CONDITIONS = exp.MAIN_CONDITIONS
PREAMBLE_ORDER = exp.PREAMBLE_ORDER
PREAMBLE_LABELS = exp.PREAMBLE_LABELS

JUDGES = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-v3.2",
    "mistralai/mistral-small-2603",
]

# 8-item rubric — single-file-measurable subset of python-coder S3+ + lite gate
RUBRIC = [
    ("mode_flag",          "Does the code introduce boolean or mode-flag parameters on a non-underscore-prefixed function? (e.g. `def foo(x, *, verbose=False, dry_run=False, strict=True)`)"),
    ("dict_domain",        "Does the code RETURN or ACCEPT dict-shaped domain data across a function boundary where a dataclass / TypedDict / NamedTuple would clarify the structure? (a typed object would be more idiomatic)"),
    ("hidden_side_effects","Are there hidden side effects inside a function that LOOKS pure from its signature? (env-var reads, filesystem access, logging embedded in computation, mutating global/module-level state)"),
    ("swallowed_excepts",  "Is there any except clause that swallows the exception? (e.g. `except ...: pass`, or catching then returning a silent sentinel without re-raising or typed handling)"),
    ("broad_except",       "Is there a broad `except Exception` or bare `except:` at a library/function boundary without specific re-raise or narrowly-typed handling?"),
    ("dead_code",          "Are there unused imports, dead code branches, or sentinel return values that are never meaningfully checked?"),
    ("orch_mixed_impl",    "Does any single function BOTH coordinate workflow (calling many helpers, sequencing steps) AND do low-level transforms / I/O inline? (orchestration mixed with implementation in one function)"),
    ("overgrown_class",    "Are there classes with many methods, weak invariants, or vague catch-all names (Manager / Handler / Helper / Processor) that should probably be a module of functions or smaller collaborators?"),
]
ITEM_IDS = [k for k, _ in RUBRIC]

SYSTEM_PROMPT = (
    "You are a senior Python code reviewer applying a strict 8-item smell checklist.\n"
    "For each item below, decide ABSENT (0) or PRESENT (1) on the code shown.\n"
    "Only flag a smell that is CLEARLY present in the code as written — do not speculate about hypothetical usage.\n"
    "If the code is too short or trivial to exhibit a smell, mark it ABSENT.\n\n"
    "Items:\n"
    + "\n".join(f"  {i+1}. {k}: {desc}" for i, (k, desc) in enumerate(RUBRIC))
    + "\n\n"
    "Respond with ONLY a single JSON object — no prose, no markdown fences:\n"
    "{\n"
    + ",\n".join(f'  "{k}": {{"score": 0, "rationale": "<one short sentence>"}}' for k in ITEM_IDS)
    + "\n}\n"
)


async def judge_one(client: AsyncOpenAI, sem: asyncio.Semaphore,
                    sample: dict, judge_model: str) -> dict:
    user_msg = f"Code under review:\n\n```python\n{sample['code']}\n```"
    text, err = await exp._call_one(
        client, sem, judge_model, SYSTEM_PROMPT, user_msg,
        label=f"rubric|{sample['task_id']}|{sample['preamble']}|{sample['model']}|{judge_model}",
        temperature=0.1, max_tokens=900, timeout=exp.JUDGE_TIMEOUT,
    )
    base = {
        "task_id": sample["task_id"], "preamble": sample["preamble"],
        "subject_model": sample["model"], "judge_model": judge_model,
    }
    if err:
        return {**base, **{k: None for k in ITEM_IDS}, "judge_error": err}
    parsed = exp._extract_json_safe(text)
    if parsed is None:
        return {**base, **{k: None for k in ITEM_IDS},
                "judge_error": f"Parse failure: {text[:100]}"}
    out = {**base, "judge_error": None}
    for k in ITEM_IDS:
        entry = parsed.get(k, {})
        if isinstance(entry, dict):
            s = entry.get("score")
        else:
            s = entry  # tolerant of {item: 0/1} shape
        try:
            out[k] = int(s) if s in (0, 1, "0", "1") else None
        except (TypeError, ValueError):
            out[k] = None
    return out


async def run_rubric_judging(samples: list[dict]) -> list[dict]:
    client = AsyncOpenAI(api_key=exp.get_api_key(), base_url=exp.OPENROUTER_BASE_URL)
    sem = asyncio.Semaphore(exp.CONCURRENCY)
    jobs = [(s, j) for s in samples for j in JUDGES]
    print(f"[rubric] {len(jobs)} judge calls queued ({len(samples)} samples × {len(JUDGES)} judges)...")
    results = await asyncio.gather(*[judge_one(client, sem, s, j) for s, j in jobs])
    ok = sum(1 for r in results if r.get("judge_error") is None)
    print(f"[rubric] Done: {ok}/{len(results)} judge calls successful")
    return list(results)


def aggregate_to_sample_level(rubric_records: list[dict]) -> list[dict]:
    """Per-sample mean across cross-judges (self-judge excluded)."""
    by_sample: dict[tuple, list[dict]] = {}
    for r in rubric_records:
        if r["subject_model"] == r["judge_model"]:
            continue  # exclude self-judgment
        if r["judge_error"]:
            continue
        key = (r["task_id"], r["preamble"], r["subject_model"])
        by_sample.setdefault(key, []).append(r)

    out = []
    for (task, pre, model), recs in by_sample.items():
        row = {"task_id": task, "preamble": pre, "model": model, "n_judges": len(recs)}
        for k in ITEM_IDS:
            vals = [rec[k] for rec in recs if rec.get(k) is not None]
            row[k] = float(np.mean(vals)) if vals else None
        out.append(row)
    return out


def per_item_separation(sample_rows: list[dict]) -> dict:
    """KW per item across main conditions + overall smell-load score."""
    summary = {}
    # also compute overall smell load = mean of all 8 items per sample (lower=better)
    for r in sample_rows:
        vals = [r[k] for k in ITEM_IDS if r.get(k) is not None]
        r["_smell_load"] = float(np.mean(vals)) if vals else None

    for key in ITEM_IDS + ["_smell_load"]:
        means = {}
        groups = []
        for c in MAIN_CONDITIONS:
            vals = [r[key] for r in sample_rows if r["preamble"] == c and r.get(key) is not None]
            if vals:
                means[c] = float(np.mean(vals))
                groups.append(vals)
        if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
            H, p = stats.kruskal(*groups)
        else:
            H, p = float("nan"), float("nan")
        summary[key] = {"H": float(H), "p": float(p), "means": means,
                        "significant": bool(p < 0.05)}
    return summary


def plot_per_item(summary: dict, sample_rows: list[dict], out: Path) -> None:
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 3, figsize=(15, 10), sharey=True)
    axes = axes.flat
    items = ITEM_IDS + ["_smell_load"]
    cond_order = [c for c in PREAMBLE_ORDER if c in MAIN_CONDITIONS]
    cond_labels = [PREAMBLE_LABELS[c] for c in cond_order]

    for ax, item in zip(axes, items):
        means = [summary[item]["means"].get(c, 0.0) for c in cond_order]
        p = summary[item]["p"]
        color = "#2ca02c" if p < 0.05 else "#888888"
        ax.bar(range(len(cond_order)), means, color=color)
        ax.set_xticks(range(len(cond_order)))
        ax.set_xticklabels(cond_labels, rotation=40, ha="right", fontsize=7)
        title = item if item != "_smell_load" else "overall smell load"
        ax.set_title(f"{title}  (p={p:.3f})", fontsize=10)
        ax.set_ylim(0, 1)
    fig.suptitle("Per-item smell rate by preamble condition (lower = better)\n"
                 "green = preamble effect significant (KW p<0.05)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=120)
    print(f"[viz] {out.name}")


def main() -> None:
    gen_path = RESULTS_DIR / "generation_results.jsonl"
    gens = [json.loads(l) for l in gen_path.read_text().splitlines() if l.strip()]
    samples = [g for g in gens
               if g.get("code") and not g.get("error")
               and g.get("extraction_method") != "extraction_failed"]
    print(f"Loaded {len(gens)} generations; {len(samples)} have valid code.")

    rubric_records = asyncio.run(run_rubric_judging(samples))
    (RESULTS_DIR / "rubric_judge_records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rubric_records) + "\n")

    sample_rows = aggregate_to_sample_level(rubric_records)
    print(f"Aggregated to {len(sample_rows)} sample-level rows (cross-judge mean per item).")

    summary = per_item_separation(sample_rows)
    print(f"\n{'Item':<22} {'KW H':>7} {'KW p':>9}   per-condition smell rate (lower=better)")
    for item in ITEM_IDS + ["_smell_load"]:
        s = summary[item]
        flag = "  <-- SEPARATES" if s["significant"] else ""
        order_pairs = sorted(s["means"].items(), key=lambda kv: kv[0])
        means_str = "  ".join(f"{c[:4]}={v:.2f}" for c, v in order_pairs)
        print(f"{item:<22} {s['H']:>7.2f} {s['p']:>9.4f}   {means_str}{flag}")

    plot_per_item(summary, sample_rows, RESULTS_DIR / "rubric_per_item_smell_rate.png")

    out = {
        "rubric_items": [{"id": k, "description": d} for k, d in RUBRIC],
        "judges": JUDGES,
        "n_samples_judged": len(samples),
        "n_sample_rows_cross_judge": len(sample_rows),
        "per_item_separation": summary,
    }
    (RESULTS_DIR / "rubric_summary.json").write_text(json.dumps(out, indent=2))
    print(f"\nSaved rubric_summary.json + rubric_judge_records.jsonl + figure.")


if __name__ == "__main__":
    main()
