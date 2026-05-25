# Reproduce

How to re-run the v2 investigation end-to-end. Every script in the experiment directory uses `uv run` with PEP 723 inline metadata — no virtualenv, no `pyproject.toml`. Set `OPENROUTER_API_KEY` and you're ready.

- [**Quickstart**](quickstart.md) — minimal command sequence to reproduce the v2 main run, mixed-effects analysis, confound probes, and figures.
- [**Main run**](main-run.md) — how to run `preamble_quality_v2_main.py` end-to-end: smoke-test slice, full run, useful flags, expected runtime, output layout.
- [**Post-run analysis**](analysis.md) — how to run `analysis_addendum.py` (mixed-effects M0/M1/M2 + weight sensitivity) and `figures.py` (5 matplotlib/seaborn figures), and what each produces.
- [**Confound probes**](confound-probes.md) — how to run `confound_probes.py` (post-hoc probes A/B/C distinguishing H-mechanism from H-judge-priming).
