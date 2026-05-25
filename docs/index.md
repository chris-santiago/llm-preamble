# LLM Preamble Experiments

Empirical investigation of whether coding-agent preambles measurably change the quality of code that LLMs produce. **They do — and the channel is load-bearing in both directions.** Two pre-registered investigations, 1,290 generations, 25,140 cross-judge ratings.

## TL;DR

The preamble channel is genuinely load-bearing — content choices measurably move outputs in *either* direction relative to a no-preamble baseline. There is no universal "best preamble"; a preamble's effect is governed by overlap between the dimensions the preamble enumerates and the dimensions your downstream evaluator measures. Modest effect sizes in either direction (~3–6 points out of 100).

The full headline table with empirical evidence per claim is in [the five findings](findings/index.md).

## Start here

### If you're a practitioner deciding what to put in your agent's system prompt

- **[The five findings](findings/index.md)** — each with claim, evidence table, action, and related-work pointer.
- **[Designing a preamble](how-to/design-a-preamble.md)** — a six-step procedure derived from the findings.
- **[Preambles tested verbatim](reference/preambles.md)** — the actual text of all 12 conditions, with mean CQS-craft per condition.
- **[Interpret CQS-craft effect sizes](how-to/interpret-cqs-craft.md)** — when the measured effect matters and when it doesn't.

### If you're a researcher or methodologist

- **[Explanation](explanation/index.md)** — mechanism arguments: attention-allocation, enumeration-vs-demonstration, the verified system-vs-user channel asymmetry, why static metrics miss, the v1 → v2 instrument correction.
- **[Methodology](methodology/index.md)** — pre-registration, ml-lab debate workflow, investigation logs, the five spec amendments, limitations.
- **[Statistical methods](reference/statistical-methods.md)** — Kruskal–Wallis omnibus, mixed-effects M0/M1/M2, bootstrap 95% CI.
- **[Related work](explanation/related-work.md)** — situating in the 2024–2026 literature on persona/system-prompt effects and LLM-as-judge evaluation.

### If you want to reproduce the runs

- **[Quickstart](reproduce/quickstart.md)** — setup + commands.
- **[Main run](reproduce/main-run.md)** — full v2 experiment end-to-end (~1 hour).
- **[Confound probes](reproduce/confound-probes.md)** — the 3-probe identification test (~5 min).

## What this site is

A Diátaxis-organized companion to the [llm-preamble repo](https://github.com/chris-santiago/llm-preamble). The repo's `README.md`, `PREAMBLES.md`, `RELATED_WORK.md`, and per-cycle `CONCLUSIONS.md` remain the source-of-truth artifacts; this site reorganizes them for navigation and adds the explanation pages that consolidate mechanism arguments developed during and after the investigation. Every page links back to the underlying source — script, results file, or markdown artifact — under the repo root.

## ML-Lab

Designed, executed, and analyzed using [**ml-lab**](https://github.com/chris-santiago/ml-lab) — a Claude Code plugin for rigorous, pre-registered ML hypothesis investigations (hypothesis → adversarial critique → PoC → empirical resolution → peer review). Every artifact in this repo (`HYPOTHESIS.md`, `SPEC_V2.md`, `CONCLUSIONS.md`, `REPORT_ADDENDUM.md`, `INVESTIGATION_LOG.jsonl`) is a canonical output of that workflow.
