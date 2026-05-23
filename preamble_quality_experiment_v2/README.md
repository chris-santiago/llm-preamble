# Preamble Quality Experiment v2 — Proof of Concept

This directory holds the v2 cycle of an ml-lab investigation. The v1 results
(at `../preamble_quality_experiment/`) showed that preambles do change LLM-
generated code quality, but only on craft dimensions (idiomaticity, comment
quality) — the static-analysis-heavy v1 composite hid the effect. v2 fixes
the instrument and adds discrimination. `SPEC_V2.md` is the authoritative
pre-registration; `HYPOTHESIS.md` restates the cycle-2 claim and metric.

## Hypothesis (one paragraph)

Coding-agent preambles change the quality of code an LLM writes, detectable
on a LLM-judge-only Composite Quality Score (CQS-craft = 0.45·idiom + 0.45·
comment + 0.10·rubric-hygiene). The primary contrast is any rich preamble
vs. `none` vs. `negative_control` — the v1 question, tested under a
corrected instrument. The effect is expected to be larger on creation tasks
than refactoring tasks. The `python_coder_agent` condition is included as
one rich-preamble data point (a real production system prompt verbatim),
not as a contrast being tested for itself.

## Quickstart

```bash
export OPENROUTER_API_KEY=<your key>
uv run preamble_quality_v2_poc.py
```

Runtime ~30 seconds. Total cost: ~$0.01 (6 generations + 18 judge calls,
cheap models only).

## Pipeline

1. **Generate** — one Python code response per (condition × task) cell from
   `openai/gpt-4o-mini`. Conditions: `none`, `real_agent`, `python_coder_agent`
   (loaded verbatim from `/Users/chrissantiago/Dropbox/claude-config/plugins/`
   `chris-code/agents/python-coder.md`). Tasks: `task_lru_ttl_cache`
   (creation) + `task_modeflag_sort` (trap-based refactor probe).
2. **Extract** — fenced-code-block extraction with a raw-code fallback.
   Failed extractions are logged and excluded from scoring.
3. **Judge** — three-judge cross-panel (`gpt-4o-mini`, `deepseek-v3.2`,
   `mistral-small-2603`) scoring each sample on idiomaticity (1–10),
   comment quality (1–10), and 11 single-file rubric dimensions (0–5
   severity) drawn from the python-coder agent's S3+ checklist + the
   python-review-lite gate (`SPEC_V2.md §6.4`).
4. **Aggregate** — self-judgments excluded (F3 hygiene). CQS-craft is
   computed per sample, then averaged per condition.
5. **Visualize** — single bar chart of idiom, comment, and CQS-craft by
   condition (`poc_results/poc_cqs_craft.png`).

## Output

After a run, `poc_results/` contains:
- `poc_generation_results.jsonl` — raw model responses + extracted code.
- `poc_judge_records.jsonl` — per (sample × judge) ratings.
- `poc_per_sample_results.jsonl` — cross-judge means + CQS-craft per sample.
- `poc_summary.json` — per-condition aggregates + config metadata.
- `poc_cqs_craft.png` — primary visualization.

## Deliberately omitted at PoC scope

- All 7 subject models (PoC: 1) and all 9 conditions (PoC: 3).
- All 8 tasks (PoC: 2). No multi-file task.
- n ≥ 100/arm replication (PoC: n = 2 per condition across tasks).
- Static-analysis diagnostic panel (radon/pylint/PEP8). v1 showed these are
  flat across conditions; the full v2 run will reproduce this as a
  precondition check, but the PoC skips it.
- Bootstrap CIs, mixed-effects model, F3 self-preference stratification.
- Creation-vs-refactor stratification of per-dimension severity.

## Known limitations / intent-review notes

These are flagged for the Step 2 review with the human; some may be real
findings to carry into Step 3, others may be PoC-scope artifacts to ignore.

1. **In-condition variation between rich preambles is large at PoC scale.**
   On 2 samples per condition, `python_coder_agent` came out lower than
   both `none` (0.79) and `real_agent` (0.82) on CQS-craft (0.63), driven
   by lower idiom (0.63) and comment (0.55) scores even though its rubric
   severity is the lowest (0.09 — cleanest by the agent's own checklist).
   Generated outputs are ~25–35% shorter. Plausible mechanism: the
   python-coder agent's prompt explicitly emphasizes "prefer deletion to
   invention," "avoid speculative architecture" — the model produces
   terser code with sparser comments, which LLM judges score lower on
   comment quality. The corrected v2 hypothesis (above) does *not*
   predict any specific ordering among rich preambles; the primary
   contrast is rich-preamble *vs.* `none` / `negative_control`. This PoC
   observation is incidental to that contrast and may reflect noise at
   n = 2. The full run aggregates `python_coder_agent` into the rich-
   preamble pool; whether it specifically tracks high or low within that
   pool is a side-observation, not a primary verdict.

2. **The trap task did not trigger.** All three conditions, including
   `python_coder_agent`, implemented `def sort(items, key=None, reverse=
   False, stable=True)` verbatim despite the python-coder agent's S3+ #1
   principle explicitly forbidding boolean mode-flags on public functions.
   Two interpretations: (a) the trap is too subtle for a small subject
   model (`gpt-4o-mini`); (b) explicit prompt requirements always override
   preamble principles. The full run uses 7 models; if even
   `nemotron-3-super` or `deepseek-v3.2` fall for the trap, that's a
   stronger signal that the trap-resistance probe doesn't work at the
   single-turn prompting layer.

3. **One judge call (1/18 ≈ 5.5%) failed to parse.** Mistral-small produced
   valid-looking JSON but the greedy `\{.*\}` regex didn't terminate. The
   full run needs a more robust JSON extractor — this matters more at
   2,000+ judge calls than at 18.

4. **Subject pool of 1 (`gpt-4o-mini`) at PoC.** The full v2 design uses
   7 models. A "weak" subject is likelier to follow explicit instructions
   than to internalize preamble principles, biasing the trap probe. The
   PoC's evidence on flags 1–2 is consistent with this expectation.

5. **Preamble length varies across the rich-preamble pool.** The
   `python_coder_agent` preamble is 6,775 chars; `real_agent` is ~400
   chars; `long_directive` is ~1,200 chars. Under the corrected v2
   hypothesis (primary contrast = rich-preamble pool vs. `none` /
   `negative_control`), within-pool length variation is not a primary-
   contrast confound — all of these are pooled on the "rich preamble"
   side. It remains a *within-pool* descriptive note worth surfacing in
   conclusions, but it does not threaten the primary inference.

None of these flags require a change to `SPEC_V2.md`. Items 1 and 2 are
empirical questions the full debate + experiment cycle is designed to
resolve. Item 3 is a PoC artifact (fix before full run). Items 4 and 5
are descriptive / PoC-scope notes that do not threaten the primary
contrast under the corrected hypothesis.
