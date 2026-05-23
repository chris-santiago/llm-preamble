# Phase D2 re-check: calibrated multi-judge panel

**Judge panel:** openai/gpt-4o-mini, deepseek/deepseek-v3.2, mistralai/mistral-small-2603 (cross-judge mean per sample)
**Samples scored:** 32
**Calibration anchor:** explicit "severity 0 is rare; default mid-scale" directive added to prompt.

## Gate decisions

- **Pre-registered gate** (panel mean ≥ 1.0 on ≥3 of 9 always-on dims): **pass** (9/9)
- Diagnostic loose (panel mean ≥ 0.5 on ≥3 of 9): **pass** (9/9)

## Per-dimension prevalence (cross-judge panel mean per sample)

| Dimension | kind | n | n_NA | n≥1.0 | rate≥1.0 | n≥0.5 | rate≥0.5 | mean | median |
|-----------|------|---|------|-------|---------|-------|---------|------|--------|
| ✓ `data_structure_choice` | always | 32 | 0 | 20 | 62.5% | 26 | 81.2% | 0.94 | 1.00 |
| ✓ `algorithm_correctness` | always | 32 | 0 | 15 | 46.9% | 24 | 75.0% | 0.77 | 0.67 |
| ✓ `error_handling_inconsistency` | always | 32 | 0 | 32 | 100.0% | 32 | 100.0% | 1.56 | 1.33 |
| ✓ `api_ergonomics` | always | 32 | 0 | 25 | 78.1% | 32 | 100.0% | 0.98 | 1.00 |
| ✓ `abstraction_miscalibration` | always | 32 | 0 | 18 | 56.2% | 25 | 78.1% | 0.90 | 1.00 |
| ✓ `code_organization` | always | 32 | 0 | 14 | 43.8% | 25 | 78.1% | 0.79 | 0.67 |
| ✓ `type_hint_gap` | always | 32 | 0 | 17 | 53.1% | 28 | 87.5% | 0.86 | 1.00 |
| ✓ `edge_case_gap` | always | 32 | 0 | 32 | 100.0% | 32 | 100.0% | 1.98 | 2.00 |
| ✓ `documentation_appropriateness` | always | 32 | 0 | 13 | 40.6% | 31 | 96.9% | 0.79 | 0.67 |
|   `concurrency_safety` | conditional | 11 | 21 | 1 | 9.1% | 4 | 36.4% | 0.33 | 0.33 |
|   `example_quality` | conditional | 29 | 3 | 6 | 20.7% | 19 | 65.5% | 0.56 | 0.50 |

## Per-judge saturation check

Per (judge × dim), what fraction of scores are exactly 0? If any judge is ≥90% zero on a dim, that judge is still saturating and the calibration anchor didn't bind for them.

| Judge | dim | n | mean | frac zero |
|-------|-----|---|------|-----------|
| `openai/gpt-4o-mini` | data_structure_choice | 32 | 1.00 | 0% |
| `openai/gpt-4o-mini` | algorithm_correctness | 32 | 0.12 | 88% |
| `openai/gpt-4o-mini` | error_handling_inconsistency | 32 | 1.28 | 0% |
| `openai/gpt-4o-mini` | api_ergonomics | 32 | 1.00 | 0% |
| `openai/gpt-4o-mini` | abstraction_miscalibration | 32 | 0.34 | 66% |
| `openai/gpt-4o-mini` | code_organization | 32 | 0.72 | 28% |
| `openai/gpt-4o-mini` | type_hint_gap | 32 | 0.56 | 44% |
| `openai/gpt-4o-mini` | edge_case_gap | 32 | 1.88 | 0% |
| `openai/gpt-4o-mini` | documentation_appropriateness | 32 | 0.97 | 3% |
| `openai/gpt-4o-mini` | concurrency_safety | 11 | 0.00 | 100% |
| `openai/gpt-4o-mini` | example_quality | 9 | 0.00 | 100% |
| `deepseek/deepseek-v3.2` | data_structure_choice | 28 | 0.89 | 39% |
| `deepseek/deepseek-v3.2` | algorithm_correctness | 29 | 1.55 | 21% |
| `deepseek/deepseek-v3.2` | error_handling_inconsistency | 30 | 1.73 | 0% |
| `deepseek/deepseek-v3.2` | api_ergonomics | 30 | 0.83 | 23% |
| `deepseek/deepseek-v3.2` | abstraction_miscalibration | 30 | 1.13 | 23% |
| `deepseek/deepseek-v3.2` | code_organization | 30 | 0.77 | 40% |
| `deepseek/deepseek-v3.2` | type_hint_gap | 30 | 0.70 | 33% |
| `deepseek/deepseek-v3.2` | edge_case_gap | 28 | 2.07 | 0% |
| `deepseek/deepseek-v3.2` | documentation_appropriateness | 30 | 0.43 | 60% |
| `deepseek/deepseek-v3.2` | concurrency_safety | 11 | 0.55 | 64% |
| `deepseek/deepseek-v3.2` | example_quality | 24 | 0.17 | 83% |
| `mistralai/mistral-small-2603` | data_structure_choice | 32 | 0.94 | 22% |
| `mistralai/mistral-small-2603` | algorithm_correctness | 32 | 0.75 | 28% |
| `mistralai/mistral-small-2603` | error_handling_inconsistency | 32 | 1.69 | 0% |
| `mistralai/mistral-small-2603` | api_ergonomics | 32 | 1.09 | 0% |
| `mistralai/mistral-small-2603` | abstraction_miscalibration | 32 | 1.25 | 0% |
| `mistralai/mistral-small-2603` | code_organization | 32 | 0.88 | 12% |
| `mistralai/mistral-small-2603` | type_hint_gap | 32 | 1.31 | 6% |
| `mistralai/mistral-small-2603` | edge_case_gap | 32 | 2.00 | 3% |
| `mistralai/mistral-small-2603` | documentation_appropriateness | 26 | 0.96 | 4% |
| `mistralai/mistral-small-2603` | concurrency_safety | 11 | 0.45 | 64% |
| `mistralai/mistral-small-2603` | example_quality | 27 | 0.96 | 7% |