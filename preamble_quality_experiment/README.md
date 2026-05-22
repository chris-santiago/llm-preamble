# Preamble Quality Experiment

Do coding-agent preambles (system prompts) change the quality of code an LLM writes?
**Yes — but only on craft dimensions that static analysis cannot see.**

The pre-registered composite metric showed a null result (Kruskal–Wallis p = 0.63).
That null is a measurement artifact: static-analysis components (radon, pylint,
complexity metrics — 65% of the composite weight) are flat across all preamble
conditions (p ≈ 0.998), while LLM-judge components detect a strong,
hypothesis-consistent effect (idiomaticity p = 0.0022, comment quality p = 0.0058).
A "junior developer" negative-control preamble produced the worst code; rich
expert/long-directive preambles produced the best.

**If you measure preamble effects with static analysis, you will get a false negative.**

---

## Results

Kruskal–Wallis test across 7 preamble conditions, per score component (n = 274 samples):

| Score component | Weight in composite | KW p-value | Separates conditions? |
|---|---|---|---|
| static score (radon MI, pylint, CC) | 45% | 0.998 | No |
| AST score (nesting, type hints, naming) | 20% | 0.907 | No |
| **LLM-judge: idiomaticity** | 20% | **0.0022** | **Yes** |
| **LLM-judge: comment quality** | **15%** | **0.0058** | **Yes** |
| Pre-registered composite (CQS) | 100% | 0.633 | No — signal diluted by static weight |

A mixed-effects model (`score ~ preamble + (1|model)`) agrees: composite p = 0.16,
idiomaticity p = 0.010, comment quality p = 0.020.

When the static/AST weight is reduced below 50%, the composite crosses significance
(LLM-only weighting: p = 0.003). The pre-registered composite remains the primary
(null) result; the decomposition is the explanation for it.

---

## Critical warning: do not use static analysis to measure preamble effects

> Any CI or eval pipeline that scores agent output with radon, pylint, or cyclomatic
> complexity will systematically report "no preamble effect" — a false negative.
> These metrics do not move with preamble condition across 7 models and 6 hard tasks.
> Use an LLM-judge panel scoring idiomaticity and comment quality instead.

---

## Per-condition effect (LLM-judged dimensions)

Scores are cross-judge means on a 0–1 scale. The "junior developer" negative control
and the "long directive" expert preamble mark the predicted floor and ceiling.

| Preamble condition | Idiomaticity | Comment quality |
|---|---|---|
| negative_control ("junior developer still learning") | 0.774 | **0.601 (worst)** |
| minimal ("You are a helpful assistant.") | 0.757 | 0.668 |
| none (no system prompt) | 0.821 | 0.681 |
| generic_coding ("You are an expert software engineer") | 0.802 | 0.680 |
| persona_only (senior engineer, no explicit directives) | 0.811 | 0.715 |
| real_agent (expert persona + 6 quality directives) | 0.809 | 0.711 |
| **long_directive (expert persona + full directive set)** | **0.842 (best)** | **0.746 (best)** |

Effect size is modest (≈0.10–0.15 on comment quality). This establishes direction and
existence, not magnitude sufficient for a production decision without further A/B
validation.

Notable: `persona_only` (a senior-engineer persona with no explicit instructions)
matches `real_agent` on quality. Distributional priming alone — without directives —
lifts quality above the no-preamble baseline.

---

## Production recommendation

**For choosing a preamble:** a rich, directive-heavy expert preamble is worth it for
code-craft-sensitive agents. A "junior developer" framing is actively harmful and
should never ship. Weigh the gain (≈0.10–0.15 on comment quality) against token
cost — `long_directive` adds approximately 300 preamble tokens to every call.

**For building an eval pipeline:** use an LLM-judge panel (3–4 models, none of which
are the subject model being evaluated) scoring idiomaticity and comment quality with
structured output. Do not include static analysis as a primary signal; include it as a
debugging diagnostic only.

**Deployment path:**
1. Shadow — run the LLM-judge eval offline on a sample of existing agent output across
   candidate preambles; confirm the separation reproduces on your own task distribution.
2. Canary — A/B two preambles (e.g. current vs `long_directive`) on a subset of real
   traffic; measure craft scores plus token-cost delta and any task-success regression.
3. Full — adopt the winning preamble; keep the judge-panel eval as a recurring
   regression gate on craft quality, separate from functional correctness tests.

---

## Quickstart

Requires Python with `uv` and an OpenRouter API key.

```bash
export OPENROUTER_API_KEY=your-key-here

# Sanity check: 1 model × 2 conditions × 1 task (~20 API calls, fast)
uv run preamble_quality_experiment2.py

# Full experiment: 7 models × 8 conditions × 6 tasks (~3456 API calls)
uv run preamble_quality_experiment2.py --full

# Re-run analysis on existing results without re-generating code
uv run reanalyze.py
```

Results are written to `experiment2_results/`. Key outputs:
- `experiment2_results/full_results.jsonl` — one row per (task, preamble, model) triple
- `experiment2_results/reanalysis_component_separation.png` — the main result figure
- `experiment2_results/reanalysis_reweight_sensitivity.png` — sensitivity to composite weighting

---

## How we got here

**Design.** The experiment generated code using 7 LLM subject models across 8 preamble
conditions and 6 hard tasks (3 from-scratch creation, 3 refactoring). Each generated
code sample was then scored by a cross-judge panel of 8 LLM judges — every judge
scored every sample, and self-judgments (where the subject and judge model are the same)
were excluded from the primary scores. This produced 274 scored samples and 2192
cross-judge ratings.

The Composite Quality Score (CQS) combines static-analysis metrics (radon Maintainability
Index, cyclomatic complexity, Halstead difficulty, pylint severity — weighted 65%
combined) with LLM-judge ratings for idiomaticity ("how Pythonically idiomatic is this
code?") and comment quality ("do comments explain why, not just what?" — weighted 35%
combined). Scores are normalized to 0–1 using data-driven [5th, 95th] percentile bounds.

**The PoC and what changed.** An earlier proof-of-concept run (3 models, 5 conditions,
3 easy tasks) returned a null. Before running the full experiment, a structured critique
identified two likely problems: static metrics may be insensitive to the craft-level
differences preambles produce, and easy tasks may ceiling out before preamble effects
can appear. The full experiment used harder tasks (creation + refactoring) and tracked
component scores separately to test whether the null was a real result or a metric
artifact. It was a metric artifact.

**The decomposition.** Static-analysis scores (radon MI, pylint, complexity) produced
p ≈ 0.998 — essentially no variance across conditions, on 7 models and 6 hard tasks.
AST-derived scores (nesting depth, type-hint presence, naming compliance) were similarly
flat at p = 0.907. The LLM-judge components — idiomaticity and comment quality — clearly
separated conditions (p = 0.0022 and p = 0.0058). A post-hoc sensitivity analysis
confirmed that the composite crosses significance precisely as the static weight falls
below 50%. The pre-registered composite stayed null because 65% of its weight is assigned
to components with zero discriminative power for preamble-driven quality differences.

**Self-preference bias check.** Because the same model families appear as both subjects
and judges, self-preference bias was tested directly. The self-vs-cross idiomaticity
delta was 0.36 on a 10-point scale (Cohen's d = 0.16, Mann–Whitney p = 0.13) — present
but negligible, and the primary scores already exclude self-judgments.

---

## Caveats

- **grok-4.1-fast was deprecated mid-run.** All 48 calls returned 404. This model
  contributed no data, leaving 7 effective subject models instead of 8. Update the
  model list (e.g. to grok-4.3) before any re-run.
- **Elevated extraction failures** for nemotron-3-super (~15%), qwen3.5, and minimax —
  these models emit reasoning prose instead of fenced code. Failures are logged and
  excluded, not scored zero, which thins those models' per-cell counts.
- **Effect sizes are modest.** The ≈0.10–0.15 comment-quality gap establishes direction
  and statistical significance; it is not a calibrated magnitude for a production ROI
  decision without further validation on your own task distribution.
- **Single-turn generation only.** Whether the effect holds on multi-turn agentic tasks
  (multi-file edits, tool calls, iterative refinement) is unknown.
- **The F1 sensitivity probe rests on 3 hand-authored synthetic samples.** The
  ordering violation (static mis-ranks known-quality samples) is directionally
  informative but not a calibrated psychometric result.
- **Two AST sub-metrics carry near-zero variance:** cognitive-complexity violations
  (nonzero in 5/274 samples) and bare-except count (1/274). Modern models essentially
  never commit these errors.

---

<details>
<summary>File inventory and reference material</summary>

### Experiment scripts

| File | Purpose |
|---|---|
| `preamble_quality_experiment2.py` | Full experiment — generation, judging, scoring |
| `reanalyze.py` | Re-run analysis on existing `experiment2_results/` without re-generating |
| `preamble_quality_poc.py` | Original proof-of-concept script (Step 2, stale) |
| `diag_components.py` | Diagnostic: per-component score distributions |
| `log_entry.py` | Investigation log writer |

### Results and figures (`experiment2_results/`)

| File | Contents |
|---|---|
| `full_results.jsonl` | One row per (task, preamble, model) triple |
| `generation_results.jsonl` | Raw generation outputs |
| `judge_results.jsonl` | Raw per-judge ratings |
| `extraction_failures.jsonl` | Samples that could not be parsed for static analysis |
| `stats_results.json` | Kruskal–Wallis, Spearman rho, per-condition CQS |
| `reanalysis_results.json` | Mixed-effects model results and re-weighting sensitivity |
| `normalization_bounds.json` | Data-driven [5th, 95th] percentile bounds used for normalization |
| `f1_sensitivity_probe.json` | Static mis-ranking probe on 3 synthetic samples |
| `f3_self_preference.json` | Self-vs-cross judge delta calculation |
| `reanalysis_component_separation.png` | Main result: per-component KW separation (primary figure) |
| `reanalysis_reweight_sensitivity.png` | Composite p-value as static weight varies |
| `finding_component_breakdown.png` | Per-condition score by component |
| `finding_all_conditions_cqs.png` | All-condition composite CQS bar chart |
| `finding_per_model_heatmap.png` | CQS heatmap across subject models |
| `finding_f2_mechanism.png` | Persona-only vs directive-based priming comparison |

### Documentation

| File | Purpose |
|---|---|
| `CONCLUSIONS.md` | Authoritative final findings with full statistical detail |
| `REPORT_ADDENDUM.md` | Production re-evaluation and revised recommendation |
| `HYPOTHESIS.md` | Pre-registered hypothesis and metric specification |
| `INVESTIGATION_LOG.jsonl` | Machine-readable investigation event log |

### Preamble conditions (full experiment — 8 conditions)

| Condition | Description |
|---|---|
| `none` | No system prompt |
| `minimal` | "You are a helpful assistant." |
| `generic_coding` | "You are an expert software engineer..." |
| `persona_only` | Senior engineer persona, no explicit quality directives |
| `real_agent` | Expert persona + 6 explicit quality directives |
| `long_directive` | Expert persona + full extended directive set (~300 tokens) |
| `negative_control` | "You are a junior developer still learning..." |
| `trivial_baseline` | Degenerate floor: prompt is the task name only, no system prompt, temperature 1.0 |

### CQS component definitions

| Component | Metrics included | Weight |
|---|---|---|
| static_score | Radon Maintainability Index, cyclomatic complexity, Halstead difficulty, pylint severity, PEP8 name-compliance ratio | 45% |
| ast_score | Max nesting depth, type-hint presence, bare-except count, cognitive-complexity violations | 20% |
| llm_idiom_score | 8-judge panel (1–10): "How Pythonically idiomatic is this code?" | 20% |
| llm_comment_score | 8-judge panel (1–10): "Do comments explain why, not what?" | 15% |

</details>
