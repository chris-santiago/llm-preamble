# Models

The v2 main run uses a **10-model subject pool** that doubles as the **10-model judge panel**. This produces a full cross-judge matrix with self-judgments dropped from primary CQS-craft.

**Source of truth:** [`preamble_quality_v2_main.py` lines 65–88](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L65).

---

## Subject pool

### Reasoning models (3)

```python
REASONING_MODELS = [
    "qwen/qwen3.6-flash",
    "deepseek/deepseek-v4-flash",
    "minimax/minimax-m2.5",
]
```

These models receive `reasoning: {effort: "high"}` on every generation call ([`preamble_quality_v2_main.py:655–659`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L655)). Reasoning-effort is a property of the subject under test, not a control variable.

### Non-reasoning models (7)

```python
NON_REASONING_MODELS = [
    "deepseek/deepseek-v3.2",
    "google/gemma-4-31b-it",
    "mistralai/mistral-small-2603",
    "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-4o-mini",
    "google/gemini-3.1-flash-lite",
    "google/gemini-2.5-flash",
]
```

These models receive no `reasoning` parameter — the field is omitted from the request body entirely.

The pool was widened from 7 (non-reasoning only) to 10 during pre-flight Amendment A3 after a methodological challenge that "a non-reasoning-only pool answers a question of low production relevance." A4 then added the explicit `reasoning: {effort: "high"}` parameter after a routing-variability audit found that the same model identifier could return different reasoning behavior across calls.

---

## Reasoning-parameter handling

Three modes are sent on the wire, distinguished by [`_post()`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L568) at lines 590–594:

| Mode | When used | Body field |
|------|-----------|------------|
| `high` | Generation by a reasoning subject | `"reasoning": {"effort": "high"}` |
| `exclude` | Judging by a reasoning judge | `"reasoning": {"exclude": true}` |
| `off` | All non-reasoning calls (subjects and judges) | (field omitted) |

The `exclude` mode on the judge side ([`preamble_quality_v2_main.py:690`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L690)) reflects that judging is a structured fill-the-JSON task and **judge-side reasoning is not the variable under test**. The judge prompt is identical across tiers; only the wire-level reasoning flag differs.

---

## Cross-judge matrix

All 10 models judge every non-self extracted sample on both `idiom_comment` and `rubric` kinds:

```python
SUBJECT_MODELS = ALL_MODELS    # 10
JUDGE_MODELS   = ALL_MODELS    # 10 (full v1-equivalent cross-judge matrix)
```

Each extracted generation produces 10 judges × 2 kinds = **20 judge calls**, of which 2 are same-family self-judgments that are dropped from primary CQS (see below).

**Total scale of the run.** 1260 generations × 2 judge kinds × 10 judges = 25,200 nominal judge calls; in practice 24,300 judge calls were issued (extraction failures skip judging). 22,028 parsed cleanly. See [`experiment_v2_results/REPORT.md`](../../preamble_quality_experiment_v2/experiment_v2_results/REPORT.md).

---

## Self-judgment exclusion

A judgment is **self** if the subject model and judge model share a provider-prefix family. The family helper is just `model.split("/", 1)[0]`:

```python
def model_family(model: str) -> str:
    return model.split("/", 1)[0]
```

So `deepseek/deepseek-v3.2` judged by `deepseek/deepseek-v4-flash` counts as a self-judgment and is excluded from primary CQS. The full self/cross stratification is retained in the report for F3 hygiene checking.

| Subject family | Models in family (both tiers) |
|----------------|-------------------------------|
| `qwen` | `qwen/qwen3.6-flash` |
| `deepseek` | `deepseek/deepseek-v4-flash`, `deepseek/deepseek-v3.2` |
| `minimax` | `minimax/minimax-m2.5` |
| `google` | `google/gemma-4-31b-it`, `google/gemini-3.1-flash-lite`, `google/gemini-2.5-flash` |
| `mistralai` | `mistralai/mistral-small-2603` |
| `nvidia` | `nvidia/nemotron-3-super-120b-a12b` |
| `openai` | `openai/gpt-4o-mini` |

Notably, the `deepseek` and `google` families each have multiple models — cross-family judgments within those families (e.g. `deepseek-v3.2` judging `deepseek-v4-flash`) are still treated as self-judgments and excluded. See the [glossary](glossary.md#self-judgment-exclusion) and [judge protocol](judge-protocol.md) for the downstream consequences.
