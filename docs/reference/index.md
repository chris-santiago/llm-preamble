# Reference

Lookup-oriented documentation for the v2 investigation. Each page is canonical for one slice of the experimental design or output — extract one fact, link out, return.

For narrative discussion, see the [conclusions](../../preamble_quality_experiment_v2/CONCLUSIONS.md) and the [README findings](../../README.md). For the verbatim text of every preamble tested, see [preambles](preambles.md).

## Pages

- **[Preambles](preambles.md)** — Verbatim text of all 12 conditions (9 main-run + 3 confound probes).
- **[Rubric](rubric.md)** — The 11 algorithmic-code quality dimensions, severity scale, calibration anchor, and conditional-N/A rules.
- **[Models](models.md)** — The 10-model subject pool (3 reasoning + 7 non-reasoning), reasoning-parameter handling, and the family-based self-judgment rule.
- **[Tasks](tasks.md)** — The 7 Python tasks (5 creation incl. one multi-file, 2 refactor) with full prompts and category notes.
- **[Generation protocol](generation-protocol.md)** — Subject- and judge-side generation constants (T = 0.3, max_tokens = 10000, concurrency = 50), reasoning-effort gating, retry semantics, and extraction.
- **[Judge protocol](judge-protocol.md)** — Judge blindness, the two judge kinds (`idiom_comment`, `rubric`), the full 10-judge cross-judge matrix, and self-judgment exclusion.
- **[Statistical methods](statistical-methods.md)** — Kruskal–Wallis omnibus, bootstrap 95% CI (`n_boot = 2000`), and the mixed-effects M0 / M1 / M2 ladder with `preamble × tier` interaction.
- **[Results schema](results-schema.md)** — Field-level reference for every output file: `generations.jsonl`, `judgments.jsonl`, `sample_cqs.json`, `static_analysis.jsonl`, `REPORT.md`, `MIXED_EFFECTS.md`, `WEIGHT_SENSITIVITY.md`, `confound_probe_results/REPORT.md`.
- **[Glossary](glossary.md)** — Definitions for CQS-craft, rubric severity, always-on / conditionally-N/A dimensions, rubric overlap density, attention-allocation, self-judgment exclusion, ETA, defense_wins, critique_wins.
