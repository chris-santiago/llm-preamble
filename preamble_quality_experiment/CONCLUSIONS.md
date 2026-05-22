# Conclusions — Preamble Quality Experiment

**Hypothesis tested:** Coding-agent preambles change the quality of code an LLM
writes, detectable as a main effect of preamble condition on a Composite Quality
Score (CQS) that is consistent across models and tasks.

**Headline finding:** **Preambles do change code quality — but only on the
dimensions a static analyzer cannot see.** The pre-registered composite CQS shows
no significant effect (Kruskal–Wallis p = 0.63), but that null is a *metric
artifact*: the 65%-weighted static/AST components are blind to preamble-driven
quality, while the LLM-judge components (idiomaticity, comment quality) detect a
strong, hypothesis-consistent effect (p = 0.002 and p = 0.006). Weighting flat
static noise at 65% buries a real signal.

Design: 7 effective subject models × 8 preamble conditions × 6 hard tasks
(3 from-scratch creation, 3 refactoring), full 8-judge cross-judge matrix,
cross-judge-only primary scores, data-driven percentile normalization. 274 scored
samples, 2192 cross-judge ratings. (`grok-4.1-fast` was deprecated mid-run and
contributed no data — see Data Quality.)

---

## Debate Scorecard

| Finding | Debate verdict | Empirical resolution | Who was right |
|---|---|---|---|
| **F1** — static metrics insensitive to craft; reward simplicity | critique (FATAL) → empirical | **CONFIRMED.** static p=0.998, ast p=0.907 (no separation across conditions). Sensitivity probe: composite mis-ranks known-quality samples — static-only `excellent(0.57) < average(0.66)`; even full-CQS-with-judges `excellent(0.78) < average(0.80)`. Re-weighting: effect goes significant only as static weight falls below ~0.5. | **Critic.** The PoC null was the metric, not the world. |
| **F2** — "real_agent" is a condensed instruction list, not a real preamble; tests instruction-following, not priming | critique (FATAL) → empirical | **PARTIALLY CONFIRMED / nuanced.** On comment quality: none 0.681 < persona_only 0.715 ≈ real_agent 0.711 < long_directive 0.746. Pure-persona priming (no directives) lifts quality above `none`, *and* instruction-richness lifts it further (long_directive highest). Mechanism is **both** distributional priming and instruction-following. | **Split.** Priming alone works (refutes the strong form); more directives still help (supports the concern that instruction content matters). |
| **F3** — same models are subjects and judges → self-preference bias | critique (MATERIAL) → empirical | **REFUTED.** Self vs cross idiomaticity delta = 0.36 on a 10-pt scale (Cohen's d = 0.16, Mann–Whitney p = 0.13). Negligible, and the primary CQS already excludes self-judgments. | **Defender.** Bias present but immaterial. |
| **F4** — tasks too easy → ceiling effect | critique (MATERIAL) → empirical | **RESOLVED by redesign, with a twist.** Hard creation + refactoring tasks were used. Static metrics stayed flat *even on hard tasks* (creation p=0.68, refactoring p=0.77) — the ceiling was in the metric, not the tasks. The LLM-judge signal emerged on exactly these hard tasks. | **Both.** Harder tasks were the right call; they revealed that the static metric — not difficulty — was the binding constraint. |
| **F5** — identifier entropy is bidirectional | conceded | **HONORED.** Replaced with PEP8 name-compliance ratio (directional). Did not rescue static separation — consistent with F1 being the dominant problem. | n/a (conceded pre-experiment). |
| **F6** — fixed normalization ceilings compress signal | critique → empirical | **APPLIED, not causal.** Data-driven [5th, 95th] percentile bounds were used. Static separation remained p=0.998 — so compression was not what hid the signal; insensitivity (F1) was. | Normalization mattered less than F1. |
| **F7** — radon class/method CC double-count | defense_wins | Closed in debate; not revisited. | **Defender.** |

---

## Primary Result — the metric decomposition

Kruskal–Wallis across the 7 main conditions, per CQS component:

| Component | Weight | KW p | Separates conditions? |
|---|---|---|---|
| static_score | 45% | 0.998 | No |
| ast_score | 20% | 0.907 | No |
| **llm_idiom_score** | 20% | **0.0022** | **Yes** |
| **llm_comment_score** | 15% | **0.0058** | **Yes** |
| composite CQS (pre-registered) | 100% | 0.633 | No (signal diluted) |

Mixed-effects `score ~ preamble + (1|model)` (main conditions, n=237) agrees:
composite min-preamble p = 0.16; idiomaticity p = 0.010; comment quality p = 0.020.
(Model random-effect variance was ~singular — between-model differences are small
relative to within; the fixed preamble effects are unaffected.)

**Figure:** `reanalysis_component_separation.png`.

## The effect is hypothesis-consistent on LLM-judged dimensions

Per-condition means (cross-judge, 0–1):

| Condition | idiomaticity | comment quality |
|---|---|---|
| negative_control (junior dev) | 0.774 | **0.601 (worst)** |
| minimal | 0.757 | 0.668 |
| generic_coding | 0.802 | 0.680 |
| none | 0.821 | 0.681 |
| real_agent | 0.809 | 0.711 |
| persona_only | 0.811 | 0.715 |
| long_directive | **0.842 (best)** | **0.746 (best)** |

The "junior developer still learning" negative control reliably produces the
**lowest** comment quality, and expert/long-directive preambles the highest — the
predicted direction. The effect size is modest (≈0.10–0.15 on a 0–1 scale for
comment quality) but statistically robust.

## Re-weighting sensitivity (post-hoc, not a metric redefinition)

| Weighting | static+AST weight | KW p |
|---|---|---|
| pre-registered | 0.65 | 0.633 |
| balanced | 0.50 | 0.185 |
| LLM-heavy | 0.25 | **0.012** |
| LLM-only | 0.00 | **0.003** |

The preamble effect crosses significance precisely as static weight drops below
half. **Figure:** `reanalysis_reweight_sensitivity.png`. This is reported as a
sensitivity analysis; the pre-registered composite remains the primary (null)
result, and the decomposition is the explanation for it.

## Trivial baseline

Best condition (long_directive composite 0.704) vs trivial baseline (0.683):
beaten, but by a hair on the composite — again because the static-dominated
composite compresses everything into [0.67, 0.70]. On comment quality the gap is
real (long_directive 0.746 vs negative_control 0.601).

---

## Surprises

- **The metric, not the hypothesis, produced the original null.** Neither side of
  the debate predicted that the LLM-judge components would cleanly separate
  conditions while static metrics stayed flat *to three decimal places*
  (p=0.998). The critic argued static metrics were *weak*; the data shows they are
  effectively *constant* across preamble conditions.
- **Pure persona priming works without directives.** `persona_only` (a senior-
  engineer persona with no explicit instructions) matched `real_agent` on quality,
  arguing for a genuine distributional-priming mechanism, not only instruction
  compliance.

## Data quality / limitations

- **`grok-4.1-fast` deprecated mid-run** (all 48 calls 404'd) → 7 effective subject
  models. The model list should be updated (e.g. to grok-4.3) before any re-run.
- **Elevated extraction failures** for nemotron-3-super (~15%), qwen3.5, minimax —
  these models emit prose/reasoning instead of fenced code. Logged and excluded,
  not scored zero; they thin those models' per-cell counts.
- **Two AST sub-metrics are dead weight:** cognitive-complexity violations
  (nonzero in 5/274) and bare-except count (1/274) — modern models essentially
  never commit these errors, so the metrics carry no variance.
- **F1 probe rests on 3 hand-authored synthetic samples.** The order violation is
  directionally informative but not a calibrated psychometric result.
- Effect sizes on LLM-judged dimensions are modest; this establishes existence and
  direction, not magnitude for any production decision.

## Bottom line

The hypothesis is **supported on the dimensions that matter for the question the
user actually asked** (idiomaticity, comment quality — the "hard-to-judge"
craft dimensions), and the support is masked by a static-analysis-heavy composite.
Static analysis (radon MI/CC, Halstead, pylint, cognitive complexity) is the wrong
instrument for measuring preamble-driven code quality: across 7 models and 6 hard
tasks it does not move with preamble condition and actively mis-ranks
craftsmanship. LLM-as-judge on idiomaticity and comment quality is the valid
instrument here.
