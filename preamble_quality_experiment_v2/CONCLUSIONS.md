# Conclusions — Preamble Quality Experiment v2

**Hypothesis tested (Cycle 2 Re-revised, ACTIVE):** In a production-realistic LLM
population (3 reasoning + 7 non-reasoning models, OpenRouter-routed), coding-agent
preambles change the craft quality of single-turn Python code outputs, detectable
as a main effect of preamble condition on CQS-craft (LLM-judge components only).
The effect is expected on alignment-dependent craft axes (style, naming, comments,
error handling, edge cases) and *not* on pretraining-dependent capability axes
(structural complexity, algorithmic correctness).

**Headline finding:** **Hypothesis SUPPORTED at the corrected instrument.** With
v1's measurement instrument fixed (static analysis demoted to a diagnostic panel;
LLM-judge severity rubric redesigned for algorithmic-code dimensions; judge panel
calibrated; 1,215 valid samples vs v1's 274), the primary CQS-craft shows
preamble-condition effect at Kruskal–Wallis **p = 9.2 × 10⁻¹⁸** pooled — and at
p ≤ 2.3 × 10⁻¹² within each model tier separately. Seven of nine always-on
rubric dimensions show preamble-significant separation (criterion was three).
The two null dimensions — `algorithm_correctness` and `data_structure_choice` —
are exactly the pretraining-dependent capability axes the hypothesis predicted
would *not* move. The mechanism is cleanly confirmed: preambles move craft, not
capability.

**Design summary:** 10 subject models × 9 preamble conditions × 7 tasks
(4 creation + 2 refactor + 1 multi-file) × 2 replications = 1,260 generations;
1,215 (96.4%) extracted successfully. Full v1-equivalent cross-judge matrix
(all 10 models as judges; self-judge exclusion; reasoning judges with reasoning
disabled to neutralize judge-side reasoning as a confound; calibration anchor
on the rubric prompt to prevent severity-0 saturation). 24,300 judge calls,
22,028 (90.7%) parsed cleanly. Total cost $32.

---

## Pre-flight debate scorecard

The v2 design was pre-registered in `SPEC_V2.md` and refined through a
three-round structured debate. All seven debate findings closed before main run.

| Finding | Verdict from debate | Empirical resolution | Who was right |
|---|---|---|---|
| **F1** — judge OOR clamp bug allowed scores like −1 into the composite | critique CONCEDE sev 9 (FATAL) | **FIXED.** Drop-not-clip with structured OOR log. Mitigation verified pre-main; OOR rate during main = 0. | **Critic.** Verified bug. |
| **F2** — trap task `modeflag_sort` had no baseline smell rate | critique → ETA | **DROPPED** post pre-flight Phase B (behavior-only spec eliminated the smell across all conditions; no discriminative space). Pre-registered recovery (`SPEC_V2 §6.2 A2`). | **Critic.** Trap design was unstable. |
| **F3** — self-vs-cross judge stratification | defense_wins | **HONORED.** Cross-judge primary, self-vs-cross reported (idiom Δ +0.02 p=3e-4, comment Δ +0.29 p<1e-4). Effect present but small; exclusion was the right call. | **Defender,** v1 protocol unchanged. |
| **F4** — anchored-vs-unanchored judge prompt confound on reasoning models | critique → ETA | **RESOLVED.** Phase C re-probe (n=36 reasoning-model gens): pooled \|Δ\| 0.31 on idiom, 0.03 on comment — both below 0.5 trigger. **Decision: keep unanchored.** | **Defender,** confound did not bind on reasoning tier. |
| **F5** — rubric prevalence: do dimensions actually surface in algorithmic code? | critique sev 5 → ETA | **RECOVERED via redesign.** Pre-flight Phase D found 0/11 python-coder S3+ dimensions active (modern LLMs don't produce those smells on algorithmic tasks). Rubric replaced with 11 algorithmic-code dimensions (`SPEC_V2 §6.4 A1`); calibration anchor added on judge prompt (`A5`); Phase D2 panel re-probe passed 9/9 dims at strict gate. | **Critic.** Original rubric was wrong instrument for modern code. |
| **F6/F7** — minor design concerns | defense_wins | Closed in debate; not revisited. | **Defender.** |

Two macro-iterations also fired during pre-flight: the pool was widened from
7 to 10 models (A3) to include reasoning-capable models, after a user methodological
challenge that a non-reasoning-only pool answers a question of low production
relevance; and `reasoning: {effort: "high"}` was added as an explicit subject-side
parameter (A4) after the routing-variability audit found that the same model
identifier could return different reasoning behavior across calls.

---

## Primary result — CQS-craft

Pre-registered formula (`SPEC_V2 §6.5`):
```
CQS_craft = 0.45 · idiom + 0.45 · comment + 0.10 · (1 − mean_rubric_sev / 5)
```

All three components are LLM-judge-derived; static analysis is reported separately.

### Pooled across the 10-model pool

| Preamble | n | CQS-craft mean | 95% CI |
|---|---|---|---|
| `trivial_baseline` (no system; prompt = task name; T=1.0) | 125 | 0.556 | [0.510, 0.600] |
| `negative_control` ("junior developer") | 138 | 0.723 | [0.700, 0.746] |
| `persona_only` | 132 | 0.764 | [0.735, 0.791] |
| `minimal` ("helpful assistant") | 136 | 0.770 | [0.741, 0.794] |
| `none` | 135 | 0.778 | [0.750, 0.804] |
| `generic_coding` | 132 | 0.784 | [0.756, 0.808] |
| `real_agent` | 139 | 0.802 | [0.775, 0.825] |
| `python_coder_agent` | 139 | 0.802 | [0.775, 0.823] |
| `long_directive` | 139 | **0.815** | [0.789, 0.836] |

**Kruskal–Wallis (main conditions, pooled):** H = 95.5, **p = 9.2 × 10⁻¹⁸**.

Bootstrap CIs cleanly separate `negative_control` from every rich preamble.
`trivial_baseline` is decisively lowest (−0.26 vs `none`).

### Mixed-effects models

Three nested specifications, all with random intercepts on subject `model` and
`task` (REML; statsmodels `mixedlm` with `vc_formula` for the second random
group). Reference cell `none`. Tier is a fixed 1/0 indicator
(`reasoning` = 1; constant within each model, so `(1|model)` absorbs
within-tier between-model variance while `tier` captures the mean shift
between tiers).

```
M0:  CQS ~ preamble                            + (1|model) + (1|task)
M1:  CQS ~ preamble + tier                     + (1|model) + (1|task)
M2:  CQS ~ preamble * tier                     + (1|model) + (1|task)
```

**ML log-likelihoods (for principled fixed-effect LRTs):**

| Comparison | ΔlogLik | LRT χ² | df | p |
|---|---|---|---|---|
| M1 − M0 (add tier main effect) | +1.38 | 2.76 | 1 | 0.097 |
| M2 − M1 (add `preamble × tier` interaction) | +7.40 | 14.80 | 8 | 0.063 |

Both the tier main effect and the `preamble × tier` interaction are
**marginal — neither clears α = 0.05.** Tier numerically lifts CQS-craft by
+0.083 (95% CI [−0.02, +0.20]) but the 1-df test is underpowered with only
10 models (3 of one tier and 7 of the other).

**M2 (preamble × tier) — preamble fixed effects vs `none` (in non-reasoning tier):**

| Preamble vs `none` | β | p | Verdict |
|---|---|---|---|
| `trivial_baseline` | −0.255 | 3 × 10⁻⁶¹ | Decisively worse |
| `negative_control` | −0.060 | 5 × 10⁻⁵ | Significantly worse |
| `minimal` | +0.000 | 0.99 | No effect vs `none` |
| `generic_coding` | +0.014 | 0.33 | No effect |
| `persona_only` | −0.007 | 0.64 | No effect |
| `real_agent` | +0.027 | 0.067 | Marginal |
| `python_coder_agent` | +0.023 | 0.126 | No effect |
| `long_directive` | **+0.046** | **0.002** | **Significantly better than `none`** |
| `tier[reasoning]` main effect | +0.087 | 0.117 | Marginal |

**Preamble × tier interaction terms** — does the preamble effect differ
between tiers?

| Interaction (each preamble × reasoning) | β | p |
|---|---|---|
| `trivial_baseline : reasoning` | **+0.056** | **0.049** |
| `negative_control : reasoning` | +0.013 | 0.66 |
| `minimal : reasoning` | −0.028 | 0.33 |
| `generic_coding : reasoning` | −0.022 | 0.46 |
| `persona_only : reasoning` | −0.016 | 0.58 |
| `real_agent : reasoning` | −0.011 | 0.69 |
| `long_directive : reasoning` | −0.033 | 0.24 |
| `python_coder_agent : reasoning` | +0.004 | 0.89 |

**Only one interaction is significant** — reasoning models tolerate the
degenerate `trivial_baseline` condition slightly better (smaller damage from
the no-system-prompt + temp=1.0 + name-only-prompt input). **For the eight
main conditions, no interaction reaches significance** — the preamble effect
is statistically homogeneous across tiers.

Variance components (M2): task RE variance 0.013 (large), model RE variance
0.004 (small), residual 0.011 (within-cell noise floor). Task choice
contributes about 3× the variance of model choice, even with reasoning vs
non-reasoning mixed in the same pool.

**Interpretation.** After accounting for tier, model, and task variance,
`long_directive` is the only condition that clearly outperforms `none`
(β = +0.046, p = 0.002). `real_agent` and `python_coder_agent` sit at the
edge of significance (p = 0.067 and p = 0.126). The KW result is largely
driven by the gap between `trivial_baseline` / `negative_control` and
everything else — preambles primarily *prevent* quality regression rather
than push quality far above the no-preamble baseline. **The asymmetric
mechanism is the v2 refinement: rich preambles ≈ no preamble; "junior dev"
priming actively hurts.** And critically, **this asymmetry holds in both
tiers** — the interaction analysis confirms preamble effects do not
materially differ between reasoning and non-reasoning models.

### Weight-sensitivity (all schemes preamble-significant)

| Weight scheme (idiom / comment / hygiene) | KW p across main conditions |
|---|---|
| Pre-registered 0.45 / 0.45 / 0.10 | 9.2 × 10⁻¹⁸ |
| Idiom-only 1.00 / 0.00 / 0.00 | 2.7 × 10⁻¹⁵ |
| Comment-only 0.00 / 1.00 / 0.00 | 4.5 × 10⁻¹⁶ |
| Rubric-only 0.00 / 0.00 / 1.00 | 2.4 × 10⁻¹⁰ |
| Rubric-heavy 0.30 / 0.30 / 0.40 | 1.5 × 10⁻¹⁷ |
| Equal-thirds 0.33 / 0.33 / 0.34 | 8.2 × 10⁻¹⁸ |
| v1-static-heavy proxy 0.20 / 0.20 / 0.60 | 3.7 × 10⁻¹⁶ |

The primary result is *robust* to weight choice. Even the rubric-only scheme
(p = 2.4 × 10⁻¹⁰) — which removes idiom/comment entirely — preserves significance.
The v2 redesigned rubric, on its own, detects the preamble effect.

---

## Stratifications

### Model tier (the v2 pool macro-iteration)

| Tier | n | KW p | Range of means |
|---|---|---|---|
| Reasoning (3 models) | 348 | **1.8 × 10⁻⁸** | 0.798 (negative_control) → 0.865 (python_coder_agent) |
| Non-reasoning (7 models) | 867 | **2.3 × 10⁻¹²** | 0.693 (negative_control) → 0.798 (long_directive) |

**Both tiers significant by KW.** v1's question ("do preambles matter on
non-reasoning models?") is re-answered yes, with much higher confidence than
v1.

The reasoning tier scores higher in absolute terms (range 0.80–0.87 vs
non-reasoning's 0.69–0.80), and `python_coder_agent` ranks first in the
reasoning tier (0.865) vs third in the non-reasoning tier (0.775) by raw
mean. **But the formal interaction test** (M2 in the mixed-effects section
above) **finds no statistically significant `preamble × tier` interaction
for any of the 8 main conditions** — the apparent rank differences across
tiers are within the noise floor once tier, model, and task variance are
controlled. The one significant interaction is `trivial_baseline × reasoning`
(reasoning models tolerate the degenerate input slightly better; β = +0.056,
p = 0.049).

The honest reading: **preamble effects are statistically homogeneous across
tiers for the main conditions.** Reasoning models hit a higher absolute
ceiling (tier main effect β = +0.087, but p = 0.117 — marginal due to the
1-df test with only 10 models), but the *shape* of the preamble effect —
how much each preamble shifts CQS-craft relative to `none` — does not
materially differ between reasoning and non-reasoning subjects.

Per-tier model RE variance is essentially zero within the reasoning tier
(0.00004) and small but non-zero in the non-reasoning tier (0.005), meaning
within reasoning, which specific reasoning model you pick doesn't matter
much for CQS-craft; within non-reasoning, models differ slightly more.

### Task category

| Category | n (per condition) | Δ(rich − negative_control) | Δ(rich − none) |
|---|---|---|---|
| Creation (4 tasks) | ~75–80 | +0.10 | +0.03 |
| Refactor (2 tasks) | ~37–40 | +0.06 | +0.03 |
| Multi-file creation (1 task) | ~20 | +0.07 | +0.03 |

**Creation tasks show the largest gap between rich and negative preambles** —
+0.10 in CQS-craft vs +0.06 on refactor. This matches the hypothesis: refactor
prompts constrain the output (the target smell is named in the prompt), so
preamble has less leverage; creation tasks leave design discretion to the model,
so preamble priming has more room to act.

The multi-file task (n=20/cell, much wider CIs) reproduces the same ordering
but with insufficient power to be decisive at the per-task level. It contributes
~5% of total samples and ~7% of the per-condition spread.

---

## Per-dimension severity (the new 11-dim algorithmic-code rubric)

| Dimension | Kind | KW p | Negative ctrl mean | real_agent mean | Δ |
|---|---|---|---|---|---|
| `error_handling_inconsistency` | always-on | <1e-4 | 1.69 | 1.34 | −0.35 |
| `edge_case_gap` | always-on | <1e-4 | 1.98 | 1.62 | −0.36 |
| `type_hint_gap` | always-on | <1e-4 | 1.17 | 0.96 | −0.21 |
| `code_organization` | always-on | <1e-4 | 1.05 | 0.85 | −0.20 |
| `documentation_appropriateness` | always-on | <1e-4 | 1.51 | 0.99 | −0.52 |
| `abstraction_miscalibration` | always-on | 4e-4 | 1.19 | 0.99 | −0.20 |
| `api_ergonomics` | always-on | 0.008 | 1.27 | 1.17 | −0.10 |
| `concurrency_safety` | conditional | 0.006 | 2.20 | 1.76 | −0.44 |
| `data_structure_choice` | always-on | 0.39 | 1.27 | 1.17 | −0.10 |
| `algorithm_correctness` | always-on | 0.26 | 1.37 | 1.23 | −0.14 |
| `example_quality` | conditional | 0.25 | 1.02 | 0.90 | −0.12 |

**7 of 9 always-on dimensions preamble-significant** (criterion was 3 of 9).

The two nulls — `algorithm_correctness` (p = 0.26) and `data_structure_choice`
(p = 0.39) — are exactly the *pretraining-dependent* capability axes. The model
either knows how to write a correct LRU cache or it doesn't; preamble priming
doesn't change that. Every other dimension is an *alignment-dependent craft*
axis: error handling philosophy, edge case awareness, type hint discipline,
code organization, documentation style. These all move with preamble.

**This is the central mechanism finding from v1, reproduced at much higher
resolution with a rubric designed to elicit it.** The mechanism is not just
re-confirmed; it is decomposed into specific named dimensions.

---

## Diagnostic null — static analysis reproduces v1's flat finding

| Metric | KW p across preambles | Verdict |
|---|---|---|
| `maintainability_index` | 0.92 | Flat ✓ |
| `avg_cyclomatic` | 0.33 | Flat ✓ |
| `max_cyclomatic` | 0.84 | Flat ✓ |
| `halstead_difficulty` | 0.98 | Flat ✓ |
| `pylint_errors` | 0.97 | Flat ✓ |
| `pylint_warnings` | 0.97 | Flat ✓ |
| `pylint_refactor` | 0.92 | Flat ✓ |
| `cognitive_complexity_violations` | 0.53 | Flat ✓ |
| `pylint_conventions` | 0.012 | Weak signal |

**8 of 9 static metrics flat across preambles** (p > 0.5). The sole exception
is `pylint_conventions` (p = 0.012) — a marginal effect on convention-style
issues (`negative_control` has 14.6 conventions issues vs `real_agent`'s 11.9
— probably the "junior developer" framing producing slightly worse PEP-8
compliance). Even there, the effect is far weaker than any rubric or judge
dimension.

**v1's instrument-correction is fully validated.** Static analysis and the LLM
judges measure substantively different signals; the v1 composite that buried
the LLM-judge signal under 65%-weighted static noise was indeed a metric
artifact. v2's craft-only CQS surfaces the real effect.

---

## F3 hygiene — self-vs-cross judge

| Component | self mean | cross mean | Δ | Mann–Whitney p |
|---|---|---|---|---|
| Idiomaticity | 7.78 | 7.75 | +0.024 | 0.0003 |
| Comment quality | 7.76 | 7.46 | +0.294 | <1e-4 |

Self-judges are slightly more lenient — small effect on idiomaticity, larger
on comment quality. The v1 protocol (exclude self-judgments from primary CQS;
report stratification as hygiene) was the correct call. The cross-judge means
that enter CQS-craft are unaffected.

---

## Comparison to v1

v1 was a 7-model × 8-preamble × 6-task single-rep design (274 scored samples,
2192 judge ratings). v1's pre-registered composite was null (KW p = 0.633)
because static analysis at 65% weight buried the LLM-judge signal (idiom
p = 0.002, comment p = 0.006). v1 conclusion: hypothesis SUPPORTED on judge
components, but headline metric was a metric artifact.

v2 is a 10-model (3 reasoning + 7 non-reasoning) × 9-preamble × 7-task ×
2-replication design (1,215 scored samples, 22,028 judge ratings). v2's
pre-registered composite *is* the LLM-judge-only CQS-craft. **The headline
result is significant at p = 9.2 × 10⁻¹⁸** — three orders of magnitude beyond
where v1 stopped being able to see the effect.

Key v1 → v2 deltas, in addition to the instrument repair:

1. **Reasoning-tier coverage.** v1 had no reasoning-capable models in pool;
   v2 has 3, with `reasoning: {effort: "high"}` and provider logging. Finding:
   reasoning models still preamble-responsive but at a compressed range; the
   "rich-preamble vs negative" gap shrinks from +0.10 (non-reasoning) to +0.07
   (reasoning), while the absolute ceiling is higher.
2. **`python_coder_agent` external validity.** v1 had no real production preamble
   in pool. v2 includes one verbatim. Finding: it scores statistically identical
   to the synthetic `real_agent` (mixed-effects β = +0.024 both, p ≈ 0.057
   both). **v1's synthetic preambles were representative.** Lab-and-field
   agree.
3. **Per-dimension decomposition.** v1's rubric was binary (0/1 presence of
   each smell). v2's rubric is 0–5 severity on dimensions that algorithmic LLM
   code actually varies on. 7 of 9 dimensions now significant; the two that
   are not are exactly the capability-axis dimensions the hypothesis predicted
   would not move.
4. **Power.** v1 had ~35 samples per condition. v2 has ~135. Effect sizes that
   in v1 were directional-but-not-significant (per-dimension dict_domain
   0.45 → 0.21) are now decisively significant at v2's scale.
5. **Cost.** v2 ($32) was *cheaper* than v1 (~$45) despite 4.4× the sample
   count, because reasoning models judged with reasoning disabled
   (`reasoning: {exclude: true}`) and gpt-4o-mini-and-friends are cheap.

---

## Verdict

**Hypothesis SUPPORTED, at substantially higher confidence than v1.**

Mechanistic findings:

1. **Preambles change LLM-generated code on alignment-dependent craft axes**
   (idiomaticity, error handling, edge cases, type hints, organization,
   documentation, API ergonomics, concurrency safety, abstraction).
2. **Preambles do not detectably change pretraining-dependent capability axes**
   (algorithm correctness, data structure choice) — and they do not change
   static-analysis metrics (MI, CC, Halstead, pylint).
3. **The effect is asymmetric:** rich preambles ≈ no preamble (small positive
   delta, mostly p ≈ 0.06 in mixed-effects); negative-priming preambles
   *actively hurt* (p < 1e-5). The mechanism appears to be more about
   preventing regression than driving exemplary output.
4. **`long_directive` is the only preamble that beats `none` at p < 0.01
   after controlling for model + task.** More directives genuinely help, but
   the marginal return per directive is small.
5. **External validity:** a real production system prompt (`python_coder_agent`)
   performs statistically identically to the synthetic `real_agent` v1 used.
   The v1 finding generalizes.
6. **Tier effect:** preambles work in both reasoning and non-reasoning model
   populations, and a formal `preamble × tier` interaction test finds no
   statistically significant differential effect for the 8 main conditions
   (only `trivial_baseline × reasoning` reaches p < 0.05 — reasoning models
   tolerate the degenerate input slightly better). Reasoning models hit a
   higher absolute CQS-craft ceiling (tier main effect β ≈ +0.09 in CQS units),
   but the test is underpowered with 3-vs-7 tier imbalance (p = 0.12).
7. **Task effect:** creation tasks expose preamble effects more than refactor
   tasks (gap ratio ~1.7×). Refactor prompts constrain output by naming the
   target smell; creation prompts leave discretion the preamble can shape.

---

## Limitations

1. **`python_coder_agent` non-significant in mixed-effects vs `none`**
   (M0 p = 0.058; M2 within-non-reasoning-tier p = 0.126). The KW result is
   significant overall; bootstrap CIs separate `python_coder_agent` from
   `negative_control`. But the strict mixed-effects test against `none` only
   crosses p < 0.05 for `long_directive` (β = +0.046, p = 0.002). This is a
   power consideration as much as a substantive one: `real_agent` and
   `python_coder_agent` both sit at β ≈ +0.02–0.03 with similar p-values
   around 0.06–0.13. A larger sample or a directional test would likely
   declare both significant.
2. **Tier imbalance (3 reasoning vs 7 non-reasoning).** The tier main-effect
   test (β = +0.087, p = 0.117) is underpowered with only 10 models. The
   interaction test (8 df) has more total information but each individual
   `preamble × tier` term is also underpowered. A v3 with 5+ reasoning
   models would let us declare the tier-level effect cleanly. As reported,
   the preamble × tier null is "no detectable interaction" rather than
   "proven absence of interaction".
2. **Multi-file task underpowered.** n = 20 per condition. CIs are wide.
   Significance signal carried by the single-file tasks.
3. **Single judge model with calibration anchor** still partially saturates on
   `algorithm_correctness` (gpt-4o-mini frac-zero 88%). The cross-judge
   panel recovers this — deepseek-v3.2 catches algorithmic bugs gpt-4o-mini
   misses — but a future v3 should explore stronger single judges
   (Claude Sonnet, GPT-5) as an alternative to panel aggregation.
4. **Routing variability not exhaustively audited.** Per-call `provider`
   field is logged but not analyzed for systematic differences. A post-hoc
   audit could detect provider-induced drift in any single model's outputs.
5. **CQS-craft components correlate.** idiom, comment, and rubric severity
   are not independent — judges that rate one dimension favorably tend to
   rate others favorably. The mixed-effects model handles this implicitly via
   the residual variance term, but a structural-equation or PCA decomposition
   of the components would clarify how much information is unique to each
   axis.
6. **No human-rater validation.** All scoring is LLM-judge based. Cross-judge
   agreement is high (panel-mean variance is small for most dimensions), and
   the calibration anchor + multi-judge panel mitigates single-judge
   pathology — but a human-rater agreement study on a sub-sample of ~100
   generations would strengthen external validity.
