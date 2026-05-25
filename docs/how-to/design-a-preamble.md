# Designing a preamble for *your* system

The five findings collapse into a procedure:

1. **Write down the dimensions your downstream evaluator scores.** This is the most important step. If you don't have an evaluator, build one before iterating on preambles — otherwise you cannot tell if your preamble changes are helping. If your evaluator is end-user thumbs-up, treat that as a noisy proxy for the dimensions your end-users actually notice, and try to articulate what those are.

2. **Treat every preamble change as bidirectional.** Don't assume new content is neutral or positive — the channel is sensitive enough that well-intentioned additions can degrade output. v2's `negative_control` was a synthetic probe ("junior developer still learning Python") that pushed output below the no-preamble baseline, demonstrating the negative direction exists; production prompts rarely contain language that blunt, but the realistic failure modes (rubric-mismatch and verbose dilution) are covered in steps 3–5 and produce the same directional effect at smaller magnitude. Test every preamble change against your evaluator.

3. **Enumerate the evaluator's dimensions in plain language.** A bare list is sufficient; you'll capture ~70% of the maximum lift this way. The model genuinely allocates output capacity to whatever you enumerate.

4. **(Optional, low priority)** **Add imperative tone and per-dimension explanations** to capture the remaining ~30%. "Your code must: (1) [dim] — [why]; (2) [dim] — [why]; …" beats a bare list by ~30% of the gap from `none` to the maximum positive lift.

5. **Keep it focused.** Each token of preamble that isn't enumerating a dimension your evaluator scores is a token diluting the model's attention away from those that are. Workflow content, tooling preferences, and unrelated engineering virtues cost you if they aren't being measured downstream.

6. **Test it.** Run your candidate preamble vs `none` on the same eval harness. The expected lift is small but real — on the order of 1–5 points on a 100-point scale. If you see >10 points, your eval is probably overfit to your preamble (the dimensions match too tightly); if you see 0, your preamble isn't enumerating dimensions your evaluator actually measures.
