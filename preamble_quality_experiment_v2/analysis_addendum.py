# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "statsmodels", "pandas"]
# ///
"""Add two §9 acceptance criteria to the main-run report:

  (a) Mixed-effects model: CQS_craft ~ preamble + (1|model) + (1|task)
  (b) CQS weight-sensitivity table over alternative weighting schemes

Reads experiment_v2_results/{generations.jsonl, judgments.jsonl, sample_cqs.json}
produced by preamble_quality_v2_main.py. Writes:
  - experiment_v2_results/MIXED_EFFECTS.md
  - experiment_v2_results/WEIGHT_SENSITIVITY.md
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = Path(__file__).parent
RES = ROOT / "experiment_v2_results"

REASONING_MODELS = {
    "qwen/qwen3.6-flash", "deepseek/deepseek-v4-flash", "minimax/minimax-m2.5"
}
MAIN_CONDITIONS = [
    "none", "minimal", "generic_coding", "real_agent", "negative_control",
    "persona_only", "long_directive", "python_coder_agent",
]
PREAMBLE_ORDER_DISPLAY = [
    "trivial_baseline", "none", "negative_control", "minimal",
    "generic_coding", "persona_only", "real_agent", "long_directive",
    "python_coder_agent",
]

RUBRIC_IDS = [
    "data_structure_choice", "algorithm_correctness",
    "error_handling_inconsistency", "api_ergonomics",
    "abstraction_miscalibration", "code_organization",
    "type_hint_gap", "edge_case_gap", "documentation_appropriateness",
    "concurrency_safety", "example_quality",
]


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def build_dataframe() -> pd.DataFrame:
    """One row per generation with its CQS-craft + cross-judge components."""
    gens = _load_jsonl(RES / "generations.jsonl")
    sample_cqs = json.loads((RES / "sample_cqs.json").read_text())
    cqs_by_key = {s["gen_key"]: s for s in sample_cqs}
    rows = []
    for g in gens:
        if not g["extraction_ok"]:
            continue
        s = cqs_by_key.get(g["key"])
        if not s or s["cqs_craft"] is None:
            continue
        rows.append({
            "gen_key": g["key"], "preamble": g["preamble_id"],
            "model": g["model"], "task": g["task_id"],
            "category": g["category"],
            "tier": "reasoning" if g["model"] in REASONING_MODELS else "non_reasoning",
            "idiom": s["idiom_score"],
            "comment": s["comment_score"],
            "rubric_sev": s["rubric_sev_mean"],
            "cqs": s["cqs_craft"],
        })
    return pd.DataFrame(rows)


def fit_mixed_effects(df: pd.DataFrame, *, label: str) -> str:
    """Fit CQS ~ preamble + (1|model) + (1|task). statsmodels supports
    one variance component group natively; we add the second via vc_formula."""
    if len(df) == 0:
        return f"### {label}\n\n(no data)\n"
    # Use a categorical with `none` as the reference cell — interpretable baseline
    df = df.copy()
    df["preamble"] = pd.Categorical(
        df["preamble"], categories=["none"] + [p for p in PREAMBLE_ORDER_DISPLAY if p != "none"]
    )
    # Two crossed random intercepts via groups + vc_formula trick
    df["_one"] = 1
    md = smf.mixedlm(
        "cqs ~ C(preamble)",
        df,
        groups=df["model"],
        vc_formula={"task": "0 + C(task)"},
        re_formula="1",
    )
    try:
        fit = md.fit(method="lbfgs", reml=True, maxiter=200)
    except Exception as exc:
        return f"### {label}\n\nmixedlm failed: {exc}\n"

    lines: list[str] = [f"### {label}\n"]
    lines.append(f"- n = {len(df)}")
    lines.append(f"- random effect (model) variance: {float(fit.cov_re.iloc[0, 0]):.5f}")
    if hasattr(fit, "vcomp") and fit.vcomp is not None and len(fit.vcomp) > 0:
        lines.append(f"- random effect (task) variance: {float(fit.vcomp[0]):.5f}")
    lines.append(f"- residual variance: {float(fit.scale):.5f}")
    lines.append("")
    lines.append("**Fixed effects vs `none` (reference):**")
    lines.append("")
    lines.append("| Term | β | SE | z | p | 95% CI |")
    lines.append("|---|---|---|---|---|---|")
    params = fit.params
    bse = fit.bse
    tvals = fit.tvalues
    pvals = fit.pvalues
    ci = fit.conf_int()
    for term in params.index:
        if term == "Group Var":
            continue
        lo = ci.loc[term, 0]
        hi = ci.loc[term, 1]
        lines.append(
            f"| `{term}` | {params[term]:+.4f} | {bse[term]:.4f} | "
            f"{tvals[term]:+.2f} | {pvals[term]:.4g} | [{lo:+.4f}, {hi:+.4f}] |"
        )
    lines.append("")
    return "\n".join(lines)


def weight_sensitivity_table(df: pd.DataFrame) -> str:
    """Recompute CQS under alternative weight schemes; report per-condition means
    + KW p across MAIN_CONDITIONS for each scheme."""
    schemes = [
        ("pre-reg (0.45/0.45/0.10)", 0.45, 0.45, 0.10),
        ("idiom-only (1.00/0.00/0.00)", 1.00, 0.00, 0.00),
        ("comment-only (0.00/1.00/0.00)", 0.00, 1.00, 0.00),
        ("rubric-only (0.00/0.00/1.00)", 0.00, 0.00, 1.00),
        ("rubric-heavy (0.30/0.30/0.40)", 0.30, 0.30, 0.40),
        ("equal-thirds (0.33/0.33/0.34)", 0.34, 0.33, 0.33),
        ("v1-static-heavy proxy (0.20/0.20/0.60)", 0.20, 0.20, 0.60),
    ]
    df = df.dropna(subset=["idiom", "comment", "rubric_sev"]).copy()
    df["idiom_n"] = df["idiom"] / 10.0
    df["comment_n"] = df["comment"] / 10.0
    df["hygiene"] = 1.0 - df["rubric_sev"] / 5.0

    lines = ["| Weight scheme |"]
    cells_header = ["mean (" + c + ")" for c in PREAMBLE_ORDER_DISPLAY]
    lines[0] += " " + " | ".join(cells_header) + " | KW p (main conds) |"
    lines.append("|" + "|".join(["---"] * (len(cells_header) + 2)) + "|")

    for label, wi, wc, wh in schemes:
        cqs = wi * df["idiom_n"] + wc * df["comment_n"] + wh * df["hygiene"]
        df_local = df.assign(cqs_alt=cqs)
        means = {}
        groups_for_kw: list[list[float]] = []
        for cond in PREAMBLE_ORDER_DISPLAY:
            vals = df_local[df_local["preamble"] == cond]["cqs_alt"].tolist()
            means[cond] = float(np.mean(vals)) if vals else None
            if cond in MAIN_CONDITIONS and vals:
                groups_for_kw.append(vals)
        try:
            H, p = stats.kruskal(*groups_for_kw)
            p_s = f"{p:.4g}"
        except Exception:
            p_s = "—"
        cells = []
        for c in PREAMBLE_ORDER_DISPLAY:
            v = means[c]
            cells.append("—" if v is None else f"{v:.3f}")
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {p_s} |")
    return "\n".join(lines)


def fit_mixed_effects_with_formula(df: pd.DataFrame, formula: str, *, label: str):
    """Generic fitter; returns (markdown_block, fitted_result or None)."""
    if len(df) == 0:
        return f"### {label}\n\n(no data)\n", None
    df = df.copy()
    df["preamble"] = pd.Categorical(
        df["preamble"], categories=["none"] + [p for p in PREAMBLE_ORDER_DISPLAY if p != "none"]
    )
    df["tier"] = pd.Categorical(df["tier"], categories=["non_reasoning", "reasoning"])
    md = smf.mixedlm(
        formula, df,
        groups=df["model"],
        vc_formula={"task": "0 + C(task)"},
        re_formula="1",
    )
    try:
        fit = md.fit(method="lbfgs", reml=True, maxiter=200)
    except Exception as exc:
        return f"### {label}\n\nmixedlm failed: {exc}\n", None

    lines: list[str] = [f"### {label}\n", f"**Formula:** `{formula}`", ""]
    lines.append(f"- n = {len(df)}")
    lines.append(f"- random effect (model) variance: {float(fit.cov_re.iloc[0, 0]):.5f}")
    if hasattr(fit, "vcomp") and fit.vcomp is not None and len(fit.vcomp) > 0:
        lines.append(f"- random effect (task) variance: {float(fit.vcomp[0]):.5f}")
    lines.append(f"- residual variance: {float(fit.scale):.5f}")
    lines.append(f"- log-likelihood: {float(fit.llf):.4f}")
    lines.append("")
    lines.append("| Term | β | SE | z | p | 95% CI |")
    lines.append("|---|---|---|---|---|---|")
    params = fit.params; bse = fit.bse; tvals = fit.tvalues; pvals = fit.pvalues
    ci = fit.conf_int()
    for term in params.index:
        if term == "Group Var":
            continue
        lo = ci.loc[term, 0]; hi = ci.loc[term, 1]
        lines.append(
            f"| `{term}` | {params[term]:+.4f} | {bse[term]:.4f} | "
            f"{tvals[term]:+.2f} | {pvals[term]:.4g} | [{lo:+.4f}, {hi:+.4f}] |"
        )
    lines.append("")
    return "\n".join(lines), fit


def main() -> int:
    df = build_dataframe()
    print(f"loaded {len(df)} samples across {df['preamble'].nunique()} preambles")

    # ---- Mixed-effects: baseline, tier-main-effect, full interaction ----
    me_lines = ["# Mixed-effects models",
                "",
                "All models: random intercepts on subject `model` and `task` (REML; statsmodels",
                "`mixedlm` with `vc_formula` for the second random group). `preamble`",
                "categorical with `none` as reference cell. `tier` is a fixed 1/0 indicator",
                "(`reasoning=1`, `non_reasoning=0`). Tier is constant within each model, so",
                "`(1|model)` absorbs within-tier between-model variance and `tier` captures",
                "the mean shift between tiers.",
                "",
                "## Model comparison — does tier matter? Does it interact with preamble?",
                ""]

    m0_md, m0 = fit_mixed_effects_with_formula(
        df, "cqs ~ C(preamble)",
        label="M0 — baseline (no tier term)",
    )
    me_lines.append(m0_md)

    m1_md, m1 = fit_mixed_effects_with_formula(
        df, "cqs ~ C(preamble) + C(tier)",
        label="M1 — preamble + tier main effect",
    )
    me_lines.append(m1_md)

    m2_md, m2 = fit_mixed_effects_with_formula(
        df, "cqs ~ C(preamble) * C(tier)",
        label="M2 — preamble × tier interaction (FULL MODEL)",
    )
    me_lines.append(m2_md)

    # Likelihood-ratio comparisons (caveat: REML LRTs are valid only for random-effect
    # comparisons, not fixed-effects; switching to ML for fixed-effect LRT would be
    # principled. We report log-likelihood deltas descriptively.)
    if m0 is not None and m1 is not None:
        d10 = float(m1.llf - m0.llf)
        me_lines.append(f"**ΔlogLik(M1 − M0):** {d10:+.4f} — magnitude of tier main effect on fit quality.")
    if m1 is not None and m2 is not None:
        d21 = float(m2.llf - m1.llf)
        me_lines.append(f"**ΔlogLik(M2 − M1):** {d21:+.4f} — magnitude of preamble × tier interaction on fit quality.")
    me_lines.append("")
    me_lines.append("(REML log-likelihoods are not directly comparable across models with "
                    "different fixed-effects structure; signs and magnitudes are descriptive. "
                    "A principled fixed-effect LRT requires ML estimation; see ML refit below.)")
    me_lines.append("")

    # ML refit for fixed-effect LRT
    me_lines.append("## ML refit for principled fixed-effect LRT")
    me_lines.append("")
    for label, formula in [
        ("M0 (ML)", "cqs ~ C(preamble)"),
        ("M1 (ML, +tier)", "cqs ~ C(preamble) + C(tier)"),
        ("M2 (ML, ×tier)", "cqs ~ C(preamble) * C(tier)"),
    ]:
        df2 = df.copy()
        df2["preamble"] = pd.Categorical(
            df2["preamble"], categories=["none"] + [p for p in PREAMBLE_ORDER_DISPLAY if p != "none"]
        )
        df2["tier"] = pd.Categorical(df2["tier"], categories=["non_reasoning", "reasoning"])
        try:
            fit = smf.mixedlm(
                formula, df2, groups=df2["model"],
                vc_formula={"task": "0 + C(task)"}, re_formula="1",
            ).fit(method="lbfgs", reml=False, maxiter=200)
            me_lines.append(f"- **{label}** logLik = {fit.llf:.4f}, df_resid = {int(fit.df_resid)}")
        except Exception as exc:
            me_lines.append(f"- {label} fit failed: {exc}")
    me_lines.append("")

    # ---- Per-tier (stratified, for back-compat with prior reporting) ----
    me_lines.append("## Stratified fits (for reference; superseded by M2 above)")
    me_lines.append("")
    me_lines.append(fit_mixed_effects(df[df["tier"] == "reasoning"], label="Reasoning tier only"))
    me_lines.append(fit_mixed_effects(df[df["tier"] == "non_reasoning"], label="Non-reasoning tier only"))

    (RES / "MIXED_EFFECTS.md").write_text("\n".join(me_lines))
    print(f"wrote {RES / 'MIXED_EFFECTS.md'}")

    # ---- Sensitivity ----
    sens = [
        "# CQS weight-sensitivity table",
        "",
        "Each scheme reweights the three CQS-craft components",
        "(idiom, comment, hygiene). Pre-registered weights are 0.45 / 0.45 / 0.10.",
        "Rows show the per-condition mean under each scheme plus the Kruskal-Wallis",
        "p-value across the 8 main conditions (excluding `trivial_baseline`).",
        "",
        weight_sensitivity_table(df),
    ]
    (RES / "WEIGHT_SENSITIVITY.md").write_text("\n".join(sens))
    print(f"wrote {RES / 'WEIGHT_SENSITIVITY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
