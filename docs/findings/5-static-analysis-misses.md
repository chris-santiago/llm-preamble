# Finding 5 — Static-analysis tools cannot detect preamble effects on craft

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
