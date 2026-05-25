# Run a 3-probe identification test on your own preamble

The v2 confound probes (`preamble_quality_experiment_v2/confound_probes.py`) answer one question: *does this preamble lift CQS because it teaches better Python, or because it tells the model to satisfy the judge's rubric?* If you claim a real-world effect, rule out the rubric-overlap confound. See [confound probes — identification](../explanation/confound-probes-identification.md) for mechanism and v2 results; this page is the operational recipe.

## 1. Measure your preamble's rubric-overlap density

Lay your preamble next to your evaluator rubric (see the [rubric reference](../reference/rubric.md) or your extended version per [extend the rubric](extend-the-rubric.md)). For each rubric dimension, ask: does the preamble explicitly enumerate it? ~80% overlap puts you in the high-overlap regime where the confound dominates; ~20% is the low-overlap regime where any lift is likely mechanistic. Record the fraction — it sets your prior on what the probes should show.

## 2. Construct probe A — same expert framing, NON-rubric content

Probe A controls for *framing*. Keep persona, register, length, and imperative tone — swap content for dimensions the rubric *doesn't* score. v2's `PROBE_A_NONRUBRIC` (line 91 in `confound_probes.py`) lists line-count minimization, single-pass algorithms, in-place ops, asymptotic-cost matching. If probe A lifts as much as your target, the lift was framing-driven. If it doesn't, your dimensions are doing real work.

## 3. Construct probe B — bare rubric, no framing

Probe B strips persona, imperative voice, and motivational language. Just list the rubric dimensions in one sentence. v2's `PROBE_B_BARE_RUBRIC` (line 109) is the template: *"Your code will be evaluated on these specific dimensions: error handling consistency, edge case handling …"* If probe B captures most of the lift, [Finding 3](../findings/3-bare-enumeration.md) replicates and bare enumeration is the active ingredient. If it falls flat, framing matters more for your preamble than it did for v2.

## 4. Construct probe C — anti-rubric with expert framing

Probe C is the falsifier. Keep expert framing — but content explicitly deprioritizes rubric items. v2's `PROBE_C_ANTIRUBRIC` (line 119) tells the model type hints are clutter, edge cases are the caller's responsibility, comments belong in commit messages. If the judge still rewards probe C, framing dominates. If the judge penalizes probe C below `none`, rubric content dominates and the channel is content-mediated.

## 5. Run all three on one task with the full cross-judge panel

```bash
export OPENROUTER_API_KEY=<your key>
uv run preamble_quality_experiment_v2/confound_probes.py
```

The script generates one task × three probes × all models × cross-judge panel, with `none` as reference. Output lands in `confound_probe_results/`. To adapt to your own preamble, copy the script, swap `PROBE_PREAMBLES`, keep the rest intact. One task is enough because the comparison is *between probes*, not across tasks. The cross-judge panel is non-negotiable; single-judge probes aren't interpretable, and self-judgments are excluded per [judge protocol](../reference/judge-protocol.md).

## 6. Interpret the triangulation

Build the per-probe CQS-craft table against `none`:

| Probe | What it isolates | If high vs `none` … | If flat vs `none` … |
|---|---|---|---|
| A — expert framing, non-rubric content | Framing effect | Framing alone lifts; your target preamble's content may not be active | Content matters, not framing |
| B — bare rubric, no framing | Pure enumeration | Bare enumeration captures the lift (Finding 3 replicates) | Framing or content phrasing matters more |
| C — anti-rubric, expert framing | Rubric content (negatively) | Framing dominates content (judges reward register over substance) | Content dominates — your channel is real |

The interesting cell is **C low vs `none` AND B high vs `none`** — that's the v2 signature: bare enumeration helps, anti-rubric hurts, content is doing the work.

If your probes don't reproduce that pattern, you've identified a different mechanism — log it. See [confound probes — identification](../explanation/confound-probes-identification.md) for the full v2 result and what to read into each pattern.
