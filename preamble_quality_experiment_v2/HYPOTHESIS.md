# Hypothesis — Preamble Quality Experiment v2 (Cycle 2)

This is a second-cycle investigation succeeding the v1 work in
`/Users/chrissantiago/Dropbox/GitHub/llm-preamble/preamble_quality_experiment/`.
v1 verdict: hypothesis SUPPORTED on LLM-judged craft dimensions (idiomaticity
KW p = 0.0022, comment-quality KW p = 0.0058) but masked at the headline by a
static-analysis-heavy composite (KW p = 0.633) whose static components were
flat to p = 0.998 and mis-ranked known-quality samples (F1 confirmed). The
v2 design is pinned in `SPEC_V2.md`; that document is authoritative for
conditions, tasks, rubric dimensions, primary metric formula, sample-size
target, and the pre-registration boundary. This file restates the cycle-2
hypothesis and metrics for the investigation log.

> **Revision log:** This file now contains THREE hypothesis statements,
> in reverse chronological order. The currently-active one is
> "Cycle 2 — Re-revised (ACTIVE)" immediately below. Two prior versions
> are preserved as a record of the framing drift caught and corrected
> during pre-registration:
>   - "Cycle 2 — Revised" (SUPERSEDED at pre-flight Phase D after the
>     pool was macro-iterated to a reasoning-inclusive design and the
>     rubric was redesigned for algorithmic-code dimensions; see
>     `INVESTIGATION_LOG.jsonl` seq 30 and `SPEC_V2.md §12`).
>   - "Cycle 2 — Initial draft" (SUPERSEDED at Step 2 intent review;
>     see seq 5).

## Hypothesis — Cycle 2 (Re-revised, ACTIVE)

**Claim:** In a production-realistic LLM population (reasoning-capable +
non-reasoning models, OpenRouter-routed, with reasoning enabled where
supported), coding-agent preambles change the craft quality of single-turn
Python code outputs. Detection criterion: a statistically significant main
effect of preamble condition on CQS-craft (LLM-judge components only) in at
least one of the two stratified analyses — non-reasoning tier (the v1
question, re-answered with the corrected instrument) and reasoning tier
(the production-realistic regime). Central contrast: any rich preamble
vs. `none` vs. `negative_control`. The effect is expected to be larger
on creation tasks than on refactor tasks.

**Mechanism (pre-registered, later refined post-main-run):** Preambles act
as distributional priming on the *alignment-dependent* axis of LLM
capability — style, idiom, naming, comment quality, abstraction
calibration — shaped during instruction-tuning. They do not measurably
move *pretraining-dependent* axes — structural complexity, functional
correctness as captured by static analysis. This split is the v1 finding
and the published literature it cites (`RELATED_WORK.md`; USC PRISM 2026;
Zheng et al. EMNLP 2024).

> **Post-hoc mechanism refinement (after the confound probes, see
> `CONCLUSIONS.md §"Confound probes"`):** The pre-registered
> "alignment vs capability" framing was partially correct but
> over-stated. The three post-main-run probes (A nonrubric-expert,
> B bare-rubric, C anti-rubric) showed that what governs whether a
> dimension moves under preamble is the **overlap between dimensions
> the preamble enumerates and dimensions the rubric measures**. The
> pre-registered hypothesis predicted that capability-side dimensions
> (algorithm_correctness, data_structure_choice) would be immobile
> under preamble; this came out empirically true in v2, but the probes
> suggest the proximate reason is that *no preamble in v2's condition
> set enumerates those dimensions* — not that they are structurally
> pretraining-locked. A v3 probe naming algorithmic correctness directly
> would discriminate. Refined mechanism: preambles direct the model's
> craft-attention budget to enumerated dimensions; CQS-craft measures
> the overlap. The headline H1 (preambles move judge-scored craft)
> remains supported; the mechanistic gloss is refined from
> "alignment vs capability" to "preamble-enumerated vs unenumerated"
> dimensions.

**Open sub-question (reasoning tier):** Reasoning models may absorb craft
signals during their internal chain-of-thought before content generation,
which could either amplify the preamble effect (the preamble shapes the
reasoning trajectory) or dilute it (the model overrides the priming via
explicit deliberation). The reasoning-tier stratum tests which.

**Signal:** Per-dimension severity ratings (0–5) from a cross-judge panel
on the redesigned 11-dim algorithmic-code rubric defined in
`SPEC_V2.md §6.4 (Amendment A1)`. Aggregate signal: CQS-craft mean per
condition (cross-judge, self-judgments excluded) with bootstrap CIs.
Per-dimension signal: KW tests across conditions for each of 9 always-on
rubric items (plus the 2 conditional items where applicable), stratified
by task category (`creation` vs `refactor`) and model tier (reasoning vs
non-reasoning).

**Expected observable (pre-specified pass criteria):**

- **Primary (stratified):** CQS-craft Kruskal–Wallis p < 0.05 across the
  9 main conditions in **at least one** of {non-reasoning sub-pool,
  reasoning sub-pool, pooled 10-model pool}; bootstrap 95% CIs separate
  `negative_control` from at least one rich-preamble condition in the
  same stratum.
- **Per-dimension:** at least 3 of the 9 always-on rubric dimensions
  show preamble-significant separation (KW p < 0.05) in at least one
  tier stratum. Threshold lowered from v2-initial's "4 of 11" to "3 of
  9" to reflect the new rubric's fewer always-on dimensions; relative
  fraction unchanged (~33%).
- **Task-category stratification:** aggregate rubric severity mean is
  lower (better) under rich preambles than under `none` /
  `negative_control` in **both** creation and refactor strata, with a
  larger absolute gap in the creation stratum.
- **Tier effect-size delta:** report the difference between
  reasoning-tier and non-reasoning-tier effect sizes (rank-biserial r or
  ε² from KW) as a panel; no significance threshold pre-registered for
  this — it is descriptive only.
- **Diagnostic null (expected):** static-analysis metrics remain flat
  across preamble conditions in both tiers (KW p > 0.5 on each).

**Role of `python_coder_agent`:** unchanged — one rich-preamble data point
in the pool, included for external validity, not adjudicated against other
rich preambles.

---

## Hypothesis — Cycle 2 (Revised — SUPERSEDED at Phase D)

> **Status:** SUPERSEDED at pre-flight Phase D when (a) the rubric was
> redesigned for algorithmic-code dimensions after the python-coder S3+
> checklist showed 0/11 dimension prevalence, and (b) the pool was
> macro-iterated to a reasoning-inclusive design after the user
> methodological challenge that a non-reasoning-only pool answers a
> question of low practical relevance. The 7-model pool and 14-dim S3+
> rubric in this section are no longer authoritative. Preserved for the
> investigation record only.

**Claim:** Coding-agent preambles change the quality of code an LLM writes —
the v1 hypothesis, tested under a corrected instrument. Detection criterion:
a statistically significant main effect of preamble condition on a
craft-weighted Composite Quality Score (CQS-craft) constructed from
LLM-judge components only, where the central contrast is **any non-trivial
preamble vs. no preamble vs. negative control**. The effect is expected to
be larger on creation tasks (where the model has unspecified design
discretion) than on refactoring tasks (where the target smell is named
in the prompt).

**Mechanism:** Preambles act as distributional priming on the
*alignment-dependent* axis of LLM capability — style, idiom, naming,
comment quality, abstraction calibration — shaped during instruction-tuning.
They do not measurably move *pretraining-dependent* axes — structural
complexity, functional correctness as captured by static analysis. This
split is the v1 finding and the published literature it cites
(`RELATED_WORK.md`; USC PRISM 2026; Zheng et al. EMNLP 2024). Preambles
that frame the model as competent should lift craft scores; "junior
developer" framing should lower them; static-analysis metrics should
remain insensitive to preamble condition across all tasks.

**Signal:** Per-dimension severity ratings (0–5) from a cross-judge panel on
the 14-dimension rubric defined in `SPEC_V2.md §6.4`. Aggregate signal:
CQS-craft mean per condition (cross-judge, self-judgments excluded) with
bootstrap CIs. Per-dimension signal: KW tests across conditions for each
of 11 single-file rubric items, stratified by task category (`creation` vs
`refactor`).

**Expected observable (pre-specified pass criteria):**

- **Primary:** CQS-craft Kruskal–Wallis p < 0.05 across the 9 main
  conditions; bootstrap 95% CIs separate `negative_control` from at least
  one rich-preamble condition (`real_agent`, `long_directive`, or
  `python_coder_agent`). Reproduces v1's idiom/comment significance at
  the now-corrected metric level.
- **Per-dimension:** at least 4 of the 11 single-file rubric dimensions
  show preamble-significant separation (KW p < 0.05). v1 baseline: 0 of
  8 binary items reached significance; v2 expects severity-scale + larger
  n to surface the directionally-consistent effects we saw at p ≈
  0.12–0.35.
- **Task-category stratification:** aggregate rubric severity mean is
  lower (better) under rich preambles than under `none` / `negative_control`
  in **both** creation and refactor strata, with a larger absolute gap
  in the creation stratum.
- **Diagnostic null (expected):** static-analysis metrics remain flat
  across preamble conditions (KW p > 0.5 on each). This is the v1 finding
  re-tested as a precondition.

**Role of the `python_coder_agent` condition:** included as one of the
rich-preamble conditions, sampled in the comparison alongside `real_agent`
and `long_directive`. The investigation is **not** designed to determine
whether `python_coder_agent` is better than other rich preambles; that
contrast is incidental, not primary. The condition broadens the
"rich preamble" category to include a real production system prompt
verbatim, increasing external validity of the rich-preamble pool.

---

## Hypothesis — Cycle 2 (Initial draft — SUPERSEDED)

> **Status:** SUPERSEDED at Step 2 intent review. Preserved for the
> investigation record only. Do not use for any subsequent step.

**Claim:** Coding-agent preambles change the quality of code an LLM writes,
detectable as a statistically significant main effect of preamble condition on
a craft-weighted Composite Quality Score (CQS-craft) constructed from LLM-judge
components only (≤10% rubric-derived hygiene weight, no static-analysis-derived
component). The effect is larger on creation tasks (where the model has
unspecified design discretion) than on refactoring tasks (where the target
smell is named in the prompt). A real production preamble (the chris-code
python-coder agent's full system prompt) produces craft quality at least as
high as the strongest synthetic preambles (`real_agent`, `long_directive`).

**Mechanism:** Preambles act as distributional priming on the
*alignment-dependent* axis of LLM capability — style, idiom, naming, comment
quality, abstraction calibration — shaped during instruction-tuning. They do
not measurably move *pretraining-dependent* axes — structural complexity,
functional correctness as captured by static analysis. This split is the
finding of the v1 investigation and the published literature it cites
(`RELATED_WORK.md`; USC PRISM 2026; Zheng et al. EMNLP 2024). Preambles that
combine a credible expert persona with explicit quality directives should
produce the largest craft gains; a "junior developer" framing should
reliably produce the lowest craft scores; static-analysis metrics should
remain insensitive to preamble condition across all tasks.

**Signal:** Per-dimension severity ratings (0–5) from a cross-judge panel on
the 14-dimension rubric defined in `SPEC_V2.md §6.4`, drawn from the
chris-code python-coder agent's S3+ checklist and python-review-lite gate.
Aggregate signal: CQS-craft mean per condition (cross-judge, self-judgments
excluded) with bootstrap CIs. Per-dimension signal: KW tests across conditions
for each of 11 single-file rubric items (plus 3 multi-file items if the
multi-file task ships), stratified by task category (`creation` vs `refactor`,
plus `multifile_creation` if applicable).

**Expected observable (pre-specified pass criteria):**

- **Primary:** CQS-craft Kruskal–Wallis p < 0.05 across the 9 main conditions;
  bootstrap 95% CIs separate `negative_control` from at least one of
  `long_directive`, `real_agent`, or `python_coder_agent`.
- **Per-dimension:** at least 4 of the 11 single-file rubric dimensions show
  preamble-significant separation (KW p < 0.05). v1 baseline: 0 of 8 binary
  items reached significance; v2 expects severity-scale + larger n to surface
  the directionally-consistent effects we saw at p ≈ 0.12–0.35.
- **External validity of the new condition:** the `python_coder_agent`
  condition's CQS-craft is within bootstrap CI overlap with — or strictly
  greater than — `long_directive`. (Tests whether real production preambles
  behave like the synthetic strong-preamble conditions.)
- **Task-category stratification:** aggregate rubric severity mean is lower
  (better) under `long_directive` / `python_coder_agent` than under `none` /
  `negative_control` in **both** creation and refactor strata, with a
  larger absolute gap in the creation stratum.
- **Diagnostic null (expected):** static-analysis metrics (radon MI, avg
  cyclomatic complexity, Halstead difficulty, pylint penalty) remain flat
  across preamble conditions (KW p > 0.5 on each). This is the v1 finding
  re-tested as a precondition; if false, the v1 instrument-correction was
  wrong and the metric design must be revisited.

## Evaluation Metrics

**Primary — CQS-craft** (pre-registered formula, see `SPEC_V2.md §6.5`):

```
CQS_craft = 0.45 * llm_idiom_score
          + 0.45 * llm_comment_score
          + 0.10 * (1 - mean_rubric_severity / 5)
```

All three components are LLM-judge-derived. `llm_idiom_score` and
`llm_comment_score` are cross-judge means on a 1–10 scale, divided by 10.
`mean_rubric_severity` is the mean of the 11 single-file rubric dimensions
(0–5 scale), cross-judge averaged per sample; the `(1 - ./5)` transform
makes lower severity contribute higher CQS. Weights are locked at
pre-registration. A sensitivity table over alternative weighting schemes
is reported alongside the primary result but does not redefine the metric.

**Secondary — Per-dimension severity separation.** For each of the 11
single-file rubric dimensions, per-condition mean severity with KW p-value
and creation-vs-refactor stratification.

**Tertiary — Static-analysis diagnostic panel.** Radon Maintainability Index,
average cyclomatic complexity, Halstead difficulty, pylint penalty, PEP8
name-compliance ratio. Reported as a separate diagnostic, never as a CQS
input. Used to verify the v1 null reproduces (precondition for the v2
hypothesis to be meaningful).

**Domain:** `preamble_quality_v2`

## Pre-registration boundary

The design elements pinned in `SPEC_V2.md` §§6.1–6.5 (conditions, tasks,
rubric dimensions, judge pool, primary-metric formula and weights, sample-size
target, severity scale) are **locked** at the moment investigation_start is
logged. Any subsequent change must be recorded as a documented amendment with
rationale, re-opening Gate 1 if it would alter the primary result. The
intent-watch monitor will run during scripting to flag silent drift.
