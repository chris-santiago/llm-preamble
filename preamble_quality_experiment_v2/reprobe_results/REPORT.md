# Re-probe report: Phase C + Phase D2

**Generations:** 32/36 extracted; total cost $0.3473

## Phase C — anchored vs unanchored judge prompts (reasoning models)

- Pooled mean Δidiom (anch − unanch): +0.312
- Pooled mean Δcomment (anch − unanch): -0.031
- Trigger dims (|Δ| > 0.5): []
- **Decision: keep_unanchored**

### Per-model deltas

| Model | n | mean Δidiom | mean Δcomment | max |Δ| |
|-------|---|-------------|----------------|---------|
| `qwen/qwen3.6-flash` | 12 | +0.333 | -0.167 | 1.000 |
| `deepseek/deepseek-v4-flash` | 11 | +0.364 | +0.091 | 1.000 |
| `minimax/minimax-m2.5` | 9 | +0.222 | +0.000 | 1.000 |

## Phase D2 — prevalence audit of redesigned 11-dim rubric

- Samples scored: 32
- Always-on dims with non-zero rate ≥ 10%: **2/9**
- Gate (≥3 of 9 always-on at ≥10%): **fail_escalate**

### Per-dimension prevalence

| Dimension | kind | n | n_NA | n≥1 | rate≥1 | mean sev | median |
|-----------|------|---|------|-----|--------|----------|--------|
|   `data_structure_choice` | always | 32 | 0 | 0 | 0.0% | 0.00 | 0.00 |
|   `algorithm_correctness` | always | 32 | 0 | 0 | 0.0% | 0.00 | 0.00 |
| ✓ `error_handling_inconsistency` | always | 32 | 0 | 14 | 43.8% | 0.66 | 0.00 |
|   `api_ergonomics` | always | 32 | 0 | 2 | 6.2% | 0.06 | 0.00 |
|   `abstraction_miscalibration` | always | 32 | 0 | 0 | 0.0% | 0.00 | 0.00 |
|   `code_organization` | always | 32 | 0 | 0 | 0.0% | 0.00 | 0.00 |
|   `type_hint_gap` | always | 32 | 0 | 2 | 6.2% | 0.06 | 0.00 |
| ✓ `edge_case_gap` | always | 32 | 0 | 14 | 43.8% | 0.94 | 0.00 |
|   `documentation_appropriateness` | always | 32 | 0 | 0 | 0.0% | 0.00 | 0.00 |
|   `concurrency_safety` | conditional | 11 | 21 | 0 | 0.0% | 0.00 | 0.00 |
|   `example_quality` | conditional | 11 | 21 | 0 | 0.0% | 0.00 | 0.00 |