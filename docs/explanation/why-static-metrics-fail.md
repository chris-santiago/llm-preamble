# Why static-analysis metrics cannot detect preamble effects

> Radon, pylint, cyclomatic complexity, Halstead difficulty — the
> standard static-analysis panel — are flat across preamble conditions.
> This page explains the mechanism: preamble effects are
> alignment-tunable, static metrics measure pretraining-dependent
> structural properties, and the two signals barely overlap.

## The empirical baseline

From the v2 main run's static-analysis diagnostic panel:

| Metric | KW p across preambles | Verdict |
|---|---|---|
| `maintainability_index` | 0.92 | Flat |
| `avg_cyclomatic` | 0.33 | Flat |
| `max_cyclomatic` | 0.84 | Flat |
| `halstead_difficulty` | 0.98 | Flat |
| `pylint_errors` | 0.97 | Flat |
| `pylint_warnings` | 0.97 | Flat |
| `pylint_refactor` | 0.92 | Flat |
| `cognitive_complexity_violations` | 0.53 | Flat |
| `pylint_conventions` | 0.012 | Weak signal (the only one) |

**8 of 9 static metrics produced KW p > 0.5 across the 8 main preamble
conditions.** The single weak signal (`pylint_conventions`, p = 0.012)
overlaps semantically with documentation and type-hint dimensions the
LLM-judge rubric measures separately — and even there the judge signal
on the same axes is orders of magnitude stronger
(p < 10⁻¹⁶ on docstring quality and type-hint coverage).

v1 reproduced the same pattern independently: its 65%-weighted
static-heavy composite produced a false null (KW p = 0.633) while the
LLM-judge sub-components separately detected significance (idiom
p = 0.0022, comment p = 0.0058). See
[v1 vs v2 — the instrument correction](v1-vs-v2-instrument-correction.md)
for the full story of how that false null came about.

## The mechanism: alignment-tunable vs pretraining-dependent

Preambles operate by directing the model's craft-attention budget
(see [attention allocation](attention-allocation-mechanism.md)).
They reallocate output capacity toward the dimensions the preamble
enumerates: style, idiom, error-handling shape, naming, comment
appropriateness, type-hint discipline. These are **alignment-tunable**
dimensions — they were shaped during instruction-tuning, and they
respond to instruction-level signals like a preamble.

Static-analysis metrics measure something else. Radon's maintainability
index, cyclomatic complexity, Halstead difficulty, and most of pylint's
output measure **structural properties of the code**:

- How many control-flow branches does this function contain?
- How many distinct operators and operands appear?
- How deeply nested are the control structures?
- Does the function exceed a length threshold?
- Is the import order canonical?

These properties are dominated by the model's pretraining-time
distribution of how Python is written. A preamble that tells the
model to "validate inputs" produces more `if` statements, slightly
raising cyclomatic complexity — but not in any systematic direction
across the panel of preambles. A preamble that tells the model to
"prefer composition over inheritance" produces different
class/function decomposition, but again not in a way that pushes any
single static metric reliably up or down. The signals the metrics
track simply do not move much in response to instruction-level
changes; they move in response to the model's underlying generative
distribution, which is set by pretraining and largely insensitive to
preamble.

This is the v2 attention-allocation reading restated in static-metric
terms: the dimensions a preamble can enumerate (and therefore
direct attention toward) are not the dimensions a static analyzer
measures.

## Why this is not a v2-specific artifact

The static-metric insensitivity result is independently established
in the literature. Three points pin this down:

- **arXiv 2504.13656** ("Do Prompt Patterns Affect Code Quality?")
  tested prompt patterns and found no significant differences in
  maintainability, security, or reliability across patterns — all
  static-analysis-based measurements. Same null result, different
  experimental design.
- **Concurrent argument** (arXiv 2508.14419, 2506.10330) that static
  metrics alone are insufficient as a quality measure and should be
  used as a *feedback* signal rather than a *quality* signal.
- **v1's own panel** (different model pool, different rubric, same
  static analyzers) reached the same conclusion: KW p ≈ 0.998 on the
  static components, p < 0.01 on the LLM-judge components.

The pattern reproduces across populations, evaluators, and
investigators. It is not a v2 design artifact.

See the [related work explanation page](related-work.md) for the full
literature mapping.

## Why the one weak signal does not rescue static analysis

`pylint_conventions` (p = 0.012) is the only static metric that moves
under preamble. The mechanism is plausible: `negative_control` produces
slightly worse PEP-8 compliance (14.6 conventions issues vs
`real_agent`'s 11.9). This is real — the model writes slightly less
canonical Python when told it is a "junior developer still learning"
— and it is consistent with the attention-allocation reading.

But the signal is weaker than the LLM-judge signal on overlapping
dimensions by orders of magnitude. If a practitioner relies on
`pylint_conventions` to A/B-test preambles, they will:

1. Detect a directional effect with much wider confidence intervals
   than the LLM-judge panel would produce.
2. Miss the bulk of the preamble effect, which lives on dimensions
   pylint does not score (idiomaticity of stdlib usage, why-not-what
   comment quality, abstraction calibration, edge-case awareness).
3. Mis-rank preambles whenever the strongest preamble's effect lives
   on those un-scored dimensions.

The asymmetry is structural. Static analyzers measure what they can
measure deterministically — and what they can measure is not the
craft signal preambles tune.

## The methodological implication

The v1 → v2 instrument correction makes this concrete. v1's
pre-registered composite weighted static components at 65%. The
result was a false null at the headline level
(composite KW p = 0.633) even though the underlying LLM-judge signal
was strong (idiom p = 0.002, comment p = 0.006). The static-heavy
weighting mechanically buried the real signal under noise.

The v2 instrument correction was: drop static analysis from the
primary metric entirely, restrict CQS-craft to LLM-judge components
(`CQS-craft = 0.45 · idiom + 0.45 · comment + 0.10 · (1 − rubric/5)`).
v2's primary metric then detected the effect at p = 9.24 × 10⁻¹⁸ — a
gap of more than 17 orders of magnitude vs v1's null on the same
question. See
[v1 vs v2 — the instrument correction](v1-vs-v2-instrument-correction.md)
for the full diagnostic.

## What to use instead

For any work where preamble effects (or, more broadly, prompt-engineering
effects on code craft) matter, the appropriate measurement instrument
is a multi-judge LLM panel scoring craft dimensions with a calibrated
rubric. The v2 design ships one concrete instantiation; see the
[methodology section](../methodology/index.md) for the judge protocol
and the [reference section](../reference/index.md) for the rubric
itself.

Static analyzers remain valid for what they measure: structural
complexity, MI, lint compliance. They are not invalid; they are
*orthogonal* to the preamble signal. Use them for the things they
measure well; do not use them to A/B-test preambles. If your CI
gates preamble or prompt changes on radon/pylint metrics today, you
are systematically receiving false nulls.

## Sources

- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Diagnostic null —
  static analysis reproduces v1's flat finding".
- `README.md` Finding 5 — the practitioner-facing version of this
  argument.
- `RELATED_WORK.md` §"Prompt variation does not move static
  code-quality metrics".
- [Finding 5 — static analysis cannot detect preamble effects](../findings/5-static-analysis-misses.md).
- [v1 vs v2 — the instrument correction](v1-vs-v2-instrument-correction.md).
- The [attention-allocation mechanism](attention-allocation-mechanism.md)
  page, which provides the underlying reason these signals do not
  overlap.
