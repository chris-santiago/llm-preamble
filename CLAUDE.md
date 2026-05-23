# CLAUDE.md

> Repo-specific context for Claude Code. Loaded every session.
> Document what Claude gets wrong, not comprehensive manuals.

---

## Project Overview

**Purpose:** Empirical ML-lab investigation of whether coding-agent preambles (system prompts) measurably change the quality of code LLMs produce. v1 established the effect exists on craft dimensions (idiomaticity, comment quality); v2 corrects the v1 instrument and adds discrimination.

**Stack:** Python ≥3.11, [`uv`](https://docs.astral.sh/uv/) for script execution with inline PEP 723 metadata, OpenRouter API for multi-model generation/judging. Per-script deps include `openai`, `scipy`, `numpy`, `matplotlib`, `statsmodels`, `radon`, `pylint`, `flake8`, `flake8-cognitive-complexity`.

**Structure:**
```
RELATED_WORK.md                   # repo-level literature situating (covers v1 + v2)
preamble_quality_experiment/      # v1 — completed cycle; see CONCLUSIONS.md
  preamble_quality_experiment2.py # main experiment runner
  reanalyze.py                    # re-run analysis without re-generating
  experiment2_results/            # full_results.jsonl + figures
  {HYPOTHESIS,SPEC_V2,CONCLUSIONS,REPORT_ADDENDUM}.md
  INVESTIGATION_LOG.jsonl         # append-only ml-lab event log
preamble_quality_experiment_v2/   # v2 — in-progress cycle
  preamble_quality_v2_poc.py      # proof-of-concept
  preflight.py                    # phases B/C/D pre-flight gates
  probe_*.py / reprobe_*.py       # ad-hoc model/task probes
  {HYPOTHESIS,SPEC_V2,GATE_1_PLAN,README}.md
  {poc,preflight,reprobe}_results/
  INVESTIGATION_LOG.jsonl
```

Each experiment directory is self-contained — scripts, results, artifacts, and docs live together. There is no shared top-level package, no `pyproject.toml`, and no `Makefile`/`justfile`.

---

## Environment & Commands

```bash
export OPENROUTER_API_KEY=<your key>   # required for any generation/judging

# v1
uv run preamble_quality_experiment/preamble_quality_experiment2.py            # sanity check (~20 calls)
uv run preamble_quality_experiment/preamble_quality_experiment2.py --full     # full run (~3456 calls)
uv run preamble_quality_experiment/reanalyze.py                               # re-analyze existing results

# v2
uv run preamble_quality_experiment_v2/preamble_quality_v2_poc.py              # ~30s, ~$0.01
uv run preamble_quality_experiment_v2/preflight.py                            # gate-1 pre-flight phases
```

No test suite, no linter config, no CI. Scripts are run directly; analysis output is JSONL + PNG written next to the script.

---

## Code Style

- Scripts use PEP 723 inline metadata (`# /// script ... # ///`) — `uv run` resolves deps per-invocation. Do **not** add a `pyproject.toml` or `requirements.txt`; keep deps in the script header.
- Each script is standalone (top-to-bottom executable). No shared utility package across experiments — duplication between v1 and v2 is intentional so each cycle's artifacts stay reproducible from its own directory.
- Results are append-only JSONL (one row per sample/judge call). Never rewrite or sort `*_results.jsonl` or `INVESTIGATION_LOG.jsonl` in place.
- Match nearby code before introducing new patterns. Never add dependencies without asking.
- **Default `concurrency=50` for all OpenRouter async scripts.** New async runners (generation, judging, probes) should set their `asyncio.Semaphore` / concurrency cap to 50 unless there's a documented reason to deviate.

---

## Architecture Notes

- **ml-lab investigation cycle.** This repo follows the `ml-lab:ml-lab` skill flow (hypothesis → critique → debate → spec → PoC → full run → conclusions). `HYPOTHESIS.md`, `SPEC_V2.md`, and `INVESTIGATION_LOG.jsonl` are the canonical artifacts of that flow — treat them as pre-registered, not free-form notes.
- **Pre-registration matters.** `SPEC_V2.md` is the authoritative metric/condition definition for v2. Changes to the metric or conditions mid-run must be logged as drift events per `SPEC §7`, not silently edited.
- **Self-judgments are excluded.** When a subject model and judge model are the same, the judgment is dropped from primary scores (F3 hygiene). Any new aggregation code must preserve this.
- **Investigation logs are append-only.** Use `log_entry.py` in each experiment dir to write to `INVESTIGATION_LOG.jsonl` — do not hand-edit the JSONL.
- **The python-coder agent preamble is loaded verbatim** from `/Users/chrissantiago/Dropbox/claude-config/plugins/chris-code/agents/python-coder.md` (absolute path baked into v2 PoC). If that file moves, the `python_coder_agent` condition breaks silently.

---

## Known Gotchas

- **`OPENROUTER_API_KEY` is required** for every generation/judging script. There is no mock mode.
- **Costs add up.** v1 `--full` is ~3456 API calls; check the script's cost note before launching a full run.
- **Model availability drifts.** v1 lost `grok-4.1-fast` mid-run (deprecated → 404s on all 48 calls); always confirm the model list resolves on OpenRouter before a long run.
- **Score clamping is load-bearing.** Judges can emit out-of-range values (e.g. `-1` sentinels) that poison aggregates. Idiom/comment scores must be clamped to `[1, 10]` and rubric items to `[0, 5]` in `judge_one_sample`. See `GATE_1_PLAN.md` F1.
- **Extraction failures are excluded, not zeroed.** Models that emit reasoning prose instead of fenced code (nemotron-3-super ~15%, qwen3.5, minimax) thin per-cell counts; never impute zero for an extraction failure.
- **v1's static-analysis components are flat across preamble conditions** (KW p ≈ 0.998 on radon/pylint/AST). Do not propose static metrics as the primary signal for any preamble-effect measurement — that's the documented false-negative trap (`README.md`, `CONCLUSIONS.md`).
- **v1 and v2 are separate cycles.** Do not cross-import or merge result files between the two directories — their conditions, metrics, and weightings differ.
