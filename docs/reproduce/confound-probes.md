# Confound probes

The three post-hoc confound probes — A, B, C — are run by a single script: [`confound_probes.py`](https://github.com/chrissantiago/llm-preamble/blob/main/preamble_quality_experiment_v2/confound_probes.py). They were added after the main run to distinguish two indistinguishable predictions of the main result: an `H-mechanism` story (preambles change code-craft) vs. an `H-judge-priming` story (preambles align the model's surface markers to the enumerated rubric dimensions). The probes use the [main run's](main-run.md) judge panel and rubric verbatim — same 10-judge cross-judge matrix, same self-exclusion, same calibration anchor, reasoning judges with reasoning excluded.

## Command

```bash
uv run preamble_quality_experiment_v2/confound_probes.py
```

**Prerequisite:** `OPENROUTER_API_KEY` set, and the main run's `experiment_v2_results/{generations.jsonl, judgments.jsonl, sample_cqs.json}` already exist (the probes pull reference-condition stats from the main-run data).

**Expected runtime and cost.** ~5 minutes wall-clock at concurrency=50, ~$3–5 (the actual run came in at $1.04).

## What the three probes test

All three are run on `task_expr_parser` (a creation task that elicits all 9 always-on rubric dimensions plus `example_quality`, but not `concurrency_safety`). Subjects: all 10 v2 main-run models. n=10 generations per probe under the full 10-judge cross-judge panel.

| Probe | Preamble shape | What it isolates |
|---|---|---|
| **A — `long_directive_misaligned`** | Same length + expert tone as `long_directive`, but 12 clauses naming axes *not* in the rubric (compactness, performance, determinism, etc.). | If CQS-craft stays substantially above `none`, expert-framed directive priming has effect beyond rubric-naming. If it drops below, rubric-overlap is doing the work. |
| **B — `rubric_bare_list`** | Just the rubric items as a bare enumerated list — no engineering-discipline framing. | If this matches `long_directive`, naming the rubric items *is* the whole effect. If it falls short, imperative tone + framing contribute too. |
| **C — `antirubric_directive`** | Same expert framing, but clauses explicitly **deprioritize** the rubric items (no docstrings, no type hints, no defensive guards). | If CQS-craft drops below `none`, code-level surface markers track preamble priming even against the judges' stated rubric. |

## Expected output

All artifacts land under `preamble_quality_experiment_v2/confound_probe_results/`:

- `generations.jsonl` — one row per probe generation (30 rows total: 3 probes × 10 subjects × 1 rep).
- `judgments.jsonl` — one row per `(sample, judge_model)` rubric evaluation.
- `sample_cqs.json` — per-generation CQS-craft and components.
- `REPORT.md` — headline numbers per probe vs. main-run reference conditions (`none`, `long_directive`, `negative_control`, `python_coder_agent`), per-probe significance tests vs. `none`, per-dimension severity table, and a verdict on which mechanism story the probes support.

The original probe run found Probe A −0.155 vs. `none` (p=0.0001), Probe B +0.015 vs. `none` (p=0.50, recovering ~70% of `long_directive`'s lift), Probe C −0.154 vs. `none` (p=0.0001). The refined mechanism story — attention-allocation, not judge information-leakage — is documented at `INVESTIGATION_LOG.jsonl` seq 49–51 and in `REPORT_ADDENDUM.md`.

## Cross-reference

- The probes were prompted by the post-main-run mechanism question. See [Investigation logs](../methodology/investigation-logs.md) seq 49 for the trigger.
- Judges remained **blind to the preamble** throughout — the judge prompt sees only the code, not the subject's preamble. The clarification was added to `CONCLUSIONS.md` and the root README at log entry seq 51 to head off the "judges reward expert-toned preambles" misreading.
- The probes provide the empirical basis for [Limitation 1](../methodology/limitations.md): CQS-craft is rubric-dependent.
