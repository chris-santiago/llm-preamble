# From "asymmetry" to "load-bearing channel" — refining Finding 1

> This page documents the interpretive history of Finding 1. The headline
> moved from a "negative effect is larger than the positive effect" reading
> to a sharper "the preamble channel can push output below the no-preamble
> baseline at all" reading. The shift matters because the two readings
> license different actions for practitioners.

## The original asymmetry reading

The v2 main run produced two effects vs `none` that, on first inspection,
looked like an asymmetry:

| Preamble | β vs `none` (mixed-effects) | p |
|---|---|---|
| `negative_control` ("junior developer") | **−0.060** | **5 × 10⁻⁵** |
| `long_directive` (strongest rich preamble) | +0.046 | 0.002 |

Read naively, the bad preamble hurt by 0.060, the good preamble helped
by 0.046, and the difference suggested the channel was more efficient
at *damaging* output than at *improving* it.

The naive interpretation was: "negative preambles are more dangerous
than positive preambles are useful." On that reading, the headline
takeaway becomes "be careful what you write" — a risk-management framing.

## Why that reading is misleading

The asymmetry framing has two problems.

**First, it confuses sign with strength.** What the v2 data actually
demonstrates is not that negatives are stronger than positives. It
demonstrates that *the preamble channel reaches below baseline*. If
preambles were inert or weakly additive, you could not write one that
moves output below what the model produces with no system prompt at all.
The fact that `negative_control` lands at −0.060 — strictly below `none`
— is the demonstration. The magnitude is secondary; the sign and
direction are the load-bearing observation.

**Second, the magnitude gap is partly an artifact of ceiling effects.**
`none` already scores near the top of several rubric dimensions
(documentation, type hints, organization on tasks where the model
defaults to writing them). A preamble that targets those same
dimensions has limited headroom to push them higher — the dimension is
near-ceilinged. A preamble that pushes them *down* has the full range
of the scale to work with. The asymmetry, where it appears, is partly a
mechanical consequence of where baseline sits on the rubric, not
evidence that the channel is structurally biased toward damage.

## The refined reading: a load-bearing channel

The current Finding 1 framing reads:

> The preamble channel is powerful enough that content choices move
> outputs measurably above *and* below a no-system-prompt baseline. The
> cleanest evidence is the degradation case: framings like "junior
> developer", "still learning Python", or "don't worry too much about
> style" produce *worse* code than supplying no system prompt at all.
> That's the sharp test — the model isn't just amplified by good
> preambles or unaffected by bad ones, it's actively responsive to
> content in both directions. Preambles are not decorative; they steer.

This is the same data with a different load-bearing claim. The claim
is not "negatives hurt more than positives help". The claim is
**`none` is not a floor**. The channel carries signal in both
directions, with sufficient magnitude that content choices on the
*bad* end of the spectrum demonstrate the channel exists at all.

## What this licenses

Two practical implications follow from the load-bearing reframe that
the asymmetry framing obscured.

1. **Treat every preamble change as bidirectional.** A new clause, a
   reworded directive, or an added persona is not assumed to be neutral
   or positive. If preambles can push *below* baseline, then any change
   to a working preamble is a candidate to make output worse, not just
   to leave it unchanged. The v2 evidence that supports this is `none`
   not being a floor — that is the load-bearing fact, not the relative
   magnitudes of `long_directive` vs `negative_control`.

2. **The realistic failure modes are smaller in magnitude than the
   synthetic probe but in the same direction.** `negative_control` was
   a deliberately blunt synthetic probe ("junior developer still
   learning Python") whose purpose was to *prove the channel can move
   output below baseline at all*. Production prompts rarely contain
   language that direct. The realistic failure modes — rubric mismatch
   (see [Finding 2](../findings/2-overlap-not-expertness.md)) and
   verbose dilution (see [Finding 3](../findings/3-bare-enumeration.md))
   — produce the same directional effect at smaller magnitude. The
   probe is upper-bound evidence for a channel that operates with the
   same sign in production conditions.

## The secondary observation, properly bounded

The negative-vs-positive magnitude difference is real, but it does not
support the strong asymmetry claim:

- *Real component.* `negative_control` shifts the model's stylistic
  register downward — "learning Python", "don't worry too much about
  style" — and judges (blind to the preamble) score the resulting code
  lower on the dimensions that register affects. This is a content-level
  effect, not a measurement artifact. See the
  [judge protocol methodology](../methodology/index.md).
- *Ceiling-bounded component.* The dimensions where `none` already
  scores near the top have less room to lift than to drop. The
  apparent "negative bigger than positive" gap is partly a consequence
  of where the no-preamble baseline lands on the rubric.

The two components are not separately quantified in v2; a v3 design
with a more saturated mid-range rubric could in principle decompose
them. For practical purposes, the takeaway is that the asymmetry should
not be treated as a structural fact about preambles — it is partly real
and partly a property of where `none` sits on this particular rubric.

## Why the reframe matters

The asymmetry reading risks two errors. The first is over-claiming:
"preambles are more dangerous than helpful" implies a defensive
posture (avoid changes, keep preambles minimal) that the data does not
support. The second is under-claiming the mechanism: the asymmetry
framing treats the negative as the special case to be explained, when
in fact *both* directions are evidence of the same load-bearing
channel, just with different headroom on this rubric.

The load-bearing channel reading collapses the two effects into a
single claim — `none` is not a floor — and lets the per-direction
magnitudes be whatever they are, without making the magnitude gap do
interpretive work it cannot support.

## Sources

- `README.md` Finding 1 — current framing.
- `preamble_quality_experiment_v2/CONCLUSIONS.md`
  §"Mixed-effects models", interpretation paragraph: *"The sharpest
  reading is not a positive/negative asymmetry but a demonstration that
  the preamble channel is load-bearing: `none` is not a floor —
  `negative_control` pushes CQS-craft below what the model produces
  with no system prompt at all. … The negative effect being larger in
  magnitude than the positive effect is a secondary observation,
  partly real and partly bounded by ceiling effects on rubric
  dimensions where `none` already scores near the top."*
- `preamble_quality_experiment_v2/CONCLUSIONS.md` §"Verdict", bullet 2.
- See [Finding 1](../findings/1-load-bearing-channel.md) for the
  evidence summary in finding form, and the
  [attention-allocation mechanism](attention-allocation-mechanism.md)
  for the underlying mechanism story.
