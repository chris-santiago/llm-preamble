# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Phase D2 re-judge with calibrated multi-judge panel.

Trigger: the single-judge gpt-4o-mini panel saturated at severity=0 on 7 of 9
algorithmic dimensions with positive-toned rationales — a judge-calibration
failure, not a rubric-design failure. Per user direction, re-judge the existing
32 reprobe generations with:
  (a) a 3-judge panel drawn from the v2 non-reasoning tier
        - openai/gpt-4o-mini
        - deepseek/deepseek-v3.2
        - mistralai/mistral-small-2603
  (b) an explicit calibration anchor in the rubric prompt instructing judges
      that severity 0 should be uncommon; most realistic code has minor issues
      on multiple dimensions.

No new generations — uses reprobe_results/generations.json from the prior run.
Outputs reprobe_results/PHASE_D2_RECHECK_REPORT.md.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

import httpx

ROOT = Path(__file__).parent
OUTDIR = ROOT / "reprobe_results"
GEN_FILE = OUTDIR / "generations.json"

JUDGE_PANEL = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-v3.2",
    "mistralai/mistral-small-2603",
]
JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_TOKENS = 1800
JUDGE_TIMEOUT = 120.0
CONCURRENCY = 50          # match preflight + v1 rubric run
RETRY_ATTEMPTS = 2

# Identical rubric to reprobe_phase_c_d2.py — kept inline for stand-alone re-judge.
NEW_RUBRIC = [
    ("data_structure_choice",        "Inappropriate data structure picks (e.g., list for membership testing, dict where dataclass/NamedTuple would clarify, list where deque is the right tool for FIFO).",  "always"),
    ("algorithm_correctness",        "Algorithm fails to meet stated complexity/correctness requirements (wrong output, wrong big-O, breaks on documented edge cases).",                                          "always"),
    ("error_handling_inconsistency", "Inconsistent or ad-hoc error handling (some paths raise, others silently return None; sentinels mixed with exceptions; no coherent philosophy).",                          "always"),
    ("api_ergonomics",               "Public API is awkward for callers (positional-arg explosion, leaky internals, inconsistent method naming, no kwargs where they'd clarify).",                              "always"),
    ("abstraction_miscalibration",   "Over- or under-engineered for the task (speculative class hierarchies for one function; one god-function for what should be 3 cohesive units).",                          "always"),
    ("code_organization",            "Tangled decomposition; functions doing too many things; unclear boundaries between layers.",                                                                              "always"),
    ("type_hint_gap",                "Public surface lacks correct/complete type annotations (private helpers exempt; 0=full coverage, 5=none).",                                                               "always"),
    ("edge_case_gap",                "Obvious edge cases not handled (empty inputs, boundary conditions, invalid inputs).",                                                                                     "always"),
    ("documentation_appropriateness","Docstrings/comments mismatched to code complexity (overly verbose for trivial code, missing for complex code, what-not-why comments).",                                   "always"),
    ("concurrency_safety",           "When the task requires concurrency: race conditions, missing locks, broken async patterns, double-checked-locking bugs. If the task does NOT involve concurrency, return null.", "conditional"),
    ("example_quality",              "When usage examples are requested: trivial/redundant examples that fail to demonstrate the API's real shape. If no examples are requested, return null.",                "conditional"),
]
NEW_ITEM_IDS = [k for k, _, _ in NEW_RUBRIC]
ALWAYS_ON_IDS = [k for k, _, kind in NEW_RUBRIC if kind == "always"]


CALIBRATION_ANCHOR = (
    "CALIBRATION (READ CAREFULLY):\n"
    "  - The 0-5 severity scale is NOT 'present vs absent'. It is a graded measure.\n"
    "  - Severity 0 means 'no detectable issue on this dimension' — uncommon. \n"
    "    Reserve it for code that is genuinely exemplary on that specific dimension.\n"
    "  - Severity 1 = a minor nuance (e.g., one type hint missing on a non-public helper;\n"
    "    one docstring slightly verbose). Most realistic algorithmic code has\n"
    "    severity 1-2 on AT LEAST 3 of the 9 always-on dimensions.\n"
    "  - Severity 2-3 = noticeable but not pervasive (e.g., one function mixing two\n"
    "    concerns; a list used where set would be marginally better).\n"
    "  - Severity 4-5 = pervasive or material defect.\n"
    "  - Refuse to score 0 unless you can name a specific reason the code is \n"
    "    unimprovable on that dimension. Do NOT default to 0 because nothing\n"
    "    obvious is wrong — score 1 when the dimension is fine-but-not-exemplary.\n"
    "  - Your job is to surface real variation between samples. If every sample\n"
    "    gets 0 on most dims, the scoring is useless to the experiment.\n"
)


def _build_rubric_judge_calibrated() -> str:
    lines = "\n".join(f"  - {k}: {desc}" for k, desc, _ in NEW_RUBRIC)
    schema_inner = ",\n  ".join(
        f'"{k}": {{"severity": <0-5 or null>, "rationale": "<one sentence>"}}'
        for k in NEW_ITEM_IDS
    )
    return (
        "You are a senior Python code reviewer scoring an algorithmic Python sample on "
        "11 specific quality dimensions on a 0-5 severity scale "
        "(0=clean / no detectable issue, 5=severe / pervasive).\n\n"
        + CALIBRATION_ANCHOR +
        "\nFor the two CONDITIONAL dimensions (concurrency_safety, example_quality), "
        "return null only if the dimension does not apply to this code (no concurrency "
        "requirement; no examples requested in the task).\n\n"
        "Dimensions:\n" + lines + "\n\n"
        "Respond with ONLY a single JSON object, no markdown fences, no prose:\n"
        "{\n  " + schema_inner + "\n}\n"
    )


RUBRIC_JUDGE_PROMPT = _build_rubric_judge_calibrated()


def _to_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _clamp(value: Any, lo: float, hi: float) -> float | None:
    f = _to_float(value)
    if f is None or f < lo or f > hi:
        return None
    return f


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def _post(client, sem, *, model, system, user, temperature, max_tokens, timeout) -> dict:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_err = None
    async with sem:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                        "Content-Type": "application/json",
                    },
                    json=body, timeout=timeout,
                )
                resp = r.json()
                if r.status_code != 200 or "error" in resp:
                    last_err = f"HTTP {r.status_code}: {resp.get('error', resp)}"
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                msg = resp["choices"][0]["message"]
                content = (msg.get("content") or "").strip()
                u = resp.get("usage", {})
                return {"content": content, "cost": u.get("cost", 0.0), "error": None}
            except Exception as exc:  # noqa: BLE001
                last_err = f"{type(exc).__name__}: {exc}"
                await asyncio.sleep(1.0 * (attempt + 1))
    return {"content": "", "cost": 0.0, "error": last_err}


async def judge_one(client, sem, *, code: str, judge_model: str) -> dict:
    user = f"Code under review:\n\n```python\n{code}\n```"
    result = await _post(
        client, sem,
        model=judge_model, system=RUBRIC_JUDGE_PROMPT, user=user,
        temperature=JUDGE_TEMPERATURE, max_tokens=JUDGE_MAX_TOKENS, timeout=JUDGE_TIMEOUT,
    )
    if result["error"]:
        return {"judge_error": result["error"], "parsed": None, "cost": 0.0}
    parsed = _extract_json(result["content"])
    if parsed is None:
        return {"judge_error": f"parse_fail: {result['content'][:120]}",
                "parsed": None, "cost": result["cost"]}
    return {"judge_error": None, "parsed": parsed, "cost": result["cost"]}


def analyze(generations: list[dict], all_judgments: list[dict]) -> dict:
    """Compute panel-mean severity per (gen, dim), then per-dim prevalence."""
    # Group judgments by gen_idx, then aggregate across judges
    by_gen: dict[int, list[dict]] = defaultdict(list)
    for j in all_judgments:
        if j.get("parsed") is not None:
            by_gen[j["gen_idx"]].append(j)

    per_dim_scores: dict[str, list[float]] = defaultdict(list)  # cross-judge means
    per_dim_na: dict[str, int] = defaultdict(int)
    per_judge_means: dict[tuple[str, str], list[float]] = defaultdict(list)  # judge → dim → means
    n_scored = 0

    for gid, gen in enumerate(generations):
        if not gen["extraction_ok"]:
            continue
        judgments_here = by_gen.get(gid, [])
        if not judgments_here:
            continue
        n_scored += 1
        for k in NEW_ITEM_IDS:
            sevs_this_sample: list[float] = []
            nulls_this_sample = 0
            for j in judgments_here:
                item = j["parsed"].get(k)
                if isinstance(item, dict):
                    sev_raw = item.get("severity")
                else:
                    sev_raw = item
                if sev_raw is None:
                    nulls_this_sample += 1
                    continue
                sev = _clamp(sev_raw, 0.0, 5.0)
                if sev is None:
                    continue
                sevs_this_sample.append(sev)
                per_judge_means[(j["judge_model"], k)].append(sev)
            # All judges agreed N/A → mark sample N/A on this dim
            if nulls_this_sample == len(judgments_here) and sevs_this_sample == []:
                per_dim_na[k] += 1
                continue
            if sevs_this_sample:
                per_dim_scores[k].append(mean(sevs_this_sample))

    prevalence_rows = []
    for k, _, kind in NEW_RUBRIC:
        scores = per_dim_scores[k]
        na_count = per_dim_na[k]
        n_active_loose = sum(1 for s in scores if s >= 0.5)  # cross-judge mean ≥ 0.5
        n_active_strict = sum(1 for s in scores if s >= 1.0)
        n_total = len(scores)
        rate_loose = (n_active_loose / n_total) if n_total else 0.0
        rate_strict = (n_active_strict / n_total) if n_total else 0.0
        prevalence_rows.append({
            "dim": k, "kind": kind,
            "n_scored": n_total, "n_na": na_count,
            "n_nonzero_loose": n_active_loose, "rate_loose": rate_loose,
            "n_nonzero_strict": n_active_strict, "rate_strict": rate_strict,
            "mean_sev": mean(scores) if scores else None,
            "median_sev": median(scores) if scores else None,
        })

    # Per-judge means table (lets us see if any single judge still saturates)
    per_judge_table = {}
    for (judge, dim), means_list in per_judge_means.items():
        per_judge_table.setdefault(judge, {})[dim] = {
            "n": len(means_list),
            "mean": mean(means_list) if means_list else None,
            "frac_zero": sum(1 for s in means_list if s == 0) / len(means_list) if means_list else None,
        }

    always_active_loose = [r for r in prevalence_rows if r["kind"] == "always" and r["rate_loose"] >= 0.10]
    always_active_strict = [r for r in prevalence_rows if r["kind"] == "always" and r["rate_strict"] >= 0.10]
    return {
        "n_samples": n_scored,
        "per_dim": prevalence_rows,
        "per_judge": per_judge_table,
        "always_on_loose_at_10pct": len(always_active_loose),
        "always_on_strict_at_10pct": len(always_active_strict),
        "always_on_total": len(ALWAYS_ON_IDS),
        # Pre-registered gate (severity strict ≥ 1.0 panel mean): pass = ≥3 of 9
        "decision_strict": "pass" if len(always_active_strict) >= 3 else "fail",
        # Loose criterion (≥0.5) reported for diagnostic, not pre-reg
        "decision_loose": "pass" if len(always_active_loose) >= 3 else "fail",
    }


def write_report(analysis: dict, panel: list[str]) -> None:
    lines = [
        "# Phase D2 re-check: calibrated multi-judge panel",
        "",
        f"**Judge panel:** {', '.join(panel)} (cross-judge mean per sample)",
        f"**Samples scored:** {analysis['n_samples']}",
        f"**Calibration anchor:** explicit \"severity 0 is rare; default mid-scale\" "
        f"directive added to prompt.",
        "",
        f"## Gate decisions",
        "",
        f"- **Pre-registered gate** (panel mean ≥ 1.0 on ≥3 of 9 always-on dims): "
        f"**{analysis['decision_strict']}** "
        f"({analysis['always_on_strict_at_10pct']}/{analysis['always_on_total']})",
        f"- Diagnostic loose (panel mean ≥ 0.5 on ≥3 of 9): "
        f"**{analysis['decision_loose']}** "
        f"({analysis['always_on_loose_at_10pct']}/{analysis['always_on_total']})",
        "",
        "## Per-dimension prevalence (cross-judge panel mean per sample)",
        "",
        "| Dimension | kind | n | n_NA | n≥1.0 | rate≥1.0 | n≥0.5 | rate≥0.5 | mean | median |",
        "|-----------|------|---|------|-------|---------|-------|---------|------|--------|",
    ]
    for r in analysis["per_dim"]:
        ms = "—" if r["mean_sev"] is None else f"{r['mean_sev']:.2f}"
        md = "—" if r["median_sev"] is None else f"{r['median_sev']:.2f}"
        mark = "✓" if (r["kind"] == "always" and r["rate_strict"] >= 0.10) else " "
        lines.append(
            f"| {mark} `{r['dim']}` | {r['kind']} | {r['n_scored']} | {r['n_na']} | "
            f"{r['n_nonzero_strict']} | {r['rate_strict']*100:.1f}% | "
            f"{r['n_nonzero_loose']} | {r['rate_loose']*100:.1f}% | {ms} | {md} |"
        )

    lines += ["", "## Per-judge saturation check", "",
              "Per (judge × dim), what fraction of scores are exactly 0? If any "
              "judge is ≥90% zero on a dim, that judge is still saturating and the "
              "calibration anchor didn't bind for them.",
              "",
              "| Judge | dim | n | mean | frac zero |",
              "|-------|-----|---|------|-----------|"]
    for judge, dims in analysis["per_judge"].items():
        for d in NEW_ITEM_IDS:
            entry = dims.get(d, {})
            n = entry.get("n", 0)
            mn = entry.get("mean")
            fz = entry.get("frac_zero")
            mn_s = "—" if mn is None else f"{mn:.2f}"
            fz_s = "—" if fz is None else f"{fz*100:.0f}%"
            lines.append(f"| `{judge}` | {d} | {n} | {mn_s} | {fz_s} |")

    (OUTDIR / "PHASE_D2_RECHECK_REPORT.md").write_text("\n".join(lines))


async def main() -> int:
    if not GEN_FILE.exists():
        print(f"ERROR: {GEN_FILE} missing — run reprobe_phase_c_d2.py first.", file=sys.stderr)
        return 2
    if "OPENROUTER_API_KEY" not in os.environ:
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2

    generations = json.loads(GEN_FILE.read_text())
    ok_gens = [(i, g) for i, g in enumerate(generations) if g["extraction_ok"]]
    print(f"=== Phase D2 re-judge with 3-judge panel + calibration anchor ===")
    print(f"  loaded {len(generations)} generations, {len(ok_gens)} extracted ok")
    print(f"  judge panel: {JUDGE_PANEL}")
    print(f"  total judge calls: {len(ok_gens) * len(JUDGE_PANEL)}")

    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as client:
        jobs = []
        for gid, gen in ok_gens:
            for judge_model in JUDGE_PANEL:
                jobs.append((gid, judge_model, gen["code"]))

        async def _do(gid, judge_model, code):
            res = await judge_one(client, sem, code=code, judge_model=judge_model)
            res["gen_idx"] = gid
            res["judge_model"] = judge_model
            return res

        print(f"  judging...")
        judgments = await asyncio.gather(*[_do(g, j, c) for (g, j, c) in jobs])
        n_ok = sum(1 for j in judgments if j.get("parsed"))
        cost = sum((j.get("cost") or 0.0) for j in judgments)
        print(f"  judge parses ok: {n_ok}/{len(judgments)}; cost ${cost:.4f}")

    (OUTDIR / "phase_d2_panel_judgments.json").write_text(
        json.dumps(judgments, indent=2, default=str)
    )

    analysis = analyze(generations, judgments)
    (OUTDIR / "phase_d2_panel_analysis.json").write_text(
        json.dumps(analysis, indent=2, default=str)
    )
    write_report(analysis, JUDGE_PANEL)

    print(f"\n=== summary ===")
    print(f"  decision_strict (panel mean ≥1.0 on ≥3 of 9): {analysis['decision_strict']}  "
          f"({analysis['always_on_strict_at_10pct']}/{analysis['always_on_total']})")
    print(f"  decision_loose  (panel mean ≥0.5 on ≥3 of 9): {analysis['decision_loose']}  "
          f"({analysis['always_on_loose_at_10pct']}/{analysis['always_on_total']})")
    print(f"  per-dim summary:")
    for r in analysis["per_dim"]:
        if r["kind"] != "always":
            continue
        ms = "—" if r["mean_sev"] is None else f"{r['mean_sev']:.2f}"
        print(f"    {r['dim']}: mean={ms}, ≥1.0 rate={r['rate_strict']*100:.1f}%, "
              f"≥0.5 rate={r['rate_loose']*100:.1f}%")
    print(f"  artifacts: {OUTDIR}/PHASE_D2_RECHECK_REPORT.md")
    return 0 if analysis["decision_strict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
