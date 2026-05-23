# Confound probe report

Task: `task_expr_parser`  |  subjects: 10 models  |  judges: full cross-judge matrix

## 1. CQS-craft per probe vs reference conditions

| Condition | n | mean | 95% CI |
|---|---|---|---|
| `none (main-run reference)` | 20 | 0.8271 | [0.8073, 0.8446] |
| `long_directive (main-run reference)` | 20 | 0.8480 | [0.8240, 0.8701] |
| `negative_control (main-run reference)` | 19 | 0.7489 | [0.7128, 0.7829] |
| `python_coder_agent (main-run reference)` | 20 | 0.8537 | [0.8344, 0.8749] |

| Probe | n | mean | 95% CI | Δ vs `none` (main) |
|---|---|---|---|---|
| `probe_A_nonrubric_expert` | 10 | 0.6726 | [0.6122, 0.7257] | -0.1545 |
| `probe_B_bare_rubric` | 10 | 0.8416 | [0.8065, 0.8758] | +0.0145 |
| `probe_C_antirubric_expert` | 10 | 0.6733 | [0.6121, 0.7316] | -0.1539 |
| `none_control` | 10 | 0.8057 | [0.7705, 0.8393] | -0.0214 |

## 2. Significance — Mann-Whitney U vs main-run `none`

| Probe | n | mean | U | p (two-sided) |
|---|---|---|---|---|
| `probe_A_nonrubric_expert` | 10 | 0.6726 | 9.0 | 0.0001 |
| `probe_B_bare_rubric` | 10 | 0.8416 | 116.0 | 0.4953 |
| `probe_C_antirubric_expert` | 10 | 0.6733 | 10.0 | 0.0001 |
| `none_control` | 10 | 0.8057 | 72.0 | 0.2263 |

## 3. Per-dimension severity — probes vs reference conditions

Cross-judge mean severity (0 = clean, 5 = severe) per probe condition
on the 9 always-on rubric dimensions. Reference columns are from the
v2 main run on the same task.

| Dimension | none ref | long_dir ref | neg ref | A (misalign) | B (bare) | C (anti) | none_control |
|---|---|---|---|---|---|---|---|
| `data_structure_choice` | 1.00 (n=20) | 1.00 (n=20) | 1.02 (n=19) | 0.99 (n=10) | 0.98 (n=10) | 1.12 (n=10) | 1.03 (n=10) |
| `algorithm_correctness` | 0.77 (n=20) | 1.02 (n=20) | 1.10 (n=19) | 1.12 (n=10) | 1.21 (n=10) | 1.21 (n=10) | 1.00 (n=10) |
| `error_handling_inconsistency` | 1.19 (n=20) | 1.02 (n=20) | 1.33 (n=19) | 1.32 (n=10) | 1.12 (n=10) | 1.30 (n=10) | 1.12 (n=10) |
| `api_ergonomics` | 0.77 (n=20) | 0.82 (n=20) | 0.89 (n=19) | 0.93 (n=10) | 0.75 (n=10) | 0.91 (n=10) | 0.92 (n=10) |
| `abstraction_miscalibration` | 0.94 (n=20) | 0.92 (n=20) | 1.06 (n=19) | 1.02 (n=10) | 0.94 (n=10) | 1.03 (n=10) | 1.06 (n=10) |
| `code_organization` | 0.79 (n=20) | 0.76 (n=20) | 0.92 (n=19) | 0.97 (n=10) | 0.75 (n=10) | 0.93 (n=10) | 0.96 (n=10) |
| `type_hint_gap` | 1.09 (n=20) | 0.96 (n=20) | 1.14 (n=19) | 1.17 (n=10) | 0.99 (n=10) | 1.36 (n=10) | 1.13 (n=10) |
| `edge_case_gap` | 1.51 (n=20) | 1.36 (n=20) | 1.78 (n=19) | 1.77 (n=10) | 1.59 (n=10) | 1.79 (n=10) | 1.51 (n=10) |
| `documentation_appropriateness` | 0.84 (n=20) | 0.74 (n=20) | 1.24 (n=19) | 1.59 (n=10) | 0.79 (n=10) | 1.57 (n=10) | 0.92 (n=10) |

## 4. Discrimination verdict

**Probe A — misaligned expert directive:** mean CQS = 0.6726
  - Δ vs `none`: -0.1545
  - Δ vs `long_directive`: -0.1754
  - **Recovery ratio** (A − none) / (long − none): -7.42
    - ratio ≈ 1.0 → expert framing accounts for nearly all of long_directive's effect (H-mechanism weak; expert priming generic)
    - ratio ≈ 0.0 → naming the rubric items is what matters (H-judge-priming or H-mechanism-via-naming)
    - ratio < 0  → misaligned directives actively hurt vs no preamble

**Probe B — bare rubric list:** mean CQS = 0.8416
  - Δ vs `none`: +0.0145
  - Δ vs `long_directive`: -0.0063
  - **Recovery ratio** (B − none) / (long − none): +0.70
    - ratio ≈ 1.0 → naming the rubric items reproduces the full effect (H-judge-priming dominant)
    - ratio ≈ 0.0 → bare naming is insufficient; expert framing matters separately

**Probe C — anti-rubric directive:** mean CQS = 0.6733
  - Δ vs `none`: -0.1539
    - Δ << 0 → judges follow preamble priming even against their stated rubric (strong H-judge-priming evidence)
    - Δ ≈ 0  → anti-rubric framing produces neutral effect (judges weight rubric over preamble)
    - Δ > 0  → unexpected; possibly artifact of clearer / more focused code under simpler instructions
