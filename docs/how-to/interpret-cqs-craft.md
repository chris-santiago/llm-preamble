# Effect-size calibration — when this matters and when it doesn't

CQS-craft is on a [0, 1] scale. The empirical anchors:

| Anchor | CQS-craft |
|---|---|
| `trivial_baseline` (no system, name-only prompt, T=1.0) | 0.556 |
| `negative_control` ("junior developer") | 0.723 |
| `none` (no system prompt at all) | 0.778 |
| Strongest single preamble (`long_directive`) | 0.815 |

**This matters when:**

- You ship to a high-volume coding agent where small per-sample quality differences compound (millions of code suggestions per day → small β × large N → real measurable downstream user impact).
- Your downstream evaluator measures the same dimensions the v2 rubric measures (error handling, edge cases, type discipline, documentation, organization, abstraction calibration, API ergonomics, concurrency safety).
- You have an A/B test budget large enough to detect a 5-point shift (n ≥ a few hundred samples per arm; v2's per-arm n was ~138).

**This matters less when:**

- Your downstream evaluator measures different dimensions (compactness, performance, security). The probes proved the preamble winners flip under a different rubric.
- You're shipping to a low-volume specialty system where per-sample variance dwarfs the expected preamble effect.
- Your model is already on the high end of the CQS-craft range. There's evidence of a ceiling near ~0.85 on this rubric for current frontier models; preamble can move you toward it but not past it.

**This matters not at all when:**

- You're using static-analysis tools (radon, pylint, cyclomatic complexity) as your quality bar. Those don't detect preamble effects.
