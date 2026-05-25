# Post-run analysis

After the [main run](main-run.md) writes its JSONL artifacts, two follow-up scripts produce the §9 acceptance-criteria deliverables: the mixed-effects model with weight-sensitivity table, and the five figures.

Both scripts read from `experiment_v2_results/` and write back to the same directory. They are idempotent — re-running overwrites the derived markdown/figure files but never touches the raw JSONL.

## Mixed-effects model + weight-sensitivity (`analysis_addendum.py`)

```bash
uv run preamble_quality_experiment_v2/analysis_addendum.py
```

**When to run.** After `experiment_v2_results/{generations.jsonl, judgments.jsonl, sample_cqs.json}` exist — i.e. after the main run has completed.

**What it produces.**

- `experiment_v2_results/MIXED_EFFECTS.md` — three nested models per the [pre-registration](../methodology/pre-registration.md) (§9 acceptance criterion):
    - **M0:** `CQS_craft ~ preamble + (1|model) + (1|task)` (preamble only).
    - **M1:** M0 + reasoning-tier main effect.
    - **M2:** M1 + preamble × tier interaction.
    - Likelihood-ratio tests M0-vs-M1 and M1-vs-M2 adjudicate whether tier matters as a main effect or as a moderator. Per-tier stratified fits are reported alongside for back-compat with prior reporting.
- `experiment_v2_results/WEIGHT_SENSITIVITY.md` — KW omnibus p-value and per-condition ranking under alternative CQS weight schemes, including v1's static-heavy pre-registration as a documented contrast. The pre-registered v2 weights are `w_idiom = 0.45`, `w_comment = 0.45`, `w_hygiene = 0.10`.

## Figures (`figures.py`)

```bash
uv run preamble_quality_experiment_v2/figures.py
```

**When to run.** After the main run completes. Independent of `analysis_addendum.py` — either can run first.

**What it produces** (all under `experiment_v2_results/figures/`, as SVG + PNG pairs):

| File | Content |
|---|---|
| `fig1_headline_cqs_by_preamble` | Per-preamble mean CQS-craft with bootstrap CIs, ordered by mean, color-coded by category bucket (trivial / negative / neutral / rich). |
| `fig2_per_dim_severity_heatmap` | 11 rubric dimensions x 9 preambles, with annotated cell severities. |
| `fig3_mechanism_split` | -log10(p) per measure, split into craft / capability / static-analysis groups; dashed alpha=0.05 reference line. |
| `fig4_tier_comparison` | Side-by-side reasoning vs non-reasoning panels showing same-shape-different-ceiling. |
| `fig5_task_category` | Three panels by task category (creation / refactor / multifile_creation). |

The script depends on `polars`, `numpy`, `scipy`, `matplotlib`, and `seaborn` (resolved automatically by `uv` from the PEP 723 header). The switch from ferrum-viz to matplotlib + seaborn happened at log entry seq 48 for finer label-spacing and y-axis-range control.

## Cross-reference

- Mixed-effects interpretation lives in `CONCLUSIONS.md` next to the script.
- The headline figure (fig1) is embedded in the [Findings overview](../findings/index.md) and the project root README.
- The user-caught mixed-effects correction (adding the tier indicator) is logged at `INVESTIGATION_LOG.jsonl` seq 45 — see [Investigation logs](../methodology/investigation-logs.md).
