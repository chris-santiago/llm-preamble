# /// script
# requires-python = ">=3.10"
# dependencies = ["polars", "numpy", "scipy", "matplotlib", "seaborn"]
# ///
"""Generate v2 figures from the main-run JSONL artifacts.

Switched from ferrum-viz to matplotlib + seaborn for finer control over label
spacing, y-axis range, and value annotations. Produces 5 SVG+PNG pairs under
experiment_v2_results/figures/:

  1. fig1_headline_cqs_by_preamble — bar + bootstrap CI, ordered by mean
  2. fig2_per_dim_severity_heatmap — 11 rubric dims × 9 preambles + annotations
  3. fig3_mechanism_split — −log10(p) per measure, craft / capability / static
  4. fig4_tier_comparison — side-by-side reasoning vs non-reasoning panels
  5. fig5_task_category — three panels by task category
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
from matplotlib.patches import Patch
from scipy import stats

ROOT = Path(__file__).parent
RES = ROOT / "experiment_v2_results"
OUT = RES / "figures"
OUT.mkdir(exist_ok=True)

REASONING_MODELS = {
    "qwen/qwen3.6-flash", "deepseek/deepseek-v4-flash", "minimax/minimax-m2.5",
}

# Display order: trivial first (worst), long_directive last (best)
PREAMBLE_ORDER = [
    "trivial_baseline", "negative_control", "persona_only", "minimal",
    "none", "generic_coding", "real_agent", "python_coder_agent",
    "long_directive",
]

# Friendly labels for axis ticks
PREAMBLE_LABEL = {
    "trivial_baseline": "trivial\nbaseline",
    "negative_control": "negative\ncontrol",
    "persona_only": "persona\nonly",
    "minimal": "minimal",
    "none": "none",
    "generic_coding": "generic\ncoding",
    "real_agent": "real_agent",
    "python_coder_agent": "python_coder\nagent",
    "long_directive": "long\ndirective",
}

# Category buckets and their colors
CAT_COLORS = {
    "trivial_baseline": "#444444",   # dark gray — degenerate
    "negative":         "#d62728",   # red — actively hurts
    "neutral":          "#dbb759",   # warm yellow — neutral
    "rich":             "#2ca02c",   # green — helps
}


def _preamble_bucket(cond: str) -> str:
    if cond == "trivial_baseline":
        return "trivial_baseline"
    if cond == "negative_control":
        return "negative"
    if cond in ("none", "minimal", "generic_coding", "persona_only"):
        return "neutral"
    return "rich"


ALWAYS_ON_DIMS = [
    "data_structure_choice", "algorithm_correctness",
    "error_handling_inconsistency", "api_ergonomics",
    "abstraction_miscalibration", "code_organization",
    "type_hint_gap", "edge_case_gap", "documentation_appropriateness",
]
CRAFT_DIMS = {
    "error_handling_inconsistency", "edge_case_gap",
    "type_hint_gap", "code_organization", "documentation_appropriateness",
    "abstraction_miscalibration", "api_ergonomics", "concurrency_safety",
}
CAPABILITY_DIMS = {"algorithm_correctness", "data_structure_choice"}
ALL_DIMS = ALWAYS_ON_DIMS + ["concurrency_safety", "example_quality"]

STATIC_METRICS = [
    "maintainability_index", "avg_cyclomatic", "max_cyclomatic",
    "halstead_difficulty", "pylint_errors", "pylint_warnings",
    "pylint_conventions", "pylint_refactor", "cognitive_complexity_violations",
]


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def build_sample_frame() -> pl.DataFrame:
    gens = _load_jsonl(RES / "generations.jsonl")
    cqs_records = json.loads((RES / "sample_cqs.json").read_text())
    cqs_by_key = {s["gen_key"]: s for s in cqs_records}
    rows = []
    for g in gens:
        if not g["extraction_ok"]:
            continue
        s = cqs_by_key.get(g["key"])
        if not s or s["cqs_craft"] is None:
            continue
        per_dim = s.get("per_dim_means", {})
        row = {
            "preamble": g["preamble_id"],
            "model": g["model"],
            "task": g["task_id"],
            "category": g["category"],
            "tier": "reasoning" if g["model"] in REASONING_MODELS else "non_reasoning",
            "cqs": s["cqs_craft"],
        }
        for d in ALL_DIMS:
            v = per_dim.get(d)
            row[f"dim_{d}"] = v if v is not None else None
        rows.append(row)
    return pl.DataFrame(rows)


def build_static_frame() -> pl.DataFrame:
    gens = _load_jsonl(RES / "generations.jsonl")
    s_recs = _load_jsonl(RES / "static_analysis.jsonl")
    s_by_key = {r["key"]: r for r in s_recs}
    rows = []
    for g in gens:
        if not g["extraction_ok"]:
            continue
        sm = s_by_key.get(g["key"])
        if not sm:
            continue
        row: dict = {"preamble": g["preamble_id"]}
        for k in STATIC_METRICS:
            v = sm.get(k)
            if v is None:
                continue
            try:
                row[k] = float(v)
            except (TypeError, ValueError):
                continue
        rows.append(row)
    return pl.DataFrame(rows)


def bootstrap_ci(values: list[float], n_boot: int = 2000, alpha: float = 0.05):
    arr = np.asarray(values, dtype=float)
    if len(arr) < 2:
        m = float(arr.mean()) if len(arr) else float("nan")
        return m, m, m
    rng = np.random.default_rng(2026_05_23)
    boot = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    return (float(arr.mean()),
            float(np.quantile(boot, alpha / 2)),
            float(np.quantile(boot, 1 - alpha / 2)))


def kw_p(by_group: dict[str, list[float]]) -> float | None:
    groups = [v for v in by_group.values() if len(v) >= 2]
    if len(groups) < 2:
        return None
    try:
        _, p = stats.kruskal(*groups)
        return float(p)
    except Exception:
        return None


def _apply_style() -> None:
    sns.set_theme(style="whitegrid", context="paper")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.linestyle": ":",
        "grid.alpha": 0.5,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
    })


def _save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.svg", format="svg")
    fig.savefig(OUT / f"{name}.png", format="png", dpi=150)
    plt.close(fig)


# =============================================================================
# Figure 1 — headline CQS-craft by preamble
# =============================================================================
def fig1_headline_cqs(df: pl.DataFrame) -> None:
    rows = []
    for cond in PREAMBLE_ORDER:
        vals = df.filter(pl.col("preamble") == cond)["cqs"].to_list()
        if not vals:
            continue
        m, lo, hi = bootstrap_ci(vals)
        bucket = _preamble_bucket(cond)
        rows.append({"preamble": cond, "mean": m, "lo": lo, "hi": hi,
                     "n": len(vals), "category": bucket})

    fig, ax = plt.subplots(figsize=(11, 5.2))
    x = np.arange(len(rows))
    colors = [CAT_COLORS[r["category"]] for r in rows]
    means = [r["mean"] for r in rows]
    los = [r["lo"] for r in rows]
    his = [r["hi"] for r in rows]
    yerr_lo = [m - lo for m, lo in zip(means, los)]
    yerr_hi = [hi - m for m, hi in zip(means, his)]

    bars = ax.bar(x, means, color=colors, edgecolor="black", linewidth=0.6, width=0.78)
    ax.errorbar(x, means, yerr=[yerr_lo, yerr_hi], fmt="none",
                ecolor="black", capsize=4, linewidth=1.2)

    # Bar value annotations above each bar (slightly above upper CI bound)
    for i, r in enumerate(rows):
        ax.text(i, r["hi"] + 0.012, f"{r['mean']:.3f}",
                ha="center", va="bottom", fontsize=9.5)

    ax.set_xticks(x)
    ax.set_xticklabels([PREAMBLE_LABEL[r["preamble"]] for r in rows], fontsize=10)
    ax.set_ylim(0.40, 0.92)  # zoom to meaningful range
    ax.set_ylabel("CQS-craft  (cross-judge composite, 0–1 scale)")
    ax.set_xlabel("")
    ax.set_title(
        "CQS-craft by preamble — bootstrap 95% CI, n=125-139 per condition\n"
        "KW p = 9.2e-18  •  rich preambles ≈ neutral; long_directive only one clearing p<0.01 vs none; negatives hurt",
        loc="left", pad=14,
    )

    legend_patches = [
        Patch(facecolor=CAT_COLORS["trivial_baseline"], edgecolor="black",
              label="trivial baseline (no system + name-only + T=1.0)"),
        Patch(facecolor=CAT_COLORS["negative"], edgecolor="black",
              label="negative control (\"junior developer\")"),
        Patch(facecolor=CAT_COLORS["neutral"], edgecolor="black",
              label="neutral / minimal"),
        Patch(facecolor=CAT_COLORS["rich"], edgecolor="black",
              label="rich preamble"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", framealpha=0.95, fontsize=9)
    fig.tight_layout()
    _save(fig, "fig1_headline_cqs_by_preamble")
    print(f"  fig1: {OUT / 'fig1_headline_cqs_by_preamble.png'}")


# =============================================================================
# Figure 2 — per-dimension severity heatmap (annotated)
# =============================================================================
def fig2_severity_heatmap(df: pl.DataFrame) -> None:
    # Order dimensions: capability nulls last, conditional last
    dim_order = [
        "error_handling_inconsistency", "edge_case_gap", "documentation_appropriateness",
        "type_hint_gap", "code_organization", "abstraction_miscalibration",
        "api_ergonomics", "concurrency_safety",
        "data_structure_choice", "algorithm_correctness", "example_quality",
    ]
    dim_labels = {
        "error_handling_inconsistency": "error handling inconsistency",
        "edge_case_gap": "edge case gap",
        "documentation_appropriateness": "documentation appropriateness",
        "type_hint_gap": "type hint gap",
        "code_organization": "code organization",
        "abstraction_miscalibration": "abstraction miscalibration",
        "api_ergonomics": "api ergonomics",
        "concurrency_safety": "concurrency safety  *(conditional)*",
        "data_structure_choice": "data structure choice  ✗ null",
        "algorithm_correctness": "algorithm correctness  ✗ null",
        "example_quality": "example quality  *(conditional, null)*",
    }

    # Build matrix
    matrix = np.full((len(dim_order), len(PREAMBLE_ORDER)), np.nan)
    for i, dim in enumerate(dim_order):
        col = f"dim_{dim}"
        if col not in df.columns:
            continue
        for j, cond in enumerate(PREAMBLE_ORDER):
            vals = [
                v for v in df.filter(pl.col("preamble") == cond)[col].to_list()
                if v is not None
            ]
            if vals:
                matrix[i, j] = float(np.mean(vals))

    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    cmap = sns.color_palette("Blues", as_cmap=True)
    sns.heatmap(
        matrix, ax=ax, cmap=cmap, vmin=0.0, vmax=2.8,
        annot=True, fmt=".2f", annot_kws={"fontsize": 9},
        cbar_kws={"label": "mean cross-judge severity\n(0 = clean, 5 = severe)"},
        linewidths=0.4, linecolor="white",
    )
    ax.set_yticklabels(
        [dim_labels[d] for d in dim_order], rotation=0, fontsize=10,
    )
    ax.set_xticklabels(
        [PREAMBLE_LABEL[c].replace("\n", " ") for c in PREAMBLE_ORDER],
        rotation=30, ha="right", fontsize=10,
    )
    ax.set_title(
        "Per-dimension severity by preamble — redesigned 11-dim algorithmic-code rubric\n"
        "Darker = worse. Note flat rows for capability dims (data_structure_choice, algorithm_correctness)",
        loc="left", pad=14,
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    _save(fig, "fig2_per_dim_severity_heatmap")
    print(f"  fig2: {OUT / 'fig2_per_dim_severity_heatmap.png'}")


# =============================================================================
# Figure 3 — mechanism split
# =============================================================================
def fig3_mechanism_split(df: pl.DataFrame, static_df: pl.DataFrame) -> None:
    main_conds = [c for c in PREAMBLE_ORDER if c != "trivial_baseline"]
    rows = []

    for dim in ALL_DIMS:
        col = f"dim_{dim}"
        by_c: dict[str, list[float]] = defaultdict(list)
        for r in df.to_dicts():
            if r["preamble"] not in main_conds:
                continue
            v = r.get(col)
            if v is None:
                continue
            by_c[r["preamble"]].append(float(v))
        p = kw_p(by_c)
        if p is None:
            continue
        if dim in CRAFT_DIMS:
            kind = "craft (alignment-sensitive)"
        elif dim in CAPABILITY_DIMS:
            kind = "capability (pretraining)"
        else:
            kind = "conditional"
        rows.append({"measure": dim, "kind": kind,
                     "nlp": -float(np.log10(p)), "p": p})

    for m in STATIC_METRICS:
        if m not in static_df.columns:
            continue
        by_c = defaultdict(list)
        for r in static_df.to_dicts():
            if r["preamble"] not in main_conds:
                continue
            v = r.get(m)
            if v is None:
                continue
            by_c[r["preamble"]].append(float(v))
        p = kw_p(by_c)
        if p is None:
            continue
        rows.append({"measure": m, "kind": "static analysis (diagnostic, not in CQS)",
                     "nlp": -float(np.log10(p)), "p": p})

    rows.sort(key=lambda r: r["nlp"], reverse=True)

    kind_colors = {
        "craft (alignment-sensitive)":              "#1f77b4",
        "capability (pretraining)":                 "#2ca02c",
        "conditional":                              "#7f7f7f",
        "static analysis (diagnostic, not in CQS)": "#d62728",
    }
    fig, ax = plt.subplots(figsize=(11, 8.5))
    y = np.arange(len(rows))
    nlps = [r["nlp"] for r in rows]
    colors = [kind_colors[r["kind"]] for r in rows]

    bars = ax.barh(y, nlps, color=colors, edgecolor="black", linewidth=0.5, height=0.78)

    # Annotate each bar with the p-value
    for i, r in enumerate(rows):
        x_text = r["nlp"] + 0.18 if r["nlp"] > 0 else 0.05
        ha = "left"
        ax.text(x_text, i, f"p = {r['p']:.2g}", va="center", ha=ha, fontsize=8.5)

    ax.set_yticks(y)
    ax.set_yticklabels([r["measure"] for r in rows], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("-log10(p)  for Kruskal-Wallis preamble effect across 8 main conditions")
    ax.axvline(-np.log10(0.05), color="black", linestyle="--", linewidth=0.9, alpha=0.6)
    ax.text(-np.log10(0.05), -0.5, " α = 0.05",
            va="bottom", ha="left", fontsize=9, fontstyle="italic")
    ax.set_xlim(left=-0.5)
    ax.set_title(
        "Mechanism split — craft dimensions move under preamble; capability and static do not\n"
        "Bars right of dashed line are significant. 7 of 9 always-on craft dims clear it; 0 of 9 static metrics do; 0 of 2 capability dims do.",
        loc="left", pad=14,
    )

    legend_patches = [
        Patch(facecolor=kind_colors["craft (alignment-sensitive)"], edgecolor="black", label="craft  (alignment-sensitive)"),
        Patch(facecolor=kind_colors["capability (pretraining)"],    edgecolor="black", label="capability  (pretraining-dependent)"),
        Patch(facecolor=kind_colors["conditional"],                  edgecolor="black", label="conditional rubric dim"),
        Patch(facecolor=kind_colors["static analysis (diagnostic, not in CQS)"], edgecolor="black", label="static analysis  (diagnostic, not in CQS)"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", framealpha=0.95, fontsize=9)
    fig.tight_layout()
    _save(fig, "fig3_mechanism_split")
    print(f"  fig3: {OUT / 'fig3_mechanism_split.png'}")


# =============================================================================
# Figure 4 — tier comparison (side-by-side)
# =============================================================================
def fig4_tier_comparison(df: pl.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)
    titles = {"non_reasoning": "Non-reasoning subjects (7 models, n=867 samples)",
              "reasoning":     "Reasoning subjects (3 models, n=348 samples)"}

    for ax, tier in zip(axes, ("non_reasoning", "reasoning")):
        rows = []
        for cond in PREAMBLE_ORDER:
            vals = df.filter(
                (pl.col("preamble") == cond) & (pl.col("tier") == tier)
            )["cqs"].to_list()
            if not vals:
                continue
            m, lo, hi = bootstrap_ci(vals)
            rows.append({"preamble": cond, "mean": m, "lo": lo, "hi": hi,
                         "n": len(vals), "category": _preamble_bucket(cond)})
        x = np.arange(len(rows))
        colors = [CAT_COLORS[r["category"]] for r in rows]
        means = [r["mean"] for r in rows]
        los = [r["lo"] for r in rows]
        his = [r["hi"] for r in rows]
        yerr_lo = [m - lo for m, lo in zip(means, los)]
        yerr_hi = [hi - m for m, hi in zip(means, his)]

        ax.bar(x, means, color=colors, edgecolor="black", linewidth=0.5, width=0.78)
        ax.errorbar(x, means, yerr=[yerr_lo, yerr_hi], fmt="none",
                    ecolor="black", capsize=3, linewidth=1.0)
        for i, r in enumerate(rows):
            ax.text(i, r["hi"] + 0.014, f"{r['mean']:.2f}",
                    ha="center", va="bottom", fontsize=8.5)
        ax.set_xticks(x)
        ax.set_xticklabels([PREAMBLE_LABEL[r["preamble"]] for r in rows], fontsize=9)
        ax.set_ylim(0.40, 0.95)
        ax.set_title(titles[tier], loc="left", fontsize=11.5, pad=8)
        ax.set_xlabel("")
        if tier == "non_reasoning":
            ax.set_ylabel("CQS-craft")

    fig.suptitle(
        "CQS-craft by preamble × model tier — same preamble shape, different ceilings\n"
        "preamble × tier interaction is statistically non-significant for the 8 main conditions (only trivial_baseline × reasoning crosses α=0.05)",
        x=0.01, ha="left", y=0.99, fontsize=12.5, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, "fig4_tier_comparison")
    print(f"  fig4: {OUT / 'fig4_tier_comparison.png'}")


# =============================================================================
# Figure 5 — task category
# =============================================================================
def fig5_task_category(df: pl.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.0), sharey=True)
    cats = [
        ("creation",            "Creation tasks (4 tasks, n≈75-80 / condition)"),
        ("refactor",            "Refactor tasks (2 tasks, n≈37-40 / condition)"),
        ("multifile_creation",  "Multi-file creation (1 task, n≈20 / condition)"),
    ]
    for ax, (cat, title) in zip(axes, cats):
        rows = []
        for cond in PREAMBLE_ORDER:
            vals = df.filter(
                (pl.col("preamble") == cond) & (pl.col("category") == cat)
            )["cqs"].to_list()
            if not vals:
                continue
            m, lo, hi = bootstrap_ci(vals)
            rows.append({"preamble": cond, "mean": m, "lo": lo, "hi": hi,
                         "n": len(vals), "category": _preamble_bucket(cond)})
        x = np.arange(len(rows))
        colors = [CAT_COLORS[r["category"]] for r in rows]
        means = [r["mean"] for r in rows]
        los = [r["lo"] for r in rows]
        his = [r["hi"] for r in rows]
        yerr_lo = [m - lo for m, lo in zip(means, los)]
        yerr_hi = [hi - m for m, hi in zip(means, his)]
        ax.bar(x, means, color=colors, edgecolor="black", linewidth=0.5, width=0.78)
        ax.errorbar(x, means, yerr=[yerr_lo, yerr_hi], fmt="none",
                    ecolor="black", capsize=3, linewidth=1.0)
        for i, r in enumerate(rows):
            ax.text(i, r["hi"] + 0.014, f"{r['mean']:.2f}",
                    ha="center", va="bottom", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels([PREAMBLE_LABEL[r["preamble"]] for r in rows], fontsize=8.5)
        ax.set_ylim(0.30, 0.98)
        ax.set_title(title, loc="left", fontsize=10.5, pad=6)
        ax.set_xlabel("")
        if cat == "creation":
            ax.set_ylabel("CQS-craft")

    fig.suptitle(
        "CQS-craft by preamble × task category — pattern preserved across categories; refactor most sensitive to bad preambles",
        x=0.01, ha="left", y=0.99, fontsize=12.5, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig5_task_category")
    print(f"  fig5: {OUT / 'fig5_task_category.png'}")


def main() -> int:
    _apply_style()
    print(f"Generating v2 figures → {OUT}/")
    df = build_sample_frame()
    static_df = build_static_frame()
    print(f"  loaded {len(df)} CQS-scored samples + {len(static_df)} static records")
    fig1_headline_cqs(df)
    fig2_severity_heatmap(df)
    fig3_mechanism_split(df, static_df)
    fig4_tier_comparison(df)
    fig5_task_category(df)
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
