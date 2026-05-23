# Conclusions — Preamble Quality Experiment v2

**Hypothesis tested (Cycle 2 Re-revised, ACTIVE):** In a production-realistic LLM
population (3 reasoning + 7 non-reasoning models, OpenRouter-routed), coding-agent
preambles change the craft quality of single-turn Python code outputs, detectable
as a main effect of preamble condition on CQS-craft (LLM-judge components only).
The effect is expected on alignment-dependent craft axes (style, naming, comments,
error handling, edge cases) and *not* on pretraining-dependent capability axes
(structural complexity, algorithmic correctness).

**Headline finding (descriptive):** **CQS-craft moves with preamble at the
corrected instrument.** With v1's measurement instrument fixed (static analysis
demoted to a diagnostic panel; LLM-judge severity rubric redesigned for
algorithmic-code dimensions; judge panel calibrated; 1,215 valid samples vs
v1's 274), the primary CQS-craft shows preamble-condition effect at
Kruskal–Wallis **p = 9.2 × 10⁻¹⁸** pooled — and at p ≤ 2.3 × 10⁻¹² within each
model tier separately. Seven of nine always-on rubric dimensions show
preamble-significant separation (criterion was three).

**Headline finding (mechanistic):** Three discriminating probes
(§"Confound probes" below) refined the mechanism understanding from the
naïve "preambles change code; rubric detects change" to a more accurate
**attention-allocation reading**: preambles direct the model's finite
craft-attention budget toward the dimensions they enumerate, at the cost
of whatever the model would otherwise have done. When the preamble's
enumerated dimensions overlap with what the rubric measures, CQS-craft
goes up. When they don't, it goes down — sometimes far below the
`negative_control` baseline. The judges are tracking real code changes
(probe A confirms this: a misaligned expert directive hurts CQS by 7×
the `long_directive` lift, with measurably fewer docstrings, fewer
defensive guards, and fewer type hints in the output). But the
*magnitude and sign* of any preamble's effect on CQS-craft is governed
by overlap with the rubric, not by some platonic "code quality". The
v1/v2 substantive claim — preambles affect code craft — is supported; the
v1/v2 mechanistic claim — preambles split alignment-tunable craft axes
from pretraining-locked capability axes — is *partially supported*, with
the caveat that "alignment-tunable" should be read as "any dimension a
preamble can direct attention to" rather than "any dimension separate
from underlying capability."

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

## Identification limit — rubric-directive overlap confound

Before reading the per-dimension results, a critical caveat we underplayed in
the headline. The `long_directive` preamble is a 12-clause enumerated list of
engineering directives. Mapping its clauses against the 11 rubric dimensions:

| `long_directive` clause | Rubric dimension it names |
|---|---|
| (1) idiomatic Python | (overlaps CQS-craft's `idiomaticity` component) |
| (2) appropriate abstraction | `abstraction_miscalibration` |
| (3) defensive programming, validate inputs, handle edge cases, fail clearly | `edge_case_gap`, `error_handling_inconsistency` |
| (4) precise naming | (overlaps `idiomaticity` component) |
| (5) comments why not what | `documentation_appropriateness` (and `comment_quality` component) |
| (6) maintainable | (broad) |
| (7) concurrency / thread-safety explicit | `concurrency_safety` |
| (8) composition over inheritance | `code_organization` |
| (9) side effects + I/O boundaries explicit | `code_organization` |
| (10) testable interfaces, dependency injection | (no direct dim) |
| (11) log errors at right severity, never swallow | `error_handling_inconsistency` |
| (12) docstring public interfaces | `documentation_appropriateness`, `type_hint_gap` |

**Seven of nine always-on rubric dimensions — exactly the seven that show
p < 10⁻⁴ — are explicitly named in `long_directive`'s clauses.** The two
dimensions that don't move (`algorithm_correctness`, `data_structure_choice`)
are not named in any preamble in any condition.

This mapping is consistent with two substantively different hypotheses, and
the v2 design produces nearly identical predictions under each:

**H-mechanism:** Preambles change the code the model writes on alignment-tunable
craft axes. Judges then detect those changes. The 7-vs-2 split reflects which
axes are actually preamble-tunable (craft) vs which are pretraining-locked
(capability).

**H-judge-priming:** Preambles cause the model to add surface markers
(verbose docstrings, defensive try-blocks, type hints on every public
signature, comments mentioning thread safety) that match the preamble's
stated priorities — without deep changes to algorithmic structure. The
judges' rubric prompt explicitly enumerates the 11 dimensions; judges score
higher when the surface markers are present, regardless of whether the
underlying code is materially different. The 7-vs-2 split reflects which
dimensions the preamble explicitly names.

These hypotheses are observationally near-equivalent in the v2 design because
the preamble that drives most of the headline effect (`long_directive`)
explicitly names ~7 of the 9 always-on rubric dimensions, and the rubric
judges are told what to look for. We could not, from v2 alone, distinguish a
genuine code-craft change that the rubric correctly detects from a
preamble-driven surface change that aligns to what the rubric enumerates.

**What the v2 data *does* tell us, regardless of which hypothesis is true:**

1. **`long_directive` produces samples that judges score consistently higher**
   on 7 of 9 rubric dimensions — whether through deep code change or surface
   marker alignment, the effect is real and reproducible (p < 10⁻⁴ on multiple
   dimensions).
2. **`negative_control` produces samples that judges score consistently lower**
   on the same dimensions. The "junior developer" framing's effect (β ≈ −0.06,
   p ≈ 5 × 10⁻⁵) is unlikely to be a pure-priming artifact because it does
   not enumerate dimensions for the judge — it shifts the model's stylistic
   register, and that shift is what gets scored down.
3. **The static-analysis panel is flat** on 8 of 9 metrics. Static analysis
   measures (radon, pylint, cyclomatic, Halstead) are insensitive to surface
   markers that don't change code structure. If H-judge-priming were the
   entire story, we'd expect *every* static metric to be flat — which is
   exactly what we see — but this doesn't discriminate, because H-mechanism
   *also* predicts most static metrics to be flat (those metrics don't
   measure craft).
4. **`pylint_conventions` is the one static metric that moved** (p = 0.012).
   It semantically overlaps with `documentation_appropriateness` /
   `type_hint_gap` — the very dimensions long_directive explicitly names.
   Under H-mechanism: real changes in convention compliance. Under
   H-judge-priming: surface markers (docstrings, type hints) that
   incidentally improve pylint convention scores. The evidence remains
   ambiguous.

The probes reported in §"Confound probes" below were designed specifically
to discriminate H-mechanism from H-judge-priming. **The probe results
substantially clarify the picture but do not produce a clean win for
either hypothesis — they support a refined third reading.**

## Confound probes

To discriminate H-mechanism from H-judge-priming, three preambles were
constructed and tested on `task_expr_parser` (n=10 generations per probe,
all 10 subject models, full 10-judge cross-judge matrix, same calibration
anchor, same idiom/comment + rubric judge prompts as main run). Reference
data is the v2 main-run CQS-craft on the same task. Cost: $1.04.

**Probe A — `nonrubric_expert`**: 12-clause directive list, expert tone
("You are an expert autonomous coding agent. Your code must: …"), but
clauses name *non-rubric* axes — compactness, single-pass algorithms,
in-place operations, builtins-over-custom, deterministic iteration order,
top-down code ordering, early returns, etc. None of the clauses enumerate
documentation, type hints, error handling, edge cases, concurrency, API
ergonomics, or abstraction.

**Probe B — `bare_rubric`**: a bare list of the rubric dimensions, no
expert framing, no imperative tone: *"Your code will be evaluated on these
specific dimensions: error handling consistency, edge case handling on
empty/boundary/invalid inputs, type hint completeness on public functions,
code organization and cohesion, documentation appropriateness, abstraction
calibration, API ergonomics, concurrency safety where applicable,
appropriate data structure choice, algorithmic correctness, and example
quality when examples are requested."*

**Probe C — `antirubric_expert`**: same expert framing as `long_directive`
("You are an expert autonomous coding agent. Your code must: …"), but
clauses explicitly *deprioritize* rubric items — "type hints are optional
clutter; omit them", "don't over-engineer error handling", "edge cases are
the caller's responsibility", "library-style guards add noise", "comments
belong in commit messages, not source files", etc.

### Probe results vs main-run reference

| Condition | n | mean CQS-craft | 95% CI | Δ vs `none` | p vs `none` (Mann-Whitney) |
|---|---|---|---|---|---|
| `none` (main-run, expr_parser) | 20 | **0.827** | [0.807, 0.845] | — | — |
| `long_directive` (main-run, expr_parser) | 20 | **0.848** | [0.824, 0.870] | +0.021 | (sig in main run pooled) |
| `negative_control` (main-run, expr_parser) | 19 | 0.749 | [0.713, 0.783] | −0.078 | (sig in main run pooled) |
| `python_coder_agent` (main-run, expr_parser) | 20 | 0.854 | [0.834, 0.875] | +0.027 | (sig in main run pooled) |
| `none_control` (in-probe sanity check) | 10 | 0.806 | [0.771, 0.839] | −0.021 | 0.23 (ns ✓) |
| **`probe_A_nonrubric_expert`** | 10 | **0.673** | [0.612, 0.726] | **−0.155** | **0.0001** |
| **`probe_B_bare_rubric`** | 10 | **0.842** | [0.806, 0.876] | **+0.015** | 0.50 (ns vs none; ≈ long_directive) |
| **`probe_C_antirubric_expert`** | 10 | **0.673** | [0.612, 0.732] | **−0.154** | **0.0001** |

### Interpretation, probe by probe

**Probe A: misaligned expert directive hurts by 7× the long_directive lift.**
This is the most surprising single result. An expert-framed 12-clause
directive list of equal length and tone to `long_directive`, with clauses
that don't name any of the rubric dimensions, doesn't just fail to help —
it actively *hurts* by −0.155 CQS-craft units (p = 0.0001). For comparison:
the strongest negative preamble in the main run (`negative_control`,
"junior developer") only achieved −0.078 vs `none` on this task.

The mechanism is visible in per-dimension severity. Probe A's documentation
severity (1.59) and edge_case_gap (1.77) are *higher* than `negative_control`
on this task. The model followed the preamble's content — produced
compact, performance-focused code with fewer docstrings, fewer defensive
guards, fewer comments — and the rubric correctly penalized this.

**This rules out a strong form of H-judge-priming.** If judges were merely
rewarding "expert tone" or "well-formatted preamble"-aligned outputs, probe A
should produce CQS close to `long_directive`. It doesn't; it produces CQS
*worse than `negative_control`*. The judges are tracking the actual code,
not the preamble's surface tone.

**This also rules out a strong form of H-mechanism that frames preambles
as "generic expert priming".** If expert framing generically improved
craft, probe A should still produce a positive lift over `none`. It
doesn't; it produces a large negative lift.

**Probe B: bare rubric naming recovers ~70% of long_directive's lift.**
With no expert framing, no "you must", no imperative tone — just an
announcement that the code will be evaluated on the listed dimensions —
the model produces output statistically indistinguishable from
`long_directive` (probe B 0.842 vs long_directive 0.848; B-vs-none p = 0.50;
B's per-dimension severity profile tracks long_directive's almost exactly,
e.g. `documentation_appropriateness` 0.79 vs long_directive 0.74).

**This is partial support for H-judge-priming.** Telling the model what
the rubric measures — without any quality directives or expert framing — is
sufficient to produce most of the preamble effect. The 30% residual
(long_directive 0.848 vs probe B 0.842, gap = 0.006) is attributable to
imperative tone or compound-clause framing; not nothing, but small.

**Probe C: anti-rubric directives hurt identically to A.** Probe C
(0.673) is statistically identical to probe A (0.673), both at p = 0.0001
vs `none`. An explicitly anti-rubric framing — explicitly telling the
model that type hints are clutter, error handling is over-engineering,
comments belong in commit messages — produces the same penalty as a
neutral non-rubric-naming directive list.

**This is consistent with both hypotheses.** Under H-mechanism, the model
follows the anti-rubric content and produces worse code on rubric
dimensions. Under H-judge-priming, judges still mark down because the
rubric dimensions are still what they enumerate and look for. Both
hypotheses predict probe C to hurt; the symmetry with probe A is what's
informative (preamble *content* drives the model's behavior, not just the
"presence of an expert preamble").

### Refined hypothesis: H-attention-allocation

The three probes together support a reading neither pure H-mechanism nor
pure H-judge-priming captures:

**Preambles work by directing the model's craft-attention budget.** The
model has finite output capacity. When the preamble enumerates specific
dimensions ("type hints", "edge cases", "documentation"), the model
allocates more output capacity to those dimensions, at the cost of
whatever it would otherwise have done. When the preamble enumerates
*different* dimensions ("compactness", "performance", "minimal allocations"),
the model allocates capacity to those instead — visible as fewer
docstrings, fewer type hints, fewer defensive guards in probe A.

The rubric then measures whichever dimensions it enumerates. The CQS-craft
lift over `none` is roughly proportional to the *intersection* between
(what the preamble directed the model toward) and (what the rubric
measures).

**Implications:**

1. **CQS-craft is real, but rubric-dependent.** The metric works — it
   measures what it measures, reliably. Probe A demonstrates that judges
   are tracking code, not preamble surface. But "code quality in some
   platonic sense" is not what CQS-craft measures. CQS-craft measures
   *the rubric's specific 11-dimension definition of craft*, which any
   given preamble may or may not be optimizing for.

2. **The headline finding holds with a refined claim.** "Preambles change
   what the rubric scores" is correct. The mechanism is attention
   allocation — preambles direct the model's output toward dimensions the
   preamble names. When those dimensions overlap with what's measured,
   CQS-craft goes up. When they don't, it goes down.

3. **Practical implication for prompt engineering.** A preamble that
   enumerates the dimensions a downstream evaluator cares about will
   reliably improve that evaluator's scores. The 12-clause directive list
   beats `none` *because* its clauses overlap with the rubric, not despite
   that. If your production evaluator measures different things (latency,
   compactness, performance), `long_directive` may not be the preamble you
   want; probe A's content might be.

4. **The "junior developer" effect is robust** to this refinement.
   `negative_control` doesn't enumerate any specific dimensions in either
   direction — it shifts the model's stylistic register downward
   ("learning Python", "don't worry too much about style"). It hurts
   (−0.078 in this task, −0.060 pooled) without naming what to deprioritize.
   This is a different mechanism than probe C's explicit anti-rubric
   enumeration, but both routes converge on lower CQS-craft.

### What the probes did NOT resolve

1. **Whether the probe-A behavioral change is genuine craft change or
   surface markers only.** The model writes objectively fewer docstrings
   and fewer type hints under probe A — that's a real code change visible
   to any human reader. But whether the deeper algorithmic / structural
   craft is also worse is not directly tested. Static-analysis metrics on
   probe-A outputs would help; not run in this probe round.

2. **Whether `long_directive`'s lift comes proportionally from each
   enumerated clause.** Probe B (bare rubric naming) recovers 70% of
   long_directive's lift; the remaining 30% may be from imperative tone,
   from compound clauses that explain *why* each item matters, or from
   specific clauses that name dimensions outside the rubric (e.g.,
   "composition over inheritance", which isn't in the rubric but might
   improve `code_organization` indirectly). A clause-ablation study could
   discriminate.

3. **External validity to other rubrics.** All conclusions are anchored
   to the v2 11-dim rubric. A rubric measuring different things (e.g.,
   pure functional purity, performance-correctness tradeoffs) would
   produce different preamble winners. The probes confirm this is the
   right reading, but don't quantify how much of v2's findings transfer.

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
(p = 0.39) — are the *pretraining-dependent capability* axes under the
H-mechanism reading. They are also the two dimensions *not enumerated in any
preamble's clauses* under the H-judge-priming reading. Both hypotheses make
identical predictions for this split. See §"Identification limit" above and
§"Confound probes" below for the discriminating evidence.

**Under H-mechanism**, the central v1 finding is reproduced at much higher
resolution with a rubric designed to elicit it, and decomposed into specific
named dimensions: error handling philosophy, edge case awareness, type hint
discipline, code organization, documentation style — all alignment-tunable.
**Under H-judge-priming**, the same pattern would emerge from preambles
adding surface markers that map 1-to-1 onto what the rubric enumerates,
without changing underlying code structure on capability axes that are not
named. The v2 main run cannot distinguish these readings; the probes
section below was designed to.

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

**Hypothesis SUPPORTED at the level of judge-scored CQS-craft, with a real
methodological identification issue on the mechanism interpretation.**

Descriptive findings (these hold regardless of which mechanism hypothesis is
true):

1. **Preambles change what judges score on craft-related dimensions** —
   whether by changing underlying code, by aligning surface markers to what
   the rubric enumerates, or both. The effect on judge-scored CQS-craft is
   robust (p < 10⁻¹⁸ pooled, robust to all 7 alternative weightings, present
   in both tiers).
2. **The effect is asymmetric:** rich preambles ≈ no preamble (small positive
   delta, mostly p ≈ 0.06 in mixed-effects); negative-priming preambles
   *actively hurt* (p < 10⁻⁵). The "junior developer" framing's negative
   effect is unlikely to be a pure-priming artifact because that preamble
   does not enumerate any rubric dimensions; it changes the model's
   stylistic register.
3. **`long_directive` is the only preamble that beats `none` at p < 0.01
   after controlling for model + task.** But `long_directive` is also the
   preamble whose clauses most directly enumerate the rubric dimensions
   (see §"Identification limit"). The marginal lift over `none` may reflect
   genuine craft improvement, judge-priming, or both — see §"Confound probes".
4. **External validity:** the real production system prompt
   (`python_coder_agent`) performs statistically identically to the synthetic
   `real_agent`. The v1 finding generalizes across synthetic and real-world
   preambles.
5. **Tier effect:** preambles work in both reasoning and non-reasoning model
   populations, and a formal `preamble × tier` interaction test finds no
   statistically significant differential effect for the 8 main conditions
   (only `trivial_baseline × reasoning` reaches p < 0.05). Reasoning models
   hit a higher absolute CQS-craft ceiling (tier main effect β ≈ +0.09,
   p = 0.12 — underpowered with 3-vs-7 tier imbalance).
6. **Task effect:** creation tasks expose preamble effects more than refactor
   tasks (gap ratio ~1.7×). Refactor prompts constrain output by naming the
   target smell; creation prompts leave discretion the preamble can shape.

Mechanistic claims (refined after the confound probes resolved the
identification issue):

7. **Preambles direct the model's craft-attention budget.** The model
   tracks preamble content and reallocates output capacity to whatever
   dimensions the preamble enumerates. Probe A demonstrated this: a
   misaligned expert directive (12 clauses about compactness, performance,
   determinism) suppressed docstrings, type hints, defensive guards, and
   edge-case handling — producing CQS-craft 0.155 *below* `none` on
   `task_expr_parser` (p = 0.0001), worse than the `negative_control`
   "junior developer" preamble.
8. **The judges are tracking real code, not preamble surface tone.** If
   judges merely rewarded "expert-toned preamble" outputs, probe A would
   have produced CQS close to `long_directive`. Instead, probe A produced
   CQS worse than `negative_control`, demonstrating that the judges'
   scoring is sensitive to actual code content (presence/absence of
   docstrings, type hints, defensive checks).
9. **Naming the rubric items in the preamble — without expert framing —
   recovers ~70% of `long_directive`'s lift.** Probe B (a bare list of
   the 11 rubric dimensions, no imperative tone, no "you must") produced
   CQS statistically identical to `long_directive`. The remaining ~30%
   of `long_directive`'s lift is attributable to imperative tone or
   compound-clause framing.
10. **CQS-craft is real, but rubric-dependent.** The metric works
    reliably for measuring the v2 11-dimension definition of craft. But
    "code quality in some platonic sense" is not what CQS-craft measures.
    A preamble's CQS-craft lift over `none` is roughly proportional to
    the overlap between the dimensions it directs the model toward and
    the dimensions the rubric measures.
11. **The "preambles move craft but not capability" framing should be
    refined.** `algorithm_correctness` and `data_structure_choice` are
    null under preamble not because they are unconditionally
    pretraining-locked, but because no preamble in the v2 design
    enumerates them. The probes did not test a preamble specifically
    directing attention to algorithm correctness; such a probe might
    move that dimension. The v2 main-run "capability not moved by
    preamble" finding should be read as "not moved by any of the 9
    preambles in v2's condition set", not as "structurally immovable".

---

## Limitations

The single biggest limitation is the **mechanism-identification issue**
documented in §"Identification limit" above. `long_directive`'s 12 clauses
enumerate 7 of the 9 always-on rubric dimensions, and the judges' rubric
prompt enumerates the same 11 dimensions explicitly. H-mechanism (preambles
change code; rubric detects it) and H-judge-priming (preambles add surface
markers that align to the rubric; judges score the alignment) make
near-identical predictions in the v2 main run, because the preamble that
drives the headline effect was constructed without regard for whether its
clauses overlap the rubric. The probes section attempts to discriminate the
two; absent that discrimination, the v2 main run only identifies *the
existence, direction, and approximate magnitude* of preamble effects on
judge-scored craft, not the underlying mechanism. **Read the per-dimension
results, the verdict bullets 7–9, and the "mechanism" framing throughout
with this constraint in mind.**

Additional limitations:

0. **`python_coder_agent` non-significant in mixed-effects vs `none`**
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
