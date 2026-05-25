# ml-lab debate protocol

The investigation was driven by the [`ml-lab`](https://github.com/anthropics/claude-code) skill in **debate mode**. Debate mode replaces a single critique pass with a structured adversarial protocol: a critic and a defender agent argue every finding to convergence under explicit verdict rules. The protocol exists because a one-shot critique either over-accepts (defender concedes everything to look cooperative) or under-accepts (defender rebuts everything to defend turf). The multi-round structure forces both sides to commit to falsifiable positions.

## The 4-stage flow

The protocol runs in fixed stages, each captured as a JSON artifact in the experiment directory:

1. **Stage A.1 — Critic R1.** Single ml-critic pass against the active hypothesis + PoC. Output: a list of findings each tagged with severity (0–10) and class (FATAL / MATERIAL / MINOR / NIT). Artifact: `critic_r1.json`.
2. **Stage A.2 — Defender R1.** Single ml-defender pass adjudicating each non-suppressed finding. For each finding the defender selects one of: **CONCEDE** (accept fully, commit to fix), **DEFER** (accept but propose an empirical-test pathway), or **REBUT-DESIGN / REBUT-SCOPE** (argue the finding is wrong or out-of-scope). Artifact: `defender_r1.json`.
3. **Stage B — Multi-round critic-r2 ↔ defender-R2.** Critic and defender alternate, refining adjusted severities, with `min_rounds=2` and `max_rounds=4`. Each round produces `critic_r2_round{N}.json` and `defender_r2_round{N}.json`. Convergence: all findings reach terminal states (no PARTIAL moves), or `max_rounds` exhausted.
4. **Stage C — `derive_verdict`.** A mechanical scorecard converts the per-finding terminal states into a case-level verdict:
    - **`critique_wins`** — any finding ends as a CONCEDE at severity ≥ 9 (constitutional override).
    - **`empirical_test_agreed` (ETA)** — finding ends as a DEFER with a concrete empirical gate.
    - **`defense_wins`** — finding ends as REBUT or as a low-severity CONCEDE.

The case verdict is the most severe per-finding verdict; a single `critique_wins` dominates any number of `defense_wins`.

## Worked example — v2 F1 (the constitutional override)

The v2 PoC review surfaced an F1 finding that drove the entire debate to `critique_wins`. The full sequence is in [`preamble_quality_experiment_v2/INVESTIGATION_LOG.jsonl`](https://github.com/chrissantiago/llm-preamble/blob/main/preamble_quality_experiment_v2/INVESTIGATION_LOG.jsonl) seq 8–25. The relevant `detail` field text, quoted verbatim:

**seq 10 — Critic R1 returns F1 (Stage A.1):**

> Critic R1 returned 7 findings. F1 (sev 9, FATAL): out-of-range judge scores enter CQS-craft unclamped — VERIFIED in PoC data (deepseek emitted -1 on python_coder_agent/modeflag_sort). F2 (sev 8, FATAL): trap task 'exact signature' clause defeats resistance probe. F3-F5 (sev 5-6, MATERIAL): rubric hygiene flooring, comment-quality vs preamble-conciseness confound, 9/11 rubric dims structurally inapplicable to algorithmic tasks. F6-F7 (sev 2-3, MINOR): judge calibration, length-confound sensitivity.

**seq 11 — Orchestrator marks F1 ORACLE-VERIFIED before defender sees it (Stage A.2 setup):**

> Dispatching ml-defender R1 (Mode 1) with 7 non-suppressed findings from critic R1. Note: F1 has been ORACLE-VERIFIED by the orchestrator (deepseek -1 sentinel found in PoC judge records); defender should not REBUT the empirical claim, only adjudicate severity/scope.

**seq 12 — Defender R1 (Stage A.2):**

> Defender R1: F1 CONCEDE (sev 9, fix=clamp); F2 DEFER (sev 8, prompt rewrite); F3 REBUT-DESIGN (sev 6->2); F4 DEFER (sev 6); F5 DEFER (sev 5); F6 REBUT-DESIGN (sev 3->1); F7 REBUT-SCOPE (sev 2->0). Overall: empirical_test_agreed.

Note the defender's initial overall verdict was `empirical_test_agreed` — they had not yet recognized that a sev-9 CONCEDE constitutes a constitutional override.

**seq 15 — Defender R2 Round 1 self-corrects (Stage B):**

> Defender R2 R1: F1 CONCEDE sev 9 (unchanged); F2 DEFER sev 7 (accepted critic reduction, tightened settling); F3 REBUT-DESIGN sev 2; F4 DEFER sev 5 (tightened); F5 DEFER sev 5; F6 REBUT-DESIGN sev 1 (rank-invariance argument, held below critic 2); F7 REBUT-SCOPE sev 0. Defender SELF-CORRECTED R1 verdict from empirical_test_agreed to critique_wins citing F1 CONCEDE at sev 9 mechanically triggering it.

**seq 16 — derive_verdict Round 1 (Stage C, mechanical):**

> Round 1 verdict: critique_wins (F1 CONCEDE sev 9, constitutional override). F2/F4/F5 → ETA. F3/F6/F7 → defense_wins. Not converged: min_rounds=2 not reached AND non-terminal findings remain. Proceed to round 2.

Rounds 2 and 3 then settled the remaining findings without disturbing F1. The final state at seq 25:

> Debate converged after 3 rounds: stop_reason=fully_resolved (all findings at terminal states — F1 critique_wins, F2-F7 defense_wins). Verdict stable critique_wins driven solely by F1 CONCEDE sev 9. No min_rounds guard needed.

The F1 fix — clamping out-of-range judge scores — was implemented in Phase A pre-flight (`INVESTIGATION_LOG.jsonl` seq 29) before the main run began, and the PoC re-run confirmed it changed `python_coder_agent` CQS-craft from 0.627 to 0.805. Without the debate protocol, the `-1` sentinel was a silent data-poisoning bug that would have shipped into the headline metric.

## Meta-observation: the same shape in both cycles

Both v1 and v2 ended with `critique_wins` driven by a **single high-severity CONCEDE**, with the remaining findings either ETA-converted to concrete empirical tests or rebutted to `defense_wins`. In v2 the constitutional override was F1 (unclamped judge scores). In v1 the analogous override was the original instrument's static-analysis dominance, which was conceded and demoted to a diagnostic panel.

The pattern is not coincidental — the debate protocol is calibrated so that the strongest single finding moves the case verdict, and the remaining findings are forced into one of two productive end-states: a committed fix (ETA, becomes a pre-flight phase) or a documented disagreement (defense_wins, becomes a methodology note). The protocol is hostile to vague, unfalsifiable critique — every finding must terminate in something the experimentalist can act on or argue with.

## Where this lives in the repo

- **v2 debate artifacts** — `preamble_quality_experiment_v2/critic_r1.json`, `defender_r1.json`, and `critic_r2_round{1,2,3}.json` / `defender_r2_round{1,2,3}.json`.
- **Verdict trail** — every dispatch, return, and verdict derivation has a corresponding entry in [`INVESTIGATION_LOG.jsonl`](investigation-logs.md) with `cat` in `{subagent, debate, decision}`.
- **Resulting amendments** — F1's fix became Phase A; F2's became the prompt-rewrite gate; F4/F5 became Phase D2 calibration. The full inventory is in [Amendments](amendments.md).
