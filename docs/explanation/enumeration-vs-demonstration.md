# Enumeration vs demonstration — why plans don't transfer structural quality

> Showing an executing agent well-structured code in a plan does not
> transfer structural quality to the agent's output. **Examples are
> descriptive context; enumeration is directive content.** A planner and
> an executor can be the same model and still produce code of different
> quality, because what each attends to is governed by the preamble each
> runs under — and preambles work by enumeration, not by demonstration.

## The puzzle this page explains

A common assumption in multi-agent coding workflows is that if a planner
produces a well-structured implementation plan — with good function
decomposition, clear error handling, typed interfaces — the executor
will inherit that quality when it implements the plan. The structural
choices the planner made will, the assumption goes, propagate into the
executor's output.

The v2 evidence says this assumption is wrong, and the
[attention-allocation mechanism](attention-allocation-mechanism.md)
explains why.

## The argument

### 1. Preambles work by enumerating dimensions, not by exhibiting them

Probe B, the "bare rubric" preamble, contained no engineering virtue
language, no expert framing, no demonstrations of well-structured code.
It contained one sentence: a list of the dimensions the rubric would
score. It recovered 70% of `long_directive`'s lift over `none`
(probe B 0.842 vs `long_directive` 0.848 on `task_expr_parser`,
B-vs-`none` p = 0.50). The recovery ratio is the load-bearing fact:
**naming the dimensions is sufficient to reallocate the model's
craft-attention budget toward them.**

See [Finding 3](../findings/3-bare-enumeration.md) for the empirical
detail.

### 2. Examples in a plan are descriptive, not directive

When a plan shows the executor a well-structured function, the plan is
saying *"this is how the author wrote it"*. The model has no preamble
clause that says *"your output will be evaluated on docstring quality,
type hint coverage, error handling consistency"*. The example sits in
user-message content as a description of one solved instance — it
demonstrates that someone, at some point, wrote it that way.

The attention-allocation reading predicts that this descriptive context
does not redirect the model's output budget the way enumeration does. A
demonstration of a well-typed function does not enumerate *type hint
completeness* as a dimension the executor's output will be measured on.
It exhibits the property in one instance. The two are not the same
signal to the model.

### 3. Probe A is the negative-direction proof

If demonstration were equivalent to enumeration, then probe A's
preamble — which describes a *non-rubric* set of qualities (compactness,
performance, determinism, in-place operations) — should at minimum be
neutral on rubric dimensions. The model has all of its pretraining-time
exposure to well-typed, well-documented Python. A non-rubric directive
should leave that pretraining-default behavior intact.

It does not. Probe A produced CQS −0.155 vs `none` (p = 0.0001) and
visibly fewer docstrings, fewer type hints, fewer defensive guards. The
model genuinely reallocated capacity away from the rubric dimensions
toward whatever the preamble named — even though the preamble named
qualities that, in many domains, would be considered marks of good
code. The model is responsive to what the preamble enumerates, full
stop.

### 4. Same model, two roles, two outputs

Consider a workflow where the same underlying model runs as both
planner and executor:

- The **planner** runs under a preamble that enumerates *plan-quality*
  dimensions: completeness, decomposition, risk identification, step
  ordering, dependency tracking.
- The **executor** runs under a preamble that enumerates *execution*
  dimensions: tool-use precision, file-edit minimality, test-running
  discipline, scope adherence.

These are the same model. Neither preamble enumerates docstring
quality, type-hint coverage, or error-handling consistency. By the
attention-allocation reading, neither role's output will be especially
strong on those dimensions — and if the executor's preamble is verbose
on workflow content that does not enumerate craft, that verbosity
*costs* craft via attention dilution
([Finding 3](../findings/3-bare-enumeration.md), `python_coder_agent`
case).

The planner's structural choices in the *plan content* it produces are
descriptive context to the executor. They do not transfer into the
executor's directive channel. The executor's craft output is governed
by what the executor's preamble enumerates, not by what the planner
demonstrated.

## What the proximate predictor actually is

The proximate predictor of craft quality in any single execution is
not "did a competent planner write a good plan" and not "is this a
strong model". It is **what the executor's preamble enumerates as
evaluation dimensions**, intersected with what the downstream evaluator
measures (see [Finding 2](../findings/2-overlap-not-expertness.md)).

This reframes a common architectural question. The question
"how do I make sure my executor produces well-typed, well-documented
code?" is often answered with "give it a better plan". The v2 evidence
says the answer is **"enumerate type-discipline and documentation in
the executor's preamble"** — because that is the channel the model
actually uses to reallocate its output budget.

## Implication for plan-driven agentic workflows

1. **The planner's craft choices do not propagate by demonstration.**
   If you want the executor to write docstrings, the executor's
   preamble must enumerate documentation as a dimension. Showing
   docstrings in the plan does not substitute.

2. **The executor's preamble is the unit of intervention for craft.**
   Iterating on plan quality optimizes the planner's output (which is
   text the executor reads as context). Iterating on the executor's
   preamble optimizes the executor's output (which is the code the
   user ships).

3. **Verbose plans dilute the executor's attention.** Even if a plan
   contains no craft directives, every token of plan the executor
   reads competes for the same finite output capacity. A plan loaded
   with workflow narrative is, on the attention-allocation reading,
   spending budget that could otherwise sit on craft dimensions.

4. **Channel asymmetry is real.** Plan content delivered to the
   executor sits in user-message content; the executor's preamble sits
   in the system slot. The two channels have different
   instruction-following weight — see the
   [system vs user channel](system-vs-user-channel.md) page for the
   wire-format verification.

## Sources

- [Finding 2 — preamble–evaluator overlap is the predictor](../findings/2-overlap-not-expertness.md).
- [Finding 3 — bare enumeration captures ~70% of the lift](../findings/3-bare-enumeration.md).
- The [attention-allocation mechanism](attention-allocation-mechanism.md)
  page, which this argument builds on directly.
- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Refined hypothesis:
  H-attention-allocation".
- `README.md` Finding 2 and Finding 3 — the empirical anchors for the
  enumeration claim.
