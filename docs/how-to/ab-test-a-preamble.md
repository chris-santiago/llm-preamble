# A/B test a candidate preamble against a baseline

Validate a candidate preamble against a baseline using *your* evaluator, not v2's rubric. The mechanism: [Finding 2](../findings/2-overlap-not-expertness.md) shows the lift comes from overlap between the preamble's dimensions and the *evaluator's* rubric, and [Finding 3](../findings/3-bare-enumeration.md) shows bare enumeration captures most of it. Both imply A/B tests must use the evaluator you actually deploy with — a generic quality probe misleads.

## 1. Define your evaluator from real production signal

Don't invent a rubric. Pull dimensions from existing artifacts: past bug reports (off-by-one, missing edge case, silent exception swallow), code-review comments your senior reviewers consistently flag, and customer-facing incidents. Each recurring theme becomes one dimension on a 0–5 severity scale with concrete anchors. See the [rubric reference](../reference/rubric.md) for the format; copy the structure, not the dimensions.

## 2. Take both prompts and run on 30–50 representative tasks

Sample tasks from your real workload — not LeetCode, not toy examples. 30–50 is the floor where per-dimension signal becomes legible above noise; below ~30 you cannot tell a 5-point shift from variance. Run **both** the candidate preamble and the baseline (which may be `none`, the current production preamble, or another candidate) on the **same** task set with the **same** generation settings. Fix temperature, seed where supported, and the model.

## 3. Score outputs against your evaluator checklist

For each (task, condition) cell, score every dimension independently. Two options:

- **LLM-as-judge.** Reuse v2's [judge protocol](../reference/judge-protocol.md) — same severity scale, blinded condition labels, multiple judge models if you can afford it. Self-judgments must be excluded (see protocol).
- **Human review.** Slower but unambiguous for low-volume work. Blind the reviewer to the condition.

Store one JSONL row per scored sample. Never overwrite — append.

## 4. Compare per-dimension, not just on the aggregate

Aggregate scores hide regressions. A preamble can raise total CQS while quietly knocking 1.5 points off "error handling" because the model reallocated capacity to a louder dimension. For each dimension, compute the mean (and ideally a Kruskal–Wallis or Mann–Whitney p-value) per condition.

## 5. Decide which dimensions regress under each prompt

Build the per-dimension delta table:

| Dimension | Baseline mean | Candidate mean | Δ |
|---|---|---|---|
| error handling | 3.8 | 4.1 | +0.3 |
| edge cases | 3.5 | 3.6 | +0.1 |
| API ergonomics | 4.0 | 3.4 | **−0.6** |
| … | … | … | … |

A negative Δ on **any** dimension your evaluator scores is a regression, even if the aggregate improves.

## 6. Roll out only if no dimension regresses

If any dimension regresses materially (say, > 0.3 on a 0–5 scale, or beyond your noise floor from a no-change A/A run), stop. Either edit the preamble to re-enumerate the dropped dimension, or accept the trade-off explicitly and document it. Do **not** ship a candidate that wins on aggregate while losing on a dimension you care about — that's how the rubric-overlap confound captured in [confound probes — identification](../explanation/confound-probes-identification.md) becomes a production incident.

## Worked example

A concrete worked example of applying this procedure to three real agent prompts (chris-code `python-coder`, `pytorch-coder`, `rust-coder`) lives in the repo's untracked `agent_proposals/` directory. That directory is gitignored — it exists only in local working copies — but it demonstrates the trim-then-validate flow end-to-end. Treat it as illustrative, not authoritative.
