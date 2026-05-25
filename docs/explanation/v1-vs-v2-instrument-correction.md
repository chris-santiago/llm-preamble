# v1 vs v2 — the instrument-correction story

> v1 ran the right experiment with the wrong instrument and produced a
> false null at p = 0.633. v2 redesigned the instrument and produced
> p = 9.24 × 10⁻¹⁸ on the same underlying question. This page documents
> how a static-heavy composite mechanically manufactures a false null
> when the real effect lives on alignment-tunable dimensions.

## The two headlines side by side

| Quantity | v1 | v2 |
|---|---|---|
| Primary headline | KW p = 0.633 (null) | KW p = 9.24 × 10⁻¹⁸ |
| Composite formula | static-heavy (~65% static + AST) | LLM-judge-only craft composite |
| Sub-component idiom p | 0.0022 | (preserved, refined) |
| Sub-component comment p | 0.0058 | (preserved, refined) |
| Sub-component static p | 0.998 | 0.92 (`maintainability_index`) — flat |
| Sample count | 274 scored samples | 1,215 scored samples |
| Rubric form | Binary (0/1 smell presence) | 0–5 severity, 11 algorithmic-code dimensions |
| Judge panel | 8-model cross-judge | 10-model cross-judge, calibrated |
| Conclusion | Hypothesis SUPPORTED on judge components, but headline metric was a metric artifact | Hypothesis SUPPORTED on a corrected instrument, with mechanism refined post-hoc |

The same hypothesis — *preambles change code craft* — produced a null
and a 17-orders-of-magnitude-significant result depending only on the
choice of measurement instrument.

## How v1's composite produced a false null

v1's pre-registered Composite Quality Score weighted four components:

```
v1 CQS = 0.45 · static_score
       + 0.20 · ast_score
       + 0.20 · llm_idiom_score
       + 0.15 · llm_comment_score
```

Two facts about the components, measured directly in v1:

1. **The static and AST components are flat across preambles.** v1's
   reanalysis reports static_score p = 0.998 and ast_score p = 0.907
   on the same data. The metrics produced no preamble-related signal.
2. **The LLM-judge components are not flat.** Idiomaticity moved at
   p = 0.0022; comment quality at p = 0.0058. The signal was strong
   on the dimensions preambles actually tune.

Combining the four with 65% weight on the flat components yielded a
composite that diluted the signal beyond detection. v1's
re-weighting sensitivity table makes the dilution mechanical:

| Weighting | static + AST weight | Composite KW p |
|---|---|---|
| pre-registered | 0.65 | 0.633 |
| balanced | 0.50 | 0.185 |
| LLM-heavy | 0.25 | 0.012 |
| LLM-only | 0.00 | 0.003 |

The composite crosses significance exactly as static weight drops
below half. This is not a re-analysis to find significance; it is the
diagnostic that pins the false null on the instrument rather than on
the world. The static-heavy composite did not fail to detect a real
effect because it lacked power. It failed because **the metric
weighted noise at 65% and signal at 35%, and then averaged them.**

See the [why-static-metrics-fail](why-static-metrics-fail.md) page for
the structural reason the static components are flat; the v1/v2
contrast is the *consequence* of that orthogonality.

## v2's instrument redesign

v2 made four changes that, taken together, repaired the instrument.

### 1. Dropped static-heavy weighting; restricted CQS to LLM judges

The v2 pre-registered primary metric is:

```
CQS-craft = 0.45 · idiom
          + 0.45 · comment
          + 0.10 · (1 − mean_rubric_severity / 5)
```

All three components are LLM-judge-derived. Static analysis is
reported in a separate diagnostic panel, not in the primary metric.
This is the single change that converts the v1 null into a v2
detection — the rest of the redesign tightens the result but is not
strictly necessary for crossing significance.

### 2. Replaced the binary smell rubric with 0–5 severity on algorithmic-code dimensions

v1's rubric was a binary presence/absence list of canonical Python
smells (boolean mode flags on public functions, dict-domain data
crossing function boundaries, bare-except clauses, hidden side
effects, overgrown classes). The pre-flight Phase D probe in v2 found
that **modern instruction-tuned LLMs essentially never produce these
smells** on hard algorithmic tasks — 0 of 11 dimensions cleared the
prevalence gate. The original rubric was the right instrument for the
wrong population.

v2 replaced it with an 11-dimension 0–5 severity rubric targeting
dimensions algorithmic Python code actually varies on: error handling
consistency, edge case gap, type hint gap, code organization,
documentation appropriateness, abstraction miscalibration, API
ergonomics, concurrency safety, data structure choice, algorithm
correctness, example quality. See the
[rubric reference](../reference/index.md).

### 3. Added a calibration anchor on the judge prompt

The pre-flight Phase D2 audit found that single-judge gpt-4o-mini
saturated 7 of 9 dimensions at severity 0 with positive-toned
rationales — a judge-calibration failure, not a rubric-design failure.
v2 added an explicit directive on the judge system prompt:

> *Severity 0 should be uncommon. Most realistic algorithmic code has
> severity 1–2 on at least 3 of the 9 always-on dimensions. Do NOT
> default to 0 because nothing obvious is wrong.*

The anchor was tuned to bind without prescribing the *direction* of
preamble effect. Phase D2 re-probed with the anchor and passed 9 of
9 dimensions at the strict gate.

### 4. Expanded the pool and added structured pre-registration

v2 expanded the subject pool from 7 (v1) to 10 models, including a
reasoning tier with explicit `reasoning: {effort: "high"}`, and added
provider logging for routing-variability auditing. The replication
count went from 1 to 2 per cell, raising per-condition n from ~35 to
~135.

These changes raise statistical power but are not what flipped the
result — the instrument changes (1) and (2) are. The pool/replication
expansion sharpens v2's confidence intervals and supports the
per-dimension stratification, but the headline detection survives at
the smaller v1 sample size if the v2 metric is used (the
weight-sensitivity table in v1 shows the LLM-only weighting reaches
p = 0.003 on v1's 274 samples).

## The mechanism: when does this failure mode bite?

The v1 false null is a specific instance of a general
metric-design failure mode that has a clean characterization:

> **If your composite metric weights signals with different effect
> profiles, and you weight the *insensitive* signals more heavily,
> your headline can be null even when sub-components show large
> effects.**

The failure is mechanical, not statistical. It is not corrected by
larger samples — v1's 274 samples were not the problem, since the
LLM-judge sub-components detected the effect at the same sample size.
It is corrected only by re-designing the composite to drop or
down-weight the insensitive components.

The condition for the failure mode to bite is **measurement
orthogonality between the manipulation and a subset of the
composite**. In the preamble-effects case, the manipulation
(preamble content) tunes alignment-dependent craft dimensions, and
static analyzers measure pretraining-dependent structural
properties. The two signal spaces barely overlap (see
[why static metrics fail](why-static-metrics-fail.md)). Any composite
that weights both will dilute its detection power on the
alignment-tunable side in proportion to how much weight it gives to
the structural side.

## Why this is the central methodological lesson

The v1/v2 contrast is the load-bearing methodological lesson of the
whole investigation. The empirical finding (preambles change craft)
is interesting; the *measurement* finding (static-heavy composites
manufacture false nulls on this question) is the one that has the
widest cross-domain implications:

1. **Any practitioner A/B-testing preambles with radon/pylint metrics
   is receiving false nulls today.** This is the production-facing
   version of v1's experience.
2. **Any researcher using a composite that mixes alignment-tunable
   and pretraining-locked signals at fixed weights is at risk of the
   same artifact** whenever the manipulation under test acts
   preferentially on one half.
3. **Pre-registering a composite does not protect against this.** v1
   pre-registered its composite; the artifact still occurred. What
   protects is **measuring the components separately** and inspecting
   the per-component effect profile before accepting the composite as
   the headline.

The v2 verdict treats the instrument correction as the central
deliverable. The detection at p = 9.24 × 10⁻¹⁸ is real and
substantive, but the durable contribution is the demonstration that
a static-heavy composite buried the same signal under noise weighted
at 65% — and the concrete procedure for repairing it.

## Sources

- `preamble_quality_experiment/CONCLUSIONS.md` — v1 headline,
  component decomposition, and re-weighting sensitivity table.
- `preamble_quality_experiment/REPORT_ADDENDUM.md` — v1's
  production-corrected recommendation framing the static-heavy
  composite as a measurement artifact.
- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Comparison to v1".
- `preamble_quality_experiment_v2/REPORT_ADDENDUM.md` — pre-flight
  amendments A1 (rubric redesign) and A5 (calibration anchor +
  multi-judge panel).
- [Finding 5 — static analysis cannot detect preamble effects](../findings/5-static-analysis-misses.md).
- [Why static metrics fail](why-static-metrics-fail.md) — the
  structural reason behind the diagnostic.
