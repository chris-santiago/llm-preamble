# Attention allocation — the mechanism behind preamble effects

> The three confound probes refined the v2 mechanism interpretation from
> "preambles change code; the rubric detects the change" to a sharper
> **attention-allocation reading**.

## The headline reading

Preambles direct the model's finite craft-attention budget toward the
dimensions they enumerate, at the cost of whatever the model would
otherwise have done. When the preamble's enumerated dimensions overlap
with what the rubric measures, CQS-craft moves up. When they don't, it
moves down — sometimes far below the `negative_control` baseline.

This is not a generic "expert preambles produce better code" effect, and
it is not a pure "judges reward expert-sounding preambles" effect. It is
a redistribution claim: the model has finite output capacity, and the
preamble decides what that capacity gets spent on.

## What the probes triangulated

Three preambles were constructed to break the rubric–directive overlap
confound that the v2 main run could not separately identify (see also
the [confound probes identification page](confound-probes-identification.md)).
All three were tested on `task_expr_parser`, n=10 each, full 10-judge
cross-judge matrix, identical judge prompts and calibration anchor to the
main run. Reference: main-run `none` on the same task = 0.827,
`long_directive` = 0.848.

| Probe | Design | Δ vs `none` | p |
|---|---|---|---|
| **A — `nonrubric_expert`** | 12-clause expert directive naming **non-rubric** axes (compactness, performance, determinism, in-place ops, ordered iteration) | **−0.155** | **0.0001** |
| **B — `bare_rubric`** | Bare list of rubric dimensions; no expert framing, no imperative tone | **+0.015** | 0.50 (ns; ≈ `long_directive`) |
| **C — `antirubric_expert`** | Same expert framing as `long_directive`, but clauses explicitly *deprioritize* rubric items | **−0.154** | **0.0001** |

These three numbers, read together, are what force the
attention-allocation reading.

### Probe A: misaligned expert directive hurts by 7× the long_directive lift

A 12-clause directive with full expert framing, but clauses that do not
name any of the rubric dimensions, does not just fail to help — it
*actively hurts* by −0.155 CQS-craft units (p = 0.0001). For comparison,
the strongest negative preamble in the main run, `negative_control`
("junior developer"), only reaches −0.078 vs `none` on this task.

The mechanism is visible in per-dimension severity: probe A's
documentation severity (1.59) and edge_case_gap (1.77) are *higher* than
`negative_control` on this task. The model followed the preamble's
content — it produced compact, performance-focused code with fewer
docstrings, fewer defensive guards, fewer comments — and the rubric
correctly penalized it.

This rules out the strong form of judge-priming: judges are blind to the
preamble (see [judge protocol in the methodology section](../methodology/index.md)),
and if they were rewarding "expert-framed preambles" rather than tracking
code content, probe A should have produced CQS close to `long_directive`.
It did not. It produced CQS worse than `negative_control`.

It also rules out a generic "expert framing produces better craft"
reading. If expert tone alone lifted craft, probe A should be at least
positive. It is sharply negative.

### Probe B: bare rubric naming recovers ~70% of long_directive's lift

A bare list of the rubric dimensions — no "you must", no expert framing,
no imperative tone — produces output statistically indistinguishable
from `long_directive` (probe B 0.842 vs long_directive 0.848,
B-vs-`none` p = 0.50). Probe B's per-dimension severity profile tracks
`long_directive`'s almost exactly (`documentation_appropriateness` 0.79
vs `long_directive`'s 0.74).

Telling the model what the rubric measures is sufficient to recover the
bulk of the preamble effect. The remaining ~30%
(`long_directive` 0.848 − probe B 0.842 = 0.006 CQS-craft units on this
task) is attributable to imperative tone, compound-clause framing, or
focused enumeration structure. See
[Finding 3](../findings/3-bare-enumeration.md) for the practical
implication.

### Probe C: anti-rubric directives hurt identically to A

Probe C (0.673) is statistically identical to probe A (0.673), both at
p = 0.0001 vs `none`. An explicitly anti-rubric framing — explicitly
telling the model that type hints are clutter, error handling is
over-engineering, comments belong in commit messages — produces the same
penalty as a neutral non-rubric-naming directive list.

The symmetry is informative: preamble *content* drives the model's
behavior, not the mere "presence of an expert preamble". A and C share
expert framing; they share roughly the same penalty; the common factor
is that neither's clauses overlap the rubric.

## Why this is the right reading

The three probes are jointly inconsistent with two simpler stories and
consistent with the attention-allocation story:

| Story | Predicts probe A | Predicts probe B | Predicts probe C |
|---|---|---|---|
| Pure judge-priming (judges reward expert tone) | ≈ `long_directive` (positive) | ≈ `none` (no lift) | ≈ `long_directive` |
| Generic expert framing improves craft | Positive | Positive | Positive |
| **Attention allocation (rubric overlap)** | **Sharply negative** | **≈ `long_directive`** | **Sharply negative** |

Only the attention-allocation reading matches the observed signs and
magnitudes across all three probes.

## Implications

1. **CQS-craft is real but rubric-dependent.** Probe A confirms judges
   are tracking real code (visibly fewer docstrings, fewer type hints,
   fewer guards). But the metric measures the v2 11-dimension definition
   of craft — not "code quality" in some platonic sense.
2. **A preamble's CQS-craft lift is proportional to the intersection
   between (what the preamble directs the model toward) and (what the
   rubric measures).** This is the operational mechanism statement.
3. **The "junior developer" negative-control effect is robust to this
   refinement.** `negative_control` doesn't enumerate any specific
   dimensions in either direction — it shifts the model's stylistic
   register downward. It hurts (−0.078 in this task, −0.060 pooled)
   without naming what to deprioritize. This is a different mechanism
   than probe C's explicit anti-rubric enumeration, but both routes
   converge on lower CQS-craft. See the
   [load-bearing channel reframe](load-bearing-channel-reframe.md) for
   how this connects to Finding 1.

## Sources

- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Confound probes" and
  §"Refined hypothesis: H-attention-allocation".
- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Methodology note —
  judges are blind to preambles".
- See also the [rubric / measurement instrument reference](../reference/index.md)
  and [Finding 2](../findings/2-overlap-not-expertness.md).
