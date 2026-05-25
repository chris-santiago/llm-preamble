# Results schema

Field-level reference for every output file produced by the v2 pipeline. All files live under [`preamble_quality_experiment_v2/experiment_v2_results/`](../../preamble_quality_experiment_v2/experiment_v2_results/) (main run) or [`preamble_quality_experiment_v2/confound_probe_results/`](../../preamble_quality_experiment_v2/confound_probe_results/) (post-hoc probes).

JSONL files are **append-only** — never rewrite, sort, or hand-edit them. See repo CLAUDE.md.

---

## `generations.jsonl`

One row per (preamble × task × model × rep) cell, written incrementally by [`run_phase_generation()`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L908). Total: 1260 rows in the main run.

| Field | Type | Description |
|-------|------|-------------|
| `key` | str | Stable per-cell ID: `"{task_id}|{preamble_id}|{model}|r{rep}"`. Used as the join key into `judgments.jsonl`, `sample_cqs.json`, and `static_analysis.jsonl`. |
| `task_id` | str | One of the 7 task IDs — see [tasks](tasks.md). |
| `category` | str | `"creation"`, `"refactor"`, or `"multifile_creation"`. |
| `preamble_id` | str | One of the 9 main conditions. |
| `model` | str | OpenRouter model slug (e.g. `"google/gemini-3.1-flash-lite"`). |
| `rep` | int | 1-indexed replication ID. |
| `code` | str | Extracted Python code (post-`extract_python_code()`). Empty if extraction failed. |
| `extraction_ok` | bool | `True` if `code` is non-empty. Failed extractions are excluded from judging and CQS. |
| `raw_preview` | str | First 400 chars of the raw model response — useful for diagnosing extraction failures. |
| `provider` | str \| null | OpenRouter routing field — which inference provider actually served the request. |
| `model_returned` | str \| null | The model slug OpenRouter reports it actually used (may diverge from requested under fallback routing). |
| `completion_tokens` | int | Total completion tokens billed. |
| `reasoning_tokens` | int | Subset of completion tokens spent on reasoning; 0 for non-reasoning models. |
| `cost` | float | USD cost for this single generation. |
| `error` | str \| null | If the request failed after all retries, the last error string; otherwise null. |

---

## `judgments.jsonl`

One row per (generation × judge_model × kind) call. Total: ~24,300 rows in the main run (22,028 with `parsed` non-null). Written by [`run_phase_judging()`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L936).

| Field | Type | Description |
|-------|------|-------------|
| `jkey` | str | Per-judge-call ID: `"{gen_key}|judge={judge_model}|kind={kind}"`. |
| `gen_key` | str | Foreign key into `generations.jsonl`. |
| `task_id`, `category`, `preamble_id` | str | Denormalized from the generation row. |
| `subject_model` | str | The model that produced the code. |
| `judge_model` | str | The model that is scoring it. |
| `is_self_judge` | bool | True iff `model_family(judge_model) == model_family(subject_model)`. Excluded from primary CQS. See [models](models.md#self-judgment-exclusion). |
| `kind` | str | `"idiom_comment"` or `"rubric"`. |
| `cost` | float | USD cost for this judge call. |
| `judge_error` | str \| null | HTTP error, parse failure (`"parse_fail: ..."`), or null on success. |
| `parsed` | object \| null | The JSON payload from the judge. Shape depends on `kind` (see [judge protocol](judge-protocol.md#two-judge-kinds)). |

For `kind=idiom_comment`: `parsed = {"idiomaticity": <1-10>, "comment_quality": <1-10>}`.

For `kind=rubric`: `parsed = {"<dim_id>": {"severity": <0-5 or null>, "rationale": "<one sentence>"}, ...}` for the 11 [rubric](rubric.md) dimensions.

---

## `sample_cqs.json`

One row per extracted generation (1215 in the main run). Produced by [`compute_sample_cqs()`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L816), self-judgments excluded.

| Field | Type | Description |
|-------|------|-------------|
| `gen_key` | str | Foreign key into `generations.jsonl`. |
| `n_cross_idiom`, `n_cross_comment`, `n_cross_rubric` | int | Number of cross-judge calls contributing to each component. |
| `idiom_score` | float \| null | Cross-judge mean of idiomaticity (1–10 scale), clamped. |
| `comment_score` | float \| null | Cross-judge mean of comment_quality (1–10 scale), clamped. |
| `rubric_sev_mean` | float \| null | Cross-judge mean of per-judge mean severity across rubric dims (0–5 scale, with conditional-N/A `null`s excluded from each judge's mean). |
| `per_dim_means` | dict | `{dim_id: cross_judge_mean_severity or null}` for all 11 rubric dimensions. |
| `cqs_craft` | float \| null | `0.45·(idiom/10) + 0.45·(comment/10) + 0.10·(1 − rubric_sev_mean/5)`. Null iff any component is null. |

---

## `static_analysis.jsonl`

One row per extracted generation, computed by [`compute_static_metrics()`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L719) via subprocess calls to radon / pylint / flake8. **Diagnostic panel only — never enters CQS.**

| Field | Type | Description |
|-------|------|-------------|
| `key` | str | Foreign key into `generations.jsonl`. |
| `avg_cyclomatic`, `max_cyclomatic` | float | radon cyclomatic complexity. |
| `maintainability_index` | float | radon MI. |
| `halstead_volume`, `halstead_difficulty` | float | radon Halstead metrics. |
| `pylint_errors`, `pylint_warnings`, `pylint_conventions`, `pylint_refactor` | float | pylint message counts. |
| `cognitive_complexity_violations` | float | flake8-cognitive-complexity CCR001 violations at `--max-cognitive-complexity=30`. |
| `error` | str (optional) | Present iff static analysis itself failed. |

---

## `REPORT.md`

Human-readable summary, written by [`write_report()`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L987). Sections:

1. **Primary — CQS-craft by preamble (pooled).** Per-condition mean + 95% bootstrap CI + Kruskal–Wallis omnibus.
2. **Tier stratification.** Same table, split by reasoning vs non-reasoning.
3. **Category stratification.** Same table, split by creation vs refactor.
4. **Per-dimension severity by preamble (cross-judge means).** 11 rubric dims × 9 conditions, with KW p per dim.
5. **Static-analysis diagnostic panel.** Confirmation that static metrics remain flat across conditions (the v1 false-null reproduction).
6. **Run cost + parse-fail rate.**

The headline KW p = 9.24 × 10⁻¹⁸ on pooled CQS-craft is in §1.

---

## `MIXED_EFFECTS.md`

Written by [`analysis_addendum.py`](../../preamble_quality_experiment_v2/analysis_addendum.py). Sections:

- **M0** (`cqs ~ C(preamble)`) — baseline mixed-effects, no tier term.
- **M1** (`cqs ~ C(preamble) + C(tier)`) — tier main effect.
- **M2** (`cqs ~ C(preamble) * C(tier)`) — **full model with `preamble × tier` interaction.** The β / SE / z / p / 95%-CI per coefficient is the table cited in CONCLUSIONS.md.
- ΔlogLik between successive models (descriptive).
- **ML refit** for principled fixed-effect LRT.
- Per-tier stratified fits (back-compat; superseded by M2).

See [statistical methods](statistical-methods.md).

---

## `WEIGHT_SENSITIVITY.md`

Per-condition CQS mean and KW p across 7 alternative weight schemes for the (idiom, comment, hygiene) components. Shows that the headline does not depend on the pre-registered `0.45 / 0.45 / 0.10` choice — all 7 schemes return KW p ≤ 2.4 × 10⁻¹⁰. Written by [`analysis_addendum.py`](../../preamble_quality_experiment_v2/analysis_addendum.py).

---

## `confound_probe_results/REPORT.md`

The post-hoc probe report. Three probes (`probe_A_nonrubric_expert`, `probe_B_bare_rubric`, `probe_C_antirubric_expert`) plus a `none_control`, all on `task_expr_parser`, all 10 subject models, full 10-judge cross-panel.

Sections:

1. **CQS-craft per probe vs reference conditions** — per-probe mean + 95% CI + Δ vs main-run `none`.
2. **Significance — Mann-Whitney U vs main-run `none`** — U statistic and two-sided p per probe.
3. **Per-dimension severity** — 9 always-on rubric dims × (4 reference cells + 4 probe cells). Reference cells are sliced from the main-run results on the same task.
4. **Discrimination verdict** — recovery-ratio interpretation. Probes A and C drop CQS by ~0.15 vs `none` (p ≈ 0.0001); probe B is statistically indistinguishable from `none`. This is the source of the [attention-allocation](glossary.md#attention-allocation) reading.

`confound_probe_results/` also contains `generations.jsonl`, `judgments.jsonl`, and `sample_cqs.json` with the same schemas as above (plus a `probe_id` field on each row in place of `preamble_id`).
