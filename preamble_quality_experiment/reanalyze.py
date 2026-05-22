# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai",
#   "radon",
#   "flake8",
#   "flake8-cognitive-complexity",
#   "pylint",
#   "matplotlib",
#   "scipy",
#   "numpy",
#   "pandas",
#   "statsmodels",
# ]
# ///
"""Re-analysis of Experiment 2 — no re-generation, reads existing artifacts.

Resolves the post-run findings (micro-iteration within Step 6-7):
  1. Per-component separation: which CQS component carries the preamble signal.
  2. Fixed mixed-effects model (now filters to main conditions).
  3. Re-weighting sensitivity: how the verdict depends on static-vs-LLM weight.
  4. Corrected F1 sensitivity probe: static-only (order-aware verdict) PLUS a
     full-CQS-with-judges variant that tests the ACTUAL metric used, not just
     its static component.

Reads:  experiment2_results/{full_results.jsonl, judge_results.jsonl,
        normalization_bounds.json}
Writes: experiment2_results/reanalysis_results.json + figures.

The pre-registered composite CQS result is preserved and reported as primary;
all re-weightings here are clearly-labeled post-hoc sensitivity analyses.
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
WEIGHTS = exp.WEIGHTS
COMPONENTS = ["static_score", "ast_score", "llm_idiom_score", "llm_comment_score"]
# grok-4.1-fast is deprecated (404s); use only working judges for the probe.
WORKING_JUDGES = [m for m in exp.JUDGE_MODELS if "grok-4.1" not in m]


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_full_results() -> list[dict]:
    path = RESULTS_DIR / "full_results.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def kw_across_conditions(rows: list[dict], key: str) -> dict:
    """Kruskal-Wallis of `key` across main conditions, with per-condition means."""
    groups, means = [], {}
    for c in MAIN_CONDITIONS:
        vals = [r[key] for r in rows if r["preamble"] == c and r.get(key) is not None]
        if vals:
            groups.append(vals)
            means[c] = float(np.mean(vals))
    if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
        H, p = stats.kruskal(*groups)
    else:
        H, p = float("nan"), float("nan")
    return {"H": float(H), "p": float(p), "means": means, "significant": bool(p < 0.05)}


def reweight_sensitivity(rows: list[dict]) -> dict:
    """Recompute a composite under several static-vs-LLM weightings; KW each.

    Post-hoc only — demonstrates how the pre-registered static-heavy weighting
    buries the LLM-judge signal. NOT a redefinition of the primary metric.
    """
    schemes = {
        "pre_registered": {"static_score": 0.45, "ast_score": 0.20,
                           "llm_idiom_score": 0.20, "llm_comment_score": 0.15},
        "balanced_50_50": {"static_score": 0.325, "ast_score": 0.175,
                          "llm_idiom_score": 0.275, "llm_comment_score": 0.225},
        "llm_heavy_75": {"static_score": 0.15, "ast_score": 0.10,
                        "llm_idiom_score": 0.40, "llm_comment_score": 0.35},
        "llm_only": {"static_score": 0.0, "ast_score": 0.0,
                    "llm_idiom_score": 0.5714, "llm_comment_score": 0.4286},
    }
    out = {}
    for name, w in schemes.items():
        for r in rows:
            r[f"_cqs_{name}"] = sum(w[c] * r[c] for c in COMPONENTS)
        res = kw_across_conditions(rows, f"_cqs_{name}")
        out[name] = {"weights": w, "kw_H": res["H"], "kw_p": res["p"],
                     "significant": res["significant"], "means": res["means"]}
    return out


def fixed_mixed_effects(rows: list[dict], target: str) -> dict:
    """Mixed-effects: target ~ preamble + (1|model), main conditions only."""
    import pandas as pd
    from statsmodels.formula.api import mixedlm

    data = [{"y": r[target], "preamble": r["preamble"], "model": r["model"]}
            for r in rows if r.get(target) is not None and r["preamble"] in MAIN_CONDITIONS]
    if len(data) < 20:
        return {"error": f"too few obs: {len(data)}"}
    df = pd.DataFrame(data)
    df["preamble"] = pd.Categorical(df["preamble"], categories=MAIN_CONDITIONS)
    try:
        m = mixedlm("y ~ C(preamble, Treatment(reference='none'))", df, groups=df["model"])
        res = m.fit(reml=True, method="lbfgs")
        fe = {k: {"coef": float(v), "pval": float(res.pvalues[k])}
              for k, v in res.fe_params.items()}
        # Joint significance of the preamble factor via the smallest fixed-effect p
        pre_pvals = [v["pval"] for k, v in fe.items() if "preamble" in k]
        return {"target": target, "n_obs": len(df), "aic": float(res.aic),
                "fixed_effects": fe, "min_preamble_pval": min(pre_pvals) if pre_pvals else None,
                "converged": True}
    except Exception as exc:  # noqa: BLE001 - report convergence failure, don't crash
        return {"target": target, "error": str(exc), "converged": False}


async def f1_probe_with_judges(bounds: dict) -> dict:
    """Score the 3 synthetic samples through the FULL CQS (static+ast+LLM judges).

    Tests the actual metric used in the experiment, calibrated on the experiment's
    own data-driven normalization bounds. Complements the static-only probe.
    """
    client = AsyncOpenAI(api_key=exp.get_api_key(), base_url=exp.OPENROUTER_BASE_URL)
    # Wrap synthetic samples as generation_results so we can reuse the judge batch.
    gen_like = [
        {"task_id": "f1_probe", "preamble": label, "model": "synthetic",
         "code": code, "raw_response": code, "extraction_method": "fenced", "error": None}
        for label, code in exp.SENSITIVITY_SAMPLES
    ]
    judge_raw = await exp.run_llm_judge_batch(gen_like, WORKING_JUDGES, client)

    by_label: dict[str, list[dict]] = {}
    for j in judge_raw:
        # coerce scores to float, drop unparseable
        ji, jc = _to_float(j.get("idiomaticity")), _to_float(j.get("comment_quality"))
        if ji is None and jc is None:
            continue
        by_label.setdefault(j["preamble"], []).append(
            {"idiomaticity": ji, "comment_quality": jc})

    scores = {}
    for label, code in exp.SENSITIVITY_SAMPLES:
        metrics = exp.compute_static_metrics(code)
        metrics["pylint_penalty"] = (
            metrics["pylint_errors"] * 1.0 + metrics["pylint_warnings"] * 0.5
            + metrics["pylint_conventions"] * 0.2 + metrics["pylint_refactor"] * 0.3)
        static_score = exp.compute_static_score_normalized(metrics, bounds)
        ast_score = exp.compute_ast_score_normalized(metrics, bounds)
        cqs = exp.compute_cqs(static_score, ast_score, by_label.get(label, []))
        scores[label] = cqs

    poor, avg, exc = scores["poor"]["cqs"], scores["average"]["cqs"], scores["excellent"]["cqs"]
    order_ok = poor < avg < exc
    rng = exc - poor
    if not order_ok:
        verdict = "confirms_critique"
        vtext = f"Full-CQS order VIOLATED (poor={poor:.3f}, avg={avg:.3f}, exc={exc:.3f})"
    elif rng >= 0.10:
        verdict = "refutes_critique"
        vtext = f"Full-CQS order preserved, range={rng:.3f} >= 0.10: metric is quality-sensitive"
    elif rng < 0.05:
        verdict = "confirms_critique"
        vtext = f"Full-CQS range={rng:.3f} < 0.05: insufficient sensitivity"
    else:
        verdict = "ambiguous"
        vtext = f"Full-CQS order preserved, range={rng:.3f} in [0.05,0.10)"
    return {"per_sample": scores, "poor_cqs": poor, "average_cqs": avg,
            "excellent_cqs": exc, "cqs_range": round(rng, 4),
            "order_preserved": order_ok, "verdict": verdict, "verdict_text": vtext}


def plot_component_separation(comp_kw: dict, out: Path) -> None:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    comps = list(comp_kw.keys())
    ps = [comp_kw[c]["p"] for c in comps]
    colors = ["#2ca02c" if p < 0.05 else "#999999" for p in ps]
    ax.bar(comps, [-np.log10(max(p, 1e-6)) for p in ps], color=colors)
    ax.axhline(-np.log10(0.05), ls="--", c="red", label="p=0.05")
    ax.set_ylabel("-log10(Kruskal-Wallis p)")
    ax.set_title("Preamble-condition separation by CQS component\n(green = significant)")
    for i, p in enumerate(ps):
        ax.text(i, -np.log10(max(p, 1e-6)), f"p={p:.3f}", ha="center", va="bottom", fontsize=9)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_reweight(reweight: dict, out: Path) -> None:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    names = list(reweight.keys())
    ps = [reweight[n]["kw_p"] for n in names]
    static_w = [reweight[n]["weights"]["static_score"] + reweight[n]["weights"]["ast_score"] for n in names]
    colors = ["#2ca02c" if p < 0.05 else "#d62728" for p in ps]
    ax.bar(names, ps, color=colors)
    ax.axhline(0.05, ls="--", c="black", label="p=0.05")
    ax.set_ylabel("Kruskal-Wallis p (preamble effect on composite)")
    ax.set_title("Significance of preamble effect vs. metric weighting\n(label shows static+AST weight)")
    for i, (p, sw) in enumerate(zip(ps, static_w)):
        ax.text(i, p, f"p={p:.3f}\nstatic={sw:.2f}", ha="center", va="bottom", fontsize=8)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def main() -> None:
    rows = load_full_results()
    bounds = {k: tuple(v) for k, v in
              json.loads((RESULTS_DIR / "normalization_bounds.json").read_text()).items()}
    print(f"Loaded {len(rows)} scored rows; {len({r['model'] for r in rows})} models present.")

    # 1. Per-component separation
    comp_kw = {c: kw_across_conditions(rows, c) for c in COMPONENTS}
    comp_kw["cqs"] = kw_across_conditions(rows, "cqs")
    print("\n[1] Component separation (KW across main conditions):")
    for c, r in comp_kw.items():
        print(f"  {c:<20} H={r['H']:.2f} p={r['p']:.4f} {'SIG' if r['significant'] else ''}")

    # 2. Fixed mixed-effects on composite + LLM components
    me = {t: fixed_mixed_effects(rows, t) for t in ["cqs", "llm_idiom_score", "llm_comment_score"]}
    print("\n[2] Mixed-effects (fixed):")
    for t, r in me.items():
        if r.get("converged"):
            print(f"  {t:<20} n={r['n_obs']} min_preamble_p={r['min_preamble_pval']:.4f}")
        else:
            print(f"  {t:<20} {r.get('error')}")

    # 3. Re-weighting sensitivity
    reweight = reweight_sensitivity(rows)
    print("\n[3] Re-weighting sensitivity (KW p by scheme):")
    for name, r in reweight.items():
        sw = r["weights"]["static_score"] + r["weights"]["ast_score"]
        print(f"  {name:<16} static+ast={sw:.2f}  p={r['kw_p']:.4f} {'SIG' if r['significant'] else ''}")

    # 4. Corrected F1 probe — static-only (order-aware) + full-with-judges
    static_probe = exp.run_sensitivity_probe(bounds)   # now order-aware verdict
    print(f"\n[4a] F1 static-only probe: {static_probe['verdict']} — {static_probe['verdict_text']}")
    judge_probe = asyncio.run(f1_probe_with_judges(bounds))
    print(f"[4b] F1 full-CQS-with-judges probe: {judge_probe['verdict']} — {judge_probe['verdict_text']}")

    # Figures
    plot_component_separation(comp_kw, RESULTS_DIR / "reanalysis_component_separation.png")
    plot_reweight(reweight, RESULTS_DIR / "reanalysis_reweight_sensitivity.png")

    out = {
        "n_scored": len(rows),
        "models_present": sorted({r["model"].split("/")[-1] for r in rows}),
        "component_separation": comp_kw,
        "mixed_effects": me,
        "reweight_sensitivity": reweight,
        "f1_probe_static_only": static_probe,
        "f1_probe_full_with_judges": judge_probe,
    }
    (RESULTS_DIR / "reanalysis_results.json").write_text(json.dumps(out, indent=2))
    print(f"\nSaved reanalysis_results.json + 2 figures to {RESULTS_DIR.name}/")


if __name__ == "__main__":
    main()
