# Preamble Quality Experiment v2 — Design Spec

**Status:** design — pre-registration input for an `/ml-lab` investigation.
**Predecessor artifacts:** `HYPOTHESIS.md`, `CONCLUSIONS.md`, `REPORT_ADDENDUM.md`,
`RELATED_WORK.md`. The v1 conclusions are the empirical basis for every change
here; this spec does not re-derive them.

## 1. Scope

A second-cycle experiment that re-tests whether coding-agent preambles change the
quality of LLM-generated Python code, with the measurement instrument, sample size,
condition set, and rubric corrected per the v1 findings. The unit of inquiry is
single-turn Python generation across 9 preamble conditions, 7 LLM subject models,
and a revised hard-task set; primary scoring is LLM-judge based, decomposed into
per-dimension severity ratings drawn from the `chris-code` python-coder agent's
operational quality gate.

## 2. Goals

- Test the v1 hypothesis — preambles change craft quality — under a corrected
  instrument. Primary contrast: any rich preamble vs. `none` vs.
  `negative_control`. Detect preamble effects on craft dimensions at adequate
  statistical power (n ≥ 100 valid samples per condition, post-attrition).
- Score specific python-coder / python-review-lite gate dimensions individually,
  with enough resolution to separate conditions per item.
- Stratify per-dimension results by task category (creation vs refactor), since
  v1 evidence suggests preamble leverage is much higher on creation tasks where
  the model has unspecified design discretion.
- Keep static-analysis metrics as a separately-reported diagnostic, no longer
  weighted heavily into the primary metric.
- Broaden the "rich preamble" condition pool to include one real production
  system prompt verbatim (`python_coder_agent`), increasing external validity.
  This condition is one rich-preamble data point — *not* a contrast being
  tested for itself. v2 does not adjudicate whether `python_coder_agent` is
  better than other rich preambles.

## 3. Non-goals

- Re-litigating v1's structural decisions (cross-judge matrix, percentile
  normalization, F3 self-preference stratification methodology) — these remain.
- Multi-turn / agentic evaluation. v2 is still single-turn generation.
- Production preamble *content optimization*. v2 measures the effect; it does not
  search the preamble space for an optimum.
- Cross-language testing. Python only.
- Functional correctness benchmarking (pass@k on test suites). v2 measures craft,
  not whether code runs.

## 4. System behavior

A single experiment run produces, per (condition × model × task × replication):
generated code, per-dimension severity scores from a multi-judge panel, optional
static-analysis diagnostics, and a metadata trail sufficient to re-derive every
statistic.

Aggregate outputs include: per-condition CQS-craft point estimates with bootstrap
CIs, per-dimension Kruskal–Wallis tests stratified by creation vs refactor, a
mixed-effects model treating subject model as a random effect, and a self-vs-cross
judge stratification report (the F3 hygiene check from v1).

Generations that fail extraction or return API errors are logged and excluded from
scoring rather than scored as zero. The replication count per cell must be set high
enough that, after expected attrition rates from v1 (~25% on weak models), each
condition still has ≥100 valid samples.

## 5. Architecture

Three logical components, in pipeline order:

1. **Generation** — given (task prompt, preamble, model, replication seed),
   produce a single Python code response. Replications use distinct seeds and a
   non-zero temperature to elicit independent samples.
2. **Static diagnostics** — run radon (MI, cyclomatic complexity, Halstead),
   pylint, and PEP8 name-compliance on each extracted code sample. Outputs are
   reported as a diagnostic panel, not as primary scoring inputs.
3. **Rubric judging** — each code sample is judged on the dimension list in §6
   by a panel of ≥3 cross-judges from the working model pool. The panel must not
   include the subject model that produced the sample (self-judgments excluded
   from primary scoring).

Aggregation, statistics, figure generation, and persistence to the existing
`experiment2_results/`-style layout follow the v1 pattern.

## 6. Canonical interfaces / data contracts

### 6.1 Preamble conditions (9 total)

The 8 v1 conditions are kept verbatim: `none`, `minimal`, `generic_coding`,
`real_agent`, `negative_control`, `persona_only`, `long_directive`,
`trivial_baseline`. One condition is added:

- **`python_coder_agent`** — the full system prompt of the `chris-code`
  python-coder agent (`agents/python-coder.md`), with file-system-specific lines
  removed where they reference tools not present in single-turn generation
  (e.g. test-runner invocation, commit boundaries). The "operating principles,"
  "S3+ patterns to avoid," "Pythonic design standards," and "refactoring
  heuristics" sections are preserved as the preamble text. This is the only
  condition that uses a real production preamble verbatim.

### 6.2 Tasks (7 total)

> **Amendment A2 (2026-05-22):** `task_modeflag_sort` (trap-based refactor)
> dropped. Pre-flight Phase B found the behavior-only specification produced
> **0% baseline rate** of the `mode_flag_params` smell across all conditions:
> the spec successfully refused to name the trap, but in doing so eliminated
> the discriminative space. No condition produced the smell, so no condition
> can resist it. Task count drops 8 → 7. Pre-registered recovery (drop the
> task) per SPEC §11's branching plan.

- **Kept from v1** (4): `task_expr_parser`, `task_lru_ttl_cache`,
  `task_flag_class`, `task_exception_pyramid`. Most-discriminating v1 tasks plus
  the two refactor probes that target named S3+ patterns.
- **Replaced**: `task_god_function` is dropped. v1 evidence: it inherited CC
  from input but offered low design discretion (output is constrained to do a
  named decomposition).
- **Added — high-discretion creation** (2): `task_mini_sql_engine` (Table with
  select/where/join/group_by/order_by/limit over dicts; many implicit
  composability choices) and `task_rate_limiter_family` (token bucket / leaky
  bucket / sliding-window-log / sliding-window-counter behind one interface;
  probes abstraction calibration).
- **Added — multi-file** (1): `task_kv_store_package` — implement a small KV
  store as a multi-file package (model returns multiple fenced blocks tagged
  with relative paths). Retained at user override of original "optional"
  framing (D11).

Task category labels (`creation` | `refactor` | `multifile_creation`) are
recorded per sample for the §6.5 stratification.

### 6.3 Subject and judge model pool (10)

> **Amendment A3 (2026-05-22):** The pool was macro-iterated from the original
> 7 non-reasoning models to a 10-model **reasoning-inclusive** pool. Rationale:
> agentic coding frameworks in production overwhelmingly use reasoning models,
> so a non-reasoning-only pool answers a question of low practical relevance.
> The amendment widens the outcome to "preambles in production-realistic
> model populations" and **stratifies the analysis by reasoning/non-reasoning
> tier** so the v1 question can still be answered within the non-reasoning
> sub-pool.

**Reasoning tier (3):**

- `qwen/qwen3.6-flash`
- `deepseek/deepseek-v4-flash`
- `minimax/minimax-m2.5`

**Non-reasoning tier (7):**

- `deepseek/deepseek-v3.2`
- `google/gemma-4-31b-it`
- `mistralai/mistral-small-2603`
- `nvidia/nemotron-3-super-120b-a12b`
- `openai/gpt-4o-mini`
- `google/gemini-3.1-flash-lite`
- `google/gemini-2.5-flash`

`x-ai/grok-4.1-fast` removed (deprecated mid-v1). `qwen/qwen3.5-35b-a3b`
replaced by the newer `qwen3.6-flash` (reasoning-capable) per user direction.

**Generation parameters:** all calls use `max_tokens=10000`. Reasoning-tier
models receive an explicit `reasoning: {effort: "high"}` parameter; this is
required because OpenRouter routes the same model identifier to different
upstream providers across calls (verified mid-pre-flight), and the explicit
parameter is the only way to guarantee reasoning is enabled. Non-reasoning
models receive no `reasoning` parameter. The `provider` field returned by
OpenRouter is persisted with each generation record to support a post-hoc
routing-variability audit.

**Stratification:** primary CQS-craft analysis is reported (a) pooled across
the full 10-model pool, (b) within the non-reasoning sub-pool only
(reproducing the v1 question), and (c) within the reasoning sub-pool only
(the production-realistic regime). Cross-tier effect-size deltas are
reported as a separate panel.

### 6.4 Rubric — scoring dimensions

> **Amendment A1 (2026-05-22):** The rubric in this section was redesigned after
> the Phase D pre-flight prevalence audit found **0 of 11 python-coder S3+
> dimensions active** on algorithmic LLM output (modern models essentially
> never emit `mode_flag_params`, `bare_except`, `dict_domain_data`, etc. on
> hard algorithmic tasks). The old 14-dimension list is preserved in §12
> Amendment Log for the pre-reg record. The redesigned rubric below targets
> dimensions algorithmic Python code *actually varies on* and is the
> authoritative scoring instrument.

Each judge rates every code sample on each dimension below using a **0–5 severity
scale** (0 = clean / no issue with this dimension, 5 = severe / pervasive). Each
rating includes a one-sentence rationale field.

Single-file dimensions (scored on every task):

1. `data_structure_choice` — inappropriate data structures (list where set is
   needed for membership; dict where a dataclass / NamedTuple would clarify;
   list where deque is the right tool for FIFO; etc.)
2. `algorithm_correctness` — algorithm fails to meet the stated complexity /
   correctness requirements (wrong output, wrong asymptotic behavior vs
   stated constraint, breaks on documented edge cases)
3. `error_handling_inconsistency` — inconsistent or ad-hoc error handling
   (some paths raise, others silently return `None`; sentinels mixed with
   exceptions; no coherent philosophy)
4. `api_ergonomics` — public API is awkward for callers (positional-arg
   explosion; leaky internals; inconsistent method naming; no kwargs where
   they would clarify)
5. `abstraction_miscalibration` — over- or under-engineered for the task
   (speculative class hierarchies for a single function; one god-function
   for what should be 3 cohesive units)
6. `code_organization` — tangled decomposition; functions doing too many
   things; unclear boundaries between layers
7. `type_hint_gap` — public surface lacks correct / complete type
   annotations (private helpers exempt; scored inversely: 0 = full coverage
   on public API, 5 = none)
8. `edge_case_gap` — obvious edge cases not handled (empty inputs, boundary
   conditions, invalid inputs)
9. `documentation_appropriateness` — docstrings / comments mismatched to
   code complexity (overly verbose for trivial code; missing for complex
   code; what-not-why comments)

Conditional dimensions (scored where the task elicits them; otherwise N/A):

10. `concurrency_safety` — *only on tasks requiring concurrency* (e.g.
    `task_lru_ttl_cache`, `task_rate_limiter_family`): race conditions,
    missing locks, broken async patterns, double-checked-locking bugs
11. `example_quality` — *only on tasks that request usage examples*:
    trivial / redundant examples that fail to demonstrate the API's real
    shape

Conditional dimensions are marked N/A on tasks that don't elicit them and
excluded from per-dimension aggregation for those rows. The multi-file task
uses the same 11-dim rubric — earlier-cycle multi-file-specific items
(`utility_dump_modules`, `all_curation`, `naming_with_neighbors`) are dropped
in this amendment; module organization is now folded into the more general
`code_organization` dimension.

### 6.5 Primary metric — CQS-craft

```
CQS_craft = w_idiom * idiomaticity + w_comment * comment_quality + w_hygiene * (1 - mean_rubric_severity/5)
where w_idiom + w_comment + w_hygiene = 1.0
      w_hygiene <= 0.10   (rubric-severity weight, capped)
      mean_rubric_severity = mean over the §6.4 dimensions scored on this sample
                             (N/A dimensions excluded from the mean per-row)
```

The pre-registered primary CQS contains **no static-analysis-derived component**
(radon MI / cyclomatic / Halstead / pylint do not contribute to the headline
metric). The `w_hygiene` term is derived from the **§6.4 redesigned 11-dim
algorithmic-code rubric**, bounded at 10% influence on the composite. Static
analysis is computed and reported separately as a diagnostic panel, never as
a CQS input.

Default pre-registered weights: `w_idiom = 0.45`, `w_comment = 0.45`,
`w_hygiene = 0.10`. Sensitivity analysis over weight schemes is reported
alongside the primary result, per v1 precedent — but unlike v1, the
pre-registered weighting itself is craft-heavy.

## 7. Invariants and constraints

- **Pre-registration boundary:** §6.1 (conditions), §6.2 (task IDs), §6.5
  (metric formula and weights) are locked at the start of generation. Any
  amendment after generation begins must be logged as a documented
  pre-registration drift event with rationale.
- **Self-judgment exclusion:** judges scoring code produced by their own model
  family are excluded from primary CQS computation; the self-vs-cross delta is
  reported as a hygiene check per v1's F3 methodology.
- **Power floor:** if any condition ends with fewer than 60 valid post-attrition
  samples, results for that condition are reported but flagged as
  underpowered; conclusions are restricted to conditions clearing 100.
- **Extraction fidelity:** code that cannot be extracted from a model response
  is logged with a non-empty raw-response preview and excluded from scoring.
  Never scored as zero.
- **Reproducibility:** replication seeds, temperature, model versions, and
  preamble text hashes are persisted with each generation record.

## 8. Key decisions and tradeoffs

- **Static metrics out of primary metric.** v1 showed they are flat across
  preamble conditions (KW p = 0.998), mis-rank known-quality code in
  sensitivity probing, and dilute LLM-judge signal. Demoting them to a
  diagnostic panel is the central instrument-correction.
- **Severity 0–5, not binary.** v1 rubric collapsed each smell to {0, 1} and
  detected no significant per-item effect despite directional consistency and
  large effect sizes (e.g. `dict_domain` halved from 0.45 → 0.21). Severity
  preserves the resolution where most preamble-induced change actually lives —
  smells of degree, not presence/absence.
- **n ≈ 100/arm, achieved via replication, not condition expansion.**
  Replicating each cell with distinct seeds is cheaper than adding tasks and
  preserves task balance. Estimated scale: 9 conditions × 7 models × 8 tasks ×
  ~2 replications ≈ 1,008 generations and ~3,000 judge calls — well within v1
  cost envelope.
- **python_coder_agent as a real preamble.** The v1 `real_agent` and
  `long_directive` conditions are synthetic condensations. v1's F2 finding was
  partially confirmed (priming alone helps, instruction-richness adds more) but
  with limited external validity. Including a verbatim production system
  prompt directly closes that gap.
- **Trap-based task replaces god-function refactor.** v1 refactor prompts
  *named* the target smell, so all conditions removed it; preamble could only
  affect peripheral choices. The mode-flag-sort trap is a single-axis probe
  that should respond strongly to preamble-induced resistance.
- **Creation-vs-refactor stratification is required, not optional.** v1
  evidence: refactor tasks constrain output; creation tasks expose discretion.
  Reporting one pooled per-dimension number obscures the most likely place
  preambles bite.
- **Multi-file task is optional.** Unlocks 3 gate dimensions but adds
  extraction complexity and judge-prompt length. If retained, it counts as a
  single task in the n calculation but its rubric rows include items 12–14.

## 9. Acceptance criteria

- Every condition in §6.1 has ≥100 valid post-attrition samples; no condition
  has fewer than 60.
- The 14-dimension rubric is reported with KW p-values and severity means per
  condition, stratified by task category (creation, refactor; plus
  multifile_creation if §6.2's multi-file task ships).
- The pre-registered CQS-craft is reported with bootstrap CIs and a
  mixed-effects model (`CQS_craft ~ preamble + (1|model) + (1|task)`).
- Self-vs-cross judge stratification is reported per v1's F3 methodology.
- Static-analysis diagnostics (MI, CC, pylint penalty, PEP8 name-compliance)
  are reported as a separate panel with their own KW tests, explicitly labeled
  as diagnostic — not primary.
- A re-weighting sensitivity table is included, demonstrating how the primary
  result changes under alternative weight schemes (including v1's
  static-heavy pre-registration as a documented contrast).
- All v1 findings (F1–F7) have explicit verdict updates: still confirmed,
  resolved, refuted, or unchanged.

## 10. Validation strategy

- **Power calibration before main run.** A pilot of ~30 generations covering
  the new tasks and `python_coder_agent` condition confirms the rubric judges
  produce non-degenerate severity distributions on each dimension (not all 0,
  not all 5).
- **Rubric calibration probe.** A handful of hand-authored Python samples with
  known smells (one per dimension, exhibiting that smell at known severity)
  are scored before the main run. If judges cannot rank known-severity samples
  monotonically per dimension, that dimension is flagged as low-validity for
  the run.
- **Extraction-failure audit.** Per-model, per-task extraction failure rates
  are reported; any model exceeding 20% extraction failure on a task is
  flagged as a data-quality limitation in the conclusion.
- **Trap-task verification.** For `task_modeflag_sort`, the trap-resistance
  measurement is the per-condition rate of `mode_flag_params` severity ≥ 3
  ("clearly violates"). This is a single-dimension power-focused readout.

## 11. Open questions

- **Multi-file task in v2 or v3?** Including it adds significant extraction
  and judge-prompt complexity. Recommended decision point at the end of pilot:
  if extraction succeeds on ≥80% of pilot multi-file responses, include;
  otherwise defer.
- **`python_coder_agent` preamble length budget.** The full agent prompt is
  ~3,000 tokens. If model context limits or per-call cost concerns surface
  during pilot, a budgeted abridgment (preserving operating principles + S3+
  checklist; trimming refactoring heuristics table) is permissible —
  documented at pre-registration.
- **Replication count.** Default 2 replications/cell. If pilot shows
  within-cell variance is small relative to between-condition variance, 1 may
  suffice; if large, escalate to 3. Decided at end of pilot. **Resolved at
  Gate 1 → 3 replications (D10 override).** **Re-resolved post-pool macro-
  iteration (A3) → 2 replications.** Reason: with the 10-model pool,
  n_per_condition = 10 × 7 × 2 = 140 raw → ~105 post 25% attrition, clearing
  the §7 power floor of 100 with margin. The D10 override was sized for the
  original 7-model pool where R=3 was needed to reach n≥100; the larger
  pool absorbs the same statistical role at lower replication. Between-model
  variance (10 models) does the external-validity work; within-cell
  replication captures residual variance for the mixed-effects model and
  bootstrap CIs, which R=2 supplies.

## 12. Amendment log (pre-registration drift events)

All amendments below are logged under SPEC §7's "documented pre-registration
drift event" provision. Each entry names the trigger, the change, and the
rationale.

### A1 — Rubric redesign (2026-05-22) — `§6.4`

**Trigger:** Pre-flight Phase D prevalence audit, 0 of 11 python-coder S3+
rubric dimensions active on algorithmic LLM output (n=30 generations across
the model pool). The dimensions encode patterns that modern instruction-tuned
LLMs essentially never produce on algorithmic tasks (`mode_flag_params`,
`bare_except`, `dict_domain_data`, `swallowed_excepts`, etc.). Per-dimension
KW tests would have been null by construction.

**Change:** Replaced 14-dim S3+ rubric with 11-dim algorithmic-code rubric
targeting dimensions algorithmic code actually varies on (data structure
choice, algorithm correctness, error-handling philosophy, API ergonomics,
abstraction calibration, code organization, type-hint gap, edge-case gap,
concurrency safety, example quality, documentation appropriateness).
Conditional dimensions (`concurrency_safety`, `example_quality`) are
N/A-coded on tasks that don't elicit them.

**Old rubric (preserved):**
`mode_flag_params`, `dict_domain_data`, `hidden_side_effects`,
`swallowed_excepts`, `broad_except`, `dead_code`,
`orchestration_mixed_with_impl`, `overgrown_class`,
`return_shape_consistency`, `type_hint_coverage`, `exception_drift`,
`utility_dump_modules`, `all_curation`, `naming_with_neighbors`.

**Rationale:** The instrument must measure dimensions the population varies
on, otherwise the per-dimension secondary criterion is null by construction
regardless of preamble effect. The redesigned rubric preserves the 0–5
severity scale, the cross-judge panel, and the same role in CQS-craft —
only the dimension set changes.

### A2 — Drop `task_modeflag_sort` (2026-05-22) — `§6.2`

**Trigger:** Pre-flight Phase B, behavior-only mode-flag-sort specification
yielded 0% baseline rate of the `mode_flag_params` smell across all
conditions. Behavior-only framing successfully refused to name the trap but
in doing so eliminated the discriminative space — no condition produced the
smell, so no condition can resist it.

**Change:** Task dropped from §6.2. Total tasks 8 → 7. The behavior-only
framing was the correct choice (the alternative — naming the smell — would
have measured compliance with explicit instructions, not preamble effect);
the test simply has no signal to read in this design.

**Rationale:** Pre-registered branching recovery clause in original SPEC §11
covered this contingency; no Gate 1 reopen required.

### A3 — Pool macro-iteration to reasoning-inclusive (2026-05-22) — `§6.3`

**Trigger:** User methodological challenge: a non-reasoning-only pool answers
a question of low practical relevance because agentic coding frameworks in
production overwhelmingly use reasoning models.

**Change:** Pool expanded from 7 non-reasoning models to 10 models stratified
across a 3-model reasoning tier and a 7-model non-reasoning tier. Analysis
stratified by tier so v1's original question (preamble effects on
non-reasoning models) is still answerable within the non-reasoning sub-pool,
while the headline result speaks to the production-realistic regime.

**Rationale:** External-validity gap. The earlier pool answered a question
the user does not have. Stratified analysis preserves both questions.

### A5 — Multi-judge panel + calibration anchor on rubric prompt (2026-05-22) — `§6.4`

**Trigger:** Phase D2 re-probe with single judge (gpt-4o-mini) on the
redesigned 11-dim rubric: 7 of 9 always-on dimensions saturated at severity=0
with positive-toned rationales ("well-organized", "appropriate"). Only
`error_handling_inconsistency` (43.8%) and `edge_case_gap` (43.8%) surfaced
variation. Single-judge calibration failure, not a rubric-design failure.

**Change:**

1. Rubric scoring uses the **full v1-equivalent cross-judge matrix**:
   all 10 models in the §6.3 pool serve as judges (`JUDGE_MODELS =
   ALL_MODELS`, matching the v1 design). Cross-judge mean severity is
   computed per `(sample, dimension)` over the 9 non-self judges. The v1
   self-judgment-exclusion rule applies — judges scoring code produced by
   their own model family are excluded from primary CQS computation but
   their scores are retained for the self-vs-cross stratification report
   (F3 hygiene).
2. **Reasoning-tier judges run with `reasoning: {exclude: true}`** —
   reasoning models judge as standard judges (no reasoning token budget).
   Justification: judging is a structured fill-the-JSON task; subject-side
   reasoning behavior is the variable under test, not judge-side. Keeps
   the judge instrument cost-bounded (~$120 total vs ~$300 with reasoning
   enabled) and removes a confound (judge reasoning depth) that v1 didn't
   have.
3. **Calibration anchor** added to the rubric judge prompt: explicit
   directive that "severity 0 means no detectable issue and should be
   uncommon; realistic algorithmic code typically has severity 1-2 on at
   least 3 of the 9 always-on dimensions; do not default to 0 because
   nothing obvious is wrong". The full anchor text is preserved in
   `rejudge_phase_d2.py` and reproduced verbatim in the main-run script.

**Verification:** Phase D2 re-probe with a 3-judge calibration panel
(gpt-4o-mini + deepseek-v3.2 + mistral-small) passed all 9 of 9 always-on
dimensions at the strict gate (panel mean ≥1.0 on ≥10% of samples). The
3-judge panel was a calibration-validation artifact only; the main-run
panel is the full 10-judge cross-judge matrix. Per-judge saturation audit
on the 3-judge probe: gpt-4o-mini partially saturates on
`algorithm_correctness` (88% zero) and `abstraction_miscalibration` (66%
zero); deepseek-v3.2 (21% zero, mean 1.55) and mistral-small recover the
variation in cross-judge mean. The full 10-judge pool has stronger panel
diversity than the 3-judge probe by construction.

**Rationale:** The instrument was the problem, not the dimensions. The
full cross-judge matrix restores the v1 design that was already validated;
the calibration anchor is the one prompt-level tweak the v1 instrument
didn't have. `reasoning: {exclude: true}` on judge-side keeps subject-side
reasoning as the only deliberate reasoning-tier variable.

### A4 — Explicit `reasoning` parameter and provider logging (2026-05-22) — `§6.3`

**Trigger:** OpenRouter routing-variability audit during pre-flight: the
same model identifier returns different reasoning behavior across calls (one
call to `minimax/minimax-m2.5` returned 6,258 reasoning tokens; another
returned 0). Source: upstream-provider routing variability not controlled by
the model identifier.

**Change:** All reasoning-tier calls pass `reasoning: {effort: "high"}`
explicitly. `max_tokens` raised to 10,000 globally (covers reasoning + content
budget for all observed model behaviors). The `provider` field returned by
OpenRouter is persisted with each generation record.

**Rationale:** Without the explicit parameter, the reasoning-tier label is
not actually controlled — it becomes a stochastic property of OpenRouter's
routing layer. The post-hoc provider log enables a routing-variability
audit if results show anomalous within-model variance.
