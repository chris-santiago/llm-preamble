## Hypothesis — Cycle 1

**Claim:** LLMs prompted with expert-level coding preambles produce code scoring measurably higher on a composite quality rubric than LLMs with no/minimal preamble, with the effect consistent across models and tasks — detectable as a statistically significant main effect of preamble condition after controlling for task variance.

**Mechanism:** Expert preambles prime the LLM to adopt an expert persona, activating higher-quality code generation patterns (lower cyclomatic complexity, better naming, defensive programming, appropriate abstraction) that would otherwise not be reliably elicited. The preamble acts as a distributional shifter: it constrains the model's output distribution toward the expert coding subdomain.

**Signal:** Measurable differences in static analysis metrics (Radon MI, cyclomatic complexity, Halstead volume, pylint scores, AST-derived quality indicators) and LLM-as-judge scores for dimensions that static tools cannot cover (idiomaticity, comment quality).

**Expected observable:** A statistically significant main effect of preamble condition on Composite Quality Score (CQS), with:
- Expert preamble CQS > No-preamble CQS across at least 5/8 models
- Spearman rank correlation of preamble conditions >= 0.6 across models (rank stability)
- Effect remains significant in a mixed-effects model controlling for model-identity and task fixed effects

## Evaluation Metrics

**Primary:** Composite Quality Score (CQS) — weighted average of 6 dimensions:
  - static_score (45%): Radon MI, cyclomatic complexity, Halstead volume, pylint message severity
  - ast_score (20%): bare except count, identifier entropy, nesting depth, class-to-function ratio
  - llm_idiom_score (20%): LLM-as-judge for idiomaticity (multi-model consensus)
  - llm_comment_score (15%): LLM-as-judge for comment quality (multi-model consensus)

**Secondary:** Preamble condition rank stability — Spearman rank correlation of per-model condition rankings across tasks (target: rho >= 0.6)

**Tertiary:** Maintainability Index (MI) — Radon-computed, reported separately as a standalone interpretable metric

**Domain:** preamble_quality
