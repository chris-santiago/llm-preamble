# Gate 1 — Experiment Plan (v2)

**Status:** APPROVED with 13 decisions captured (see "Captured Decisions"
section below). Pre-flight execution begins after intent-watch clean pass.
**Debate outcome:** `critique_wins` after 3 rounds (stop_reason:
fully_resolved). Verdict driven solely by F1 CONCEDE sev 9 (one verifiable
code bug). All other findings reached terminal states at adj_sev ≤ 3
(defense_wins).

## Pre-flight checklist

| # | Source | Finding | Point Verdict | Required action before main run | Status |
|---|---|---|---|---|---|
| 1 | F1 critique_wins / CONCEDE | sev 9 | critique_wins | Add `clamp(1, 10)` to idiom/comment score extraction in `judge_one_sample` (mirroring existing `clamp(0,5)` on rubric items at line ~354). Add an out-of-range detection log per judge call. Re-run PoC and verify deepseek's -1 sample no longer poisons the python_coder_agent aggregate. | PENDING |
| 2 | F4 CONCEDE | sev 3 | defense_wins | Style-directive confound probe: before the main run, generate ≥10 samples on 2–3 experimental tasks under the `python_coder_agent` preamble. Score each output with two judge prompts — the current (unanchored) prompt, and a complexity-anchored variant ("Score comment quality relative to the inherent complexity of the task, not the verbosity of the implementation"). If mean comment_quality difference > 0.5 points, amend judge prompt to use the anchored variant and log the amendment as a pre-registration drift event per SPEC §7. | PENDING |
| 3 | F2 DEFER | sev 3 | defense_wins | Empirical gate on `task_modeflag_sort` rewrite: rewrite the prompt to describe behavior only ("implement a stable sort that preserves element order on ties; supports an optional key callable and a reverse flag") with no code stub and no parameter prescription. Then run a ≥5-sample pilot under no-preamble. **Gate criterion:** no-preamble must show ≥40% mode_flag_params implementation rate (severity ≥3) to confirm the discriminative space is open. If gate fails, reject and rewrite. | PENDING |
| 4 | F5 DEFER | sev 2 | defense_wins | Two-question validation before main run: (a) Rubric calibration probe with hand-authored smell-bearing samples (one per dimension) confirms judge sensitivity per dimension. (b) Pilot non-zero-rate audit on ≥30 model-generated outputs covering all 8 tasks confirms ≥4 of the 11 rubric dimensions appear at >10% prevalence. **Recovery if (b) fails:** log as pre-reg drift; if ≥2 dims viable, formally amend criterion to achievable number; if <2 dims, flag rubric as structurally misaligned and report secondary criterion null by construction. Primary CQS-craft KW is independent. | PENDING |
| 5 | trivial baseline | — | always required | Include `trivial_baseline` condition (temp=1.0, prompt = task name only, no preamble) per SPEC_V2.md §6.1 and the skill's non-negotiable requirement. | LOCKED IN SPEC |
| 6 | F3, F6, F7 | defense_wins | — | No remediation required; design decisions stand as documented in SPEC_V2.md §6.5/§7. | CLOSED |

## Conceded critique points addressed in experiment design

**F1 (sev 9) — out-of-range judge score contamination:**
- Add a `clamp(1, 10)` to both `idiomaticity` and `comment_quality` extraction in
  `judge_one_sample` (where rubric items are already clamped to `[0, 5]`).
- Add a structured out-of-range counter to the judge log so any future
  sentinel emission is surfaced rather than silently corrupting the mean.
- Re-run the PoC and confirm the python_coder_agent × task_modeflag_sort
  cell's idiom/comment scores rise toward 0.9 (mistral's valid score) once
  the deepseek -1 record is correctly excluded.

**F4 (sev 3) — style-directive confound on comment_quality:**
- Run the pre-main-run style-directive probe described in checklist item 2
  *before* writing the experiment script (Step 6) — its result determines
  whether the judge prompt is amended.
- The probe is empirical (real model outputs under python_coder_agent
  preamble), not just smell-detection sensitivity on hand-authored samples.
- Outcome documentation: either "no amendment needed (anchored vs unanchored
  ≤ 0.5 mean diff)" or "amendment applied + pre-reg drift logged per SPEC §7."

## Empirical tests (DEFER findings → settling experiments)

**F2 settling test — task_modeflag_sort prompt rewrite gate**
- *Experimental condition:* candidate behavioral-spec rewrite, no parameter
  prescription, no code stub. ≥5 samples in no-preamble condition.
- *Pre-specified verdicts:*
  - Confirms rewrite (proceed): no-preamble mode_flag_params severity ≥3
    rate ≥ 40%. Discriminative space is open; rich-preamble conditions have
    room to suppress the smell.
  - Refutes rewrite (reject + rewrite again): no-preamble rate < 40%.
    Behavioral space remains constrained by something in the new prompt.
  - Ambiguous: 30–40% rate. Increase pilot to 10 samples and re-evaluate.

**F5 settling test — rubric prevalence audit**
- *Experimental condition:* ≥30 generations across all 8 experimental tasks
  (pilot subset of the main run, all 7 subject models, no preamble).
- *Pre-specified verdicts:*
  - Confirms ≥4-dim criterion is achievable: ≥4 of 11 rubric dimensions
    appear at >10% non-zero severity rate in pilot outputs. Main run proceeds
    with the locked criterion.
  - Triggers recovery branch (a): only 2–3 dims achieve >10% prevalence.
    Formally amend the secondary criterion to the achievable number; log as
    pre-reg drift; proceed.
  - Triggers recovery branch (b): <2 dims achieve >10% prevalence. Flag rubric
    as structurally misaligned with the task set; report secondary criterion
    as null by construction; primary CQS-craft KW stands independently.

## Experimental conditions (all 9 from SPEC_V2.md §6.1, unchanged)

`none`, `minimal`, `generic_coding`, `real_agent`, `negative_control`,
`persona_only`, `long_directive`, `trivial_baseline`, `python_coder_agent`.
No new conditions added; no existing conditions modified or removed.

## Stratifications (per SPEC_V2.md §6.5)

- **Primary contrast:** rich-preamble pool vs. `none` vs. `negative_control`.
- **Per-dimension secondary:** KW across conditions for each of 11
  single-file rubric dimensions, stratified by task category (creation vs.
  refactor; plus multifile_creation if §6.2's optional multi-file task ships).
- **Self vs cross judge stratification:** F3 hygiene check per v1 methodology.
- **Diagnostic panel:** static-analysis metrics (radon MI, avg cyclomatic,
  Halstead difficulty, pylint penalty, PEP8 name-compliance) reported
  separately, not as CQS inputs.

## Captured Decisions (13 items)

| # | Decision | Captured choice |
|---|---|---|
| D1 | F1 out-of-range judge-score handling | **Drop** (treat as None, exclude from cross-judge mean) |
| D2 | F2 prompt rewrite text for `task_modeflag_sort` | Use the behavior-only spec in this plan (no signature, no code stub) |
| D3 | F2 gate threshold (no-preamble mode_flag_params rate) | **≥ 40%** |
| D4 | F2 gate pilot size | **30 samples** (15 × no-preamble + 15 × python_coder_agent) |
| D5 | F4 anchored-judge-prompt language | Use the complexity-relative anchor in this plan |
| D6 | F4 amendment trigger | **\|Δ\| > 0.5** points on 1–10 comment-quality scale |
| D7 | F4 probe sample scope | **3 tasks × 7 models, both python_coder_agent AND real_agent** (~42 outputs) |
| D8 | F5 prevalence-audit pilot size | **30 generations** distributed across 8 tasks × ~4 models, no-preamble |
| D9 | F5 prevalence threshold for "active" dim | **> 10%** of pilot samples with severity ≥ 1 |
| D10 | Main-run replications per cell | **3** (~$13 main run; ~168/condition pre-attrition) |
| D11 | Multi-file task `task_kv_store_package` | **INCLUDE** — activates rubric dims 12–14 |
| D12 | Static-analysis diagnostic panel | Include, reported separately (never in CQS-craft) |
| D13 | Out-of-range judge-score logging | Add structured counter; surface in run report |

**Net cost impact vs my baseline:** ~$15–16 total (vs $8.50). Drivers: 3 replications (+$5), F4 broader scope (+$0.30), F2 larger pilot (+$0.05), multi-file task (+$1).

**Pre-registration amendment implication of D11:** activating the multi-file task changes the scope from "8 tasks" to "9 tasks effective" — `SPEC_V2.md §6.2` permits this (it was pre-registered as optional with a pilot-conditional decision). The activation is logged in this plan rather than as a drift event.

## What remains LOCKED in SPEC_V2.md (no amendments)

- CQS-craft formula (`0.45·idiom + 0.45·comment + 0.10·hygiene`).
- 9 condition definitions.
- 8 task IDs (subject to F2's prompt-text rewrite for `task_modeflag_sort`).
- 11-dim rubric (subject to F5's pre-registered branching if pilot prevalence
  insufficient).
- 0–5 severity scale.
- Sample-size target n ≥ 100 per condition post-attrition.
- 7-model subject and judge pool (grok-4.1-fast deprecated, removed).
- Cross-judge primary scoring; self-judgments excluded.
