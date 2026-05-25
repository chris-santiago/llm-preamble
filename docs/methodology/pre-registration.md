# Pre-registration

The v2 investigation is **pre-registered** against [`SPEC_V2.md`](https://github.com/chrissantiago/llm-preamble/blob/main/preamble_quality_experiment_v2/SPEC_V2.md). Pre-registration is not ceremonial — it is the boundary between an experiment that tests a hypothesis and one that interprets noise. Everything below was locked before any main-run generation was made.

## What was pre-registered

The authoritative pre-registration document is `SPEC_V2.md`. The locked items are:

### Primary metric (SPEC §6.5)

`CQS_craft` is the headline outcome:

```
CQS_craft = w_idiom * idiomaticity + w_comment * comment_quality + w_hygiene * (1 - mean_rubric_severity/5)
where w_idiom + w_comment + w_hygiene = 1.0
      w_hygiene <= 0.10   (rubric-severity weight, capped)
      mean_rubric_severity = mean over the §6.4 dimensions scored on this sample
                             (N/A dimensions excluded from the mean per-row)
```

Default pre-registered weights: `w_idiom = 0.45`, `w_comment = 0.45`, `w_hygiene = 0.10`. The metric contains **no static-analysis-derived component**.

### Rubric (SPEC §6.4 — as amended by A1, A5)

Eleven algorithmic-code dimensions scored on a **0–5 severity scale** (0 = clean, 5 = severe). Nine are always-on; two (`concurrency_safety`, `example_quality`) are conditional and N/A-coded on tasks that don't elicit them. Scoring uses the **full v1-equivalent 10-judge cross-judge matrix** with a calibration anchor on the rubric prompt directing judges away from defaulting to severity 0.

### Conditions (SPEC §6.1)

Nine preamble conditions: `none`, `minimal`, `generic_coding`, `real_agent`, `negative_control`, `persona_only`, `long_directive`, `trivial_baseline`, plus the verbatim `python_coder_agent` production system prompt.

### Model pool (SPEC §6.3 — as amended by A3, A4)

Ten models stratified by tier: 3 reasoning models (`qwen3.6-flash`, `deepseek-v4-flash`, `minimax-m2.5`) receiving `reasoning: {effort: "high"}`, and 7 non-reasoning models. Same 10 models serve as both subjects and judges (cross-judge matrix); judges from the reasoning tier run with `reasoning: {exclude: true}`. Self-judgments (judge family matches subject family) are excluded from primary CQS computation.

### Primary statistical criterion (SPEC §9)

The pre-registered headline result is a Kruskal–Wallis omnibus test on `CQS_craft` across the 9 preambles, with a mixed-effects model `CQS_craft ~ preamble + (1|model) + (1|task)` as the secondary contrast, plus bootstrap CIs on per-condition means. The hypothesis is supported if KW p < 0.05 in **at least one** of {pooled, non-reasoning sub-pool, reasoning sub-pool} stratifications.

### Other locked items (SPEC §7)

- **Self-judgment exclusion** for primary CQS, with the self-vs-cross delta reported as an F3-style hygiene check.
- **Power floor:** any condition with <60 valid post-attrition samples is flagged; conclusions restricted to conditions clearing 100.
- **Extraction fidelity:** failed extractions are logged and excluded, never scored as zero.
- **Reproducibility:** seeds, temperature, model versions, and preamble text hashes persisted with every generation record.

## How amendments are handled

SPEC §7 establishes the boundary explicitly:

> §6.1 (conditions), §6.2 (task IDs), §6.5 (metric formula and weights) are locked at the start of generation. Any amendment after generation begins must be logged as a documented pre-registration drift event with rationale.

In practice, pre-flight discovery (Phases A–D before the main run) surfaced several issues that required design changes. Each change is documented as an **Amendment** entry in `SPEC_V2.md §12` — never silently edited into the spec. Each amendment names:

1. The **trigger** — what was empirically discovered.
2. The **change** — what was modified in which SPEC section.
3. The **rationale** — why the change is more faithful to the hypothesis than the original design.
4. (Where relevant) the **verification** — pre-flight evidence the new design works.

Five amendments (A1–A5) were filed during pre-flight. See [Amendments](amendments.md) for the full inventory. No amendments were filed after the main run began.

## Why this matters

Without a pre-registered metric and rubric, the rubric redesign in [Amendment A1](amendments.md#a1-rubric-redesign) would look like p-hacking — swapping in dimensions that respond to preambles after seeing which ones don't. The amendment log makes it visible that the rubric was redesigned **before the main run** in response to a specific empirical failure (Phase D prevalence audit: 0 of 11 original dimensions active), and the redesign was itself validated by a pre-flight re-probe (Phase D2: 9 of 9 new dimensions active under the multi-judge panel).

The [ml-lab debate protocol](ml-lab-workflow.md) and the [append-only investigation log](investigation-logs.md) are the two mechanisms that keep the pre-registration boundary honest: every spec edit is paired with a logged event that names the trigger and the verification.
