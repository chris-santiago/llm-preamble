# Finding 4 — No "alignment vs capability" split, just preamble–evaluator overlap

**Claim.** v1 inherited a "preambles change alignment-tunable craft but not pretraining-locked capability" framing from PRISM (USC 2026). v2's probes refined this: the proximate predictor of which dimensions move under preamble is whether the preamble enumerates them, not whether they're "craft" or "capability" in some structural sense.

**Evidence.** In the v2 main run, 7 of 9 always-on rubric dimensions moved with preamble (KW p < 10⁻⁴), and 2 didn't (`algorithm_correctness` p = 0.26; `data_structure_choice` p = 0.39). Looking at `long_directive`'s clause list:

| `long_directive` clause | Rubric dimension it names |
|---|---|
| (3) defensive programming, validate inputs, handle edge cases | `edge_case_gap`, `error_handling_inconsistency` |
| (5) comments why not what | `documentation_appropriateness` |
| (7) concurrency / thread-safety explicit | `concurrency_safety` |
| (8) composition over inheritance | `code_organization` |
| (9) side effects + I/O boundaries explicit | `code_organization` |
| (11) log errors at right severity, never swallow | `error_handling_inconsistency` |
| (12) docstring public interfaces | `documentation_appropriateness`, `type_hint_gap` |
| (2) appropriate abstraction | `abstraction_miscalibration` |

The 7 dimensions that move are exactly the 7 enumerated by `long_directive`. The 2 that don't move (`algorithm_correctness`, `data_structure_choice`) are exactly the 2 not enumerated in *any* v2 preamble. The pattern fits both the original "alignment/capability split" and the simpler "enumerated/not-enumerated" reading. Probe A breaks the tie: a preamble that doesn't enumerate the 7 craft dimensions but is otherwise expert-toned doesn't lift them — it actively suppresses them. The proximate predictor is enumeration.

![Per-dimension mechanism split](../../preamble_quality_experiment_v2/experiment_v2_results/figures/fig3_mechanism_split.png)

**Action.** Don't assume any dimension is "preamble-immovable" without testing it. If you care about algorithmic correctness, enumerate it in your preamble — it may move (v2 didn't test this; an explicit-correctness probe is plausibly worth running for your domain).

**Related work.** F4 is the headline form of the same PRISM refinement called out in F2 — the v2 update at the end of [Related work § "Personas help style, not substance"](../explanation/related-work.md#personas-help-style-not-substance-the-alignment-vs-pretraining-split) discusses the implication: a preamble that explicitly enumerated correctness could in principle move accuracy too, against a strict reading of PRISM. F4's evidence is the within-rubric version of that argument.
