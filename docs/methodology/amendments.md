# Amendments to the pre-registration

The v2 design was amended five times during pre-flight (between Gate 1 plan construction and the main run). Each amendment is documented in [`SPEC_V2.md §12`](https://github.com/chrissantiago/llm-preamble/blob/main/preamble_quality_experiment_v2/SPEC_V2.md) under SPEC §7's "documented pre-registration drift event" provision. No amendments were filed after the main run began.

The amendments are summarized below in their pre-registration order (A1–A5), each with **trigger** (empirical discovery), **change** (what was modified), **justification** (why it preserves the hypothesis), and where it was applied.

See also: [Pre-registration](pre-registration.md), [Investigation logs](investigation-logs.md).

## A1 — Rubric redesign (2026-05-22, SPEC §6.4)

**Trigger.** Pre-flight Phase D prevalence audit (n=30 generations across the model pool) found **0 of 11 python-coder S3+ rubric dimensions active** on algorithmic LLM output. The original rubric encoded patterns that modern instruction-tuned LLMs essentially never produce on algorithmic tasks (`mode_flag_params`, `bare_except`, `dict_domain_data`, `swallowed_excepts`, etc.). Per-dimension Kruskal–Wallis tests would have been null by construction.

**Change.** Replaced the 14-dimension S3+ rubric with an 11-dimension algorithmic-code rubric targeting dimensions algorithmic code actually varies on: `data_structure_choice`, `algorithm_correctness`, `error_handling_inconsistency`, `api_ergonomics`, `abstraction_miscalibration`, `code_organization`, `type_hint_gap`, `edge_case_gap`, `documentation_appropriateness`, plus the conditional `concurrency_safety` and `example_quality`. The 0–5 severity scale, cross-judge panel, and role in CQS-craft are preserved — only the dimension set changes. The old rubric is preserved verbatim in SPEC §12 for the pre-registration record.

**Justification.** The instrument must measure dimensions the population varies on, otherwise the per-dimension secondary criterion is null by construction regardless of preamble effect. Applied to SPEC §6.4 and §6.5 (which now references the new rubric).

## A2 — Drop `task_modeflag_sort` (2026-05-22, SPEC §6.2)

**Trigger.** Pre-flight Phase B found the behavior-only mode-flag-sort specification yielded **0% baseline rate** of the `mode_flag_params` smell across all conditions. The behavior-only framing successfully refused to name the trap but in doing so eliminated the discriminative space — no condition produced the smell, so no condition can resist it.

**Change.** Task dropped. Total tasks 8 → 7. The behavior-only framing was the correct choice (naming the smell would have measured compliance with explicit instructions, not preamble effect); the test simply has no signal to read in this design.

**Justification.** Pre-registered branching recovery clause in the original SPEC §11 covered this contingency; no Gate 1 reopen required. Applied to SPEC §6.2.

## A3 — Pool macro-iteration to reasoning-inclusive (2026-05-22, SPEC §6.3)

**Trigger.** User methodological challenge during pre-flight: a non-reasoning-only pool answers a question of low practical relevance because agentic coding frameworks in production overwhelmingly use reasoning models.

**Change.** Pool expanded from 7 non-reasoning models to 10 models stratified across a 3-model reasoning tier (`qwen3.6-flash`, `deepseek-v4-flash`, `minimax-m2.5`) and a 7-model non-reasoning tier. Analysis is stratified by tier so v1's original question (preamble effects on non-reasoning models) is still answerable within the non-reasoning sub-pool, while the headline result speaks to the production-realistic regime.

**Justification.** Closes an external-validity gap. The earlier pool answered a question the user does not have. Stratified analysis preserves both questions. Applied to SPEC §6.3.

## A4 — Explicit `reasoning` parameter and provider logging (2026-05-22, SPEC §6.3)

**Trigger.** OpenRouter routing-variability audit during pre-flight discovered the same model identifier returns different reasoning behavior across calls — one call to `minimax/minimax-m2.5` returned 6,258 reasoning tokens; another returned 0. Source: upstream-provider routing variability not controlled by the model identifier alone.

**Change.** All reasoning-tier calls now pass `reasoning: {effort: "high"}` explicitly. `max_tokens` raised to 10,000 globally to cover reasoning + content budget for all observed model behaviors. The `provider` field returned by OpenRouter is persisted with each generation record to enable a post-hoc routing-variability audit if results show anomalous within-model variance.

**Justification.** Without the explicit parameter, the reasoning-tier label is not actually controlled — it becomes a stochastic property of OpenRouter's routing layer. Applied to SPEC §6.3.

## A5 — Multi-judge panel + calibration anchor on rubric prompt (2026-05-22, SPEC §6.4)

**Trigger.** Phase D2 re-probe with single judge (`gpt-4o-mini`) on the A1 11-dim rubric: 7 of 9 always-on dimensions saturated at severity=0 with positive-toned rationales ("well-organized", "appropriate"). Only `error_handling_inconsistency` (43.8%) and `edge_case_gap` (43.8%) surfaced variation. This is a single-judge calibration failure, not a rubric-design failure.

**Change.** Three coupled changes:

1. **Rubric scoring uses the full v1-equivalent cross-judge matrix** — all 10 models in the SPEC §6.3 pool serve as judges (`JUDGE_MODELS = ALL_MODELS`). Cross-judge mean severity is computed per `(sample, dimension)` over the 9 non-self judges. The v1 self-judgment-exclusion rule applies.
2. **Reasoning-tier judges run with `reasoning: {exclude: true}`** — judging is a structured fill-the-JSON task; subject-side reasoning is the variable under test, not judge-side. Keeps the judge instrument cost-bounded (~$120 vs ~$300 with reasoning enabled) and removes a confound (judge reasoning depth) v1 didn't have.
3. **Calibration anchor** added to the rubric judge prompt — explicit directive that "severity 0 means no detectable issue and should be uncommon; realistic algorithmic code typically has severity 1-2 on at least 3 of the 9 always-on dimensions". The full anchor text is preserved in `rejudge_phase_d2.py` and reproduced verbatim in the main-run script.

**Justification.** The instrument was the problem, not the dimensions. The full cross-judge matrix restores the v1 design that was already validated; the calibration anchor is the one prompt-level tweak the v1 instrument didn't have. Phase D2 re-probe with a 3-judge calibration panel passed all 9 of 9 always-on dimensions at the strict gate (panel mean ≥1.0 on ≥10% of samples) — verifying the change before the main run. Applied to SPEC §6.4.
