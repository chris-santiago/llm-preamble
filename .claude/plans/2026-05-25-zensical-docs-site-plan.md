# Zensical Docs Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use chris-code:subagent-driven-development (recommended) or chris-code:executing-plans to implement this plan task-by-task.

## 1. Objective

Build a Diátaxis-organized Zensical (classic theme) documentation site for the llm-preamble experiment, consolidating existing artifacts and authoring identified content gaps.

## 2. Spec references

- Preceding conversation turn (Diátaxis layout proposal — section-by-section file map + content sourcing)
- https://zensical.org/docs/setup/basics/ — Zensical init + `classic` theme
- `/Users/chrissantiago/Dropbox/GitHub/ferrum/.github/workflows/docs.yml` — reference deploy workflow (copy verbatim, adapt branch names)
- Existing artifacts: `README.md`, `PREAMBLES.md`, `RELATED_WORK.md`, `preamble_quality_experiment_v2/{HYPOTHESIS,SPEC_V2,CONCLUSIONS,REPORT_ADDENDUM,V3_IDEA}.md`, both `INVESTIGATION_LOG.jsonl`

## 3. Files

| Action | Path | Reason |
|--------|------|--------|
| Create | `zensical.yml` (or equivalent) | Zensical config: `classic` theme, nav tabs, search, mermaid, MathJax, admonitions |
| Create | `.github/workflows/docs.yml` | Copy of ferrum's `docs.yml`; deploys via GitHub Pages Actions |
| Create | `docs/index.md` | Site landing — TL;DR + headline + nav into sections |
| Create | `docs/findings/` (5 pages + index) | One page per Finding, migrated from README §"The five findings" |
| Create | `docs/how-to/` (6 pages + index) | Practitioner recipes; mostly new content |
| Create | `docs/reference/` (9 pages + index) | Information lookup; mostly assembly from existing sources |
| Create | `docs/explanation/` (8 pages + index) | Mechanism + reframe + channel arguments; ~half new content |
| Create | `docs/methodology/` (4 pages + index) | Pre-registration, ml-lab workflow, logs, amendments, limitations |
| Create | `docs/reproduce/` (4 pages + index) | Run instructions extracted from README + scripts |
| Create | `docs/about/` (2 pages) | V3_IDEA + ml-lab attribution |
| Modify | `.gitignore` | Add `site/` (Zensical build output) |

## 4. Constraints

- **Theme:** Zensical `classic` to preserve Material look. Do not customize beyond what's needed for nav tabs, source-link button, and mermaid/MathJax rendering.
- **Figures:** Use relative paths to `preamble_quality_experiment_v2/experiment_v2_results/figures/` — single source of truth, no copies under `docs/assets/`.
- **`agent_proposals/` stays untracked.** Reference as a pointer in `docs/how-to/design-a-preamble.md`; do **not** embed contents.
- **Do not modify** `*.py` scripts, `*.jsonl` logs, or anything under `preamble_quality_experiment*/experiment*_results/`.
- **Do not modify root `README.md`.** Docs site is a supplement, not a replacement. README anchors and external links must remain stable.
- **No versioning.** Single static site, completed cycle. Do not configure mike or version selectors.
- **No `mkdocstrings`.** This repo has scripts, not a package. Install only `zensical`.
- **Deploy mechanism:** ferrum-style GitHub Pages Actions (`actions/deploy-pages@v5` from `site/` artifact). Repo Settings → Pages → Source must be set to "GitHub Actions" — the user handles this out-of-band; do not modify repo settings from the workflow.
- **Do not push, do not merge to main.** All work on the `feat/zensical-docs-site` branch. Commit freely; pushing is the user's call after review.
- **Preserve external link stability** for `README.md`, `PREAMBLES.md`, `RELATED_WORK.md`, `preamble_quality_experiment_v2/CONCLUSIONS.md` (these are linked from elsewhere).

## 5. Tasks

### Task 1: Zensical scaffolding
- [ ] Init project per https://zensical.org/docs/setup/basics/ with `classic` theme
- [ ] Configure top-level nav tabs: Home / Findings / How-to / Reference / Explanation / Methodology / Reproduce / About
- [ ] Enable instant search, mermaid, MathJax, admonitions, code copy buttons
- [ ] Add per-page "source" link template pointing to the underlying `.py` file (when applicable)
- [ ] Add `site/` to `.gitignore`
- [ ] Verify: `zensical serve` runs locally; landing page loads; all 8 nav tabs present (even if pages are stubs)

### Task 2: GitHub Pages workflow
- [ ] Copy `/Users/chrissantiago/Dropbox/GitHub/ferrum/.github/workflows/docs.yml` to `.github/workflows/docs.yml`
- [ ] Adjust `pip install` line: install only `zensical` (drop `mkdocstrings mkdocstrings-python`)
- [ ] Keep `actions/checkout@v6`, `actions/setup-python@v6`, `zensical build --clean`, `actions/upload-pages-artifact@v5` (path: `site`), `actions/deploy-pages@v5`
- [ ] Confirm trigger branches match this repo's default (`main`)
- [ ] **Do not push.** Live workflow verification is the user's responsibility after they enable the Pages source.

### Task 3: Migrate existing artifacts
- [ ] `PREAMBLES.md` → `docs/reference/preambles.md` (verbatim move)
- [ ] `RELATED_WORK.md` → `docs/explanation/related-work.md` (verbatim move)
- [ ] `preamble_quality_experiment_v2/V3_IDEA.md` → `docs/about/v3-idea.md` (verbatim move)
- [ ] README §"The five findings" → split into 5 pages under `docs/findings/`, one Claim/Evidence/Action/Related-work-pointer per page
- [ ] README §"Designing a preamble" → `docs/how-to/design-a-preamble.md`
- [ ] README §"Effect-size calibration" → `docs/how-to/interpret-cqs-craft.md`
- [ ] README §"Limitations" + add channel-asymmetry note (from this conversation) → `docs/methodology/limitations.md`
- [ ] README §"ml-lab attribution" blockquote → `docs/about/attribution.md`
- [ ] README §"Repo layout & reproduce" → `docs/reproduce/quickstart.md` (copy, not move)
- [ ] **Do not edit root `README.md`.** All "migration" steps above are copies, not moves.

### Task 4: Author reference pages
Mostly assembly; extract content from existing code/results files.
- [ ] `docs/reference/rubric.md` — 11 dimensions from `preamble_quality_experiment_v2/preamble_quality_v2_main.py`, severity scales, N/A criteria, calibration anchor text
- [ ] `docs/reference/models.md` — 10-model pool, reasoning vs non-reasoning split, judge `reasoning:{exclude:true}` config
- [ ] `docs/reference/tasks.md` — 7 tasks with descriptions + creation-vs-refactor classification
- [ ] `docs/reference/statistical-methods.md` — KW omnibus, mixed-effects M0/M1/M2 spec, bootstrap CI
- [ ] `docs/reference/judge-protocol.md` — blindness (with code refs `preamble_quality_v2_main.py:621-630`, `confound_probes.py:341-362`), panel composition, calibration, self-exclusion
- [ ] `docs/reference/generation-protocol.md` — T=0.3, max_tokens=10000, reasoning-effort gating, retry, concurrency=50
- [ ] `docs/reference/results-schema.md` — what's in each output JSONL/MD
- [ ] `docs/reference/glossary.md` — CQS-craft, severity, ETA, "always-on dim", "rubric overlap density"
- [ ] `docs/reference/index.md` — section landing

### Task 5: Author explanation pages
Substantive new content; sources tagged inline.
- [ ] `docs/explanation/attention-allocation-mechanism.md` — extract from `CONCLUSIONS.md §"Confound probes"`
- [ ] `docs/explanation/load-bearing-channel-reframe.md` — **new**; document Finding 1's interpretive history (asymmetry → load-bearing) per this conversation
- [ ] `docs/explanation/enumeration-vs-demonstration.md` — **new**; plan-vs-preamble argument per this conversation
- [ ] `docs/explanation/system-vs-user-channel.md` — **new**; wire-format verification with the official docs citations from this conversation
- [ ] `docs/explanation/why-static-metrics-fail.md` — synthesize `CONCLUSIONS.md` + README Finding 5
- [ ] `docs/explanation/v1-vs-v2-instrument-correction.md` — **new**; synthesize v1 `REPORT_ADDENDUM.md` + v2 `REPORT_ADDENDUM.md`
- [ ] `docs/explanation/confound-probes-identification.md` — extract from `CONCLUSIONS.md`
- [ ] `docs/explanation/index.md` — section landing

### Task 6: Author how-to pages
Practitioner recipes; mostly new content.
- [ ] `docs/how-to/ab-test-a-preamble.md` — **new**; validation path from `agent_proposals/CHANGES.md` (reference only, do not embed)
- [ ] `docs/how-to/extend-the-rubric.md` — **new**; adding dimensions for a non-Python domain
- [ ] `docs/how-to/add-a-condition.md` — **new**; how to add a preamble to the main run
- [ ] `docs/how-to/run-a-confound-probe.md` — **new**; from `confound_probes.py` + `confound_probe_results/REPORT.md`
- [ ] `docs/how-to/index.md` — section landing
- [ ] Reference `agent_proposals/` as worked example in `design-a-preamble.md` (pointer only)

### Task 7: Author methodology + reproduce pages
- [ ] `docs/methodology/pre-registration.md` — extract from `SPEC_V2.md`
- [ ] `docs/methodology/ml-lab-workflow.md` — **new**; synthesize debate protocol behavior with one worked example from `INVESTIGATION_LOG.jsonl`
- [ ] `docs/methodology/investigation-logs.md` — **new**; outside-observer reconstruction per this conversation
- [ ] `docs/methodology/amendments.md` — extract from `SPEC_V2.md §12`
- [ ] `docs/methodology/index.md` — section landing
- [ ] `docs/reproduce/main-run.md` — extract from existing CLAUDE.md commands + `preamble_quality_v2_main.py` header
- [ ] `docs/reproduce/analysis.md` — `analysis_addendum.py` + `figures.py` usage
- [ ] `docs/reproduce/confound-probes.md` — `confound_probes.py` usage
- [ ] `docs/reproduce/index.md` — section landing

### Task 8: Build, verify, commit prep
- [ ] `zensical build --clean` succeeds with no warnings
- [ ] All internal links resolve (use a link-checker pass)
- [ ] All `source` buttons resolve to existing `.py` files
- [ ] Figures load via relative path from each page that references them
- [ ] **Do not push, do not merge.** Live GitHub Pages deploy is the user's responsibility after they enable the Pages source.

## 6. Acceptance checks

- `zensical serve` runs locally; all 8 nav tabs work; landing page resolves
- `zensical build --clean` produces `site/` with no broken-link warnings
- Channel-asymmetry verification (from conversation) appears in `docs/explanation/system-vs-user-channel.md` with the docs citations
- The reframe history (Finding 1 asymmetry → load-bearing) appears in `docs/explanation/load-bearing-channel-reframe.md`
- `git status` (post-execution) — only `docs/`, `zensical.yml` (or equivalent), `.github/workflows/docs.yml`, and `.gitignore` changed; **no edits to** `README.md`, `*.py`, `*.jsonl`, or `experiment_v2_results/*`
- All commits live on `feat/zensical-docs-site`; nothing pushed; no merge to `main`
