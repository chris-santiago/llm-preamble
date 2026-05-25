# Glossary

Short definitions for the recurring terms in this investigation. Each entry links to the reference page where the term is defined in full.

---

### CQS-craft

The v2 **Composite Quality Score (craft-only)**. A weighted bounded composite on `[0, 1]`:

```
CQS-craft = 0.45·(idiom/10) + 0.45·(comment/10) + 0.10·(1 − rubric_sev_mean/5)
```

Computed per sample after self-judgment exclusion. The headline statistic for the v2 main run. Pre-registered weights are `(0.45, 0.45, 0.10)`; the [weight-sensitivity](statistical-methods.md#weight-sensitivity) panel confirms the headline does not depend on this choice.

The "craft" qualifier marks the deliberate exclusion of static-analysis metrics — v1 showed those are flat across preambles, so they are reported only as a diagnostic panel.

---

### Rubric severity

The 0–5 graded measure that each [rubric](rubric.md) dimension is scored on. **Not** a present-vs-absent flag — see the [calibration anchor](rubric.md#severity-scale-calibration-anchor): severity 0 is reserved for "genuinely exemplary," severity 1–2 is the realistic baseline for most algorithmic code, severity 4–5 means "pervasive or material defect."

---

### Always-on dimension

A rubric dimension that is scored on **every** sample, regardless of task. Nine of the 11 rubric dimensions are always-on: `data_structure_choice`, `algorithm_correctness`, `error_handling_inconsistency`, `api_ergonomics`, `abstraction_miscalibration`, `code_organization`, `type_hint_gap`, `edge_case_gap`, `documentation_appropriateness`. See [rubric](rubric.md#always-on-9).

---

### Conditionally-N/A dimension

A rubric dimension that judges return `null` for when the dimension does not apply to the code or task. Two such dimensions in v2: `concurrency_safety` (null when the task does not involve concurrency) and `example_quality` (null when no examples are requested). N/A judgments are excluded from that judge's per-sample mean severity. See [rubric](rubric.md#conditionally-na-2).

---

### Rubric overlap density

The fraction of rubric dimensions that a preamble explicitly enumerates. `long_directive`'s 12 clauses name 7 of 9 always-on dimensions — a high overlap density — and the [confound probes](results-schema.md#confound_probe_resultsreportmd) show that this overlap drives most of its CQS lift over `none`. The refined v2 mechanism reads preamble effects as **proportional to preamble–rubric overlap density**, not to "expertness" or preamble length.

---

### Attention-allocation

The post-confound-probe reading of the v2 mechanism: preambles direct the model's finite craft-attention budget toward whatever dimensions they enumerate, at the cost of other behaviors. CQS-craft is real and reproducible, but rubric-dependent — a preamble's lift over `none` is proportional to the overlap between (what the preamble enumerates) and (what the rubric measures). See [Finding 2](../findings/2-overlap-not-expertness.md) and [CONCLUSIONS.md §"Refined hypothesis: H-attention-allocation"](https://github.com/chris-santiago/llm-preamble/blob/main/preamble_quality_experiment_v2/CONCLUSIONS.md).

---

### Self-judgment exclusion

The rule that a judgment is dropped from primary CQS whenever the judge model and subject model share a provider-prefix family (`model.split("/", 1)[0]`). So `deepseek/deepseek-v3.2` judged by `deepseek/deepseek-v4-flash` counts as a self-judgment even though they are different models. Self-judgments are retained in the dataset for the F3 self-vs-cross hygiene stratification report, but never enter the headline CQS. See [models](models.md#self-judgment-exclusion) and [judge protocol](judge-protocol.md#cross-judge-matrix).

---

### ETA (empirical-test-agreed verdict)

A debate-scorecard verdict used in the ml-lab investigation cycle: the critic and defender agree the question cannot be resolved by argument alone, so it is **deferred to an empirical pre-flight probe** whose outcome is binding. In v2, findings F2, F4, and F5 closed via ETA — the trap task was dropped after Phase B, the anchored-vs-unanchored prompt confound was resolved by a Phase C re-probe, and the rubric was redesigned after Phase D found 0/11 dimensions active on modern code. See [CONCLUSIONS.md §"Pre-flight debate scorecard"](https://github.com/chris-santiago/llm-preamble/blob/main/preamble_quality_experiment_v2/CONCLUSIONS.md).

---

### defense_wins

A debate-scorecard verdict: the defender's position prevailed at debate close without requiring an empirical probe. In v2, findings F3, F6, and F7 closed `defense_wins` — the v1 self-vs-cross protocol was preserved, and two minor design concerns were settled in debate.

---

### critique_wins

A debate-scorecard verdict: the critic's position prevailed at debate close without requiring an empirical probe. In v2, finding F1 closed `critique_wins` — the judge OOR-clamp bug was conceded by the defender at severity 9 (FATAL) and fixed before main run (drop-not-clip with a structured OOR log; main-run OOR rate = 0). See [CONCLUSIONS.md §"Pre-flight debate scorecard"](https://github.com/chris-santiago/llm-preamble/blob/main/preamble_quality_experiment_v2/CONCLUSIONS.md).
