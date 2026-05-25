# Extend the rubric for a non-Python domain or different evaluator

The v2 rubric is calibrated for Python craft on general-purpose tasks. If you're judging Rust, SQL, frontend React, ML training scripts, or any other domain — or even Python with a non-craft evaluator (security, performance, accessibility) — you need to extend the rubric before reusing the pipeline. This recipe shows how, and how to validate the extension before committing to a full main run.

## 1. Identify dimensions your evaluator measures that v2 doesn't cover

Diff your evaluator (built per [A/B test a candidate preamble](ab-test-a-preamble.md) step 1) against the [v2 rubric](../reference/rubric.md). Anything not covered is a candidate new dimension. Examples: Rust borrow-checker idioms / `unwrap` discipline / `Result` vs panic; SQL index awareness / N+1 risk; frontend accessibility / render cost; security-focused Python secret handling / SSRF surface. Drop v2 dimensions that don't fit your domain rather than forcing them.

## 2. Write each new dimension with a 0–5 severity scale and concrete anchors

Match the existing format precisely. Each dimension needs:

- A short name (snake_case, ≤ 4 words).
- A one-sentence description of what is being scored.
- Anchored severity levels — at least 0 (absent / actively wrong), 2 or 3 (partial), and 5 (exemplary). Anchors must be **concrete** — name a function shape, a code pattern, or an antipattern, not adjectives like "good" or "comprehensive."

Example sketch for a Rust dimension:

```
unwrap_discipline (0–5):
  0 — .unwrap()/.expect() used on fallible IO with no rationale
  3 — .unwrap() limited to provably-infallible cases (e.g. compile-time constants)
  5 — every fallible path uses ? or explicit match; panics are documented
```

See the [rubric reference](../reference/rubric.md) for the canonical anchor style.

## 3. Decide always-on vs conditionally-N/A status

Some dimensions only make sense on some tasks. v2 lets the judge return `null` on inapplicable dimensions and excludes nulls from per-dimension aggregates. Decide per dimension: **always-on** (judge scores every sample, e.g. naming) vs **conditionally-N/A** (judge skips if the task doesn't surface it, e.g. concurrency safety on a single-threaded sort). Document the trigger so judges apply it consistently.

## 4. Add the dimensions to the judge prompt

Append the new dimensions to the rubric block inside the judge prompt. Keep the same anchor format and the same response schema — the existing parser expects integer or `null` per dimension. If you change the schema, you must also update aggregation (and any score-clamping; see CLAUDE.md's note on the v2 clamp at `[0, 5]`).

## 5. Calibrate before running

This step is **load-bearing** — it is the difference between a useful extension and a rubric that produces flat noise. Run a calibration phase modeled on v2's Phase D / D2:

1. Generate ~10–20 samples spanning the conditions and tasks you expect to compare.
2. Judge those samples with the new rubric and the same cross-judge panel you intend to use in the main run.
3. Inspect each new dimension:
   - Does it show variance across samples? (A dimension where every score is 4 carries no information.)
   - Do judges agree within ~1 point on most samples? (Wide disagreement means the anchors are ambiguous — rewrite them.)
   - Do high-quality and low-quality outputs separate on this dimension? Spot-check both extremes.

If a dimension is flat, ambiguous, or non-discriminating, rewrite or drop it before the full run. v2's Phase D2 caught exactly this pattern on multiple candidate dimensions; calibration is cheap, a flawed main run is not.

## 6. Then — and only then — run the full main pipeline

Once the extended rubric passes calibration, plug it into the judge prompt and run your main experiment per the [reproduce guide](../reproduce/quickstart.md). Any mid-run rubric change must be logged as drift per `SPEC §7`, not silently edited.
