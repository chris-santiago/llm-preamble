# Main run

The v2 main experiment is a single script — [`preamble_quality_v2_main.py`](https://github.com/chrissantiago/llm-preamble/blob/main/preamble_quality_experiment_v2/preamble_quality_v2_main.py) — that executes the locked design from `SPEC_V2.md` (see [Pre-registration](../methodology/pre-registration.md)).

## Prerequisites

```bash
export OPENROUTER_API_KEY=<your key>
```

`OPENROUTER_API_KEY` is required. There is no mock mode — every generation and every judge call hits OpenRouter.

`uv` resolves all Python dependencies from the script's PEP 723 inline metadata at run time; no virtualenv setup is needed.

## Smoke test

Run a 4-sample slice first to verify the pipeline end-to-end:

```bash
uv run preamble_quality_experiment_v2/preamble_quality_v2_main.py --slice
```

`--slice` runs 2 models × 2 preambles × 1 task × 1 rep. Expect ~$0.12 and a few minutes wall clock. On success the smoke run produces a `REPORT.md` showing directional sanity (e.g. `python_coder_agent` > `none`).

## Full run

```bash
uv run preamble_quality_experiment_v2/preamble_quality_v2_main.py
```

**Expected runtime:** ~1 hour.

**Expected scale (locked by SPEC §6):**

- 10 subjects × 9 preambles × 7 tasks × 2 reps = **1,260 generations**.
- Full 10-judge cross-judge matrix (self-exclusion) → ~22,680 cross-judge calls.
- Expected cost: ~$32 (smoke-extrapolation; the actual main run came in at $32.02).

## Useful flags

| Flag | Behavior |
|---|---|
| `--slice` | Small smoke-test slice (2 models × 2 preambles × 1 task × 1 rep). |
| `--resume` | Resume — skip already-completed work in JSONL files. |
| `--gen-only` | Stop after generation phase (no judging, no analysis). |
| `--skip-static` | Skip static-analysis diagnostic panel. |

JSONL files are written incrementally as work completes, so `--resume` after an interruption picks up where the previous run stopped.

## Outputs

All artifacts land under `preamble_quality_experiment_v2/experiment_v2_results/`:

- `generations.jsonl` — one row per generation (1,260 rows on a full run), including seeds, temperature, provider, raw response, and extraction result.
- `judgments.jsonl` — one row per `(sample, judge_model)` rubric evaluation, including per-dimension severities and rationale fields.
- `sample_cqs.json` — per-generation CQS-craft and its components (idiom, comment, mean rubric severity).
- `static_analysis.jsonl` — radon / pylint / flake8 cognitive-complexity panel, reported as a diagnostic — not a CQS input.
- `REPORT.md` — headline numbers (Kruskal–Wallis, per-condition means with bootstrap CIs, rubric per-dimension breakdown).

After the main run completes, see [Analysis](analysis.md) to reproduce the mixed-effects model, weight-sensitivity table, and figures, and [Confound probes](confound-probes.md) to reproduce the three post-hoc probes.

## Cross-reference

The v2 main-run completion is recorded in [`INVESTIGATION_LOG.jsonl`](../methodology/investigation-logs.md) at seq 41 — useful as a sanity check that your reproduction matches the original run's extraction rate (96.4%), judge parse rate (90.7%), and headline KW p-value (9.24×10⁻¹⁸ pooled).
