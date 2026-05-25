# Related Work

How this experiment's findings situate within the 2024–2026 literature on
persona/system-prompt effects and LLM-as-judge evaluation. The short version: our
results are consistent with an emerging consensus that personas shape *how* a model
writes (alignment-dependent style) far more than *whether* its output is correct
(pretraining-dependent substance) — and we add a concrete demonstration that the
choice of measurement instrument determines whether the effect is visible at all.

## Personas help style, not substance — the alignment-vs-pretraining split

The most directly relevant work is the USC PRISM study, **"Expert Personas Improve
LLM Alignment but Damage Accuracy"** (arXiv 2603.18507, 2026). It argues that LLMs
acquire two kinds of capability that personas affect oppositely:

- **Alignment-dependent qualities** (style, tone, formatting, intent-following),
  shaped during instruction-tuning — *improved* by personas.
- **Pretraining-dependent abilities** (coding correctness, math) — *harmed* by
  expert personas; they report overall accuracy falling from ~71.6% to ~68% under
  an expert persona.

This split predicts our result precisely. Our LLM-judged dimensions — idiomaticity
and comment quality — are alignment-dependent style, and showed a significant
preamble effect (KW p = 0.0022 and 0.0058). Our static-analysis components are
correctness/structure-adjacent (pretraining-dependent) and were flat (p ≈ 0.998).
We reproduced their split independently, via a metric decomposition rather than an
accuracy benchmark.

- USC PRISM paper: https://arxiv.org/html/2603.18507v1
- Press coverage (The Register): https://www.theregister.com/2026/03/24/ai_models_persona_prompting/

## Personas do not reliably help objective tasks

Zheng et al., **"When 'A Helpful Assistant' Is Not Really Helpful: Personas in
System Prompts Do Not Improve Performances of Large Language Models"** (EMNLP
Findings 2024), tested 162 roles across 2,410 factual questions and found no
reliable accuracy gain from adding a persona; the per-question effect was "largely
random," and automated best-persona selection was no better than chance.

This matches our observation that the `none`, `minimal`, and `generic_coding`
conditions are statistically indistinguishable on the objective (static) measures.

- https://aclanthology.org/2024.findings-emnlp.888/ · https://arxiv.org/abs/2311.10054

## Prompt variation does not move static code-quality metrics

**"Do Prompt Patterns Affect Code Quality? A First Empirical Assessment of
ChatGPT-Generated Code"** (arXiv 2504.13656) found no significant differences in
maintainability, security, or reliability across prompt patterns — all
static-analysis-based metrics.

This is independent confirmation of our central methodological finding: static
analysis (radon MI, complexity, pylint) is insensitive to prompt/preamble variation
(our static_score: p = 0.998). A related line of work argues static metrics alone
are insufficient for assessing code quality "beyond correctness" and propose using
static analysis as a *feedback* signal rather than a *quality* measure
(arXiv 2508.14419, 2506.10330).

- https://arxiv.org/pdf/2504.13656
- https://arxiv.org/pdf/2508.14419 · https://arxiv.org/html/2506.10330

## Self-preference bias in LLM-as-judge

Panickssery et al., **"LLM Evaluators Recognize and Favor Their Own Generations"**
(NeurIPS 2024), show LLM judges favor their own outputs, with bias strength linearly
correlated with self-recognition ability — a documented threat to LLM-as-judge
pipelines.

We tested this directly (finding F3): the self-vs-cross idiomaticity delta was 0.36
on a 10-point scale (Cohen's d = 0.16, Mann–Whitney p = 0.13) — present but
negligible in our setup, and our primary scores already excluded self-judgments. The
literature indicates the effect can be substantial in other settings, so our small
result is plausibly model/task-dependent; the cross-judge-only design was the
appropriate precaution regardless.

- https://arxiv.org/abs/2404.13076

## Most code-prompting work measures correctness, not craft

Persona/prompt studies in the code domain typically evaluate functional correctness
(`pass@k`) on benchmarks like MBPP/APPS/HumanEval rather than craft dimensions. For
example, **"Personality-Guided Code Generation Using Large Language Models"** (arXiv
2411.00006) injects MBTI/Big-Five personas but evaluates only pass@1/pass@5. Work on
how prompt *attributes* (e.g. gender cues) shape both generated code and its
evaluation is beginning to appear (arXiv 2603.24359), but the craft axis remains
under-measured.

- https://arxiv.org/pdf/2411.00006 · https://arxiv.org/pdf/2603.24359

## Prompt format as an independent variable

A line of work adjacent to v2's "bare enumeration captures ~70% of the
positive lift" finding ([`README.md` Finding 3](README.md)) asks the broader
question of **format-at-fixed-content** as a controlled prompt variable.

- **Liu et al., "Beyond Prompt Content: Enhancing LLM Performance via
  Content-Format Integrated Prompt Optimization" (CFPO)** — arXiv 2502.04295,
  Feb 2025. Runs a true content-vs-format ablation. Format-only optimization
  recovers a sizable fraction of joint-optimization gains: on Big-Bench
  Classification, ~83–86% of joint; on GSM8K, ~52–77% of joint
  (Llama3.1 / Llama3-Instruct). Directionally consistent with v2's ~70%
  finding, but on reasoning/classification rather than code craft, and
  "format" includes renderer structure (Question-Answer, Instruction-Response,
  MultiChoice_QA) rather than specifically enumeration vs prose.
- **He et al., "Does Prompt Formatting Have Any Impact on LLM Performance?"**
  — arXiv 2411.10541, Nov 2024. Holds prompt content fixed and varies only
  formatting (plain text, Markdown, JSON, YAML). Code-translation
  performance on GPT-3.5-turbo varies by ~40% across formats; HumanEval shows
  up to a 2× shift between Markdown and plain text. Establishes the
  precondition for any format-vs-content decomposition: format alone moves
  code-generation output substantially. Measures pass@1, not craft.
- **Sclar et al., "Quantifying Language Models' Sensitivity to Spurious
  Features in Prompt Design" (FormatSpread)** — ICLR 2024 (arXiv 2310.11324).
  Atomic perturbations of separators, casing, item formatting, and item
  ordering on few-shot prompts. Reports accuracy spreads up to 76 points
  across format-only variations. The canonical "format brittleness" result;
  documents brittleness rather than decomposing enumeration effect-size.
- **Bohr, "Show and Tell: Prompt Strategies for Style Control in Multi-Turn
  LLM Code Generation"** — arXiv 2511.13972, Nov 2025. N=160 paired
  two-turn Python sessions on Gemini 2.5 Pro across Control / Examples /
  Instructions / Combined conditions. Measures style outcomes (compression
  discipline, defensive ratios, documentation density) independent of
  correctness. Closest domain match for v2 (code craft under directive
  preambles), but does not decompose directive form into enumeration vs
  imperative vs compound-clause components.

**Net.** None of these isolates v2's specific decomposition (bare
comma-separated list vs full imperative directive vs verbose prose on
code-craft scores at fixed dimension coverage). CFPO is the closest
methodological analog; He et al. and Sclar et al. establish that format
alone moves outputs substantially (preconditions for any decomposition
claim); Bohr is the closest domain match but does not subdivide directive
form. v2's 70/30 decomposition appears to be the first published
attribution of code-craft lift to enumeration form vs imperative-tone +
compound-clause structure at fixed dimension coverage.

- https://arxiv.org/abs/2502.04295 · https://arxiv.org/abs/2411.10541
- https://arxiv.org/abs/2310.11324 · https://arxiv.org/abs/2511.13972

## What this experiment contributes

1. **Craft-axis measurement.** We target the hard-to-judge dimensions (idiomaticity,
   comment quality, abstraction) rather than `pass@k`, populating exactly the
   alignment-dependent axis the PRISM split predicts should respond to personas.
2. **Static-vs-LLM-judge decomposition.** The literature holds the two pieces
   separately ("personas don't move static metrics"; "personas help style"). Our
   re-weighting gradient (composite p: 0.63 → 0.003 as static weight falls from
   0.65 to 0) shows *mechanically* how a static-heavy composite manufactures a false
   null — a concrete measurement-design cautionary result.
3. **Negative-control evidence.** Most studies ask "does an expert persona help?";
   we also show a deliberately low-status persona ("junior developer still learning")
   reliably produces the *worst* comment quality (−0.08 below the no-preamble
   baseline) — an underexplored direction.

## Caveats on the comparison

- The PRISM accuracy result and ours are not in tension: they measured correctness
  (harmed by expert personas), we measured craft (helped). Both follow from the same
  alignment-vs-pretraining split.
- All cited code-domain results, like ours, are predominantly single-turn
  generation. Whether persona/preamble effects on craft persist or compound over
  multi-turn agentic sessions is open across this literature.

> **Update from v2 (`preamble_quality_experiment_v2/`):** v2's three
> post-main-run confound probes (`CONCLUSIONS.md §"Confound probes"`)
> refined the "alignment vs pretraining" framing the v1 work invoked
> from PRISM. The probes showed that what governs whether a dimension
> moves under preamble is not "alignment-tunable vs pretraining-locked"
> per se, but **overlap between dimensions the preamble enumerates and
> dimensions the rubric/eval measures**. The PRISM accuracy null and the
> v1/v2 craft positive remain consistent with this refinement — accuracy
> wasn't enumerated by the personas PRISM tested, and craft (style,
> idiom, error handling) was — but the framing is sharper. A preamble
> that explicitly enumerated correctness ("write rigorously correct code;
> verify edge cases by symbolic reasoning before output") could in
> principle move accuracy too, contrary to a strict reading of PRISM. A
> preamble that explicitly enumerated *only* compactness can hurt craft
> by ~7× the lift a rubric-aligned preamble provides — v2 probe A.
