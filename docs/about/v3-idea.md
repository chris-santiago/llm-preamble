# V3 Idea — Multi-Turn Agentic Preamble Investigation

> **Status: IDEA ONLY.** This is not a specification, not a pre-registration,
> not a commitment to run anything. It captures the follow-on question v2's
> findings opened up, sketches what investigating it would require, and is
> honest about what's unknown. If anyone (me, the author, a collaborator)
> picks this up later, this document is a starting point for the
> conversation — not the conversation itself. The actual design would need
> a proper `SPEC_V3.md` and a fresh debate cycle.

## The gap v2 leaves open

v2 established, with high confidence (KW p = 9.2 × 10⁻¹⁸ across 1,260
generations), that preambles affect single-turn Python code generation
under the v2 11-dim craft rubric, with rubric-overlap as the proximate
mechanism (confirmed by the post-hoc confound probes). The
practical-design implication: short, focused, rubric-aligned preambles
win for single-turn craft.

But **almost nobody actually ships single-turn coding agents**. Production
systems — Claude Code, Cursor, Aider, GitHub Copilot Workspace, Cline,
similar — run multi-turn loops: the model plans, edits files, runs tests,
reads back errors, asks clarifying questions, commits, refactors based on
review. The system prompt is loaded once and must serve every turn.

v2's central finding — *the model's attention is finite, and content that
doesn't match the downstream evaluator suppresses CQS by directing
attention away* — has a direct corollary in multi-turn: **the content
that's "wasted" in single-turn (workflow advice, tool selection, commit
discipline, stop-and-ask vs proceed-with-assumption heuristics) is
exactly the multi-turn primitives that single-turn never invokes.** That
content earns its tokens in the regime that v2 didn't measure.

The practical practitioner question — "what's the right preamble for an
agentic coding system" — is therefore *not answered by v2*, even though
v2 produced a clean single-turn ordering. The v2 finding that
`long_directive` (500 tokens, all craft) beats `python_coder_agent`
(~3000 tokens, craft + operational + workflow) is a finding about
single-turn evaluation, not a recommendation for production deployment.

## What v2 actually establishes vs what extrapolates

### Holds in v2's regime (single-turn, single Python code blob output, craft rubric)

- Preambles change generated code (KW p ≪ 10⁻¹⁰).
- Effect is asymmetric: bad preambles hurt more than good preambles help.
- Mechanism is rubric-aligned attention allocation; bare rubric naming
  captures ~70% of the maximum lift; expert framing adds the remaining
  ~30%.
- Short, focused preambles outperform long, mixed-content preambles for
  the single-turn craft objective.
- Static-analysis tools cannot detect preamble effects.

### Extrapolates plausibly to multi-turn (not measured, mechanism-based prediction)

- The asymmetric finding should transfer. Register-and-quality-bar shifts
  from negative priming are persistent properties of the conditioned
  model, not single-turn artifacts; they should persist across turns.
- The attention-allocation mechanism keeps working — preambles direct
  the model toward whatever they enumerate. The multi-turn question is
  what to enumerate.
- Cross-turn craft cohesion (does turn 7 use the same naming/error-handling
  patterns as turn 1?) is *plausibly* improved by craft-aligned preambles,
  because the model has a consistent target. This is a guess.

### Cannot be inferred from v2 at all

- How operational content (workflow, tool choice, commit discipline,
  test-before-claim-done) affects multi-turn agent behavior. v2 measured
  zero of this.
- How preamble influence decays / persists / compounds across turns.
- Whether attention-allocation theory holds when the model also has to
  manage tool calls, intermediate state, and turn-taking — three things
  v2 had none of.
- Whether explicit "agent persona" framing (operating-mode statements,
  capability self-descriptions) matters more in multi-turn where the
  model needs to maintain consistent operating mode across turns.
- The right *combination* of craft + operational content. v2 tested
  craft-only (`long_directive`) and craft-plus-operational
  (`python_coder_agent`); a third axis — operational-only,
  craft-stripped — was never tested.

## Why `python_coder_agent` looked bad in v2 — and may not be bad in production

This is worth stating clearly because the v2 headline can mislead. The
`python_coder_agent` system prompt is a real production preamble designed
for Claude Code's multi-turn loop. v2 measured it *out of its design
regime* — no tool use, no intermediate state, no user feedback turns, no
commit boundaries, no subagent dispatch, no test-then-claim-done discipline.

v2 tested only the *per-turn craft content* of a preamble whose primary
job is *across-turn operational consistency*. Of course it underperformed
`long_directive` for that narrow test. The right interpretation of v2's
ordering is "v2 evaluated single-turn craft; on that evaluation,
craft-focused preambles beat mixed-content preambles". It is *not*
"production preambles like python_coder_agent are inferior to single-turn
manifestos for shipping" — that would be a category error.

v1/v2 should arguably never have included `python_coder_agent` in the
single-turn condition set, or at least should have flagged it as
out-of-design. The post-hoc confound probes (§"Confound probes" in
`CONCLUSIONS.md`) made this gap visible by quantifying how much of
`long_directive`'s lift is attributable to rubric-aligned enumeration
density — and how much `python_coder_agent` "wastes" by spreading
attention across non-rubric content. The cleaner v2 takeaway would have
been: rubric-aligned, focused preambles win; production preambles are
designed for a different objective and shouldn't be compared like-for-like.

## What a v3 design would need

The list below is the minimum to make multi-turn measurable. Each item
opens up substantial design decisions that would need a real spec.

### 1. Multi-turn task definitions

Sessions with 5–15 turns minimum, each producing partial output,
intermediate state, or follow-up questions. **Not** a single code-blob
target. Some candidate task families:

- *Feature implementation with review-cycle*: implement → reviewer
  comments → refactor → add tests
- *Debug a failing test across 3–4 hypotheses*: read failure → propose
  hypothesis → instrument → diagnose → fix → verify
- *Extend an existing module while preserving patterns*: read existing
  code → propose change scope → ask clarifying question → implement →
  validate consistency
- *Multi-file refactor*: identify smell → propose decomposition → execute
  across files → re-test → adjust

Each task family probes a different axis (craft cohesion / operational
discipline / state management / cross-file consistency).

### 2. Three evaluation axes, scored independently

- **Per-turn craft.** v2's 11-dim rubric, applied to each turn's output.
  Already validated; carries over directly.
- **Across-turn cohesion.** Does the model preserve naming, style,
  error-handling patterns from earlier turns? Does the file structure
  stay coherent as the session progresses? Probably a holistic judge
  prompt that reads the whole session and scores 0–5 on consistency
  dimensions.
- **Operational competence.** Did the model ask appropriately when
  ambiguous? Did it test before claiming done? Did it scope changes
  correctly (not 10× larger than asked)? Did it stop and re-read when
  blocked vs forge ahead with wrong assumptions? Per-turn binary
  judgments aggregated to session-level rates.

These three axes are likely correlated but not collinear. A preamble
might trade per-turn craft for operational discipline; v3's whole point
is to quantify those trade-offs.

### 3. User-simulator or human-in-the-loop

Multi-turn requires realistic mid-session feedback. Options:

- **LLM-driven simulator** with a fixed persona ("the developer asking
  for this feature"). Cheap, scalable, but introduces another model and
  another set of confounds. Most viable for a first cycle. Would need
  careful design: simulator must not have privileged access to the
  evaluator rubric, otherwise it confounds with v2's rubric-overlap
  problem at a session level.
- **Human-in-the-loop** for a small validation set. Expensive but
  necessary for external validity — at least 20–30 sessions across
  conditions should be human-driven to confirm the simulator behaves
  like real users.
- **Hybrid**: simulator drives the main run; humans drive a validation
  subset; agreement between them is a hygiene check.

The simulator design is itself a research question. Could be a topic in
its own right before v3 — calibrating a user-simulator on a small set of
real Claude Code transcripts, then validating it produces similar
session dynamics.

### 4. Stronger evaluator for end-of-session holistic scoring

Cross-judge panels at single-turn cost ~$70 in v2. At multi-turn session
length, judging cost balloons because the judge has to read the whole
session, not one code blob. A 10-turn session at ~500 tokens per turn is
5,000 tokens of context per judge call, vs v2's ~1,500. The right move
is probably **(a) reduce panel size to 3–5 judges instead of 10**, and
**(b) use stronger judge models** (Claude Sonnet/Opus, GPT-5 if available)
that are more reliable per-call so the panel needs less averaging.

Estimated cost per session evaluation: ~$0.20–0.50 at panel size 3.
Total v3 budget probably ~$300–500 if running 500–1000 sessions across
conditions.

### 5. Preamble conditions reframed for the multi-turn regime

The v2 condition set was designed for the single-turn question. v3 needs
a different set:

- `craft_only` — `long_directive`-style. Tests whether per-turn craft
  directives alone sustain craft across turns, at the cost of
  operational discipline.
- `operational_only` — workflow + tools + process + commit discipline +
  ask-vs-proceed heuristics, with craft directives stripped. Tests
  whether operational primitives alone (without craft enumeration)
  affect cross-turn outcomes.
- `mixed` — `python_coder_agent`-style. The production-realistic
  combination.
- `bare` — `none` baseline. Tests whether multi-turn agents need *any*
  preamble at all (single-turn baseline says yes; multi-turn unknown).
- Plus possibly probes that vary *order* (craft directives first vs
  operational first, in long-mixed preambles) and *length* (compressed
  vs expanded versions of mixed).

### 6. Pre-registered hypothesis structure (sketch)

- **H1.** Craft preambles do well on per-turn craft but poorly on
  operational competence.
- **H2.** Operational preambles do the inverse — strong operational
  competence, weak per-turn craft.
- **H3.** Mixed preambles trade some per-turn craft for cross-turn
  cohesion at acceptable net quality, with the trade-off favorable in
  multi-turn but unfavorable in single-turn (a within-regime / between-
  regime asymmetry).
- **H4.** The cross-turn cohesion gain from mixed preambles is bounded
  by the per-turn craft loss — there is no free lunch.
- **H5 (mechanism).** Probes A/B/C from v2 transfer: bare enumeration of
  what the *session-level* evaluator scores reproduces most of the
  multi-turn lift, and "expert framing" is again decorative.

H3 and H4 together would resolve the v3 practitioner question: do
production-style preambles like `python_coder_agent` earn their tokens
in their design regime?

## Cost / effort estimate

Rough order-of-magnitude (not for budgeting):

- **v2 cost**: $33, ~110 min wall, ~2 weeks of design + analysis time
- **v3 cost**: $300–500 (sessions × cost-per-session × replication)
- **v3 wall time**: 4–8 hours per main run (sessions are slow; simulator
  + agent + tool calls compound)
- **v3 design time**: 6–10 weeks. The instrument is much more complex
  than v2's. Multi-turn task definitions need real care. Simulator
  design alone could be a separate small project.

The biggest design risk in v3 is **simulator confound**: if the LLM
user-simulator behaves differently across preamble conditions
(plausibly, because the agent's outputs influence what the simulator
sees and asks next), the apparent preamble effect could be
session-dynamics noise rather than agent quality. Mitigation: fix the
simulator's prompt across all conditions; pre-script the user's
opening turn; randomize over simulator seeds.

## Open design questions

These would have to be answered before any v3 run:

1. **What counts as "cohesion"?** Is it about preserving exact style
   choices (snake_case vs camelCase) or about higher-level patterns
   (error-handling philosophy, abstraction calibration)? Both, scored
   separately?
2. **How long is a session?** 5 turns vs 15 turns is a different
   experiment. 5 may be too short to see operational effects; 15 may
   be too long to scale.
3. **What tools does the agent have?** A v3 agent needs at least
   read-file, write-file, run-tests. Tool design choices (mocked vs
   real, sandboxed Python vs full shell) will leak into results.
4. **Is the simulator the same model as the agent?** Probably no
   (creates self-talk confounds), but then which model? Cheapest call
   would be a small dedicated simulator (gpt-4o-mini); but quality of
   simulated feedback matters.
5. **How to handle agent failures during a session?** Timeouts, broken
   tool calls, refusals. v3 needs an explicit policy.
6. **Tasks need ground truth.** For multi-turn evals, knowing what
   "good completion" looks like is harder than for single-turn (where
   the code blob is the entire output). Need either pre-scored
   reference sessions or a clear definition of session success
   independent of agent behavior.
7. **Subject model pool.** v2's 10-model pool extends to v3 naturally,
   but multi-turn cost may force narrowing to 4–6 models. Which ones?
   The reasoning models become more important in multi-turn (planning,
   tool use); the non-reasoning pool may be less interesting.

## What the practitioner answer is right now, without v3

For single-turn code generation (rare in production): trim aggressively,
enumerate rubric items, drop operational content.

For multi-turn agentic coding (what production actually is): **trust
production preambles like `python_coder_agent` over single-turn
benchmark winners like `long_directive`.** The operational content
earns its tokens in the regime that matters. v2's finding that it
underperforms in single-turn is real but irrelevant to deployment.

Meta-point worth stating explicitly: v2's headline "the strongest
preamble effect is `long_directive`" is a finding *about the v2
design*, not a finding any production system designer should act on.
The right action is to either (a) build a multi-turn benchmark for
your specific use case, (b) inherit a production preamble that someone
else has iterated on in-distribution, or (c) wait for a v3-style
investigation to land.

## What v3 would and wouldn't settle

**Would settle:**

- Whether production preambles like `python_coder_agent` outperform
  v2's `long_directive` in their design regime
- Whether the v2 brevity finding inverts in multi-turn (probably yes,
  given the attention-allocation mechanism applied to multi-turn
  objectives)
- The proportional contribution of craft directives vs operational
  content in mixed preambles
- Whether the attention-allocation mechanism keeps holding when the
  model also has to manage tools and state

**Would not settle:**

- Whether human users in real production sessions exhibit the same
  session dynamics as a simulator
- Whether the v3 cohesion / operational rubrics are themselves the
  right operationalization of "quality multi-turn agent behavior"
- Cross-language generalization (still Python only unless explicitly
  scoped wider)
- Long-running session behavior (>15 turns) — context-window dynamics
  become a confound at that length

## Quick reference — v2 results that motivated this

- `long_directive` (~500 tokens, 12 enumerated craft clauses): single-turn
  CQS lift +0.046, p = 0.002
- `python_coder_agent` (~3000 tokens, real production preamble): single-turn
  CQS lift +0.024, p = 0.126 (not significant in mixed-effects)
- Lift-per-100-tokens: bare rubric list (probe B) ≈ 0.015; long_directive
  ≈ 0.009; python_coder_agent ≈ 0.0008. Strongly declining.
- The 20× difference in lift-per-token between probe B and
  python_coder_agent is the mechanism evidence that suggests v3 is
  worth doing — there's something the non-craft content might be doing
  that v2 cannot measure but that production users implicitly rely on.

---

*If picking this up later: start by sketching one of the 4 candidate
task families in §"Multi-turn task definitions" in real detail (full
prompts, expected user-turn structure, success criteria), then prototype
the simulator on that single task before building any infrastructure.
v2's lesson was that pre-flight catches instrument bugs the main run
can't recover from; v3's equivalent will be sessions-flight — test the
session protocol end-to-end on one condition before scaling.*
