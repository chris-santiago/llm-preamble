# Statistical methods

The v2 main run reports three classes of statistic: a non-parametric omnibus test across preambles (Kruskal–Wallis), bootstrap 95% confidence intervals on per-condition means, and a mixed-effects model that quantifies the `preamble × tier` interaction while crossing random intercepts on subject `model` and `task`.

**Source of truth:**

- Bootstrap CI + Kruskal–Wallis: [`preamble_quality_v2_main.py` lines 885–902](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L885).
- Mixed-effects (M0/M1/M2): [`analysis_addendum.py`](../../preamble_quality_experiment_v2/analysis_addendum.py).
- Fitted output: [`experiment_v2_results/MIXED_EFFECTS.md`](https://github.com/chris-santiago/llm-preamble/blob/main/preamble_quality_experiment_v2/experiment_v2_results/MIXED_EFFECTS.md).
- Weight-sensitivity panel: [`experiment_v2_results/WEIGHT_SENSITIVITY.md`](https://github.com/chris-santiago/llm-preamble/blob/main/preamble_quality_experiment_v2/experiment_v2_results/WEIGHT_SENSITIVITY.md).

---

## Kruskal–Wallis omnibus

Non-parametric test for whether ≥2 distributions over preamble conditions differ. Used as the **primary headline test** and as the cell-statistic for every weight-sensitivity row.

```python
def kruskal_across_conditions(by_cond: dict[str, list[float]]) -> dict:
    groups = [v for v in by_cond.values() if len(v) >= 2]
    if len(groups) < 2:
        return {"H": None, "p": None, "n_groups": len(groups)}
    H, p = stats.kruskal(*groups)
    return {"H": float(H), "p": float(p), "n_groups": len(groups)}
```

**Headline result.** Across the 8 main conditions (excluding `trivial_baseline`), pooled across the full subject pool: H = 95.48, p = 9.24 × 10⁻¹⁸ on per-sample CQS-craft. Within the reasoning tier alone: H = 49.57, p = 1.76 × 10⁻⁸. The omnibus is also run per always-on rubric dimension; 7 of 9 dimensions return p < 10⁻⁴, 2 do not (`algorithm_correctness` p ≈ 0.26; `data_structure_choice` p ≈ 0.39).

Why non-parametric: CQS-craft is a weighted bounded composite, and the per-sample distributions are not Gaussian. Kruskal–Wallis avoids the normality assumption while remaining sensitive to mean differences.

---

## Bootstrap 95% CI

Percentile-bootstrap mean with `n_boot = 2000` and a fixed seed for reproducibility (`2026_05_22`):

```python
def bootstrap_ci(values, n_boot: int = 2000, alpha: float = 0.05):
    arr = np.asarray(values, dtype=float)
    if len(arr) < 2:
        m = float(arr.mean()) if len(arr) else float("nan")
        return m, m, m
    rng = np.random.default_rng(2026_05_22)
    boot = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    lo = float(np.quantile(boot, alpha / 2))
    hi = float(np.quantile(boot, 1 - alpha / 2))
    return float(arr.mean()), lo, hi
```

Reported in [`REPORT.md`](https://github.com/chris-santiago/llm-preamble/blob/main/preamble_quality_experiment_v2/experiment_v2_results/REPORT.md) for every per-condition mean, tier-stratified mean, and category-stratified mean.

---

## Mixed-effects model — M0 / M1 / M2

The mixed-effects analysis is fit in [`analysis_addendum.py`](../../preamble_quality_experiment_v2/analysis_addendum.py) with [statsmodels](https://www.statsmodels.org/) `mixedlm`. Each fit has:

- **Random intercept on `model`** (the primary group), absorbing per-subject offsets in mean CQS.
- **Random intercept on `task`** via the `vc_formula={"task": "0 + C(task)"}` trick, which statsmodels supports as a second variance component group.
- **REML estimation** with `lbfgs`, `maxiter=200`. An **ML refit** is also reported for principled fixed-effects likelihood-ratio comparisons.
- `preamble` is a categorical with `none` as the reference cell.
- `tier` is a categorical with `non_reasoning` as the reference cell. **Tier is constant within each model**, so `(1|model)` absorbs within-tier between-model variance and the `tier` term captures the mean shift between tiers.

### Model ladder

| Label | Formula | Question |
|-------|---------|----------|
| **M0** | `cqs ~ C(preamble)` | Does preamble matter, ignoring tier? |
| **M1** | `cqs ~ C(preamble) + C(tier)` | Does tier *add* explanatory power on top of preamble? |
| **M2** | `cqs ~ C(preamble) * C(tier)` | Does the preamble effect *differ by tier*? (full model) |

ΔlogLik between successive models is reported descriptively, with an ML refit included for a principled fixed-effect LRT. M2 is the model whose `preamble` coefficients are quoted in CONCLUSIONS.md as the "strict mixed-effects test against `none`."

The stratified per-tier fits (reasoning-only and non-reasoning-only) are retained as a back-compat reporting view but are **superseded by M2**, which estimates the same quantities with proper pooling.

---

## Weight sensitivity

Seven alternative CQS-component weight schemes are evaluated to show that the headline does not depend on the pre-registered `0.45 / 0.45 / 0.10` choice. For each scheme, the per-condition mean is recomputed and a fresh KW p across the 8 main conditions is reported. See [`WEIGHT_SENSITIVITY.md`](https://github.com/chris-santiago/llm-preamble/blob/main/preamble_quality_experiment_v2/experiment_v2_results/WEIGHT_SENSITIVITY.md) for the full table; all seven schemes return KW p ≤ 2.4 × 10⁻¹⁰.

Schemes tested:

| Scheme | (idiom, comment, hygiene) |
|--------|---------------------------|
| pre-reg | `(0.45, 0.45, 0.10)` |
| idiom-only | `(1.00, 0.00, 0.00)` |
| comment-only | `(0.00, 1.00, 0.00)` |
| rubric-only | `(0.00, 0.00, 1.00)` |
| rubric-heavy | `(0.30, 0.30, 0.40)` |
| equal-thirds | `(0.34, 0.33, 0.33)` |
| v1-static-heavy proxy | `(0.20, 0.20, 0.60)` |

---

## What's *not* in the primary pipeline

- **Static-analysis metrics** (radon CC, pylint, flake8 cognitive-complexity) are computed per sample but never enter CQS-craft. They are reported only as a diagnostic panel — v1 established they are flat across preambles, and reproducing that null is itself a precondition check. See [`compute_static_metrics()` at line 719](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L719).
- **Human-rater validation.** All scoring is LLM-judge based; no human rater is in the loop. The 10-judge panel + calibration anchor + self-judgment exclusion mitigate single-judge pathology.

Related: [glossary](glossary.md) for term definitions, [judge protocol](judge-protocol.md) for how the inputs to these stats are produced.
