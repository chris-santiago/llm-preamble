# Rubric

The v2 main run scores each generated Python sample on **11 algorithmic-code quality dimensions** at a 0–5 severity scale (0 = clean / no detectable issue, 5 = severe / pervasive). Nine dimensions are **always-on** (every sample is scored on them); two are **conditionally-N/A** (judges return `null` when the dimension does not apply to the code or task).

**Source of truth:** [`preamble_quality_v2_main.py` lines 405–417](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L405) (the `RUBRIC` definition), plus the calibration anchor at [lines 421–437](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L421) and the assembled judge prompt at [lines 440–457](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L440).

The rubric was redesigned during pre-flight Phase D (Amendment A1; see `SPEC_V2.md §6.4`) after the original python-coder S3+ rubric returned 0/11 active dimensions on modern algorithmic code. The calibration anchor (Amendment A5) was added to force judges off a degenerate "score 0 unless something is obviously wrong" default.

---

## The 11 dimensions

### Always-on (9)

| # | ID | What 0–5 severity means |
|---|----|--------------------------|
| 1 | `data_structure_choice` | Inappropriate data structure picks (list for membership testing, dict where dataclass/NamedTuple would clarify, list where deque is the right tool for FIFO). |
| 2 | `algorithm_correctness` | Algorithm fails to meet stated complexity/correctness requirements (wrong output, wrong big-O, breaks on documented edge cases). |
| 3 | `error_handling_inconsistency` | Inconsistent or ad-hoc error handling (some paths raise, others silently return None; sentinels mixed with exceptions; no coherent philosophy). |
| 4 | `api_ergonomics` | Public API is awkward for callers (positional-arg explosion, leaky internals, inconsistent method naming, no kwargs where they'd clarify). |
| 5 | `abstraction_miscalibration` | Over- or under-engineered for the task (speculative class hierarchies for one function; one god-function for what should be 3 cohesive units). |
| 6 | `code_organization` | Tangled decomposition; functions doing too many things; unclear boundaries between layers. |
| 7 | `type_hint_gap` | Public surface lacks correct/complete type annotations (private helpers exempt; 0 = full coverage, 5 = none). |
| 8 | `edge_case_gap` | Obvious edge cases not handled (empty inputs, boundary conditions, invalid inputs). |
| 9 | `documentation_appropriateness` | Docstrings/comments mismatched to code complexity (overly verbose for trivial code, missing for complex code, what-not-why comments). |

### Conditionally-N/A (2)

| # | ID | When `null` is returned |
|---|----|--------------------------|
| 10 | `concurrency_safety` | When the task requires concurrency: race conditions, missing locks, broken async patterns, double-checked-locking bugs. **If the task does NOT involve concurrency, return null.** |
| 11 | `example_quality` | When usage examples are requested: trivial/redundant examples that fail to demonstrate the API's real shape. **If no examples are requested, return null.** |

---

## Severity scale (calibration anchor)

The judge prompt embeds this verbatim calibration anchor:

```
CALIBRATION (READ CAREFULLY):
  - The 0-5 severity scale is NOT 'present vs absent'. It is a graded measure.
  - Severity 0 means 'no detectable issue on this dimension' — uncommon.
    Reserve it for code that is genuinely exemplary on that specific dimension.
  - Severity 1 = a minor nuance (e.g., one type hint missing on a non-public helper;
    one docstring slightly verbose). Most realistic algorithmic code has
    severity 1-2 on AT LEAST 3 of the 9 always-on dimensions.
  - Severity 2-3 = noticeable but not pervasive (e.g., one function mixing two
    concerns; a list used where set would be marginally better).
  - Severity 4-5 = pervasive or material defect.
  - Refuse to score 0 unless you can name a specific reason the code is
    unimprovable on that dimension. Do NOT default to 0 because nothing
    obvious is wrong — score 1 when the dimension is fine-but-not-exemplary.
  - Your job is to surface real variation between samples. If every sample
    gets 0 on most dims, the scoring is useless to the experiment.
```

The conditional-N/A escape is explicit in the prompt body:

> For the two CONDITIONAL dimensions (`concurrency_safety`, `example_quality`), return null only if the dimension does not apply to this code (no concurrency requirement; no examples requested in the task).

---

## How rubric severity enters CQS-craft

For each sample:

1. Cross-judge severities are collected per dimension (self-judgments dropped — see [judge protocol](judge-protocol.md)).
2. Per-judge **mean across rubric dimensions** is computed (dimensions returning `null` are excluded from that judge's mean).
3. The per-judge means are averaged to give `rubric_sev_mean ∈ [0, 5]`.
4. Hygiene is `(1 − rubric_sev_mean / 5)`.
5. CQS-craft = `0.45·(idiom/10) + 0.45·(comment/10) + 0.10·hygiene`.

See [statistical methods](statistical-methods.md) for downstream aggregation and the [results schema](results-schema.md) for where per-dimension means land in the report files.
