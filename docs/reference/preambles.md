# Preambles

Verbatim text of every system prompt (preamble) tested in the v2 investigation. The full set is 9 main-run conditions + 3 post-hoc confound probes = 12 conditions.

**Source of truth:** the Python files under `preamble_quality_experiment_v2/` are canonical — this document is a copy maintained for readability. If the two ever disagree, the `.py` files win. Specifically:

- Main-run preambles: [`preamble_quality_v2_main.py`](preamble_quality_experiment_v2/preamble_quality_v2_main.py) (lines ~104–148)
- Probe preambles: [`confound_probes.py`](preamble_quality_experiment_v2/confound_probes.py) (lines ~91–134)
- `python_coder_agent` is loaded at runtime from `~/Dropbox/claude-config/plugins/chris-code/agents/python-coder.md` and is **not** inlined below (see note in §"The 9 main-run preambles" below).

**Generation protocol (applies to every condition unless noted):** `temperature = 0.3`, `max_tokens = 10000`, reasoning effort `"high"` for the 3 reasoning models, `"off"` for the 7 non-reasoning models, full 10-judge cross-judge panel with self-judgments excluded from primary CQS.

---

## The 9 main-run preambles

Listed in approximate "weakest → strongest" order (by main-run CQS-craft mean), matching the order in [`README.md` Finding 1](README.md) and [`CONCLUSIONS.md`](preamble_quality_experiment_v2/CONCLUSIONS.md).

### 1. `trivial_baseline` (CQS-craft = 0.556)

No system prompt. The user prompt is literally just the **task name** (e.g., `"task_expr_parser"`), not the task description. Generation temperature is **1.0**, not 0.3.

```
(no system prompt)
```

User message: `task_expr_parser`

**Purpose.** Defines the lower anchor of the CQS-craft scale. Confirms the model uses *any* coherent context productively when present — the −0.222 cliff vs `none` is what the model produces when it has neither system context nor a full task description.

---

### 2. `negative_control` (CQS-craft = 0.723; β = −0.060 vs `none`, p = 5×10⁻⁵)

```
You are a junior developer still learning Python. Write code that works
but don't worry too much about style or best practices.
```

**Purpose.** A deliberately downward-anchoring framing. Pushes output measurably below the no-preamble baseline (Finding 1). Synthetic — no real production prompt has language this blunt.

---

### 3. `none` (CQS-craft = 0.778; reference)

```
(no system prompt)
```

User message: the full task description (not just the name).

**Purpose.** The no-preamble baseline. Reference for all mixed-effects β coefficients.

---

### 4. `minimal` (CQS-craft = 0.779)

```
You are a helpful assistant.
```

**Purpose.** The shortest non-empty preamble. Statistically indistinguishable from `none` — confirms that mere presence of *any* system message does not lift craft scores. Content is what moves the needle.

---

### 5. `generic_coding` (CQS-craft = 0.791)

```
You are an expert software engineer with deep knowledge of Python.
Write clean, efficient, and maintainable code.
```

**Purpose.** A reasonable-sounding but content-light expert framing. Two short sentences; no enumerated dimensions. Tests whether tone alone, with no dimension enumeration, lifts craft.

---

### 6. `persona_only` (CQS-craft = 0.794)

```
You are a senior staff software engineer at a top-tier tech company.
```

**Purpose.** Pure persona, no directives. Tests whether claimed seniority alone lifts craft scores.

---

### 7. `real_agent` (CQS-craft = 0.799; β = +0.030 vs `none`, p = 0.067)

```
You are an expert autonomous coding agent. Your code must:
(1) Be idiomatic Python — use built-ins, standard library, and established patterns.
(2) Have appropriate abstraction — no over-engineering, no under-engineering.
(3) Include defensive programming: validate inputs, handle edge cases, fail clearly.
(4) Use precise naming — variables, functions, and classes should be self-documenting.
(5) Add comments only where they explain *why*, never *what*.
(6) Be maintainable: prefer explicit over implicit, simple over clever.
Do not add unused code. Do not optimize prematurely.
Write as if the next engineer maintaining this code is skilled but unfamiliar with context.
```

**Purpose.** A synthetic but plausible production-style agent preamble. Six enumerated dimensions plus closing rules. Functions as the "what a thoughtful prompt engineer would write" reference point.

---

### 8. `long_directive` (CQS-craft = 0.815; β = +0.046 vs `none`, p = 0.002)

```
You are an expert autonomous coding agent. Your code must:
(1) Be idiomatic Python — use built-ins, standard library, and established patterns.
(2) Have appropriate abstraction — no over-engineering, no under-engineering.
(3) Include defensive programming: validate inputs, handle edge cases, fail clearly.
(4) Use precise naming — variables, functions, and classes should be self-documenting.
(5) Add comments only where they explain *why*, never *what*.
(6) Be maintainable: prefer explicit over implicit, simple over clever.
(7) Handle all concurrency and thread-safety concerns explicitly.
(8) Prefer composition over inheritance; avoid deep class hierarchies.
(9) Make all side effects and I/O boundaries explicit.
(10) Write tests or testable interfaces — prefer dependency injection over globals.
(11) Log errors at the right severity — never swallow exceptions silently.
(12) Document public interfaces with docstrings; skip obvious internal comments.
Do not add unused code. Do not optimize prematurely.
Write as if the next engineer maintaining this code is a senior developer unfamiliar with this codebase.
```

**Purpose.** The strongest single-prompt condition in the main run. Extends `real_agent` from 6 to 12 enumerated dimensions; clauses 7–12 enumerate 5 of the 9 always-on rubric dimensions ([Finding 4](README.md#finding-4--no-alignment-vs-capability-split-just-preambleevaluator-overlap)). Clause-to-rubric overlap is the dominant driver of its lift — see the confound probes below for the identification argument.

---

### 9. `python_coder_agent` (CQS-craft = 0.802; β = +0.024 vs `none`, p = 0.126)

**Loaded at runtime** from `/Users/chrissantiago/Dropbox/claude-config/plugins/chris-code/agents/python-coder.md` (everything after the second `---` YAML-frontmatter delimiter). The file is ~3,000 tokens of senior-engineer directives, S3+ pattern lists, refactoring heuristics, and workflow steps — far longer than any other condition.

**Not inlined here** because (a) it's a long external file maintained outside this repo and (b) the version that was tested at v2 main-run time may differ from the current `HEAD` of the chris-code plugin. To see the version that was tested, check `~/Dropbox/claude-config/` history at v2 main-run timestamp (May 2026).

**Purpose.** Real-world production system prompt — tests whether v2's findings generalize from synthetic preambles to a deployed agent. Result: scores between `real_agent` and `long_directive`; the ~3,000-token length **dilutes the rubric-enumerating clauses** relative to `long_directive`'s focused 12-clause form. The 11× per-token efficiency cliff between `long_directive` and `python_coder_agent` is the most striking quantitative finding about prompt brevity in v2.

---

## The 3 confound probes

Run post-hoc on `task_expr_parser` (n=10 per probe, full 10-judge cross-judge panel) to disambiguate `long_directive`'s lift between "rubric overlap" and "expert framing." See [`README.md` Finding 2](README.md#finding-2--preamble-effects-are-governed-by-rubric-overlap-not-by-expertness) and [`CONCLUSIONS.md` §"Confound probes"](preamble_quality_experiment_v2/CONCLUSIONS.md).

### A. `probe_A_nonrubric_expert` (CQS = 0.673; Δ vs `none` on this task = −0.155, p = 0.0001)

```
You are an expert autonomous coding agent. Your code must:
(1) Minimize total line count without sacrificing correctness.
(2) Favor single-pass algorithms over multi-pass when both are correct.
(3) Prefer in-place operations over copy-and-modify where safe.
(4) Choose data structures matched to access patterns and asymptotic cost.
(5) Use Python builtins over custom implementations of equivalent behavior.
(6) Avoid unnecessary intermediate allocations.
(7) Use deterministic iteration order on unordered collections.
(8) Inline trivial helpers; extract when used more than twice.
(9) Order code top-down: high-level entry points first, helpers below.
(10) Use early returns to flatten nesting.
(11) Prefer recursion only when the problem is naturally recursive.
(12) Co-locate related logic; avoid sprawling across the file.
Do not add unused code. Do not optimize prematurely.
Write as if your code will be benchmarked, not just style-reviewed.
```

**Purpose.** Same expert framing and same 12-clause structure as `long_directive`, but the **content enumerates non-rubric axes** (compactness, single-pass, in-place ops, deterministic iteration). Tests the question: *is the lift coming from the expert framing or from rubric overlap?*

**Finding.** Hurts CQS by 7× the lift `long_directive` provides — when the expert directive doesn't overlap the rubric, the channel pushes output in the opposite direction. The model genuinely follows the preamble's content: probe A's outputs have visibly fewer docstrings, type hints, and defensive guards.

---

### B. `probe_B_bare_rubric` (CQS = 0.842; Δ vs `none` on this task = +0.015, ≈ `long_directive` on the same task)

```
Your code will be evaluated on these specific dimensions: error handling
consistency, edge case handling on empty/boundary/invalid inputs, type
hint completeness on public functions, code organization and cohesion,
documentation appropriateness (why-not-what), abstraction calibration
(neither over- nor under-engineered), API ergonomics, concurrency safety
where applicable, appropriate data structure choice, algorithmic
correctness, and example quality when examples are requested.
```

**Purpose.** Bare list of rubric dimensions, **no expert framing**, no "you must", no compound clauses explaining each item. One sentence, comma-separated. Tests: *how much of `long_directive`'s lift survives stripping the framing?*

**Finding.** Captures ~70% of `long_directive`'s positive lift on this task. The recovery ratio `(B − none) / (long_directive − none) = 0.70` is the [Finding 3](README.md#finding-3--bare-enumeration-captures-most-of-the-positive-effect-expert-framing-is-decorative) headline. The remaining ~30% comes from imperative tone + compound explanatory clauses.

---

### C. `probe_C_antirubric_expert` (CQS = 0.673; Δ vs `none` on this task = −0.154, p = 0.0001)

```
You are an expert autonomous coding agent. Your code must:
(1) Focus on raw algorithmic clarity above all else.
(2) Avoid heavyweight documentation — code should be self-evident.
(3) Type hints are optional clutter; omit them unless they materially clarify intent.
(4) Don't over-engineer error handling — let exceptions propagate naturally.
(5) Edge cases are the caller's responsibility, not the implementation's.
(6) Prefer a single coherent function over decomposition for short solutions.
(7) Use Python's dynamism freely — duck typing is the language's gift.
(8) Concurrency concerns are out-of-scope for single-threaded code.
(9) Library-style guards (validation, defensive checks) add noise.
(10) Comments belong in commit messages, not source files.
(11) APIs should be minimal; expose only what callers strictly need.
(12) Naming follows convention; clarity comes from context, not verbosity.
Write as if you are coding a script for personal use, not a library for others.
```

**Purpose.** Same expert framing and same 12-clause structure as `long_directive`, but each clause **deprioritizes a rubric dimension** that `long_directive` emphasizes ("type hints are clutter", "edge cases are the caller's responsibility", "comments belong in commit messages"). Tests the symmetry of probe A: *does an explicitly anti-rubric directive hurt by the same magnitude?*

**Finding.** Same magnitude as probe A within noise (−0.154 vs −0.155). The penalty for misalignment is symmetric whether the preamble points the model at a *different* set of axes (probe A) or at the *negation* of the rubric axes (probe C). Together with probe A and probe B, this triangulates the mechanism: **preamble–evaluator overlap density drives both sign and magnitude** of the effect.

---

## Cross-references

- Mechanism interpretation and headline findings: [`README.md`](README.md)
- Full pre-registration, amendments, and the rubric these preambles were judged against: [`SPEC_V2.md`](preamble_quality_experiment_v2/SPEC_V2.md)
- All numerical results, mixed-effects analysis, weight-sensitivity panel: [`CONCLUSIONS.md`](preamble_quality_experiment_v2/CONCLUSIONS.md)
- Literature situating: [`RELATED_WORK.md`](RELATED_WORK.md)
- Raw generations under each probe condition: [`confound_probe_results/generations.jsonl`](preamble_quality_experiment_v2/confound_probe_results/generations.jsonl)
