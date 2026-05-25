# Explanation

Understanding-oriented pages: the *why* behind the findings. Each page
expands on a mechanism, an identification argument, or an interpretive
choice that the [findings](../findings/index.md) summarize at a higher
level. Read these when you want to understand *how* the v2 evidence
licenses the claims, not just *what* the claims are.

- [Attention-allocation mechanism](attention-allocation-mechanism.md) —
  the headline mechanism reading: preambles direct the model's finite
  craft-attention budget toward whatever dimensions they enumerate.
  Triangulated by probes A (−0.155), B (+0.015, recovers 70%), and
  C (−0.154).
- [Load-bearing channel reframe](load-bearing-channel-reframe.md) —
  Finding 1's interpretive history: the headline moved from a
  "negative-vs-positive asymmetry" reading to a sharper "the channel
  reaches below baseline at all" reading, and why the reframe matters.
- [Enumeration vs demonstration](enumeration-vs-demonstration.md) —
  why showing well-structured code in a plan does not transfer
  structural quality to an executing agent. Examples are descriptive
  context; enumeration is directive content.
- [System vs user channel](system-vs-user-channel.md) — wire-format
  verification that v2's preamble channel matches the production
  Claude Code subagent dispatch channel: agent prose lands in the
  subagent's **system prompt**, not user-message content. Cites the
  official Anthropic Agent SDK documentation verbatim.
- [Why static metrics fail](why-static-metrics-fail.md) — the
  structural reason radon, pylint, cyclomatic complexity, and
  Halstead difficulty cannot detect preamble effects: they measure
  pretraining-dependent structural properties, while preambles tune
  alignment-dependent craft.
- [v1 vs v2 — the instrument-correction story](v1-vs-v2-instrument-correction.md) —
  how v1's static-heavy composite (KW p = 0.633) mechanically
  manufactured a false null on the same data that v2's corrected
  instrument detected at p = 9.24 × 10⁻¹⁸. The methodology-cautionary
  page.
- [Confound probes — the formal identification argument](confound-probes-identification.md) —
  the rigorous reconstruction of how probes A, B, and C jointly
  identify overlap density as the proximate predictor of preamble
  lift, ruling out simpler "judge-priming" and "expert-framing"
  stories.
- [Related work](related-work.md) — how these findings situate within
  the 2024–2026 literature on persona/system-prompt effects, the
  alignment-vs-pretraining split, format-as-variable studies, and
  LLM-as-judge evaluation.
