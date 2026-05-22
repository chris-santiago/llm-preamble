# Report Addendum — Production Re-Evaluation

The experiment ran under controlled conditions (fixed tasks, batch execution, an
8-judge cross-judge matrix, offline scoring). This addendum re-evaluates the
finding against the constraints of *actually using it* — either to (a) choose a
preamble for a deployed coding agent, or (b) build a pipeline that measures
preamble-driven code quality. The recommendation changes under these constraints.

## Recommendation (revised under production constraints)

**Experimental recommendation:** preambles produce a modest but real improvement
in code craft (idiomaticity, comment quality), best with rich expert/long-
directive preambles; static analysis cannot detect this.

**Production-corrected recommendation — two parts:**

1. **For choosing a preamble:** a rich, directive-heavy expert preamble is worth
   it for code-craft-sensitive agents; a "junior developer" framing is actively
   harmful and should never ship. The gain is real but modest (≈0.10–0.15 on a
   0–1 comment-quality scale), so justify it against token cost (long_directive
   adds ~300 preamble tokens to *every* call).

2. **For measuring preamble quality:** **do not gate on static analysis.** Any
   CI/eval pipeline that scores agent output with radon/pylint/complexity metrics
   will systematically report "no preamble effect" — a false negative. Use an
   LLM-judge panel scoring idiomaticity and comment quality.

This is a **reversal** of the naive read of the primary metric. Taken at face
value, the composite CQS says "preambles don't matter" (p=0.63). The production-
relevant truth is the opposite: they matter on the craft dimensions, and the
default measurement instrument (static analysis) is blind to it.

## The four production checks

**1. Retraining / refresh dynamics.** The "model" here is the judge panel, not a
trained model. It drifts when vendor models change. **`grok-4.1-fast` was
deprecated mid-experiment** — a live demonstration: a hardcoded judge panel
silently loses a member and 404s. A production judge panel needs a health check
on every run and a pinned-but-monitored model list with a defined replacement
cadence.

**2. Update latency.** Preamble evaluation is inherently batch/offline — you
measure quality on a sample of generations, not in the hot path. Latency budget is
the judge round-trip (here: 8 judges × N samples). For a cross-judge panel this is
N×K calls; a fixed 3–4 model panel (none of which are the subject) is the
cost-appropriate production choice — self-preference bias was negligible (F3,
d=0.16, p=0.13), so a full self-inclusive matrix buys little.

**3. Operational complexity.** A production preamble-eval pipeline needs: a held-
out hard-task suite (creation + refactoring; trivial tasks are useless — they
ceiling out), robust code extraction (≥15% of weak-model outputs are unparseable
prose and must be detected, not scored zero), an LLM-judge panel with structured-
output parsing and retry, and aggregation that does **not** dilute the judge signal
with static metrics. Alert on: judge-panel 404/availability, extraction-failure
rate per model, and judge-score variance.

**4. Failure modes.**
- *Weak subject model emits no code* (nemotron ~15%): preamble quality is moot if
  the model can't produce parseable code. Gate on extraction success first.
- *Static-only eval* → false "no effect." The most likely real-world failure,
  because static analysis is the default, cheap, deterministic choice.
- *Judge panel collapse* (deprecation) → silent loss of statistical power.
- *Single-judge or self-judge* → small but nonzero bias; use a cross-judge panel.

## Deployment roadmap

1. **Shadow:** run the LLM-judge eval offline on a sample of existing agent
   output across candidate preambles; confirm the idiomaticity/comment-quality
   separation reproduces on your own task distribution.
2. **Canary:** A/B two preambles (e.g. current vs long_directive) on a subset of
   real traffic; measure craft scores plus token-cost delta and any task-success
   regression.
3. **Full:** adopt the winning preamble; keep the judge-panel eval as a recurring
   regression gate on craft, separate from functional correctness tests.
   Rollback trigger: craft-score regression beyond CI, or task-success drop.

## Open questions

- Does the effect hold on *agentic* multi-file tasks, not single-response
  generation? (This experiment is single-turn.)
- Magnitude vs token cost: is +0.1 comment quality worth ~300 tokens/call at scale?
- Are real production preambles (10k–50k tokens, tool definitions) qualitatively
  different from the condensed conditions tested here? (F2 remains only partially
  resolved — priming and instruction-richness both contribute, but full-length
  production preambles were not tested.)
- Would a craft-calibrated static metric (e.g. one rewarding appropriate
  abstraction) recover any signal, or is LLM-judge fundamentally required?
