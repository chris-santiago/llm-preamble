# Judge protocol

This page documents how a v2 judgment is produced: what the judge sees, what it doesn't see, and how its output enters CQS-craft.

**Source of truth:**

- Main-run judge call: [`preamble_quality_v2_main.py:621–630`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L621) (the `_post()` return) and [`judge_one()` at lines 685–713](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L685).
- Confound-probe judge call: [`confound_probes.py:341–362`](../../preamble_quality_experiment_v2/confound_probes.py#L341).
- Methodology summary: [README "Methodology in brief"](../../README.md) and [CONCLUSIONS.md "Methodology note — judges are blind to preambles"](../../preamble_quality_experiment_v2/CONCLUSIONS.md).

---

## Judge blindness

Across the v2 main run, the five pre-flight phases, and the three confound probes, **judges never see preamble information.** The judge call constructs its messages from a fixed template:

```python
async def judge_one(client, sem, *, gen_record, judge_model, kind):
    prompt = RUBRIC_JUDGE_PROMPT if kind == "rubric" else IDIOM_COMMENT_PROMPT
    user = f"Code under review:\n\n```python\n{gen_record['code']}\n```"
    ...
```

What the judge receives:

- **System message:** either the rubric prompt (`RUBRIC_JUDGE_PROMPT`, with the [calibration anchor](rubric.md#severity-scale-calibration-anchor)) or the idiom-comment prompt — both fixed templates that contain no preamble, condition label, subject-model identity, or original task prompt.
- **User message:** literally `"Code under review:\n\n```python\n{code}\n```"` — fenced extracted code, nothing else.

What the judge does **not** receive: the preamble text, the condition ID (`none`, `long_directive`, etc.), the subject model name, the task prompt, the rep index, or any other generation metadata.

This blindness is what licenses the "H-judge-priming" hypothesis to be about code-level surface markers, not leaked preamble information — see [CONCLUSIONS.md §"Methodology note"](../../preamble_quality_experiment_v2/CONCLUSIONS.md).

---

## Two judge kinds

Each extracted generation is judged on **both** kinds:

| Kind | System prompt | Output schema |
|------|---------------|---------------|
| `idiom_comment` | `IDIOM_COMMENT_PROMPT` (unanchored; Phase C resolved) | `{"idiomaticity": <1-10>, "comment_quality": <1-10>}` |
| `rubric` | `RUBRIC_JUDGE_PROMPT` (calibration-anchored; 11 dims) | `{"<dim_id>": {"severity": <0-5 or null>, "rationale": "<one sentence>"}, ...}` |

The decision to keep the idiom_comment prompt **unanchored** for the main run is the Phase C resolution of F4 — see [CONCLUSIONS.md F4](../../preamble_quality_experiment_v2/CONCLUSIONS.md) (pooled |Δ| 0.31 on idiom, 0.03 on comment between anchored and unanchored re-probe; both below the 0.5 trigger).

Judges return strict JSON with no markdown fences and no prose; the response is parsed with a greedy `\{.*\}` regex (`_extract_json` at [line 535](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L535)). Parse failures are logged and excluded from aggregation.

---

## Cross-judge matrix

All 10 models judge every non-self extracted sample on both kinds. The full 10×10 (subject × judge) judging surface is:

```
           subjects →
judges ↓   qwen  ds-v4  mm  ds-v3.2  gemma  mistral  nemotron  4o-mini  flite  g2.5
qwen        S      C    C     C       C       C        C         C       C      C
ds-v4       C      S    C     S*      C       C        C         C       C      C
minimax     C      C    S     C       C       C        C         C       C      C
ds-v3.2     C      S*   C     S       C       C        C         C       C      C
gemma       C      C    C     C       S*      C        C         C       S*     S*
mistral     C      C    C     C       C       S        C         C       C      C
nemotron    C      C    C     C       C       C        S         C       C      C
gpt-4o-mini C      C    C     C       C       C        C         S       C      C
g-flite     C      C    C     C       S*      C        C         C       S      S*
g-2.5       C      C    C     C       S*      C        C         C       S*     S
```

`S` = self (same model), `S*` = self by family (cross-family within a provider prefix; e.g. `deepseek-v3.2` ↔ `deepseek-v4-flash`, gemma ↔ gemini), `C` = cross. **All S and S\* judgments are excluded from primary CQS-craft.** Cross-judgments only enter the aggregate.

Self-vs-cross stratification is retained for F3 hygiene reporting; the empirical effect is small (idiom Δ +0.02 with p ≈ 3×10⁻⁴, comment Δ +0.29 with p < 10⁻⁴ — present but not enough to threaten the headline). See [CONCLUSIONS.md F3](../../preamble_quality_experiment_v2/CONCLUSIONS.md) and the [glossary entry](glossary.md#self-judgment-exclusion).

The family-membership rule is the provider prefix:

```python
def model_family(model: str) -> str:
    return model.split("/", 1)[0]
```

See the full family table on the [models page](models.md#self-judgment-exclusion).

---

## Reasoning-parameter handling for judges

Reasoning judges receive `reasoning: {exclude: true}`; non-reasoning judges receive no reasoning field at all. Judging is a structured fill-the-JSON task — judge-side reasoning is not the variable under test. See [models page](models.md#reasoning-parameter-handling) for the wire-level details.

---

## Generation parameters for judges

- `temperature = 0.0` (`JUDGE_TEMPERATURE`)
- `max_tokens = 1800` (`JUDGE_MAX_TOKENS`)
- `timeout = 120.0 s` (`JUDGE_TIMEOUT`)
- `retry_attempts = 2`

See [generation protocol](generation-protocol.md) for the full set of constants and how they compare to subject-side generation.

---

## Calibration anchor

The rubric judge prompt embeds the verbatim calibration anchor — see the [rubric page](rubric.md#severity-scale-calibration-anchor) for the full text. The anchor was added as Amendment A5 after pre-flight Phase D found that, without it, judges defaulted to a degenerate "score 0 unless something is obviously wrong" pattern.
