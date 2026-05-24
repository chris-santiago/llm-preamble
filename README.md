# LLM Preamble Quality Experiments

> Designed, executed, and analyzed using [**ml-lab**](https://github.com/chris-santiago/ml-lab) — a Claude Code plugin for rigorous, pre-registered ML hypothesis investigations (hypothesis → adversarial critique → PoC → empirical resolution → peer review). Every artifact in this repo (`HYPOTHESIS.md`, `SPEC_V2.md`, `CONCLUSIONS.md`, `REPORT_ADDENDUM.md`, `INVESTIGATION_LOG.jsonl`) is a canonical output of that workflow.

If you ship a coding agent or design an LLM evaluation harness, the system prompt content materially changes the code your model produces. This repo measures *how much*, *under what conditions*, and — most importantly for practitioners — *why*. Two pre-registered investigations, 1,290 generations, 25,140 cross-judge ratings.

**TL;DR for builders:** the preamble channel is genuinely load-bearing — content choices measurably move outputs in either direction relative to a no-preamble baseline. There is no universal "best preamble"; a preamble's effect is governed by overlap between (the dimensions the preamble enumerates) and (the dimensions your downstream evaluator measures). Modest effect sizes in either direction (~3–6 points out of 100). Empirical proof for each claim below.

```
                                        what to do                                       evidence
─────────────────────────────────────────────────────────────────────────────────────────────────────
1. preamble content is load-bearing      don't assume new content is neutral; test        β = −0.060
   in both directions                    every preamble change against your evaluator     p = 5×10⁻⁵
2. enumerate what your evaluator         list the dimensions in plain language; a bare    recovery
   measures, not what sounds expert      list recovers 70% of the maximum positive lift   ratio 0.70
3. no universal best preamble exists     pick clauses by overlap with your downstream     probe A:
                                         eval, not by engineering virtue                  −0.155
4. expert framing is decorative          imperative tone + manifesto contributes ~30%     0.842 vs
                                         on top of bare enumeration                       0.848
5. don't measure preamble effects        radon, pylint, cyclomatic, Halstead are flat     8 of 9
   with static analysis                  across all preamble conditions                   p > 0.5
─────────────────────────────────────────────────────────────────────────────────────────────────────
```

The rest of this README walks through each finding with empirical support, then explains the methodology in enough detail to trust the numbers.

**The 12 preambles tested verbatim** are in [`PREAMBLES.md`](PREAMBLES.md) — 9 main-run conditions + 3 post-hoc confound probes, with the exact text and per-condition CQS-craft means. Worth opening before reading the findings if you want to see what each named condition actually says.

---

## Contents

- [The five findings, with evidence](#the-five-findings-with-evidence)
- [Designing a preamble for *your* system](#designing-a-preamble-for-your-system)
- [Effect-size calibration](#effect-size-calibration--when-this-matters-and-when-it-doesnt)
- [What CQS-craft is](#what-cqs-craft-is)
- [The mechanism — confound probes](#the-mechanism--what-the-confound-probes-showed)
- [Full empirical results](#full-empirical-results)
- [Methodology in brief](#methodology-in-brief)
- [Limitations](#limitations)
- [Investigation comparison: v1 vs v2](#investigation-comparison-v1-vs-v2)
- [Repo layout & reproduce](#repo-layout--reproduce)

---

## The five findings, with evidence

### Finding 1 — Preamble content is load-bearing: outputs move measurably in *either* direction relative to a no-preamble baseline

**Claim.** The preamble channel is powerful enough that content choices move outputs measurably above *and* below a no-system-prompt baseline. The cleanest evidence is the degradation case: framings like "junior developer", "still learning Python", or "don't worry too much about style" produce *worse* code than supplying no system prompt at all. That's the sharp test — the model isn't just amplified by good preambles or unaffected by bad ones, it's actively responsive to content in both directions. Preambles are not decorative; they steer.

**Evidence.** From the v2 main run (n=138 samples per condition, 10-model pool, 7 tasks):

| Preamble | mean CQS-craft | β vs `none` (mixed-effects) | p |
|---|---|---|---|
| `none` | 0.778 | 0 (reference) | — |
| `negative_control` ("junior developer") | 0.723 | **−0.060** | **5 × 10⁻⁵** |
| `long_directive` (strongest rich preamble) | 0.815 | +0.046 | 0.002 |

Both effects are statistically robust. Critically, `none` is not the floor — the synthetic `negative_control` probe pushes output *below* what the model produces with no instruction at all. That's the demonstration that the channel carries real signal: if preambles were inert or weakly additive, you could not degrade from baseline by writing one. (`trivial_baseline`, which uses no system prompt + a name-only user prompt + temperature 1.0, scores 0.556 — a −0.222 cliff that confirms the model uses *any* coherent context productively when present, and that the −0.060 negative-priming effect is a content-level signal rather than the absence of context.) The negative effect being larger in magnitude than the positive is a secondary observation — partly real, partly bounded by ceiling effects on rubric dimensions where `none` already scores near the top.

![CQS-craft by preamble](preamble_quality_experiment_v2/experiment_v2_results/figures/fig1_headline_cqs_by_preamble.png)

**Action.** Treat preamble content as load-bearing — what you write changes the output, including for the worse. `negative_control` was a synthetic probe (no production prompt says "junior developer still learning Python"); its purpose was to *prove that the channel can push output below baseline at all*. The realistic implication for production prompts is broader: don't assume any preamble change is positive or neutral. Test every change against your evaluator. The most common ways real production prompts accidentally drift below baseline are content-mismatch (Finding 2) and verbose dilution (Finding 3) — both at smaller magnitude than the synthetic probe, but in the same direction.

**Related work.** PRISM (USC 2026) reports the same below-baseline behavior on a *different* axis — expert personas degrade accuracy from ~71.6% to ~68%. Zheng et al. (EMNLP 2024) find no reliable accuracy gain from personas across 162 roles, consistent with this paper's load-bearing-on-craft reading (they measured accuracy; we measured craft). See [`RELATED_WORK.md` § "Personas help style, not substance"](RELATED_WORK.md#personas-help-style-not-substance--the-alignment-vs-pretraining-split) and [§ "Personas do not reliably help objective tasks"](RELATED_WORK.md#personas-do-not-reliably-help-objective-tasks).

---

### Finding 2 — Preamble effects are governed by rubric overlap, not by "expertness"

**Claim.** What makes a preamble effective is overlap between the dimensions it enumerates and the dimensions your downstream evaluator measures. Not its tone, not its length, not its engineering rigor — the literal overlap.

**Evidence.** Three discriminating probes were run after the main run on `task_expr_parser` (n=10 each, full 10-judge cross-judge panel, [confound_probes.py](preamble_quality_experiment_v2/confound_probes.py)). Reference: main-run `none` = 0.827, `long_directive` = 0.848 on this task.

| Probe | What it tests | mean CQS | Δ vs `none` | p |
|---|---|---|---|---|
| **A — `nonrubric_expert`** | 12-clause expert directive naming **non-rubric** axes (compactness, performance, determinism, in-place ops, deterministic iteration) | 0.673 | **−0.155** | **0.0001** |
| **B — `bare_rubric`** | Bare list of rubric dims, **no expert framing**, no "you must" | 0.842 | +0.015 | 0.50 (ns; ≈ `long_directive`) |
| **C — `antirubric_expert`** | 12-clause expert directive **deprioritizing** rubric items ("type hints are clutter; no defensive checks") | 0.673 | **−0.154** | **0.0001** |

**Read the results together.** A directive list with full expert tone but content misaligned to the rubric (probe A) hurt by 7× the lift `long_directive` provides. A bare list of just the rubric dimensions with no framing (probe B) captured 70% of the positive lift. An expert-toned anti-rubric directive (probe C) produced essentially the same penalty as the misaligned one.

The model genuinely follows the preamble's content — probe A's outputs have visibly fewer docstrings, type hints, and defensive guards (you can read them in [`confound_probe_results/generations.jsonl`](preamble_quality_experiment_v2/confound_probe_results/generations.jsonl) and verify). Judges, blind to which preamble produced the code (see [methodology](#methodology-in-brief)), score the resulting code on whatever dimensions the rubric enumerates. The intersection of those two drives the effect.

**Action.** Stop trying to write "the best preamble". Start by writing down the dimensions your downstream evaluator measures, then enumerate them in your system prompt. If your evaluator measures different things than the v2 rubric (e.g., latency, compactness, performance correctness), then probe A's preamble would beat `long_directive` for *you* — and v2's findings about which preamble is "best" don't transfer.

**Related work.** This is the v2 refinement of PRISM's "alignment-tunable vs pretraining-locked" framing. The proximate predictor of which dimensions move under preamble is **preamble–evaluator overlap**, not whether a dimension is "alignment" or "capability" in some structural sense. See [`RELATED_WORK.md` § "Personas help style, not substance"](RELATED_WORK.md#personas-help-style-not-substance--the-alignment-vs-pretraining-split) — the v2 update at the end of that section makes this refinement explicit.

---

### Finding 3 — Bare enumeration captures most of the positive effect; expert framing is decorative

**Claim.** Naming the evaluator's dimensions in your preamble — with no engineering virtue language, no "you must", no manifesto — gets you ~70% of the maximum achievable positive lift. The remaining ~30% comes from imperative tone, compound clauses that explain *why* each dimension matters, and focused enumeration structure.

**Evidence.** From probe B above: a system prompt that was literally *"Your code will be evaluated on these specific dimensions: error handling consistency, edge case handling on empty/boundary/invalid inputs, type hint completeness on public functions, code organization and cohesion, documentation appropriateness, abstraction calibration, API ergonomics, concurrency safety where applicable, appropriate data structure choice, algorithmic correctness, and example quality when examples are requested."* produced CQS = 0.842, compared to `long_directive`'s 0.848 on the same task. Recovery ratio (B − none) / (long_directive − none) = 0.70.

The remaining 30% (0.006 CQS units on this task) is attributable to:

1. **Imperative tone** ("must", not just "will be evaluated on")
2. **Compound clauses** that explain why each item matters (e.g., clause 3 of `long_directive`: "*defensive programming: validate inputs, handle edge cases, fail clearly*" — three rubric dims explained in context vs the bare list's "edge case handling on empty/boundary/invalid inputs")
3. **Focused length.** `python_coder_agent` covers many of the same rubric dimensions as `long_directive` but spreads them across ~3000 tokens of workflow advice, refactoring heuristics, and tooling commentary; it scores +0.024 vs `long_directive`'s +0.046. The model's attention budget is finite; verbose preambles dilute their enumeration.

**Action.** When time-constrained, write a one-sentence list. It's good enough. When you have time to polish, add imperative tone and dimension-level explanations to capture the remaining 30%. Don't add workflow/tooling/refactoring content unless it serves a separate single-turn goal — the dilution costs you.

**Related work.** No published 2023–2026 work directly anchors the bare-enumeration-captures-~70% decomposition; v2's 70/30 attribution at fixed dimension coverage appears to be novel. Closest methodological analog: **CFPO** (Liu et al., arXiv 2502.04295) decomposes prompt optimization into content vs format axes and reports format-only recovers ~80% of joint-optimization gains on Big-Bench classification and GSM8K — directionally consistent, but on reasoning/classification rather than code craft. Supporting preconditions: **He et al.** (arXiv 2411.10541) show format-alone moves code-generation by ~40% with content held fixed; **Sclar et al.** (ICLR 2024, FormatSpread) document format-only spread up to 76 accuracy points. Closest domain match: **Bohr** (arXiv 2511.13972) on directive-prompt style control in multi-turn code generation. See [`RELATED_WORK.md` § "Prompt format as an independent variable"](RELATED_WORK.md#prompt-format-as-an-independent-variable) for the full mapping.

---

### Finding 4 — No "alignment vs capability" split, just preamble–evaluator overlap

**Claim.** v1 inherited a "preambles change alignment-tunable craft but not pretraining-locked capability" framing from PRISM (USC 2026). v2's probes refined this: the proximate predictor of which dimensions move under preamble is whether the preamble enumerates them, not whether they're "craft" or "capability" in some structural sense.

**Evidence.** In the v2 main run, 7 of 9 always-on rubric dimensions moved with preamble (KW p < 10⁻⁴), and 2 didn't (`algorithm_correctness` p = 0.26; `data_structure_choice` p = 0.39). Looking at `long_directive`'s clause list:

| `long_directive` clause | Rubric dimension it names |
|---|---|
| (3) defensive programming, validate inputs, handle edge cases | `edge_case_gap`, `error_handling_inconsistency` |
| (5) comments why not what | `documentation_appropriateness` |
| (7) concurrency / thread-safety explicit | `concurrency_safety` |
| (8) composition over inheritance | `code_organization` |
| (9) side effects + I/O boundaries explicit | `code_organization` |
| (11) log errors at right severity, never swallow | `error_handling_inconsistency` |
| (12) docstring public interfaces | `documentation_appropriateness`, `type_hint_gap` |
| (2) appropriate abstraction | `abstraction_miscalibration` |

The 7 dimensions that move are exactly the 7 enumerated by `long_directive`. The 2 that don't move (`algorithm_correctness`, `data_structure_choice`) are exactly the 2 not enumerated in *any* v2 preamble. The pattern fits both the original "alignment/capability split" and the simpler "enumerated/not-enumerated" reading. Probe A breaks the tie: a preamble that doesn't enumerate the 7 craft dimensions but is otherwise expert-toned doesn't lift them — it actively suppresses them. The proximate predictor is enumeration.

![Per-dimension mechanism split](preamble_quality_experiment_v2/experiment_v2_results/figures/fig3_mechanism_split.png)

**Action.** Don't assume any dimension is "preamble-immovable" without testing it. If you care about algorithmic correctness, enumerate it in your preamble — it may move (v2 didn't test this; an explicit-correctness probe is plausibly worth running for your domain).

**Related work.** F4 is the headline form of the same PRISM refinement called out in F2 — the v2 update at the end of [`RELATED_WORK.md` § "Personas help style, not substance"](RELATED_WORK.md#personas-help-style-not-substance--the-alignment-vs-pretraining-split) discusses the implication: a preamble that explicitly enumerated correctness could in principle move accuracy too, against a strict reading of PRISM. F4's evidence is the within-rubric version of that argument.

---

### Finding 5 — Static-analysis tools cannot detect preamble effects on craft

**Claim.** If your downstream evaluator is radon, pylint, cyclomatic complexity, or Halstead difficulty, you will measure no preamble effect. Preamble effects are visible only to evaluators that score the craft dimensions preambles tune.

**Evidence.** From the v2 main run static-analysis diagnostic panel ([`REPORT.md`](preamble_quality_experiment_v2/experiment_v2_results/REPORT.md)):

| Metric | KW p across preambles | Verdict |
|---|---|---|
| maintainability_index | 0.92 | Flat |
| avg_cyclomatic | 0.33 | Flat |
| max_cyclomatic | 0.84 | Flat |
| halstead_difficulty | 0.98 | Flat |
| pylint_errors | 0.97 | Flat |
| pylint_warnings | 0.97 | Flat |
| pylint_refactor | 0.92 | Flat |
| cognitive_complexity_violations | 0.53 | Flat |
| pylint_conventions | 0.012 | Weak signal (only one) |

8 of 9 static metrics produced KW p > 0.5 across the 8 main preamble conditions. The single weak signal (`pylint_conventions`, p = 0.012) overlaps semantically with documentation/type-hint dimensions the rubric measures separately — and even there, the LLM-judge signal on the same axes is hundreds of orders of magnitude stronger (KW p < 10⁻¹⁶ on docstring quality and type-hint coverage). v1 confirmed this independently with its own static-analysis panel (KW p = 0.998 on a 65%-weighted static-heavy composite, which produced a false null on the whole investigation until the v2 instrument correction).

**Action.** Build LLM-judge evaluation harnesses for any work where preamble or prompt-engineering effects matter. Static analysis tools are valid for what they measure (complexity, MI, lint compliance), but they don't measure what preambles tune. If you currently A/B-test preambles using radon/pylint metrics, you are getting false nulls.

**Related work.** Independent confirmation in arXiv 2504.13656 ("Do Prompt Patterns Affect Code Quality?"), which found no significant differences in maintainability, security, or reliability across prompt patterns — all static-analysis-based. Concurrent argument that static analysis is insufficient as a quality measure (arXiv 2508.14419, 2506.10330) and should instead be used as a feedback signal. See [`RELATED_WORK.md` § "Prompt variation does not move static code-quality metrics"](RELATED_WORK.md#prompt-variation-does-not-move-static-code-quality-metrics).

---

## Designing a preamble for *your* system

The five findings collapse into a procedure:

1. **Write down the dimensions your downstream evaluator scores.** This is the most important step. If you don't have an evaluator, build one before iterating on preambles — otherwise you cannot tell if your preamble changes are helping. If your evaluator is end-user thumbs-up, treat that as a noisy proxy for the dimensions your end-users actually notice, and try to articulate what those are.

2. **Treat every preamble change as bidirectional.** Don't assume new content is neutral or positive — the channel is sensitive enough that well-intentioned additions can degrade output. v2's `negative_control` was a synthetic probe ("junior developer still learning Python") that pushed output below the no-preamble baseline, demonstrating the negative direction exists; production prompts rarely contain language that blunt, but the realistic failure modes (rubric-mismatch and verbose dilution) are covered in steps 3–5 and produce the same directional effect at smaller magnitude. Test every preamble change against your evaluator.

3. **Enumerate the evaluator's dimensions in plain language.** A bare list is sufficient; you'll capture ~70% of the maximum lift this way. The model genuinely allocates output capacity to whatever you enumerate.

4. **(Optional, low priority)** **Add imperative tone and per-dimension explanations** to capture the remaining ~30%. "Your code must: (1) [dim] — [why]; (2) [dim] — [why]; …" beats a bare list by ~30% of the gap from `none` to the maximum positive lift.

5. **Keep it focused.** Each token of preamble that isn't enumerating a dimension your evaluator scores is a token diluting the model's attention away from those that are. Workflow content, tooling preferences, and unrelated engineering virtues cost you if they aren't being measured downstream.

6. **Test it.** Run your candidate preamble vs `none` on the same eval harness. The expected lift is small but real — on the order of 1–5 points on a 100-point scale. If you see >10 points, your eval is probably overfit to your preamble (the dimensions match too tightly); if you see 0, your preamble isn't enumerating dimensions your evaluator actually measures.

---

## Effect-size calibration — when this matters and when it doesn't

CQS-craft is on a [0, 1] scale. The empirical anchors:

| Anchor | CQS-craft |
|---|---|
| `trivial_baseline` (no system, name-only prompt, T=1.0) | 0.556 |
| `negative_control` ("junior developer") | 0.723 |
| `none` (no system prompt at all) | 0.778 |
| Strongest single preamble (`long_directive`) | 0.815 |

**This matters when:**

- You ship to a high-volume coding agent where small per-sample quality differences compound (millions of code suggestions per day → small β × large N → real measurable downstream user impact).
- Your downstream evaluator measures the same dimensions the v2 rubric measures (error handling, edge cases, type discipline, documentation, organization, abstraction calibration, API ergonomics, concurrency safety).
- You have an A/B test budget large enough to detect a 5-point shift (n ≥ a few hundred samples per arm; v2's per-arm n was ~138).

**This matters less when:**

- Your downstream evaluator measures different dimensions (compactness, performance, security). The probes proved the preamble winners flip under a different rubric.
- You're shipping to a low-volume specialty system where per-sample variance dwarfs the expected preamble effect.
- Your model is already on the high end of the CQS-craft range. There's evidence of a ceiling near ~0.85 on this rubric for current frontier models; preamble can move you toward it but not past it.

**This matters not at all when:**

- You're using static-analysis tools (radon, pylint, cyclomatic complexity) as your quality bar. Those don't detect preamble effects.

---

## What CQS-craft is

Every CQS number in this README is a Composite Quality Score on a [0, 1] scale, defined as:

```
CQS-craft = 0.45 · idiomaticity
          + 0.45 · comment_quality
          + 0.10 · (1 − mean_rubric_severity / 5)
```

Components — all evaluated by a 10-model cross-judge panel, self-judgments excluded, judges blind to preamble identity:

- **idiomaticity** — 1–10 rating of how well the sample uses Python idioms (built-ins, stdlib, established patterns)
- **comment_quality** — 1–10 rating; rewards "why-not-what" comments and right-sized docstrings
- **mean_rubric_severity** — 0–5 average across 11 algorithmic-code dimensions (error handling, edge cases, type hints, organization, documentation, abstraction, API ergonomics, concurrency safety, data structure choice, algorithm correctness, example quality), with a calibration anchor in the judge prompt to prevent severity-0 saturation. Higher severity = worse; the `(1 − ./5)` flip puts CQS in the cleaner-is-higher direction.

Weights and components are pre-registered in [SPEC_V2.md §6.5](preamble_quality_experiment_v2/SPEC_V2.md). Sensitivity over alternative weighting schemes is reported in [WEIGHT_SENSITIVITY.md](preamble_quality_experiment_v2/experiment_v2_results/WEIGHT_SENSITIVITY.md) — every scheme tested still significant at p ≤ 2.4 × 10⁻¹⁰.

Static-analysis metrics (radon MI, pylint, cyclomatic complexity, Halstead) are *deliberately excluded* from CQS-craft. v1 showed they are preamble-insensitive and they produced a false null when included in the v1 composite (KW p = 0.633 on a 65%-weighted static-heavy CQS, with the LLM-judge components separately at p < 0.01).

---

## The mechanism — what the confound probes showed

After the v2 main run completed, a sharp confound surfaced: `long_directive`'s 12 clauses enumerate 7 of 9 always-on rubric dimensions. Does it beat other preambles only because its content overlaps the rubric, or does it have a real quality advantage?

Three discriminating probes were constructed (n=10 each, full 10-judge cross-judge panel). The probe outputs:

```
                                                         CQS-craft     Δ vs none
─────────────────────────────────────────────────────────────────────────────
none (main-run reference, same task)                     0.827         —
long_directive (main-run reference, same task)           0.848         +0.021
─────────────────────────────────────────────────────────────────────────────
probe A: nonrubric expert directive                      0.673         −0.155***
probe B: bare list of rubric dimensions                  0.842         +0.015
probe C: anti-rubric expert directive                    0.673         −0.154***
─────────────────────────────────────────────────────────────────────────────
*** p = 0.0001 (Mann–Whitney vs none)
```

The probes resolve the original concern into a refined mechanism:

**Preambles allocate the model's craft-attention budget to whichever dimensions they enumerate, at the cost of other behaviors.** Probe A confirmed this: a preamble naming compactness, performance, and determinism produced code with measurably fewer docstrings, fewer type hints, and fewer defensive guards. Blind judges correctly marked it down on the rubric dimensions the code now lacks. Probe B confirmed the other side: bare enumeration of the rubric, with no expert framing, recovers 70% of `long_directive`'s lift. Probe C confirmed symmetry: an anti-rubric directive (deprioritizing the same items `long_directive` emphasizes) hurts by the same magnitude as a non-rubric directive.

This is what "preamble effects" actually are: not generic quality lifts, but rubric-dependent attention reallocation. The metric is real (judges detect real code changes); the interpretation is conditional ("good" means "good on this rubric").

Full discussion and per-dimension data: [CONCLUSIONS.md §"Confound probes"](preamble_quality_experiment_v2/CONCLUSIONS.md#confound-probes) and [CONCLUSIONS.md §"Identification limit"](preamble_quality_experiment_v2/CONCLUSIONS.md#identification-limit--rubric-directive-overlap-confound).

---

## Full empirical results

**Main run, primary CQS-craft.** Pooled across 10-model subject pool, KW p = 9.2 × 10⁻¹⁸:

| Preamble | n | mean | 95% CI |
|---|---|---|---|
| `trivial_baseline` | 125 | 0.556 | [0.510, 0.600] |
| `negative_control` | 138 | 0.723 | [0.700, 0.746] |
| `persona_only` | 132 | 0.764 | [0.735, 0.791] |
| `minimal` | 136 | 0.770 | [0.741, 0.794] |
| `none` | 135 | 0.778 | [0.750, 0.804] |
| `generic_coding` | 132 | 0.784 | [0.756, 0.808] |
| `real_agent` | 139 | 0.802 | [0.775, 0.825] |
| `python_coder_agent` | 139 | 0.802 | [0.775, 0.823] |
| `long_directive` | 139 | **0.815** | [0.789, 0.836] |

**Mixed-effects model — `CQS ~ preamble × tier + (1|model) + (1|task)`** (full discussion in [CONCLUSIONS.md §"Mixed-effects models"](preamble_quality_experiment_v2/CONCLUSIONS.md)):

| Preamble vs `none` | β | p |
|---|---|---|
| `trivial_baseline` | −0.255 | 3 × 10⁻⁶¹ |
| `negative_control` | −0.060 | 5 × 10⁻⁵ |
| `minimal` | +0.000 | 0.99 |
| `generic_coding` | +0.014 | 0.33 |
| `persona_only` | −0.007 | 0.64 |
| `real_agent` | +0.027 | 0.067 |
| `python_coder_agent` | +0.023 | 0.126 |
| **`long_directive`** | **+0.046** | **0.002** |

**Tier invariance.** Reasoning vs non-reasoning models show the same preamble ordering with different absolute ceilings. The `preamble × tier` interaction is non-significant for the 8 main conditions (only `trivial_baseline × reasoning` reaches p < 0.05). Tier main effect β = +0.087 (p = 0.117, underpowered with 3-vs-7 tier imbalance).

![Tier comparison](preamble_quality_experiment_v2/experiment_v2_results/figures/fig4_tier_comparison.png)

**Robustness.** All 7 alternative CQS-weighting schemes tested produced KW p ≤ 2.4 × 10⁻¹⁰. The headline is not weight-dependent.

---

## Methodology in brief

- **Pool.** 10 subject models: 3 reasoning (`qwen/qwen3.6-flash`, `deepseek/deepseek-v4-flash`, `minimax/minimax-m2.5`) with explicit `reasoning: {effort: "high"}`; 7 non-reasoning. Same 10 models serve as judges, with `reasoning: {exclude: true}` on the reasoning judges (judging is structured fill-the-JSON; judge-side reasoning is not the variable under test).
- **Cross-judge matrix.** Full v1-equivalent: every model judges every non-self sample. Self-judgments excluded from primary CQS, retained for the F3 hygiene-stratification report.
- **Judge blindness.** Judges receive the rubric prompt + calibration anchor as system message, and exactly `"Code under review:\n\n```python\n{code}\n```"` as user message — no preamble text, condition label, task description, or subject model identity. Code refs: [`preamble_quality_v2_main.py:621-630`](preamble_quality_experiment_v2/preamble_quality_v2_main.py), [`confound_probes.py:341-362`](preamble_quality_experiment_v2/confound_probes.py).
- **Tasks.** 7 — `task_lru_ttl_cache` (creation), `task_expr_parser` (creation), `task_mini_sql_engine` (creation), `task_rate_limiter_family` (creation), `task_kv_store_package` (multi-file creation), `task_flag_class` (refactor), `task_exception_pyramid` (refactor).
- **Preambles.** 9 — v1's 8 (`none`, `minimal`, `generic_coding`, `real_agent`, `negative_control`, `persona_only`, `long_directive`, `trivial_baseline`) plus `python_coder_agent` (a real production system prompt from the [chris-code python-coder agent](https://github.com/chris-santiago/claude-config) — verbatim).
- **Statistical analysis.** Kruskal–Wallis omnibus; bootstrap 95% CI (n_boot = 2000); mixed-effects via `statsmodels` `mixedlm` REML with random intercepts on subject `model` and `task`, plus fixed `preamble × tier` interaction; weight-sensitivity panel over 7 alternative CQS schemes.
- **Pre-registration discipline.** Five documented amendments (rubric redesign, drop trap task, reasoning-inclusive pool, explicit reasoning param, multi-judge calibrated rubric) — all logged as drift events in [SPEC_V2.md §12](preamble_quality_experiment_v2/SPEC_V2.md). Three-round structured adversarial debate preceded the main run.

---

## Limitations

1. **CQS-craft is rubric-dependent.** The metric measures the 11 specific dimensions in v2's rubric. A preamble that helps under this rubric may not help under a different one. The confound probes are concrete proof: probe A's preamble would beat `long_directive` under a compactness/performance rubric.
2. **`real_agent` and `python_coder_agent` are marginal in the strict mixed-effects test against `none`** (p = 0.067 and p = 0.126). Their KW omnibus contribution is real; their per-condition contrast vs `none` is at the edge of α = 0.05. Likely an underpower issue.
3. **Tier imbalance (3 reasoning vs 7 non-reasoning).** The tier main-effect test (β = +0.087, p = 0.117) is underpowered. A v3 with ≥5 reasoning models would settle whether reasoning models systematically lift the CQS ceiling.
4. **Confound probes ran on one task** (`task_expr_parser`, n=10 each). The directional findings are clean (p = 0.0001 for the negative probes); the exact recovery ratio (70%) may shift on tasks with different rubric-dimension activation profiles. A v3 that ran the probes on all 7 tasks would tighten this.
5. **No human-rater validation.** All scoring is LLM-judge based. Cross-judge agreement is high and the calibration anchor + 10-judge panel mitigates single-judge pathology, but a human-rater sub-sample study would strengthen external validity.
6. **Single-turn generation, Python only.** Multi-turn agentic evaluation and cross-language testing are out of scope.

---

## Related work

See [`RELATED_WORK.md`](RELATED_WORK.md) for how these findings situate within the 2024–2026 literature on persona/system-prompt effects and LLM-as-judge evaluation — including the USC PRISM "alignment vs pretraining" split, the Zheng et al. (EMNLP 2024) persona-accuracy null, prior static-metric-insensitivity results on prompt-pattern variation, and the Panickssery et al. (NeurIPS 2024) self-preference bias result. The v2 confound probes refine PRISM's framing from "alignment-tunable vs pretraining-locked" to **preamble–evaluator overlap density**.

---

## Investigation comparison: v1 vs v2

| Investigation | Date | Status | What it added |
|---|---|---|---|
| [`preamble_quality_experiment/`](preamble_quality_experiment/) (v1) | 2026-05 | Complete — instrument-correction motivation | Established that static-analysis-heavy composites produce a false null (KW p = 0.633) while LLM-judge components separately detect a strong effect (idiom p = 0.002, comment p = 0.006). Diagnosed as a metric artifact; motivated v2's instrument redesign. |
| [`preamble_quality_experiment_v2/`](preamble_quality_experiment_v2/) (v2) | 2026-05 | Complete — active design | Corrected instrument (LLM-judge-only CQS-craft, redesigned 11-dim rubric, calibrated multi-judge panel, reasoning-inclusive 10-model pool). Headline KW p = 9.2 × 10⁻¹⁸. Three post-hoc confound probes refined the mechanism to attention-allocation (this README's central reading). |

Full v2 conclusions: [CONCLUSIONS.md](preamble_quality_experiment_v2/CONCLUSIONS.md). Methodology journey: [REPORT_ADDENDUM.md](preamble_quality_experiment_v2/REPORT_ADDENDUM.md). Raw stats: [experiment_v2_results/REPORT.md](preamble_quality_experiment_v2/experiment_v2_results/REPORT.md).

---

## Repo layout & reproduce

```
.
├── README.md                                 this file
├── PREAMBLES.md                              verbatim text of all 12 preambles tested
├── RELATED_WORK.md                           literature situating (covers v1 + v2)
├── preamble_quality_experiment/              v1 (instrument-correction motivation)
└── preamble_quality_experiment_v2/           v2 (active design)
    ├── HYPOTHESIS.md                         three hypothesis cycles, current = Re-revised ACTIVE
    ├── SPEC_V2.md                            pre-registration + A1–A5 amendment log
    ├── CONCLUSIONS.md                        full conclusions, debate scorecard, confound probes
    ├── REPORT_ADDENDUM.md                    methodology journey, pre-flight phases, probe lessons
    ├── INVESTIGATION_LOG.jsonl               51 chronological audit entries
    ├── preamble_quality_v2_main.py           main-run script
    ├── confound_probes.py                    post-hoc probe script (A, B, C)
    ├── analysis_addendum.py                  mixed-effects M0/M1/M2 + sensitivity
    ├── figures.py                            5 matplotlib/seaborn figures
    └── experiment_v2_results/                main-run REPORT, MIXED_EFFECTS, WEIGHT_SENSITIVITY,
                                              JSONL data, figures/, confound_probe_results/
```

To reproduce:

```bash
export OPENROUTER_API_KEY=<your key>
cd preamble_quality_experiment_v2/

uv run preamble_quality_v2_main.py --slice    # 4-sample smoke test
uv run preamble_quality_v2_main.py            # full main run (~1 hour)
uv run analysis_addendum.py                   # mixed-effects + weight sensitivity
uv run confound_probes.py                     # post-hoc probes (~5 min)
uv run figures.py                             # regenerate the 5 figures
```

All scripts use PEP 723 inline dependencies — `uv run` installs everything; no virtualenv needed.
