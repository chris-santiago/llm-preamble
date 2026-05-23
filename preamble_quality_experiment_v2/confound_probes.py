# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "numpy", "scipy"]
# ///
"""Three discriminating probes for the rubric-directive overlap confound.

Confound:
  long_directive's 12-clause directive list enumerates 7 of 9 always-on
  rubric dimensions. The 7 dims that move under preamble are exactly those
  7. H-mechanism (real code-craft change) and H-judge-priming (surface
  marker alignment to enumerated rubric dims) make identical predictions.

Probes:
  A — long_directive_misaligned: same length + expert tone, but the 12
      clauses name axes NOT in the rubric (compactness, performance,
      determinism, etc). If CQS-craft is still substantially above `none`,
      expert-framed directive priming has effect beyond rubric-naming.

  B — rubric_bare_list: just the rubric items as a bare enumerated list,
      no engineering-discipline framing. If this matches long_directive,
      naming the rubric items IS the whole effect. If it falls short of
      long_directive, the imperative tone + framing contribute too.

  C — antirubric_directive: same expert framing, but clauses explicitly
      DEPRIORITIZE the rubric items (no docstrings, no type hints, no
      defensive guards). If CQS-craft drops below `none`, judges follow
      preamble priming even against their stated rubric — strong evidence
      for H-judge-priming.

Reference conditions (reuse v2 main-run data):
  - `none`               (n=135, CQS=0.778)
  - `long_directive`     (n=139, CQS=0.815)
  - `negative_control`   (n=138, CQS=0.723)
  - `python_coder_agent` (n=139, CQS=0.802)

Task: task_expr_parser (creation, all 9 always-on dims + example_quality
elicited; no concurrency_safety to muddy the picture).

Subjects: all 10 v2 main-run models (3 reasoning + 7 non-reasoning).
Judges:   full 10-judge cross-judge matrix, self-judge exclusion,
          calibration anchor on rubric prompt, reasoning judges with
          reasoning excluded — exactly as main run.

Reps: 1 (n=10 per probe × cross-judge panel mean → comparable resolution
to main-run cells averaged over the 14 (model, rep) generations).

Total cost estimate: ~$3-5. Total time: ~5 min at concurrency=50.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from scipy import stats

ROOT = Path(__file__).parent
RES = ROOT / "experiment_v2_results"
OUT = ROOT / "confound_probe_results"
OUT.mkdir(exist_ok=True)

# Models from main run (same pool, same reasoning param treatment)
REASONING_MODELS = [
    "qwen/qwen3.6-flash", "deepseek/deepseek-v4-flash", "minimax/minimax-m2.5",
]
NON_REASONING_MODELS = [
    "deepseek/deepseek-v3.2", "google/gemma-4-31b-it",
    "mistralai/mistral-small-2603", "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-4o-mini", "google/gemini-3.1-flash-lite",
    "google/gemini-2.5-flash",
]
ALL_MODELS = REASONING_MODELS + NON_REASONING_MODELS
JUDGE_MODELS = ALL_MODELS


def model_family(m: str) -> str:
    return m.split("/", 1)[0]


# =============================================================================
# Probe preambles
# =============================================================================
PROBE_A_NONRUBRIC = (
    "You are an expert autonomous coding agent. Your code must: "
    "(1) Minimize total line count without sacrificing correctness. "
    "(2) Favor single-pass algorithms over multi-pass when both are correct. "
    "(3) Prefer in-place operations over copy-and-modify where safe. "
    "(4) Choose data structures matched to access patterns and asymptotic cost. "
    "(5) Use Python builtins over custom implementations of equivalent behavior. "
    "(6) Avoid unnecessary intermediate allocations. "
    "(7) Use deterministic iteration order on unordered collections. "
    "(8) Inline trivial helpers; extract when used more than twice. "
    "(9) Order code top-down: high-level entry points first, helpers below. "
    "(10) Use early returns to flatten nesting. "
    "(11) Prefer recursion only when the problem is naturally recursive. "
    "(12) Co-locate related logic; avoid sprawling across the file. "
    "Do not add unused code. Do not optimize prematurely. "
    "Write as if your code will be benchmarked, not just style-reviewed."
)

PROBE_B_BARE_RUBRIC = (
    "Your code will be evaluated on these specific dimensions: "
    "error handling consistency, edge case handling on empty/boundary/invalid "
    "inputs, type hint completeness on public functions, code organization "
    "and cohesion, documentation appropriateness (why-not-what), abstraction "
    "calibration (neither over- nor under-engineered), API ergonomics, "
    "concurrency safety where applicable, appropriate data structure choice, "
    "algorithmic correctness, and example quality when examples are requested."
)

PROBE_C_ANTIRUBRIC = (
    "You are an expert autonomous coding agent. Your code must: "
    "(1) Focus on raw algorithmic clarity above all else. "
    "(2) Avoid heavyweight documentation — code should be self-evident. "
    "(3) Type hints are optional clutter; omit them unless they materially clarify intent. "
    "(4) Don't over-engineer error handling — let exceptions propagate naturally. "
    "(5) Edge cases are the caller's responsibility, not the implementation's. "
    "(6) Prefer a single coherent function over decomposition for short solutions. "
    "(7) Use Python's dynamism freely — duck typing is the language's gift. "
    "(8) Concurrency concerns are out-of-scope for single-threaded code. "
    "(9) Library-style guards (validation, defensive checks) add noise. "
    "(10) Comments belong in commit messages, not source files. "
    "(11) APIs should be minimal; expose only what callers strictly need. "
    "(12) Naming follows convention; clarity comes from context, not verbosity. "
    "Write as if you are coding a script for personal use, not a library for others."
)

# Reference condition: `none` (no system prompt) — for direct comparison
# alongside the existing main-run data points.
PROBE_PREAMBLES: dict[str, str | None] = {
    "probe_A_nonrubric_expert": PROBE_A_NONRUBRIC,
    "probe_B_bare_rubric":      PROBE_B_BARE_RUBRIC,
    "probe_C_antirubric_expert": PROBE_C_ANTIRUBRIC,
    "none_control":             None,   # re-run a small `none` slice as
                                        # within-script reference for noise floor
}

# =============================================================================
# Task — task_expr_parser from v2 main run (verbatim)
# =============================================================================
TASK = {
    "id": "task_expr_parser",
    "category": "creation",
    "prompt": (
        "Write a Python recursive-descent parser and evaluator for arithmetic expressions.\n"
        "Requirements:\n"
        "- Supports: integers and floats, +, -, *, /, ** (right-associative), unary minus\n"
        "- Correct operator precedence: ** > unary minus > * / > + -\n"
        "- Parentheses for grouping\n"
        "- Tokenizer: splits input string into a token stream\n"
        "- Parser: builds an AST or evaluates directly via recursive descent\n"
        "- Evaluator: returns a float result\n"
        "- Error handling: raise a descriptive exception on malformed input "
        "  (unbalanced parens, unexpected characters, division by zero)\n"
        "- evaluate(expression: str) -> float is the public API\n"
        "Include type hints. Include at least 3 usage examples covering "
        "precedence, parentheses, and unary minus."
    ),
}


# =============================================================================
# Rubric and judge prompts — verbatim from main run (Amendment A1 + A5)
# =============================================================================
RUBRIC = [
    ("data_structure_choice",        "Inappropriate data structure picks (list for membership testing, dict where dataclass/NamedTuple would clarify, list where deque is the right tool for FIFO).",  "always"),
    ("algorithm_correctness",        "Algorithm fails to meet stated complexity/correctness requirements (wrong output, wrong big-O, breaks on documented edge cases).",                                "always"),
    ("error_handling_inconsistency", "Inconsistent or ad-hoc error handling (some paths raise, others silently return None; sentinels mixed with exceptions; no coherent philosophy).",                "always"),
    ("api_ergonomics",               "Public API is awkward for callers (positional-arg explosion, leaky internals, inconsistent method naming, no kwargs where they'd clarify).",                    "always"),
    ("abstraction_miscalibration",   "Over- or under-engineered for the task (speculative class hierarchies for one function; one god-function for what should be 3 cohesive units).",                "always"),
    ("code_organization",            "Tangled decomposition; functions doing too many things; unclear boundaries between layers.",                                                                    "always"),
    ("type_hint_gap",                "Public surface lacks correct/complete type annotations (private helpers exempt; 0=full coverage, 5=none).",                                                     "always"),
    ("edge_case_gap",                "Obvious edge cases not handled (empty inputs, boundary conditions, invalid inputs).",                                                                           "always"),
    ("documentation_appropriateness","Docstrings/comments mismatched to code complexity (overly verbose for trivial code, missing for complex code, what-not-why comments).",                         "always"),
    ("concurrency_safety",           "When the task requires concurrency: race conditions, missing locks, broken async patterns, double-checked-locking bugs. If the task does NOT involve concurrency, return null.", "conditional"),
    ("example_quality",              "When usage examples are requested: trivial/redundant examples that fail to demonstrate the API's real shape. If no examples are requested, return null.",      "conditional"),
]
RUBRIC_IDS = [k for k, _, _ in RUBRIC]
ALWAYS_ON = [k for k, _, kind in RUBRIC if kind == "always"]

CALIBRATION_ANCHOR = (
    "CALIBRATION (READ CAREFULLY):\n"
    "  - The 0-5 severity scale is NOT 'present vs absent'. It is a graded measure.\n"
    "  - Severity 0 means 'no detectable issue on this dimension' — uncommon.\n"
    "    Reserve it for code that is genuinely exemplary on that specific dimension.\n"
    "  - Severity 1 = a minor nuance (e.g., one type hint missing on a non-public helper;\n"
    "    one docstring slightly verbose). Most realistic algorithmic code has\n"
    "    severity 1-2 on AT LEAST 3 of the 9 always-on dimensions.\n"
    "  - Severity 2-3 = noticeable but not pervasive (e.g., one function mixing two\n"
    "    concerns; a list used where set would be marginally better).\n"
    "  - Severity 4-5 = pervasive or material defect.\n"
    "  - Refuse to score 0 unless you can name a specific reason the code is\n"
    "    unimprovable on that dimension. Do NOT default to 0 because nothing\n"
    "    obvious is wrong — score 1 when the dimension is fine-but-not-exemplary.\n"
    "  - Your job is to surface real variation between samples. If every sample\n"
    "    gets 0 on most dims, the scoring is useless to the experiment.\n"
)


def _build_rubric_prompt() -> str:
    lines = "\n".join(f"  - {k}: {desc}" for k, desc, _ in RUBRIC)
    schema = ",\n  ".join(
        f'"{k}": {{"severity": <0-5 or null>, "rationale": "<one sentence>"}}'
        for k in RUBRIC_IDS
    )
    return (
        "You are a senior Python code reviewer scoring an algorithmic Python sample on "
        "11 specific quality dimensions on a 0-5 severity scale "
        "(0=clean / no detectable issue, 5=severe / pervasive).\n\n"
        + CALIBRATION_ANCHOR +
        "\nFor the two CONDITIONAL dimensions (concurrency_safety, example_quality), "
        "return null only if the dimension does not apply to this code.\n\n"
        "Dimensions:\n" + lines + "\n\n"
        "Respond with ONLY a single JSON object, no markdown fences, no prose:\n"
        "{\n  " + schema + "\n}\n"
    )


RUBRIC_PROMPT = _build_rubric_prompt()
IDIOM_COMMENT_PROMPT = (
    "You are a senior Python code reviewer evaluating code quality. Assign "
    "idiomaticity and comment_quality scores on a 1-10 integer scale "
    "(1=worst, 10=best).\n\n"
    "Respond with ONLY a single JSON object, no markdown fences, no prose:\n"
    '{\n  "idiomaticity": <1-10>,\n  "comment_quality": <1-10>\n}\n'
)


# =============================================================================
# Generation parameters — match main run exactly
# =============================================================================
GEN_TEMPERATURE = 0.3
GEN_MAX_TOKENS = 10000
GEN_TIMEOUT = 300.0
JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_TOKENS = 1800
JUDGE_TIMEOUT = 120.0
CONCURRENCY = 50
RETRY_ATTEMPTS = 2

W_IDIOM = 0.45
W_COMMENT = 0.45
W_HYGIENE = 0.10


# =============================================================================
# Helpers (raw httpx with reasoning param + provider logging)
# =============================================================================
def _to_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _clamp(v: Any, lo: float, hi: float) -> float | None:
    f = _to_float(v)
    if f is None or f < lo or f > hi:
        return None
    return f


def extract_python_code(text: str) -> str:
    if not text:
        return ""
    fences = re.findall(r"```(?:python(?::[\w./]+)?|py)?\s*\n(.*?)```", text, re.DOTALL)
    if fences:
        return "\n\n# --- file boundary ---\n\n".join(b.strip() for b in fences)
    unclosed = re.search(r"```(?:python(?::[\w./]+)?|py)?\s*\n(.*)$", text, re.DOTALL)
    if unclosed:
        cand = unclosed.group(1).strip()
        if re.search(r"^(import |from |def |class |async def )", cand, re.MULTILINE):
            return cand
    first = text.lstrip().split("\n", 1)[0]
    if re.match(r"^(import |from |def |class |async def )", first):
        return text.strip()
    return ""


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def _post(client, sem, *, model, system, user, temperature, max_tokens,
                timeout, reasoning_mode):
    msgs = []
    if system is not None:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    body: dict[str, Any] = {
        "model": model, "messages": msgs,
        "temperature": temperature, "max_tokens": max_tokens,
    }
    if reasoning_mode == "high":
        body["reasoning"] = {"effort": "high"}
    elif reasoning_mode == "exclude":
        body["reasoning"] = {"exclude": True}

    last_err = None
    async with sem:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                        "Content-Type": "application/json",
                    },
                    json=body, timeout=timeout,
                )
                resp = r.json()
                if r.status_code != 200 or "error" in resp:
                    last_err = f"HTTP {r.status_code}: {str(resp.get('error', resp))[:200]}"
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                msg = resp["choices"][0]["message"]
                u = resp.get("usage", {}) or {}
                return {
                    "content": (msg.get("content") or "").strip(),
                    "provider": resp.get("provider"),
                    "cost": u.get("cost", 0.0),
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001
                last_err = f"{type(exc).__name__}: {str(exc)[:150]}"
                await asyncio.sleep(1.5 * (attempt + 1))
    return {"content": "", "provider": None, "cost": 0.0, "error": last_err}


# =============================================================================
# Pipeline
# =============================================================================
def gen_key(probe_id: str, model: str, rep: int) -> str:
    return f"{TASK['id']}|{probe_id}|{model}|r{rep}"


async def generate(client, sem, *, probe_id: str, model: str, rep: int) -> dict:
    preamble = PROBE_PREAMBLES[probe_id]
    mode = "high" if model in REASONING_MODELS else "off"
    result = await _post(
        client, sem, model=model, system=preamble, user=TASK["prompt"],
        temperature=GEN_TEMPERATURE, max_tokens=GEN_MAX_TOKENS,
        timeout=GEN_TIMEOUT, reasoning_mode=mode,
    )
    code = extract_python_code(result["content"])
    return {
        "key": gen_key(probe_id, model, rep),
        "probe_id": probe_id, "model": model, "rep": rep,
        "code": code, "extraction_ok": bool(code),
        "raw_preview": result["content"][:300],
        "provider": result.get("provider"),
        "cost": result.get("cost"),
        "error": result.get("error"),
    }


async def judge(client, sem, *, gen_record: dict, judge_model: str, kind: str) -> dict:
    prompt = RUBRIC_PROMPT if kind == "rubric" else IDIOM_COMMENT_PROMPT
    user = f"Code under review:\n\n```python\n{gen_record['code']}\n```"
    mode = "exclude" if judge_model in REASONING_MODELS else "off"
    result = await _post(
        client, sem, model=judge_model, system=prompt, user=user,
        temperature=JUDGE_TEMPERATURE, max_tokens=JUDGE_MAX_TOKENS,
        timeout=JUDGE_TIMEOUT, reasoning_mode=mode,
    )
    out: dict = {
        "gen_key": gen_record["key"], "probe_id": gen_record["probe_id"],
        "subject_model": gen_record["model"], "judge_model": judge_model,
        "is_self_judge": model_family(judge_model) == model_family(gen_record["model"]),
        "kind": kind, "cost": result["cost"], "judge_error": result["error"],
        "parsed": None,
    }
    if result["error"]:
        return out
    parsed = _extract_json(result["content"])
    if parsed is None:
        out["judge_error"] = f"parse_fail: {result['content'][:120]}"
        return out
    out["parsed"] = parsed
    return out


def compute_sample_cqs(gen: dict, judgments: list[dict]) -> dict:
    """Cross-judge mean, self excluded, identical to main-run computation."""
    idioms, comments, rubric_means = [], [], []
    per_dim: dict[str, list[float]] = defaultdict(list)
    for j in judgments:
        if j["is_self_judge"] or not j.get("parsed"):
            continue
        if j["kind"] == "idiom_comment":
            i = _clamp(j["parsed"].get("idiomaticity"), 1, 10)
            c = _clamp(j["parsed"].get("comment_quality"), 1, 10)
            if i is not None:
                idioms.append(i)
            if c is not None:
                comments.append(c)
        elif j["kind"] == "rubric":
            sevs = []
            for k in RUBRIC_IDS:
                item = j["parsed"].get(k)
                sev_raw = item.get("severity") if isinstance(item, dict) else item
                if sev_raw is None:
                    continue
                sev = _clamp(sev_raw, 0.0, 5.0)
                if sev is None:
                    continue
                per_dim[k].append(sev)
                sevs.append(sev)
            if sevs:
                rubric_means.append(float(np.mean(sevs)))

    idiom_score = float(np.mean(idioms)) if idioms else None
    comment_score = float(np.mean(comments)) if comments else None
    sev_mean = float(np.mean(rubric_means)) if rubric_means else None

    cqs = None
    if idiom_score is not None and comment_score is not None and sev_mean is not None:
        cqs = (W_IDIOM * (idiom_score / 10.0)
               + W_COMMENT * (comment_score / 10.0)
               + W_HYGIENE * (1.0 - sev_mean / 5.0))

    return {
        "gen_key": gen["key"], "probe_id": gen["probe_id"], "model": gen["model"],
        "n_idiom": len(idioms), "n_comment": len(comments),
        "n_rubric": len(rubric_means),
        "idiom": idiom_score, "comment": comment_score, "rubric_sev_mean": sev_mean,
        "per_dim_means": {k: float(np.mean(v)) if v else None for k, v in per_dim.items()},
        "cqs_craft": cqs,
    }


# =============================================================================
# Reference data extraction (re-use v2 main-run results for none/long_directive)
# =============================================================================
def load_reference_cqs() -> dict[str, Any]:
    """Pull per-sample CQS-craft for task_expr_parser from the main run."""
    gens_path = RES / "generations.jsonl"
    sample_cqs_path = RES / "sample_cqs.json"
    if not gens_path.exists() or not sample_cqs_path.exists():
        return {}
    gens = [json.loads(l) for l in gens_path.read_text().splitlines() if l.strip()]
    cqs = json.loads(sample_cqs_path.read_text())
    cqs_by_key = {s["gen_key"]: s for s in cqs}

    by_preamble: dict[str, list[float]] = defaultdict(list)
    by_preamble_dims: dict[tuple[str, str], list[float]] = defaultdict(list)
    for g in gens:
        if not g["extraction_ok"] or g["task_id"] != TASK["id"]:
            continue
        s = cqs_by_key.get(g["key"])
        if not s or s["cqs_craft"] is None:
            continue
        by_preamble[g["preamble_id"]].append(s["cqs_craft"])
        for dim, mean_v in (s.get("per_dim_means") or {}).items():
            if mean_v is not None:
                by_preamble_dims[(g["preamble_id"], dim)].append(mean_v)
    return {"cqs": by_preamble, "per_dim": by_preamble_dims}


def bootstrap_ci(vals, n_boot=2000, alpha=0.05):
    arr = np.asarray(vals, dtype=float)
    if len(arr) < 2:
        m = float(arr.mean()) if len(arr) else float("nan")
        return m, m, m
    rng = np.random.default_rng(2026_05_23)
    boot = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    return (float(arr.mean()),
            float(np.quantile(boot, alpha / 2)),
            float(np.quantile(boot, 1 - alpha / 2)))


# =============================================================================
# Main
# =============================================================================
async def main_async(args) -> int:
    if "OPENROUTER_API_KEY" not in os.environ:
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2

    print("=== confound probes (A misaligned-expert / B bare-rubric / C anti-rubric) ===")
    print(f"  task: {TASK['id']}")
    print(f"  probes: {list(PROBE_PREAMBLES.keys())}")
    print(f"  subjects: {len(ALL_MODELS)} models, {len(REASONING_MODELS)} reasoning")
    print(f"  judges:   {len(JUDGE_MODELS)} (full cross-judge matrix)")

    # ---- Generations ----
    jobs = [(p, m, 0) for p in PROBE_PREAMBLES.keys() for m in ALL_MODELS]
    print(f"\n[1/2] generating {len(jobs)} samples...")
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as client:
        gens = await asyncio.gather(*[
            generate(client, sem, probe_id=p, model=m, rep=r) for (p, m, r) in jobs
        ])
        n_ok = sum(1 for g in gens if g["extraction_ok"])
        print(f"  extracted ok: {n_ok}/{len(gens)}")

        (OUT / "generations.jsonl").write_text(
            "\n".join(json.dumps(g, default=str) for g in gens) + "\n"
        )

        # ---- Judging ----
        judge_jobs = []
        for g in gens:
            if not g["extraction_ok"]:
                continue
            for jm in JUDGE_MODELS:
                for kind in ("idiom_comment", "rubric"):
                    judge_jobs.append((g, jm, kind))
        print(f"\n[2/2] judging {len(judge_jobs)} (gen, judge, kind) tuples...")
        judgments = await asyncio.gather(*[
            judge(client, sem, gen_record=g, judge_model=jm, kind=kind)
            for (g, jm, kind) in judge_jobs
        ])
        n_parsed = sum(1 for j in judgments if j.get("parsed"))
        print(f"  parsed ok: {n_parsed}/{len(judgments)}")
        (OUT / "judgments.jsonl").write_text(
            "\n".join(json.dumps(j, default=str) for j in judgments) + "\n"
        )

    # ---- Aggregation ----
    judg_by_gen: dict[str, list[dict]] = defaultdict(list)
    for j in judgments:
        judg_by_gen[j["gen_key"]].append(j)
    sample_cqs = []
    for g in gens:
        if not g["extraction_ok"]:
            continue
        sample_cqs.append(compute_sample_cqs(g, judg_by_gen.get(g["key"], [])))
    (OUT / "sample_cqs.json").write_text(json.dumps(sample_cqs, indent=2, default=str))

    # ---- Reference data from main run ----
    ref = load_reference_cqs()
    ref_cqs = ref.get("cqs", {})
    ref_dims = ref.get("per_dim", {})

    # ---- Per-probe summary ----
    probe_cqs: dict[str, list[float]] = defaultdict(list)
    probe_dims: dict[tuple[str, str], list[float]] = defaultdict(list)
    for s in sample_cqs:
        if s["cqs_craft"] is None:
            continue
        probe_cqs[s["probe_id"]].append(s["cqs_craft"])
        for dim, mean_v in (s.get("per_dim_means") or {}).items():
            if mean_v is not None:
                probe_dims[(s["probe_id"], dim)].append(mean_v)

    # ---- Build report ----
    lines: list[str] = ["# Confound probe report",
                        "",
                        f"Task: `{TASK['id']}`  |  subjects: {len(ALL_MODELS)} models  |  judges: full cross-judge matrix",
                        ""]
    lines.append("## 1. CQS-craft per probe vs reference conditions")
    lines.append("")
    lines.append("| Condition | n | mean | 95% CI |")
    lines.append("|---|---|---|---|")

    ref_order = [
        ("none (main-run reference)", "none"),
        ("long_directive (main-run reference)", "long_directive"),
        ("negative_control (main-run reference)", "negative_control"),
        ("python_coder_agent (main-run reference)", "python_coder_agent"),
    ]
    for label, key in ref_order:
        vals = ref_cqs.get(key, [])
        if not vals:
            lines.append(f"| `{label}` | 0 | — | — |")
            continue
        m, lo, hi = bootstrap_ci(vals)
        lines.append(f"| `{label}` | {len(vals)} | {m:.4f} | [{lo:.4f}, {hi:.4f}] |")

    lines.append("")
    lines.append("| Probe | n | mean | 95% CI | Δ vs `none` (main) |")
    lines.append("|---|---|---|---|---|")
    none_mean = float(np.mean(ref_cqs.get("none", []))) if ref_cqs.get("none") else float("nan")
    for pid in ("probe_A_nonrubric_expert", "probe_B_bare_rubric",
                "probe_C_antirubric_expert", "none_control"):
        vals = probe_cqs.get(pid, [])
        if not vals:
            lines.append(f"| `{pid}` | 0 | — | — | — |")
            continue
        m, lo, hi = bootstrap_ci(vals)
        delta = m - none_mean
        lines.append(f"| `{pid}` | {len(vals)} | {m:.4f} | [{lo:.4f}, {hi:.4f}] | {delta:+.4f} |")

    # ---- Probe-specific significance tests ----
    lines.append("")
    lines.append("## 2. Significance — Mann-Whitney U vs main-run `none`")
    lines.append("")
    lines.append("| Probe | n | mean | U | p (two-sided) |")
    lines.append("|---|---|---|---|---|")
    none_vals = ref_cqs.get("none", [])
    for pid in ("probe_A_nonrubric_expert", "probe_B_bare_rubric",
                "probe_C_antirubric_expert", "none_control"):
        vals = probe_cqs.get(pid, [])
        if not vals or len(none_vals) < 2:
            lines.append(f"| `{pid}` | — | — | — | — |")
            continue
        try:
            U, p = stats.mannwhitneyu(vals, none_vals, alternative="two-sided")
            lines.append(f"| `{pid}` | {len(vals)} | {float(np.mean(vals)):.4f} | "
                         f"{U:.1f} | {p:.4f} |")
        except Exception as exc:
            lines.append(f"| `{pid}` | — | — | — | (err: {exc}) |")

    # ---- Per-dimension severity ----
    lines.append("")
    lines.append("## 3. Per-dimension severity — probes vs reference conditions")
    lines.append("")
    lines.append("Cross-judge mean severity (0 = clean, 5 = severe) per probe condition")
    lines.append("on the 9 always-on rubric dimensions. Reference columns are from the")
    lines.append("v2 main run on the same task.")
    lines.append("")
    cols = [
        ("none ref", lambda d: ref_dims.get(("none", d), [])),
        ("long_dir ref", lambda d: ref_dims.get(("long_directive", d), [])),
        ("neg ref", lambda d: ref_dims.get(("negative_control", d), [])),
        ("A (misalign)", lambda d: probe_dims.get(("probe_A_nonrubric_expert", d), [])),
        ("B (bare)", lambda d: probe_dims.get(("probe_B_bare_rubric", d), [])),
        ("C (anti)", lambda d: probe_dims.get(("probe_C_antirubric_expert", d), [])),
        ("none_control", lambda d: probe_dims.get(("none_control", d), [])),
    ]
    header = "| Dimension | " + " | ".join(c[0] for c in cols) + " |"
    sep = "|---|" + "|".join(["---"] * len(cols)) + "|"
    lines.append(header)
    lines.append(sep)
    for dim in ALWAYS_ON:
        row = [f"`{dim}`"]
        for _, getter in cols:
            vals = getter(dim)
            row.append("—" if not vals else f"{float(np.mean(vals)):.2f} (n={len(vals)})")
        lines.append("| " + " | ".join(row) + " |")

    # ---- Verdict logic ----
    lines.append("")
    lines.append("## 4. Discrimination verdict")
    lines.append("")
    if probe_cqs.get("probe_A_nonrubric_expert"):
        a_m = float(np.mean(probe_cqs["probe_A_nonrubric_expert"]))
        ld_m = float(np.mean(ref_cqs.get("long_directive", []))) if ref_cqs.get("long_directive") else None
        none_m = none_mean
        lines.append(f"**Probe A — misaligned expert directive:** mean CQS = {a_m:.4f}")
        if not np.isnan(none_m):
            lines.append(f"  - Δ vs `none`: {a_m - none_m:+.4f}")
        if ld_m is not None:
            lines.append(f"  - Δ vs `long_directive`: {a_m - ld_m:+.4f}")
            ratio = (a_m - none_m) / (ld_m - none_m) if (ld_m - none_m) != 0 else float("nan")
            lines.append(f"  - **Recovery ratio** (A − none) / (long − none): {ratio:+.2f}")
            lines.append(f"    - ratio ≈ 1.0 → expert framing accounts for nearly all of long_directive's effect (H-mechanism weak; expert priming generic)")
            lines.append(f"    - ratio ≈ 0.0 → naming the rubric items is what matters (H-judge-priming or H-mechanism-via-naming)")
            lines.append(f"    - ratio < 0  → misaligned directives actively hurt vs no preamble")
        lines.append("")

    if probe_cqs.get("probe_B_bare_rubric"):
        b_m = float(np.mean(probe_cqs["probe_B_bare_rubric"]))
        ld_m = float(np.mean(ref_cqs.get("long_directive", []))) if ref_cqs.get("long_directive") else None
        none_m = none_mean
        lines.append(f"**Probe B — bare rubric list:** mean CQS = {b_m:.4f}")
        if not np.isnan(none_m):
            lines.append(f"  - Δ vs `none`: {b_m - none_m:+.4f}")
        if ld_m is not None:
            lines.append(f"  - Δ vs `long_directive`: {b_m - ld_m:+.4f}")
            ratio = (b_m - none_m) / (ld_m - none_m) if (ld_m - none_m) != 0 else float("nan")
            lines.append(f"  - **Recovery ratio** (B − none) / (long − none): {ratio:+.2f}")
            lines.append(f"    - ratio ≈ 1.0 → naming the rubric items reproduces the full effect (H-judge-priming dominant)")
            lines.append(f"    - ratio ≈ 0.0 → bare naming is insufficient; expert framing matters separately")
        lines.append("")

    if probe_cqs.get("probe_C_antirubric_expert"):
        c_m = float(np.mean(probe_cqs["probe_C_antirubric_expert"]))
        none_m = none_mean
        lines.append(f"**Probe C — anti-rubric directive:** mean CQS = {c_m:.4f}")
        if not np.isnan(none_m):
            lines.append(f"  - Δ vs `none`: {c_m - none_m:+.4f}")
            lines.append(f"    - Δ << 0 → judges follow preamble priming even against their stated rubric (strong H-judge-priming evidence)")
            lines.append(f"    - Δ ≈ 0  → anti-rubric framing produces neutral effect (judges weight rubric over preamble)")
            lines.append(f"    - Δ > 0  → unexpected; possibly artifact of clearer / more focused code under simpler instructions")
        lines.append("")

    report_path = OUT / "REPORT.md"
    report_path.write_text("\n".join(lines))
    print(f"\nreport: {report_path}")

    total_cost = (sum(g.get("cost") or 0 for g in gens)
                  + sum(j.get("cost") or 0 for j in judgments))
    print(f"total cost: ${total_cost:.4f}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.parse_args()
    return asyncio.run(main_async(p.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
