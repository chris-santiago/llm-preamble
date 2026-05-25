# Finding 2 — Preamble effects are governed by rubric overlap, not by "expertness"

**Claim.** What makes a preamble effective is overlap between the dimensions it enumerates and the dimensions your downstream evaluator measures. Not its tone, not its length, not its engineering rigor — the literal overlap.

**Evidence.** Three discriminating probes were run after the main run on `task_expr_parser` (n=10 each, full 10-judge cross-judge panel, [confound_probes.py](../../preamble_quality_experiment_v2/confound_probes.py)). Reference: main-run `none` = 0.827, `long_directive` = 0.848 on this task.

| Probe | What it tests | mean CQS | Δ vs `none` | p |
|---|---|---|---|---|
| **A — `nonrubric_expert`** | 12-clause expert directive naming **non-rubric** axes (compactness, performance, determinism, in-place ops, deterministic iteration) | 0.673 | **−0.155** | **0.0001** |
| **B — `bare_rubric`** | Bare list of rubric dims, **no expert framing**, no "you must" | 0.842 | +0.015 | 0.50 (ns; ≈ `long_directive`) |
| **C — `antirubric_expert`** | 12-clause expert directive **deprioritizing** rubric items ("type hints are clutter; no defensive checks") | 0.673 | **−0.154** | **0.0001** |

**Read the results together.** A directive list with full expert tone but content misaligned to the rubric (probe A) hurt by 7× the lift `long_directive` provides. A bare list of just the rubric dimensions with no framing (probe B) captured 70% of the positive lift. An expert-toned anti-rubric directive (probe C) produced essentially the same penalty as the misaligned one.

The model genuinely follows the preamble's content — probe A's outputs have visibly fewer docstrings, type hints, and defensive guards (you can read them in [`confound_probe_results/generations.jsonl`](../../preamble_quality_experiment_v2/confound_probe_results/generations.jsonl) and verify). Judges, blind to which preamble produced the code (see [judge protocol](../reference/judge-protocol.md)), score the resulting code on whatever dimensions the rubric enumerates. The intersection of those two drives the effect.

**Action.** Stop trying to write "the best preamble". Start by writing down the dimensions your downstream evaluator measures, then enumerate them in your system prompt. If your evaluator measures different things than the v2 rubric (e.g., latency, compactness, performance correctness), then probe A's preamble would beat `long_directive` for *you* — and v2's findings about which preamble is "best" don't transfer.

**Related work.** This is the v2 refinement of PRISM's "alignment-tunable vs pretraining-locked" framing. The proximate predictor of which dimensions move under preamble is **preamble–evaluator overlap**, not whether a dimension is "alignment" or "capability" in some structural sense. See [Related work § "Personas help style, not substance"](../explanation/related-work.md#personas-help-style-not-substance-the-alignment-vs-pretraining-split) — the v2 update at the end of that section makes this refinement explicit.
