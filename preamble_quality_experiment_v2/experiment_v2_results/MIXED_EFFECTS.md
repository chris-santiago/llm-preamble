# Mixed-effects models

All models: random intercepts on subject `model` and `task` (REML; statsmodels
`mixedlm` with `vc_formula` for the second random group). `preamble`
categorical with `none` as reference cell. `tier` is a fixed 1/0 indicator
(`reasoning=1`, `non_reasoning=0`). Tier is constant within each model, so
`(1|model)` absorbs within-tier between-model variance and `tier` captures
the mean shift between tiers.

## Model comparison — does tier matter? Does it interact with preamble?

### M0 — baseline (no tier term)

**Formula:** `cqs ~ C(preamble)`

- n = 1215
- random effect (model) variance: 0.00480
- random effect (task) variance: 0.01258
- residual variance: 0.01085
- log-likelihood: 883.5256

| Term | β | SE | z | p | 95% CI |
|---|---|---|---|---|---|
| `Intercept` | +0.7787 | 0.0272 | +28.62 | 3.554e-180 | [+0.7254, +0.8321] |
| `C(preamble)[T.trivial_baseline]` | -0.2368 | 0.0130 | -18.25 | 1.983e-74 | [-0.2622, -0.2114] |
| `C(preamble)[T.negative_control]` | -0.0563 | 0.0126 | -4.46 | 8.078e-06 | [-0.0811, -0.0316] |
| `C(preamble)[T.minimal]` | -0.0075 | 0.0127 | -0.59 | 0.5541 | [-0.0323, +0.0173] |
| `C(preamble)[T.generic_coding]` | +0.0088 | 0.0128 | +0.69 | 0.4905 | [-0.0162, +0.0338] |
| `C(preamble)[T.persona_only]` | -0.0111 | 0.0128 | -0.87 | 0.3856 | [-0.0361, +0.0139] |
| `C(preamble)[T.real_agent]` | +0.0240 | 0.0126 | +1.90 | 0.05692 | [-0.0007, +0.0487] |
| `C(preamble)[T.long_directive]` | +0.0362 | 0.0126 | +2.87 | 0.004102 | [+0.0115, +0.0609] |
| `C(preamble)[T.python_coder_agent]` | +0.0239 | 0.0126 | +1.89 | 0.05835 | [-0.0008, +0.0485] |
| `task Var` | +1.1593 | 0.2284 | +5.08 | 3.864e-07 | [+0.7116, +1.6070] |

### M1 — preamble + tier main effect

**Formula:** `cqs ~ C(preamble) + C(tier)`

- n = 1215
- random effect (model) variance: 0.00382
- random effect (task) variance: 0.01258
- residual variance: 0.01085
- log-likelihood: 882.7047

| Term | β | SE | z | p | 95% CI |
|---|---|---|---|---|---|
| `Intercept` | +0.7538 | 0.0298 | +25.32 | 1.768e-141 | [+0.6955, +0.8122] |
| `C(preamble)[T.trivial_baseline]` | -0.2369 | 0.0130 | -18.26 | 1.837e-74 | [-0.2623, -0.2114] |
| `C(preamble)[T.negative_control]` | -0.0564 | 0.0126 | -4.47 | 8.007e-06 | [-0.0811, -0.0316] |
| `C(preamble)[T.minimal]` | -0.0075 | 0.0127 | -0.59 | 0.5536 | [-0.0323, +0.0173] |
| `C(preamble)[T.generic_coding]` | +0.0088 | 0.0128 | +0.69 | 0.4896 | [-0.0162, +0.0338] |
| `C(preamble)[T.persona_only]` | -0.0111 | 0.0128 | -0.87 | 0.386 | [-0.0361, +0.0139] |
| `C(preamble)[T.real_agent]` | +0.0240 | 0.0126 | +1.90 | 0.05723 | [-0.0007, +0.0487] |
| `C(preamble)[T.long_directive]` | +0.0361 | 0.0126 | +2.87 | 0.004146 | [+0.0114, +0.0608] |
| `C(preamble)[T.python_coder_agent]` | +0.0238 | 0.0126 | +1.89 | 0.05869 | [-0.0009, +0.0485] |
| `C(tier)[T.reasoning]` | +0.0832 | 0.0521 | +1.60 | 0.1105 | [-0.0190, +0.1854] |
| `task Var` | +1.1593 | 0.2284 | +5.08 | 3.861e-07 | [+0.7117, +1.6070] |

### M2 — preamble × tier interaction (FULL MODEL)

**Formula:** `cqs ~ C(preamble) * C(tier)`

- n = 1215
- random effect (model) variance: 0.00385
- random effect (task) variance: 0.01261
- residual variance: 0.01079
- log-likelihood: 867.1331

| Term | β | SE | z | p | 95% CI |
|---|---|---|---|---|---|
| `Intercept` | +0.7527 | 0.0303 | +24.86 | 2.129e-136 | [+0.6933, +0.8120] |
| `C(preamble)[T.trivial_baseline]` | -0.2549 | 0.0154 | -16.51 | 2.91e-61 | [-0.2852, -0.2247] |
| `C(preamble)[T.negative_control]` | -0.0600 | 0.0148 | -4.04 | 5.265e-05 | [-0.0891, -0.0309] |
| `C(preamble)[T.minimal]` | +0.0003 | 0.0148 | +0.02 | 0.9857 | [-0.0288, +0.0293] |
| `C(preamble)[T.generic_coding]` | +0.0144 | 0.0148 | +0.97 | 0.3311 | [-0.0147, +0.0435] |
| `C(preamble)[T.persona_only]` | -0.0069 | 0.0149 | -0.46 | 0.6435 | [-0.0360, +0.0223] |
| `C(preamble)[T.real_agent]` | +0.0272 | 0.0148 | +1.83 | 0.06684 | [-0.0019, +0.0563] |
| `C(preamble)[T.long_directive]` | +0.0459 | 0.0149 | +3.09 | 0.002022 | [+0.0168, +0.0751] |
| `C(preamble)[T.python_coder_agent]` | +0.0227 | 0.0148 | +1.53 | 0.126 | [-0.0064, +0.0518] |
| `C(tier)[T.reasoning]` | +0.0872 | 0.0556 | +1.57 | 0.117 | [-0.0218, +0.1962] |
| `C(preamble)[T.trivial_baseline]:C(tier)[T.reasoning]` | +0.0558 | 0.0284 | +1.97 | 0.04913 | [+0.0002, +0.1114] |
| `C(preamble)[T.negative_control]:C(tier)[T.reasoning]` | +0.0125 | 0.0280 | +0.45 | 0.6559 | [-0.0424, +0.0674] |
| `C(preamble)[T.minimal]:C(tier)[T.reasoning]` | -0.0278 | 0.0283 | -0.98 | 0.3256 | [-0.0832, +0.0276] |
| `C(preamble)[T.generic_coding]:C(tier)[T.reasoning]` | -0.0215 | 0.0288 | -0.75 | 0.4555 | [-0.0780, +0.0350] |
| `C(preamble)[T.persona_only]:C(tier)[T.reasoning]` | -0.0157 | 0.0287 | -0.55 | 0.5844 | [-0.0720, +0.0406] |
| `C(preamble)[T.real_agent]:C(tier)[T.reasoning]` | -0.0111 | 0.0279 | -0.40 | 0.691 | [-0.0658, +0.0436] |
| `C(preamble)[T.long_directive]:C(tier)[T.reasoning]` | -0.0326 | 0.0278 | -1.17 | 0.241 | [-0.0871, +0.0219] |
| `C(preamble)[T.python_coder_agent]:C(tier)[T.reasoning]` | +0.0037 | 0.0279 | +0.13 | 0.8947 | [-0.0510, +0.0584] |
| `task Var` | +1.1693 | 0.2303 | +5.08 | 3.839e-07 | [+0.7179, +1.6208] |

**ΔlogLik(M1 − M0):** -0.8210 — magnitude of tier main effect on fit quality.
**ΔlogLik(M2 − M1):** -15.5716 — magnitude of preamble × tier interaction on fit quality.

(REML log-likelihoods are not directly comparable across models with different fixed-effects structure; signs and magnitudes are descriptive. A principled fixed-effect LRT requires ML estimation; see ML refit below.)

## ML refit for principled fixed-effect LRT

- **M0 (ML)** logLik = 915.5550, df_resid = 1206
- **M1 (ML, +tier)** logLik = 916.9371, df_resid = 1205
- **M2 (ML, ×tier)** logLik = 924.3357, df_resid = 1197

## Stratified fits (for reference; superseded by M2 above)

### Reasoning tier only

- n = 348
- random effect (model) variance: 0.00004
- random effect (task) variance: 0.00490
- residual variance: 0.01197

**Fixed effects vs `none` (reference):**

| Term | β | SE | z | p | 95% CI |
|---|---|---|---|---|---|
| `Intercept` | +0.8404 | 0.0246 | +34.18 | 4.454e-256 | [+0.7923, +0.8886] |
| `C(preamble)[T.trivial_baseline]` | -0.1997 | 0.0257 | -7.76 | 8.313e-15 | [-0.2501, -0.1493] |
| `C(preamble)[T.negative_control]` | -0.0476 | 0.0253 | -1.88 | 0.0599 | [-0.0971, +0.0020] |
| `C(preamble)[T.minimal]` | -0.0280 | 0.0256 | -1.09 | 0.2737 | [-0.0782, +0.0221] |
| `C(preamble)[T.generic_coding]` | -0.0076 | 0.0261 | -0.29 | 0.7703 | [-0.0587, +0.0435] |
| `C(preamble)[T.persona_only]` | -0.0230 | 0.0259 | -0.89 | 0.3732 | [-0.0737, +0.0277] |
| `C(preamble)[T.real_agent]` | +0.0154 | 0.0253 | +0.61 | 0.5424 | [-0.0342, +0.0650] |
| `C(preamble)[T.long_directive]` | +0.0128 | 0.0254 | +0.50 | 0.6152 | [-0.0370, +0.0625] |
| `C(preamble)[T.python_coder_agent]` | +0.0257 | 0.0253 | +1.02 | 0.3097 | [-0.0239, +0.0754] |
| `task Var` | +0.4096 | 0.1591 | +2.57 | 0.01003 | [+0.0978, +0.7214] |

### Non-reasoning tier only

- n = 867
- random effect (model) variance: 0.00517
- random effect (task) variance: 0.01581
- residual variance: 0.01031

**Fixed effects vs `none` (reference):**

| Term | β | SE | z | p | 95% CI |
|---|---|---|---|---|---|
| `Intercept` | +0.7527 | 0.0341 | +22.04 | 1.087e-107 | [+0.6858, +0.8196] |
| `C(preamble)[T.trivial_baseline]` | -0.2551 | 0.0151 | -16.90 | 4.635e-64 | [-0.2847, -0.2255] |
| `C(preamble)[T.negative_control]` | -0.0600 | 0.0145 | -4.13 | 3.55e-05 | [-0.0884, -0.0316] |
| `C(preamble)[T.minimal]` | +0.0003 | 0.0145 | +0.02 | 0.9853 | [-0.0282, +0.0287] |
| `C(preamble)[T.generic_coding]` | +0.0144 | 0.0145 | +0.99 | 0.3203 | [-0.0140, +0.0429] |
| `C(preamble)[T.persona_only]` | -0.0069 | 0.0145 | -0.47 | 0.6361 | [-0.0354, +0.0216] |
| `C(preamble)[T.real_agent]` | +0.0272 | 0.0145 | +1.87 | 0.0609 | [-0.0012, +0.0556] |
| `C(preamble)[T.long_directive]` | +0.0459 | 0.0145 | +3.16 | 0.001595 | [+0.0174, +0.0744] |
| `C(preamble)[T.python_coder_agent]` | +0.0227 | 0.0145 | +1.56 | 0.1176 | [-0.0057, +0.0511] |
| `task Var` | +1.5327 | 0.3563 | +4.30 | 1.693e-05 | [+0.8344, +2.2309] |
