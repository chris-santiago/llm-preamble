# Finding 1 — Preamble content is load-bearing: outputs move measurably in *either* direction relative to a no-preamble baseline

**Claim.** The preamble channel is powerful enough that content choices move outputs measurably above *and* below a no-system-prompt baseline. The cleanest evidence is the degradation case: framings like "junior developer", "still learning Python", or "don't worry too much about style" produce *worse* code than supplying no system prompt at all. That's the sharp test — the model isn't just amplified by good preambles or unaffected by bad ones, it's actively responsive to content in both directions. Preambles are not decorative; they steer.

**Evidence.** From the v2 main run (n=138 samples per condition, 10-model pool, 7 tasks):

| Preamble | mean CQS-craft | β vs `none` (mixed-effects) | p |
|---|---|---|---|
| `none` | 0.778 | 0 (reference) | — |
| `negative_control` ("junior developer") | 0.723 | **−0.060** | **5 × 10⁻⁵** |
| `long_directive` (strongest rich preamble) | 0.815 | +0.046 | 0.002 |

Both effects are statistically robust. Critically, `none` is not the floor — the synthetic `negative_control` probe pushes output *below* what the model produces with no instruction at all. That's the demonstration that the channel carries real signal: if preambles were inert or weakly additive, you could not degrade from baseline by writing one. (`trivial_baseline`, which uses no system prompt + a name-only user prompt + temperature 1.0, scores 0.556 — a −0.222 cliff that confirms the model uses *any* coherent context productively when present, and that the −0.060 negative-priming effect is a content-level signal rather than the absence of context.) The negative effect being larger in magnitude than the positive is a secondary observation — partly real, partly bounded by ceiling effects on rubric dimensions where `none` already scores near the top.

![CQS-craft by preamble](../../preamble_quality_experiment_v2/experiment_v2_results/figures/fig1_headline_cqs_by_preamble.png)

**Action.** Treat preamble content as load-bearing — what you write changes the output, including for the worse. `negative_control` was a synthetic probe (no production prompt says "junior developer still learning Python"); its purpose was to *prove that the channel can push output below baseline at all*. The realistic implication for production prompts is broader: don't assume any preamble change is positive or neutral. Test every change against your evaluator. The most common ways real production prompts accidentally drift below baseline are content-mismatch (Finding 2) and verbose dilution (Finding 3) — both at smaller magnitude than the synthetic probe, but in the same direction.

**Related work.** PRISM (USC 2026) reports the same below-baseline behavior on a *different* axis — expert personas degrade accuracy from ~71.6% to ~68%. Zheng et al. (EMNLP 2024) find no reliable accuracy gain from personas across 162 roles, consistent with this paper's load-bearing-on-craft reading (they measured accuracy; we measured craft). See [`RELATED_WORK.md` § "Personas help style, not substance"](RELATED_WORK.md#personas-help-style-not-substance--the-alignment-vs-pretraining-split) and [§ "Personas do not reliably help objective tasks"](RELATED_WORK.md#personas-do-not-reliably-help-objective-tasks).
