# Add a new preamble condition to the v2 main run

This recipe extends the v2 pipeline with an additional preamble condition — for example, a candidate you're evaluating before production, or a variant exploring a specific hypothesis. All edits are inside `preamble_quality_experiment_v2/preamble_quality_v2_main.py`.

## 1. Add the preamble string to the `PREAMBLES` dict

Open `preamble_quality_experiment_v2/preamble_quality_v2_main.py`. Around **line 104** there is a `PREAMBLES: dict[str, str | None]` dict. Add an entry:

```python
PREAMBLES: dict[str, str | None] = {
    "none": None,
    "minimal": "You are a helpful assistant.",
    # ... existing conditions ...
    "your_new_condition": (
        "You are an expert ... your code must: (1) ... (2) ..."
    ),
    "trivial_baseline": None,
    "python_coder_agent": _load_python_coder_preamble(),
}
```

Use a stable, snake_case key — it appears in every JSONL row, figure, and report. If the preamble is long, follow the `python_coder_agent` pattern (line 147) and load it from disk via a helper. Mind the "Known Gotchas" note about absolute paths — preambles loaded from outside the repo break silently when the source moves.

## 2. Update `PREAMBLE_ORDER` to control output ordering

`PREAMBLE_ORDER` lives at **line 150**. This list controls column order in the report tables and figure x-axes. Insert your condition where it makes sense narratively (e.g. between `real_agent` and `long_directive` for a candidate of similar verbosity):

```python
PREAMBLE_ORDER = [
    "trivial_baseline", "none", "negative_control", "minimal",
    "generic_coding", "persona_only", "real_agent",
    "your_new_condition",          # <- new
    "long_directive", "python_coder_agent",
]
```

A condition missing from `PREAMBLE_ORDER` will be generated and judged but won't appear in the report — easy to miss.

## 3. Decide pre-flight gates — does it need its own confound probe?

v2's lesson: an apparent preamble effect can be entirely rubric-overlap (see [confound probes — identification](../explanation/confound-probes-identification.md)). Walk the [run a confound probe](run-a-confound-probe.md) recipe **before** the full main run if (a) the new condition enumerates ≥ 5 rubric dimensions explicitly, (b) you expect it to be a "winner" you'll cite in conclusions, or (c) it'll be compared head-to-head with `long_directive` or `python_coder_agent`. For uncontroversial variants (typo fix, minor rewording), skip and rely on the main run.

## 4. Update `MAIN_CONDITIONS` if applicable

`MAIN_CONDITIONS` is derived at **line 149** as everything in `PREAMBLES` except `trivial_baseline`. If your new condition is *also* a special-case baseline (not part of the primary comparison), exclude it explicitly:

```python
MAIN_CONDITIONS = [c for c in PREAMBLES if c not in {"trivial_baseline", "your_new_condition"}]
```

Otherwise no change is required — the derivation picks up the new key automatically.

## 5. Re-run with `--slice` first to confirm pipeline behavior

Smoke-test before paying for a full run:

```bash
export OPENROUTER_API_KEY=<your key>
uv run preamble_quality_experiment_v2/preamble_quality_v2_main.py --slice
```

`--slice` (defined at **line 1277**) runs 2 models × 2 preambles × 1 task × 1 rep. Confirm the new key appears in `experiment_v2_results/*.jsonl`, judging completes without parser errors on its outputs, and it appears in the report table. If the preamble is unusually long or structured, check that no model truncates or refuses it.

## 6. Run the full main run and re-analyze

```bash
uv run preamble_quality_experiment_v2/preamble_quality_v2_main.py
```

Use `--resume` to skip already-completed work if a previous partial run exists. Results are appended to the existing JSONL — never rewrite or sort in place.

Once generation and judging are complete, re-run analysis (analysis is invoked at the end of the main script; for re-analysis only without re-generating, use the analysis-only entrypoint per the [reproduce guide](../reproduce/quickstart.md)).

## What to check in the new report

Is the new condition's CQS-craft inside the empirical envelope (~[0.55, 0.85])? An outlier is suspicious. Does the per-dimension table show the wins/losses you predicted? Has the Kruskal–Wallis p across `MAIN_CONDITIONS` shifted materially? Document either outcome — negative results are valid.
