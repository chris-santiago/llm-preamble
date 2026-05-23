# Report Addendum — v2 Pre-flight Methodology Journey

`CONCLUSIONS.md` reports the v2 main-run results. This addendum documents the
five pre-registration amendments (A1–A5) the pre-flight produced and the
methodological discoveries behind each. The investigation log
(`INVESTIGATION_LOG.jsonl`) is the canonical chronological record; this
document is the narrative companion.

The pre-flight ran six gated phases between debate-derived experiment plan
(`GATE_1_PLAN.md`) and the locked main-run script: Phase A (F1 clamp fix),
Phase B (F2 trap-task gate), Phase C (F4 anchored-vs-unanchored judge
prompt confound), Phase D (F5 rubric prevalence audit), Phase D2 (calibrated
rubric re-probe), and a final design lock-down. Each amendment was logged as
a SPEC §7 "documented pre-registration drift event" with rationale before any
main-run generation began.

---

## A1 — Rubric redesign

**Trigger.** Pre-flight Phase D ran the original 11-dimension python-coder S3+
checklist rubric on 30 algorithmic LLM code samples spanning the model pool.
The prevalence gate required ≥10% non-zero severity rate on ≥4 of 11
dimensions. **Zero of 11 dimensions cleared the gate.** Modern instruction-tuned
LLMs essentially never produce the canonical S3+ smells on hard algorithmic
tasks: no `mode_flag_params` on public functions, no `dict_domain_data`
crossing function boundaries, no `bare_except` clauses, no
`hidden_side_effects`, no `overgrown_class`. The original rubric was the right
instrument for the wrong population.

**Decision.** User chose to redesign the rubric rather than collapse to a
v1++ design (which would have rendered the per-dimension secondary criterion
null by construction). The new rubric targets dimensions algorithmic Python
code actually varies on:

- `data_structure_choice` — appropriateness of structure picks
- `algorithm_correctness` — correctness / complexity vs requirements
- `error_handling_inconsistency` — coherence of error philosophy
- `api_ergonomics` — caller-friendliness of public API
- `abstraction_miscalibration` — over- or under-engineering
- `code_organization` — decomposition into cohesive units
- `type_hint_gap` — type annotation coverage
- `edge_case_gap` — boundary / empty / invalid input handling
- `documentation_appropriateness` — docstring quality vs complexity
- `concurrency_safety` *(conditional)* — when concurrency required
- `example_quality` *(conditional)* — when usage examples requested

The 0–5 severity scale and cross-judge panel design were preserved.

**Validation.** The redesigned rubric was re-tested at Phase D2 (see A5).

---

## A2 — Drop `task_modeflag_sort`

**Trigger.** Pre-flight Phase B tested the rewritten behavior-only
`modeflag_sort` task (30 samples across the pool). The intent was to probe
preamble-induced resistance to the v1 `mode_flag_params` smell. **Outcome:
0% baseline rate of the smell across all conditions.** The behavior-only
specification ("sort a sequence; default stable; supports descending and key;
choose any reasonable API") successfully refused to name the trap, but in
doing so eliminated the discriminative space — no condition produced a
boolean `stable` parameter; every condition picked an idiomatic API.

The behavior-only framing was the *correct* design choice. (The alternative —
naming the smell — would have measured compliance with explicit instructions,
not preamble effect.) The test simply had no signal to read.

**Decision.** Drop the task. Task count 8 → 7. Pre-registered branching
recovery in SPEC §11 covered this contingency; no Gate 1 reopen required.

---

## A3 — Pool macro-iteration to reasoning-inclusive

**Trigger.** User methodological challenge: *"I'm not happy about testing
non-reasoning. This doesn't match the reality of agentic coding frameworks.
We're answering a question that's irrelevant."* The original v2 pool inherited
v1's 7 non-reasoning models. Production agentic coding frameworks
(Claude Code, Cursor, Aider, GitHub Copilot Workspace, etc.) overwhelmingly
use reasoning-capable models.

**Decision.** Macro-iterate the hypothesis to the outcome question — "what do
preambles do in production-realistic model populations?" — and stratify the
analysis by reasoning tier so v1's original sub-question (preambles on
non-reasoning) is still answerable. Pool expanded to 10:

- **Reasoning (3):** `qwen/qwen3.6-flash`, `deepseek/deepseek-v4-flash`,
  `minimax/minimax-m2.5`
- **Non-reasoning (7):** the existing v1 pool minus `qwen3.5-35b-a3b`
  (replaced by `qwen3.6-flash` in the reasoning tier), plus
  `google/gemini-3.1-flash-lite` and `google/gemini-2.5-flash`

`HYPOTHESIS.md` was demoted (Cycle 2 Revised → SUPERSEDED) and a new
authoritative section added (Cycle 2 Re-revised → ACTIVE).

---

## A4 — Explicit reasoning parameter + provider logging

**Trigger.** Routing-variability audit during pre-flight. The same model
identifier returned different reasoning behavior across calls:
`minimax/minimax-m2.5` returned 6,258 reasoning tokens on one call and 0
reasoning tokens on the next, both with identical request body. Source:
OpenRouter routes the same model name to different upstream providers
non-deterministically.

User caught my initial misclassification of `minimax/minimax-m2.5` as
non-reasoning (based on a probe that happened to land on a non-reasoning
upstream): *"I need to challenge you: MiniMax's own docs state M2.5 is a
reasoning model."* The deep probe with explicit `reasoning: {effort: "high"}`
parameter confirmed M2.5 IS reasoning when explicitly requested.

**Decision.** All reasoning-tier calls pass `reasoning: {effort: "high"}`
explicitly. `max_tokens` raised to 10,000 globally (covers reasoning + content
budget across all observed behaviors). The `provider` field returned by
OpenRouter is persisted with each generation record to enable a post-hoc
routing-variability audit if results show anomalous within-model variance.

Without the explicit parameter, the reasoning-tier label is not actually
controlled — it becomes a stochastic property of OpenRouter's routing layer.

---

## A5 — Multi-judge panel + calibration anchor

**Trigger.** Pre-flight Phase D2 ran the redesigned 11-dim rubric (A1) on 32
generations from the reasoning tier, judged by a single judge
(`openai/gpt-4o-mini`). Result: **7 of 9 always-on dimensions saturated at
severity = 0** with positive-toned rationales ("well-organized",
"appropriate", "well-structured"). Only `error_handling_inconsistency`
(43.8% non-zero) and `edge_case_gap` (43.8%) surfaced variation. Failed the
3-of-9 strict gate.

A judge-calibration failure, not a rubric-design failure. The instrument was
the problem.

**Two-part fix.** User chose multi-judge panel + anchor directive (option α
in the AskUserQuestion fork).

1. **Multi-judge panel.** A 3-judge calibration panel
   (gpt-4o-mini + deepseek-v3.2 + mistral-small) was used for the Phase D2
   re-probe; the main-run script restored the full v1-equivalent 10-judge
   cross-judge matrix (`JUDGE_MODELS = ALL_MODELS`). The user caught my
   earlier proposal to use the 3-judge panel in the main run as a v1
   regression: *"Did we use all LLMs in v1?"* Yes. The 3-judge panel was a
   calibration-validation artifact; the main run uses all 10.
2. **Calibration anchor on the rubric judge prompt.** An explicit directive
   was added: *"Severity 0 should be uncommon. Most realistic algorithmic
   code has severity 1–2 on at least 3 of the 9 always-on dimensions. Do
   NOT default to 0 because nothing obvious is wrong."* The anchor text was
   tuned to bind without prescribing the *direction* of preamble effect.

**Validation.** Phase D2 re-probe with the 3-judge panel + anchor passed
all 9 of 9 always-on dimensions at the strict gate. Per-judge saturation
audit:

| Judge | `algorithm_correctness` mean | frac zero |
|---|---|---|
| `openai/gpt-4o-mini` (single judge, no anchor) | 0.12 | 88% |
| `openai/gpt-4o-mini` (with anchor) | 0.12 | 88% |
| `deepseek/deepseek-v3.2` (with anchor) | 1.55 | 21% |
| `mistralai/mistral-small-2603` (with anchor) | 0.75 | 28% |
| Panel mean | 0.77 | — |

**gpt-4o-mini stayed saturated on `algorithm_correctness` even with the
anchor.** The anchor partially binds but does not fully fix this judge on
this dimension. The panel mean recovers the signal: deepseek and mistral
catch algorithmic bugs gpt-4o-mini does not. This is exactly what
cross-judge designs are for, and it justifies the 10-judge matrix in the
main run.

**Reasoning-judge handling.** Reasoning-tier judges run with
`reasoning: {exclude: true}` (judging is a structured fill-the-JSON task;
subject-side reasoning is the variable under test, not judge-side).
Cost-bounds the judge phase at ~$70 vs ~$300 if reasoning were enabled,
and removes a confound (judge reasoning depth) that v1 didn't have.

---

## Pre-flight phase outcomes summary

| Phase | Test | Result | Action |
|---|---|---|---|
| **A** | F1 clamp fix verified on PoC | OOR rate 0 post-fix; CQS-craft restored for affected sample | LOCKED |
| **B** | F2 trap task baseline rate | 0% across all conditions | DROP task |
| **C** | F4 anchored vs unanchored judge prompt on reasoning tier | \|Δ\|<sub>idiom</sub> = 0.31, \|Δ\|<sub>comment</sub> = 0.03; below 0.5 trigger | KEEP unanchored |
| **D** | F5 rubric prevalence with python-coder S3+ checklist | 0 of 11 dims active | REDESIGN rubric (A1) |
| **D2** | F5 prevalence re-test with new rubric + calibration anchor + 3-judge panel | 9 of 9 always-on dims pass strict gate | LOCK rubric + judge protocol (A5) |

All seven debate findings (F1–F7) reached terminal verdict (`critique_wins`,
`defense_wins`, or `empirical_test_agreed`) before main run.

---

## Cost & timing

| Phase | Calls | Cost | Time |
|---|---|---|---|
| PoC | 12 gens + 36 judges | $0.07 | 2 min |
| Phase A (F1 fix verification) | 6 gens + 18 judges | $0.04 | 1 min |
| Phase B (modeflag_sort gate) | 30 gens + 90 judges | $0.21 | 4 min |
| Phase C (anchored/unanchored, embedded in re-probe) | 36 gens + 108 judges | (shared with D2) | (shared) |
| Phase D (S3+ prevalence audit) | 30 gens + 30 judges | $0.18 | 3 min |
| Re-probe (Phase C + D2 single-judge) | 36 gens + 96 judges | $0.46 | 4 min |
| Phase D2 panel re-judge (3 judges, no new gens) | 0 gens + 96 judges | $0.07 | 1 min |
| **Pre-flight total** | **~150 gens + ~470 judges** | **~$1.10** | **~15 min** |
| Main run | 1,260 gens + 24,300 judges | $32.02 | ~85 min |
| Analysis addendum (mixed-effects + sensitivity) | 0 calls | $0.00 | <1 min |
| **Total** | **~1,410 gens + ~24,770 judges** | **~$33** | **~100 min** |

Under the $85 main-run budget envelope by 60%. Pre-flight cost was 3.5% of
main-run cost — well-amortized.

---

## What the pre-flight changed

Five locked-in instrument changes that v1 didn't have:

1. **Rubric scoped to dimensions modern algorithmic LLM code actually varies on**
   (A1). Without this, the per-dimension secondary criterion would have been
   null by construction.
2. **Judge calibration anchor on the rubric prompt** (A5). Without this, gpt-4o-mini
   would have saturated 7 of 9 dimensions at zero and the panel mean would
   have lost most of its information.
3. **Reasoning-inclusive pool with explicit `reasoning: {effort: "high"}` on
   subjects** (A3, A4). Without this, the experiment would have measured
   preamble effects on a population unrepresentative of production agentic
   coding.
4. **`reasoning: {exclude: true}` on reasoning-tier judges** (A5). Without this,
   judge cost would have been ~$300 instead of ~$70, and judge-side reasoning
   depth would have entered as an uncontrolled variable.
5. **Drop-not-clip on judge out-of-range scores with structured OOR log** (Phase A,
   F1 fix). Without this, a transient judge bug (deepseek returning idiom = −1)
   would have silently dragged composite scores downward on affected samples.

The pre-flight invested $1.10 to prevent five measurement failures that would
have collectively rendered the main run un-interpretable. Without the
methodological journey, the v2 design as written in `SPEC_V2.md` at Gate 1
approval would have failed at the instrument layer — the same way v1 did,
just with different specific failure modes.

The investigation followed the ml-lab structured debate workflow with macro-
iteration on user methodological challenge: a defensible pre-registration
deserves a defensible pre-flight.
