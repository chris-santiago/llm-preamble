# Preamble Quality Experiment v2 — Main Run Report

**Total generations:** 1260  |  **extracted ok:** 1215
**Judge calls:** 24300  |  **parse ok:** 22028
**Samples with CQS-craft:** 1215
**Total cost:** $32.0194

## 1. Primary — CQS-craft by preamble (pooled across pool)

| Preamble | n | mean | 95% CI |
|----------|---|------|--------|
| `trivial_baseline` | 125 | 0.5563 | [0.5097, 0.6002] |
| `none` | 135 | 0.7781 | [0.7497, 0.8036] |
| `negative_control` | 138 | 0.7232 | [0.6995, 0.7456] |
| `minimal` | 136 | 0.7698 | [0.7407, 0.7936] |
| `generic_coding` | 132 | 0.7840 | [0.7564, 0.8080] |
| `persona_only` | 132 | 0.7644 | [0.7353, 0.7913] |
| `real_agent` | 139 | 0.8020 | [0.7753, 0.8248] |
| `long_directive` | 139 | 0.8145 | [0.7886, 0.8358] |
| `python_coder_agent` | 139 | 0.8019 | [0.7748, 0.8234] |

**Kruskal–Wallis (main conditions, pooled):** H = 95.4775120588366, p = 9.24222535792776e-18

## 2. Tier stratification — CQS-craft

### reasoning

| Preamble | n | mean | 95% CI |
|----------|---|------|--------|
| `trivial_baseline` | 40 | 0.6413 | [0.5678, 0.7128] |
| `none` | 37 | 0.8454 | [0.8326, 0.8575] |
| `negative_control` | 40 | 0.7978 | [0.7600, 0.8258] |
| `minimal` | 38 | 0.8132 | [0.7574, 0.8550] |
| `generic_coding` | 34 | 0.8327 | [0.7871, 0.8602] |
| `persona_only` | 35 | 0.8184 | [0.7701, 0.8556] |
| `real_agent` | 41 | 0.8549 | [0.8344, 0.8702] |
| `long_directive` | 42 | 0.8532 | [0.8132, 0.8765] |
| `python_coder_agent` | 41 | 0.8652 | [0.8507, 0.8777] |

**KW within reasoning:** H = 49.56517977862776, p = 1.7580727330478546e-08

### non_reasoning

| Preamble | n | mean | 95% CI |
|----------|---|------|--------|
| `trivial_baseline` | 85 | 0.5164 | [0.4626, 0.5678] |
| `none` | 98 | 0.7527 | [0.7144, 0.7832] |
| `negative_control` | 98 | 0.6927 | [0.6625, 0.7203] |
| `minimal` | 98 | 0.7529 | [0.7210, 0.7824] |
| `generic_coding` | 98 | 0.7671 | [0.7325, 0.7974] |
| `persona_only` | 97 | 0.7449 | [0.7084, 0.7759] |
| `real_agent` | 98 | 0.7799 | [0.7450, 0.8097] |
| `long_directive` | 97 | 0.7977 | [0.7639, 0.8270] |
| `python_coder_agent` | 98 | 0.7754 | [0.7390, 0.8062] |

**KW within non_reasoning:** H = 69.09132797711742, p = 2.2544939548912513e-12

## 3. Task-category stratification — CQS-craft

### creation

| Preamble | n | mean | 95% CI |
|----------|---|------|--------|
| `trivial_baseline` | 72 | 0.6304 | [0.5715, 0.6832] |
| `none` | 79 | 0.8130 | [0.7981, 0.8266] |
| `negative_control` | 79 | 0.7460 | [0.7253, 0.7676] |
| `minimal` | 78 | 0.8000 | [0.7798, 0.8196] |
| `generic_coding` | 75 | 0.8156 | [0.7956, 0.8337] |
| `persona_only` | 79 | 0.7996 | [0.7777, 0.8214] |
| `real_agent` | 79 | 0.8366 | [0.8214, 0.8508] |
| `long_directive` | 80 | 0.8429 | [0.8274, 0.8562] |
| `python_coder_agent` | 79 | 0.8342 | [0.8158, 0.8497] |

### refactor

| Preamble | n | mean | 95% CI |
|----------|---|------|--------|
| `trivial_baseline` | 39 | 0.4418 | [0.3742, 0.5167] |
| `none` | 37 | 0.7656 | [0.7211, 0.8046] |
| `negative_control` | 40 | 0.7296 | [0.6945, 0.7619] |
| `minimal` | 38 | 0.7687 | [0.7230, 0.8105] |
| `generic_coding` | 38 | 0.7819 | [0.7424, 0.8147] |
| `persona_only` | 33 | 0.7509 | [0.7025, 0.7969] |
| `real_agent` | 40 | 0.7900 | [0.7511, 0.8238] |
| `long_directive` | 39 | 0.8252 | [0.7935, 0.8507] |
| `python_coder_agent` | 40 | 0.7946 | [0.7625, 0.8244] |

### multifile_creation

| Preamble | n | mean | 95% CI |
|----------|---|------|--------|
| `trivial_baseline` | 14 | 0.4942 | [0.3635, 0.6269] |
| `none` | 19 | 0.6570 | [0.5092, 0.7814] |
| `negative_control` | 19 | 0.6145 | [0.4947, 0.7238] |
| `minimal` | 20 | 0.6538 | [0.5218, 0.7731] |
| `generic_coding` | 19 | 0.6632 | [0.5174, 0.7941] |
| `persona_only` | 20 | 0.6477 | [0.5266, 0.7642] |
| `real_agent` | 20 | 0.6891 | [0.5517, 0.8029] |
| `long_directive` | 20 | 0.6802 | [0.5376, 0.8020] |
| `python_coder_agent` | 20 | 0.6889 | [0.5490, 0.8136] |

## 4. Per-dimension severity by preamble (cross-judge means)

| Dimension | KW p |  trivial_baseline  |  none  |  negative_control  |  minimal  |  generic_coding  |  persona_only  |  real_agent  |  long_directive  |  python_coder_agent  |
|---|---|---|---|---|---|---|---|---|---|---|
| `data_structure_choice` | 0.3871 | 1.83 (n=125) | 1.23 (n=135) | 1.27 (n=138) | 1.19 (n=136) | 1.21 (n=132) | 1.20 (n=132) | 1.17 (n=139) | 1.16 (n=139) | 1.16 (n=139) |
| `algorithm_correctness` | 0.2603 | 2.01 (n=125) | 1.36 (n=135) | 1.37 (n=138) | 1.31 (n=136) | 1.28 (n=132) | 1.37 (n=132) | 1.23 (n=139) | 1.30 (n=139) | 1.22 (n=139) |
| `error_handling_inconsistency` | 0.0000 | 2.37 (n=125) | 1.61 (n=135) | 1.69 (n=138) | 1.54 (n=136) | 1.55 (n=132) | 1.61 (n=132) | 1.34 (n=139) | 1.35 (n=139) | 1.41 (n=139) |
| `api_ergonomics` | 0.0080 | 2.01 (n=125) | 1.23 (n=135) | 1.27 (n=138) | 1.23 (n=136) | 1.22 (n=132) | 1.22 (n=132) | 1.17 (n=139) | 1.14 (n=139) | 1.11 (n=139) |
| `abstraction_miscalibration` | 0.0004 | 1.95 (n=125) | 1.12 (n=135) | 1.19 (n=138) | 1.13 (n=136) | 1.11 (n=132) | 1.14 (n=132) | 0.99 (n=139) | 1.06 (n=139) | 1.01 (n=139) |
| `code_organization` | 0.0000 | 1.93 (n=125) | 0.96 (n=135) | 1.05 (n=138) | 0.98 (n=136) | 0.96 (n=132) | 1.03 (n=132) | 0.85 (n=139) | 0.91 (n=139) | 0.86 (n=139) |
| `type_hint_gap` | 0.0000 | 2.74 (n=125) | 1.09 (n=135) | 1.17 (n=138) | 1.09 (n=136) | 1.05 (n=132) | 1.10 (n=132) | 0.96 (n=139) | 0.94 (n=139) | 0.93 (n=139) |
| `edge_case_gap` | 0.0000 | 2.58 (n=125) | 1.89 (n=135) | 1.98 (n=138) | 1.82 (n=136) | 1.84 (n=132) | 1.89 (n=132) | 1.62 (n=139) | 1.65 (n=139) | 1.72 (n=139) |
| `documentation_appropriateness` | 0.0000 | 1.79 (n=125) | 1.15 (n=135) | 1.51 (n=138) | 1.18 (n=136) | 1.09 (n=132) | 1.19 (n=132) | 0.99 (n=139) | 0.94 (n=139) | 1.00 (n=139) |
| `concurrency_safety` | 0.0058 | 2.37 (n=54) | 1.78 (n=70) | 2.20 (n=72) | 1.56 (n=76) | 1.77 (n=72) | 1.72 (n=73) | 1.76 (n=76) | 1.13 (n=76) | 1.87 (n=75) |
| `example_quality` | 0.2452 | 1.98 (n=97) | 0.92 (n=98) | 1.02 (n=101) | 0.87 (n=98) | 0.96 (n=96) | 0.93 (n=99) | 0.90 (n=103) | 0.92 (n=98) | 0.91 (n=100) |

## 5. F3 hygiene — self vs cross judge

### idiomaticity
- self  : n=2167, mean=7.778034148592524
- cross : n=9506, mean=7.753313696612666
- Δ(self − cross) = 0.024720451979858282; Mann-Whitney p = 0.0003

### comment_quality
- self  : n=2175, mean=7.756781609195403
- cross : n=9522, mean=7.463137996219282
- Δ(self − cross) = 0.29364361297612085; Mann-Whitney p = 0.0000

## 6. Static analysis diagnostic panel (NOT in CQS)

| Metric | KW p across preambles | mean (none) | mean (real_agent) | mean (python_coder_agent) | mean (negative_control) |
|---|---|---|---|---|---|
| maintainability_index | 0.9153 | 59.297 | 60.007 | 60.516 | 60.198 |
| avg_cyclomatic | 0.3329 | 2.584 | 2.708 | 2.561 | 2.928 |
| max_cyclomatic | 0.8448 | 6.681 | 6.849 | 6.835 | 7.043 |
| halstead_difficulty | 0.9799 | 3.967 | 4.121 | 3.888 | 3.832 |
| pylint_errors | 0.9710 | 0.296 | 0.432 | 0.381 | 0.355 |
| pylint_warnings | 0.9694 | 3.681 | 3.942 | 4.309 | 3.681 |
| pylint_conventions | 0.0122 | 12.474 | 11.942 | 11.626 | 14.580 |
| pylint_refactor | 0.9168 | 2.311 | 1.935 | 1.820 | 2.174 |
| cognitive_complexity_violations | 0.5303 | 0.030 | 0.029 | 0.036 | 0.065 |