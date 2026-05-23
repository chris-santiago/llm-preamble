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

- Detect preamble effects on craft dimensions at adequate statistical power
  (n ≥ 100 valid samples per condition, post-attrition).
- Score specific python-coder / python-review-lite gate dimensions individually,
  with enough resolution to separate conditions per item.
- Test whether a python-coder-agent preamble (a real production system prompt)
  meaningfully differs from the synthetic `real_agent` and `long_directive`
  conditions — directly addressing v1 finding F2's residual ambiguity.
- Stratify per-dimension results by task category (creation vs refactor), since
  v1 evidence suggests preamble leverage is much higher on creation tasks where
  the model has unspecified design discretion.
- Keep static-analysis metrics as a separately-reported diagnostic, no longer
  weighted heavily into the primary metric.

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

### 6.2 Tasks (8 total)

- **Kept from v1** (4): `task_expr_parser`, `task_lru_ttl_cache`,
  `task_flag_class`, `task_exception_pyramid`. Most-discriminating v1 tasks plus
  the two refactor probes that target named S3+ patterns.
- **Replaced**: `task_god_function` is dropped. v1 evidence: it inherited CC
  from input but offered low design discretion (output is constrained to do a
  named decomposition).
- **Added — trap-based refactor probe** (1): `task_modeflag_sort` — request a
  stable-sort implementation with signature `def sort(items, key=None,
  reverse=False, stable=True)`. The `stable` boolean is a python-coder S3+ #1
  violation. Specification does not name this as a smell. Outcome metric: does
  the model implement the spec verbatim (smell present), or design around it
  (smell absent)? Probes preamble-induced resistance to bad API shapes.
- **Added — high-discretion creation** (2): `task_mini_sql_engine` (Table with
  select/where/join/group_by/order_by/limit over dicts; many implicit
  composability choices) and `task_rate_limiter_family` (token bucket / leaky
  bucket / sliding-window-log / sliding-window-counter behind one interface;
  probes abstraction calibration).
- **Added — multi-file** (1): `task_kv_store_package` — implement a small KV
  store as a multi-file package (model returns multiple fenced blocks tagged
  with relative paths). Unlocks measurement of module-organization gate items
  (utility-dump modules, `__all__` curation, public-API leakage). Optional —
  may be deferred if extraction complexity blocks v2 timeline.

Task category labels (`creation` | `refactor` | `multifile_creation`) are
recorded per sample for the §6.5 stratification.

### 6.3 Subject and judge model pool (7)

`deepseek/deepseek-v3.2`, `google/gemma-4-31b-it`, `minimax/minimax-m2.5`,
`mistralai/mistral-small-2603`, `nvidia/nemotron-3-super-120b-a12b`,
`openai/gpt-4o-mini`, `qwen/qwen3.5-35b-a3b`. `x-ai/grok-4.1-fast` is removed
(deprecated mid-v1). A replacement (e.g. `grok-4.3`) may be added; if added, it
joins both subject and judge pools.

### 6.4 Rubric — scoring dimensions

Each judge rates every code sample on each dimension below using a **0–5 severity
scale** (0 = absent / fully clean, 5 = severe / pervasive). Each rating includes
a one-sentence rationale field.

Dimensions inherited from python-coder S3+ checklist and python-review-lite gate,
restricted to those measurable on single-file output (with the multi-file task
unlocking items 12–14):

1. `mode_flag_params` — boolean/mode-flag parameters on public functions
2. `dict_domain_data` — dict-shaped domain data across function boundaries
   where a dataclass / TypedDict / NamedTuple would clarify
3. `hidden_side_effects` — env reads, fs access, embedded logging, global
   mutation in pure-looking helpers
4. `swallowed_excepts` — except clauses that swallow without re-raise or typed
   handling
5. `broad_except` — broad `except Exception` / bare `except:` at library
   boundaries
6. `dead_code` — unused imports, dead branches, unused sentinel returns
7. `orchestration_mixed_with_impl` — one function both coordinating workflow
   and doing low-level transforms inline
8. `overgrown_class` — classes with many methods, weak invariants, or vague
   catch-all names
9. `return_shape_consistency` — sibling functions returning inconsistent shapes
   for similar operations (low-baseline; mostly informative on multi-fn outputs)
10. `type_hint_coverage` — proportion of public functions lacking type hints
    (scored inversely: 0 = full coverage, 5 = none)
11. `exception_drift` — similar failures raising different exception types
    within the same module
12. `utility_dump_modules` — *multi-file only*: new utility functions placed in
    `utils.py` / `common.py` / `helpers.py` rather than by domain
13. `all_curation` — *multi-file only*: top-level names exposed without `__all__`
    curation when `__all__` exists
14. `naming_with_neighbors` — *multi-file only*: inconsistent naming/style
    compared to sibling modules

Dimensions 12–14 are scored only on the multi-file task; on single-file tasks
they are marked N/A and excluded from per-dimension aggregation for those rows.

### 6.5 Primary metric — CQS-craft

```
CQS_craft = w_idiom * idiomaticity + w_comment * comment_quality + w_hygiene * (1 - mean_rubric_severity/5)
where w_idiom + w_comment + w_hygiene = 1.0
      w_hygiene <= 0.10   (static-analysis hygiene weight, capped)
```

The pre-registered primary CQS contains **no static-analysis-derived component**
(radon MI / cyclomatic / Halstead / pylint do not contribute to the headline
metric). The `w_hygiene` term, if used, is derived from the rubric severity panel
itself (not from radon/pylint), bounded at 10%. Static analysis is computed and
reported separately as a diagnostic panel, never as a CQS input.

Default proposed weights: `w_idiom = 0.45`, `w_comment = 0.45`, `w_hygiene = 0.10`.
Sensitivity analysis over weight schemes is reported alongside the primary
result, per v1 precedent — but unlike v1, the pre-registered weighting itself
is craft-heavy.

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
  suffice; if large, escalate to 3. Decided at end of pilot.
