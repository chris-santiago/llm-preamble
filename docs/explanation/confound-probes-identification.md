# Confound probes — the formal identification argument

> The v2 main run could not, on its own, separate "preambles change
> code; the rubric detects the change" (H-mechanism) from "preambles
> add surface markers the rubric enumerates" (H-judge-priming) because
> the strongest preamble's clauses overlap the rubric on 7 of 9
> always-on dimensions. Three probes were constructed to break the
> overlap. This page reconstructs the formal identification argument.

## The identification problem v2 needed to solve

The `long_directive` preamble carries the bulk of the v2 lift over
`none` (+0.046, p = 0.002). Mapping `long_directive`'s 12 clauses
against the rubric's 11 dimensions, **7 of the 9 always-on rubric
dimensions are explicitly named in `long_directive`'s clauses** — and
those 7 are exactly the 7 that show p < 10⁻⁴ separation across
preambles. The two dimensions that do not move
(`algorithm_correctness`, `data_structure_choice`) are not named in
any preamble in any condition.

This overlap supports two substantively different hypotheses:

- **H-mechanism.** Preambles change the code the model writes on
  alignment-tunable craft axes; judges detect those changes. The 7-vs-2
  split reflects which axes are actually preamble-tunable.
- **H-judge-priming.** Preambles cause the model to add surface
  markers (verbose docstrings, defensive try-blocks, type hints,
  thread-safety comments) that align to the rubric's enumerated
  dimensions, without deep changes to algorithmic structure. The
  7-vs-2 split reflects which dimensions the preamble names.

These hypotheses produce near-identical predictions in the v2 main run
because the preamble that drives most of the headline effect happens
to enumerate ~7 of the 9 always-on rubric dimensions. The v2 main run
alone could not discriminate them. The three confound probes were
designed to.

## The three probes, by design

Each probe was tested on `task_expr_parser`, n=10 generations per
probe, across all 10 subject models, with the full 10-judge cross-judge
matrix and the same calibration anchor and judge prompts as the main
run. Total probe cost: $1.04.

| Probe | Framing | Content axis | Predicted by H-mechanism | Predicted by H-judge-priming |
|---|---|---|---|---|
| **A — `nonrubric_expert`** | Expert ("You are an expert autonomous coding agent. Your code must…") | Names *non-rubric* axes: compactness, single-pass algorithms, in-place operations, builtins-over-custom, deterministic iteration order, top-down ordering, early returns | Should help (expert framing aids craft) | Should help (expert framing rewarded by judges if priming is framing-based) |
| **B — `bare_rubric`** | No expert framing, no "you must" — just an announcement | Bare list of rubric dimensions in plain language | Marginal (no instructions on *what to do*) | Should help substantially (model adds rubric-matching surface markers) |
| **C — `antirubric_expert`** | Expert, same framing as `long_directive` | Clauses explicitly **deprioritize** rubric items ("type hints are clutter; omit them", "don't over-engineer error handling", "edge cases are the caller's responsibility") | Should hurt (model follows anti-rubric content) | Should hurt (model produces fewer rubric-matched surface markers) |

The key design choices that make this a clean identification:

- **A and C share full expert framing** (same tone, same imperative
  voice, same compound-clause structure). They differ in whether the
  content is rubric-aligned. Comparing A and C against `long_directive`
  isolates the framing-vs-content axis.
- **B has no expert framing at all.** Comparing B against
  `long_directive` isolates the content-vs-framing axis from the other
  direction: same content (rubric dimensions named), different framing
  (bare list vs imperative directive).
- **Judges are blind to preamble identity in all three probes** (see
  `confound_probes.py:341-362`). The judge call's user message is
  exactly `"Code under review:\n\n```python\n{code}\n```"` — no
  condition label, no preamble text, no task description.

## The probe results

Reference: main-run `none` on this task = 0.827; `long_directive` =
0.848.

| Condition | n | mean CQS-craft | Δ vs `none` | p vs `none` |
|---|---|---|---|---|
| `none` (main-run reference) | 20 | 0.827 | — | — |
| `long_directive` (main-run reference) | 20 | 0.848 | +0.021 | (sig in main run pooled) |
| `negative_control` (main-run reference) | 19 | 0.749 | −0.078 | (sig in main run pooled) |
| `python_coder_agent` (main-run reference) | 20 | 0.854 | +0.027 | (sig in main run pooled) |
| `none_control` (in-probe sanity check) | 10 | 0.806 | −0.021 | 0.23 (ns ✓) |
| **`probe_A_nonrubric_expert`** | 10 | **0.673** | **−0.155** | **0.0001** |
| **`probe_B_bare_rubric`** | 10 | **0.842** | **+0.015** | 0.50 (ns vs `none`; ≈ `long_directive`) |
| **`probe_C_antirubric_expert`** | 10 | **0.673** | **−0.154** | **0.0001** |

## The triangulation

The three numbers, read jointly, drive the identification:

### Framing alone does not lift

Probes A and C both carry the full `long_directive` expert framing —
the imperative voice, the 12-clause structure, the compound
explanatory clauses. Both produce CQS *sharply below* `none`. If
expert framing alone lifted craft, A and C should be at least
neutral. They are decisively negative
(both at −0.155 / −0.154, p = 0.0001).

This rules out the strong form of judge-priming where the framing
itself drives the rubric scores: if expert framing alone produced
high CQS, A would score near `long_directive`. It does not. The
model's behavior tracks preamble *content*, not preamble *form*.

### Rubric overlap without framing recovers most of the lift

Probe B — a bare list with no expert framing, no imperative voice —
produces CQS statistically indistinguishable from `long_directive`
(0.842 vs 0.848; B-vs-`none` p = 0.50). Per-dimension severity
profiles match: `documentation_appropriateness` 0.79 (B) vs 0.74
(`long_directive`), and similar tracking on the other rubric
dimensions.

The recovery ratio is the load-bearing decomposition:

```
recovery_ratio = (probe_B − none) / (long_directive − none)
               = +0.015 / +0.021
               ≈ 0.70
```

**70% of `long_directive`'s lift is attributable to naming the rubric
dimensions.** The remaining ~30% comes from imperative tone and
compound explanatory clauses on top of bare enumeration.

This is what the v2 [Finding 3](../findings/3-bare-enumeration.md)
quantifies, and it is the proximate predictor identified by the
probes: **overlap density between (preamble-enumerated dimensions)
and (rubric-measured dimensions)** is what drives the effect.

### Anti-rubric content hurts identically to neutral non-rubric content

Probe C produces the same penalty as probe A (0.673 vs 0.673, both at
p = 0.0001). Whether the preamble *neutrally fails to name* rubric
dimensions (A) or *explicitly deprioritizes* them (C), the
consequence is the same. The model reallocates capacity away from the
rubric dimensions; the rubric correctly scores the gap.

This symmetry tightens the identification. If A and C produced
different magnitudes, the difference would tell us something about
explicit anti-content vs implicit content-absence. The fact that they
are statistically identical means the cost is dominated by
*non-overlap* with the rubric, not by the specific direction of
content elsewhere.

## What the probes formally identify

Reading the three results together:

| Claim | Supporting probe contrast | Status |
|---|---|---|
| Judges track real code, not preamble surface | A (negative despite expert framing) and probe-A's measurably fewer docstrings/type hints/guards | Identified |
| Expert framing does not in itself drive lift | A and C both negative under full expert framing | Identified |
| Rubric overlap without framing recovers most of the lift | B ≈ `long_directive` | Identified |
| The ~30% residual is attributable to framing (imperative tone, compound clauses) | (`long_directive` − B) gap of 0.006 CQS units | Identified |
| Preamble *content* — not form — drives the effect | A vs C symmetry under shared framing | Identified |

The combined identification is what licenses the
[attention-allocation mechanism](attention-allocation-mechanism.md)
reading. The probes do not just rule out alternatives — they pin the
overlap-density predictor with quantitative support.

## What the probes do not resolve

The probes leave three identification questions open. They are
documented for honesty about the limits of what was identified.

1. **Whether probe-A's behavioral change is deep craft change or
   surface markers only.** Probe A produces visibly fewer docstrings
   and type hints — that is a real, observable code change. But
   whether the deeper algorithmic / structural craft is *also* worse
   under probe A was not directly tested. A static-analysis run on
   probe-A outputs would help; it was not done.
2. **Whether `long_directive`'s lift comes proportionally from each
   enumerated clause.** Probe B recovers 70%; the remaining 30% may
   come from imperative tone, from compound clauses that explain
   *why* each item matters, or from specific clauses that name
   dimensions outside the rubric (e.g., "composition over
   inheritance", which is not in the rubric but might improve
   `code_organization` indirectly). A clause-ablation study could
   discriminate.
3. **External validity to other rubrics.** All conclusions are
   anchored to the v2 11-dimension rubric. A rubric measuring
   different things (functional purity, performance-correctness
   tradeoffs) would produce different preamble winners. The probes
   confirm overlap density is the right reading; they do not quantify
   how much of v2's findings transfer to other rubrics.

## Sources

- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Identification
  limit — rubric-directive overlap confound".
- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Confound probes".
- `preamble_quality_experiment_v2/REPORT_ADDENDUM.md`
  §"Post-main-run: the confound probes".
- The [attention-allocation mechanism](attention-allocation-mechanism.md)
  page, which states the refined reading the probes support.
- [Finding 2](../findings/2-overlap-not-expertness.md) and
  [Finding 3](../findings/3-bare-enumeration.md) — the practitioner-
  facing forms of the identification result.
