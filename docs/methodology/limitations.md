# Limitations

1. **CQS-craft is rubric-dependent.** The metric measures the 11 specific dimensions in v2's rubric. A preamble that helps under this rubric may not help under a different one. The confound probes are concrete proof: probe A's preamble would beat `long_directive` under a compactness/performance rubric.
2. **`real_agent` and `python_coder_agent` are marginal in the strict mixed-effects test against `none`** (p = 0.067 and p = 0.126). Their KW omnibus contribution is real; their per-condition contrast vs `none` is at the edge of α = 0.05. Likely an underpower issue.
3. **Tier imbalance (3 reasoning vs 7 non-reasoning).** The tier main-effect test (β = +0.087, p = 0.117) is underpowered. A v3 with ≥5 reasoning models would settle whether reasoning models systematically lift the CQS ceiling.
4. **Confound probes ran on one task** (`task_expr_parser`, n=10 each). The directional findings are clean (p = 0.0001 for the negative probes); the exact recovery ratio (70%) may shift on tasks with different rubric-dimension activation profiles. A v3 that ran the probes on all 7 tasks would tighten this.
5. **No human-rater validation.** All scoring is LLM-judge based. Cross-judge agreement is high and the calibration anchor + 10-judge panel mitigates single-judge pathology, but a human-rater sub-sample study would strengthen external validity.
6. **Single-turn generation, Python only.** Multi-turn agentic evaluation and cross-language testing are out of scope.
