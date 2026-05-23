# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Combined re-probe: Phase C (anchored vs unanchored judge on reasoning models)
and Phase D2 (prevalence audit of the redesigned 11-dim algorithmic-code rubric).

Design:
  - Subject models: 3 reasoning-tier models (qwen3.6-flash, deepseek-v4-flash,
    minimax-m2.5). Reasoning parameter passed explicitly (effort=high).
  - Preambles: {none, python_coder_agent}.
  - Tasks: 3 algorithmic creation/refactor probes (lru_ttl_cache, expr_parser,
    mini_sql_engine) — span concurrency, parsing, and high-discretion API design.
  - Replications: 2 per cell. Total generations: 3 × 2 × 3 × 2 = 36.

Each generation is judged THREE times by a fixed judge model (gpt-4o-mini, picked
for its v1-confirmed reliability on this scoring task):
  - Phase C unanchored: bare 0-5 / 1-10 ratings.
  - Phase C anchored: same with the "score relative to inherent complexity"
    directive added (the v1 anchoring fix).
  - Phase D2 rubric: the redesigned 11-dim algorithmic-code severity rubric.

Outputs:
  - reprobe_results/generations.json (full text + extraction + provider field)
  - reprobe_results/judgments.json (all judge calls, parsed)
  - reprobe_results/REPORT.md (Phase C |Δ| panel, Phase D2 per-dim non-zero rates)

Gates:
  - Phase C trigger: |Δ| > 0.5 on either idiom or comment score (1-10 scale)
    averaged across reasoning models. If triggered, the anchored judge prompt
    becomes the default for main run; if not, judge prompt stays unanchored.
  - Phase D2 gate: ≥3 of 9 always-on rubric dimensions show ≥10% non-zero
    severity rate. If fails, escalate (rubric needs another redesign pass).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

import httpx

ROOT = Path(__file__).parent
OUTDIR = ROOT / "reprobe_results"
OUTDIR.mkdir(exist_ok=True)

REASONING_MODELS = [
    "qwen/qwen3.6-flash",
    "deepseek/deepseek-v4-flash",
    "minimax/minimax-m2.5",
]
JUDGE_MODEL = "openai/gpt-4o-mini"

GEN_TEMPERATURE = 0.3
GEN_MAX_TOKENS = 10000
GEN_TIMEOUT = 240.0
JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_TOKENS = 1500
JUDGE_TIMEOUT = 120.0
CONCURRENCY = 50          # known-safe (v1 rubric run, preflight)
RETRY_ATTEMPTS = 2

# ----- preambles -----
PYTHON_CODER_AGENT_PATH = Path(
    "/Users/chrissantiago/Dropbox/claude-config/plugins/chris-code/agents/python-coder.md"
)


def _load_python_coder_preamble() -> str:
    raw = PYTHON_CODER_AGENT_PATH.read_text()
    parts = raw.split("---\n", 2)
    return (parts[2] if len(parts) >= 3 and raw.startswith("---") else raw).strip()


PYTHON_CODER_AGENT_PREAMBLE = _load_python_coder_preamble()

PREAMBLES = {
    "none": None,
    "python_coder_agent": PYTHON_CODER_AGENT_PREAMBLE,
}

# ----- tasks (3 algorithmic creation/refactor) -----
TASKS = [
    {
        "id": "task_lru_ttl_cache",
        "category": "creation",
        "prompt": (
            "Write a Python class implementing a thread-safe LRU cache with per-entry "
            "TTL expiry. Requirements: O(1) get/put, per-entry TTL, LRU eviction (skip "
            "expired during selection), thread-safe, get(key) returns value if present "
            "and unexpired else None, put(key, value, ttl_seconds), size() returns "
            "count of non-expired entries. Include type hints and a brief usage example. "
            "Do not use functools.lru_cache."
        ),
    },
    {
        "id": "task_expr_parser",
        "category": "creation",
        "prompt": (
            "Write a Python recursive-descent parser and evaluator for arithmetic "
            "expressions. Supports integers/floats, + - * / ** (right-associative), unary "
            "minus, parentheses, correct precedence (** > unary minus > * / > + -). "
            "Tokenizer + parser + evaluator. Raise a descriptive exception on malformed "
            "input. Public API: evaluate(expression: str) -> float. Include type hints "
            "and ≥3 usage examples covering precedence, parentheses, unary minus."
        ),
    },
    {
        "id": "task_mini_sql_engine",
        "category": "creation",
        "prompt": (
            "Implement a small in-memory SQL-like query engine in Python. A Table class "
            "holds a list of dict rows. Support: select(*columns), where(predicate), "
            "join(other_table, on=lambda l,r: bool), group_by(column), "
            "order_by(column, descending=False), limit(n). Composable fluent API. "
            "Include type hints and 2-3 usage examples."
        ),
    },
]

REPLICATIONS = 2  # 3 models × 2 preambles × 3 tasks × 2 reps = 36 generations

# ----- redesigned 11-dim algorithmic-code rubric (SPEC §6.4 A1) -----
NEW_RUBRIC = [
    ("data_structure_choice",        "Inappropriate data structure picks (e.g., list for membership testing, dict where dataclass/NamedTuple would clarify, list where deque is the right tool for FIFO).",  "always"),
    ("algorithm_correctness",        "Algorithm fails to meet stated complexity/correctness requirements (wrong output, wrong big-O, breaks on documented edge cases).",                                          "always"),
    ("error_handling_inconsistency", "Inconsistent or ad-hoc error handling (some paths raise, others silently return None; sentinels mixed with exceptions; no coherent philosophy).",                          "always"),
    ("api_ergonomics",               "Public API is awkward for callers (positional-arg explosion, leaky internals, inconsistent method naming, no kwargs where they'd clarify).",                              "always"),
    ("abstraction_miscalibration",   "Over- or under-engineered for the task (speculative class hierarchies for one function; one god-function for what should be 3 cohesive units).",                          "always"),
    ("code_organization",            "Tangled decomposition; functions doing too many things; unclear boundaries between layers.",                                                                              "always"),
    ("type_hint_gap",                "Public surface lacks correct/complete type annotations (private helpers exempt; 0=full coverage, 5=none).",                                                               "always"),
    ("edge_case_gap",                "Obvious edge cases not handled (empty inputs, boundary conditions, invalid inputs).",                                                                                     "always"),
    ("documentation_appropriateness","Docstrings/comments mismatched to code complexity (overly verbose for trivial code, missing for complex code, what-not-why comments).",                                   "always"),
    ("concurrency_safety",           "When the task requires concurrency: race conditions, missing locks, broken async patterns, double-checked-locking bugs. If the task does NOT involve concurrency, return null.", "conditional"),
    ("example_quality",              "When usage examples are requested: trivial/redundant examples that fail to demonstrate the API's real shape. If no examples are requested, return null.",                "conditional"),
]
NEW_ITEM_IDS = [k for k, _, _ in NEW_RUBRIC]
ALWAYS_ON_IDS = [k for k, _, kind in NEW_RUBRIC if kind == "always"]


# ----- judge prompts -----
def _build_old_judge(anchored: bool) -> str:
    # Phase C uses the *idiom + comment* part only — old rubric items already covered
    # by the standing v2 instrument. The anchored variant adds the v1 anchoring
    # directive on comment_quality.
    anchor_extra = (
        "\n\nIMPORTANT for comment_quality: score relative to the INHERENT COMPLEXITY of "
        "the code, not its verbosity. A focused implementation with concise docstrings "
        "should score as well as a longer one with extensive documentation, if the "
        "documentation matches the code's needs.\n"
        if anchored else "\n"
    )
    return (
        "You are a senior Python code reviewer evaluating code quality. Assign "
        "idiomaticity and comment_quality scores on a 1-10 integer scale "
        "(1=worst, 10=best)." + anchor_extra +
        "\nRespond with ONLY a single JSON object, no markdown fences, no prose:\n"
        '{\n  "idiomaticity": <1-10>,\n  "comment_quality": <1-10>\n}\n'
    )


PHASE_C_UNANCHORED = _build_old_judge(anchored=False)
PHASE_C_ANCHORED = _build_old_judge(anchored=True)


def _build_new_rubric_judge() -> str:
    lines = "\n".join(f"  - {k}: {desc}" for k, desc, _ in NEW_RUBRIC)
    schema_inner = ",\n  ".join(
        f'"{k}": {{"severity": <0-5 or null>, "rationale": "<one sentence>"}}'
        for k in NEW_ITEM_IDS
    )
    return (
        "You are a senior Python code reviewer scoring an algorithmic Python sample on "
        "11 specific quality dimensions. For each dimension, assign a severity score "
        "0-5 (0 = clean / no issue with this dimension, 5 = severe / pervasive). "
        "For the two CONDITIONAL dimensions (concurrency_safety, example_quality), "
        "return null if the dimension does not apply to this code (e.g., no "
        "concurrency requirement; no examples requested in the task). Each item "
        "also gets a one-sentence rationale.\n\n"
        "Dimensions:\n" + lines + "\n\n"
        "Respond with ONLY a single JSON object, no markdown fences, no prose:\n"
        "{\n  " + schema_inner + "\n}\n"
    )


PHASE_D2_RUBRIC_JUDGE = _build_new_rubric_judge()


# ----- helpers -----
def _to_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _clamp(value: Any, lo: float, hi: float) -> float | None:
    f = _to_float(value)
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
        candidate = unclosed.group(1).strip()
        if re.search(r"^(import |from |def |class |async def )", candidate, re.MULTILINE):
            return candidate
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


# ----- raw HTTP call (so we can pass reasoning + capture provider field) -----
async def _post(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    *,
    model: str,
    system: str | None,
    user: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    use_reasoning: bool,
) -> dict:
    messages: list[dict] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if use_reasoning:
        body["reasoning"] = {"effort": "high"}

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
                    json=body,
                    timeout=timeout,
                )
                resp = r.json()
                if r.status_code != 200 or "error" in resp:
                    last_err = f"HTTP {r.status_code}: {resp.get('error', resp)}"
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                msg = resp["choices"][0]["message"]
                content = (msg.get("content") or "").strip()
                u = resp.get("usage", {})
                ctd = u.get("completion_tokens_details", {}) or {}
                return {
                    "content": content,
                    "provider": resp.get("provider"),
                    "model_returned": resp.get("model"),
                    "completion_tokens": u.get("completion_tokens"),
                    "reasoning_tokens": ctd.get("reasoning_tokens", 0),
                    "cost": u.get("cost", 0.0),
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001
                last_err = f"{type(exc).__name__}: {exc}"
                await asyncio.sleep(1.5 * (attempt + 1))
    return {"content": "", "error": last_err, "provider": None,
            "completion_tokens": 0, "reasoning_tokens": 0, "cost": 0.0}


# ----- workflow -----
async def generate(client, sem, *, task: dict, preamble_id: str, model: str, rep: int) -> dict:
    preamble = PREAMBLES[preamble_id]
    is_reasoning = model in REASONING_MODELS
    result = await _post(
        client, sem,
        model=model,
        system=preamble,
        user=task["prompt"],
        temperature=GEN_TEMPERATURE,
        max_tokens=GEN_MAX_TOKENS,
        timeout=GEN_TIMEOUT,
        use_reasoning=is_reasoning,
    )
    code = extract_python_code(result["content"])
    return {
        "task_id": task["id"],
        "category": task["category"],
        "preamble_id": preamble_id,
        "model": model,
        "rep": rep,
        "code": code,
        "extraction_ok": bool(code),
        "raw_text": result["content"][:400],
        "provider": result.get("provider"),
        "completion_tokens": result.get("completion_tokens"),
        "reasoning_tokens": result.get("reasoning_tokens"),
        "cost": result.get("cost"),
        "error": result.get("error"),
    }


async def judge(client, sem, *, code: str, system_prompt: str, kind: str) -> dict:
    user = f"Code under review:\n\n```python\n{code}\n```"
    result = await _post(
        client, sem,
        model=JUDGE_MODEL,
        system=system_prompt,
        user=user,
        temperature=JUDGE_TEMPERATURE,
        max_tokens=JUDGE_MAX_TOKENS,
        timeout=JUDGE_TIMEOUT,
        use_reasoning=False,
    )
    if result["error"]:
        return {"kind": kind, "judge_error": result["error"], "parsed": None}
    parsed = _extract_json(result["content"])
    if parsed is None:
        return {"kind": kind, "judge_error": f"parse_fail: {result['content'][:120]}",
                "parsed": None}
    return {"kind": kind, "judge_error": None, "parsed": parsed,
            "cost": result.get("cost")}


# ----- analysis -----
def analyze(generations: list[dict], judgments: list[dict]) -> dict:
    """Per-sample roll-up + Phase C delta + Phase D2 prevalence."""
    by_gen: dict[int, dict] = {}
    for j in judgments:
        gid = j["gen_idx"]
        by_gen.setdefault(gid, {})[j["kind"]] = j

    # Phase C: |Δ| anchored - unanchored on idiom + comment, by reasoning model
    phase_c_rows = []
    for gid, gen in enumerate(generations):
        if not gen["extraction_ok"]:
            continue
        b = by_gen.get(gid, {})
        unanch = (b.get("c_unanchored", {}) or {}).get("parsed")
        anch = (b.get("c_anchored", {}) or {}).get("parsed")
        if not unanch or not anch:
            continue
        ui = _clamp(unanch.get("idiomaticity"), 1, 10)
        uc = _clamp(unanch.get("comment_quality"), 1, 10)
        ai = _clamp(anch.get("idiomaticity"), 1, 10)
        ac = _clamp(anch.get("comment_quality"), 1, 10)
        if ui is None or uc is None or ai is None or ac is None:
            continue
        phase_c_rows.append({
            "model": gen["model"], "task_id": gen["task_id"],
            "preamble_id": gen["preamble_id"],
            "idiom_unanch": ui, "idiom_anch": ai, "idiom_delta": ai - ui,
            "comment_unanch": uc, "comment_anch": ac, "comment_delta": ac - uc,
        })

    phase_c_by_model = defaultdict(lambda: {"idiom_delta": [], "comment_delta": []})
    for r in phase_c_rows:
        phase_c_by_model[r["model"]]["idiom_delta"].append(r["idiom_delta"])
        phase_c_by_model[r["model"]]["comment_delta"].append(r["comment_delta"])

    phase_c_summary = {
        "rows": phase_c_rows,
        "by_model": {
            m: {
                "n": len(v["idiom_delta"]),
                "idiom_mean_delta": mean(v["idiom_delta"]) if v["idiom_delta"] else None,
                "idiom_median_delta": median(v["idiom_delta"]) if v["idiom_delta"] else None,
                "comment_mean_delta": mean(v["comment_delta"]) if v["comment_delta"] else None,
                "comment_median_delta": median(v["comment_delta"]) if v["comment_delta"] else None,
                "max_abs_delta": max(
                    [abs(x) for x in v["idiom_delta"] + v["comment_delta"]] or [0]
                ),
            } for m, v in phase_c_by_model.items()
        },
        "pooled_mean_idiom_delta": mean([r["idiom_delta"] for r in phase_c_rows]) if phase_c_rows else None,
        "pooled_mean_comment_delta": mean([r["comment_delta"] for r in phase_c_rows]) if phase_c_rows else None,
    }
    # Trigger: |pooled mean delta| > 0.5 on either idiom or comment
    triggers: list[str] = []
    if phase_c_summary["pooled_mean_idiom_delta"] is not None and abs(phase_c_summary["pooled_mean_idiom_delta"]) > 0.5:
        triggers.append("idiom")
    if phase_c_summary["pooled_mean_comment_delta"] is not None and abs(phase_c_summary["pooled_mean_comment_delta"]) > 0.5:
        triggers.append("comment")
    phase_c_summary["trigger_anchored"] = triggers
    phase_c_summary["decision"] = "switch_to_anchored" if triggers else "keep_unanchored"

    # Phase D2: per-dimension prevalence
    per_dim_scores: dict[str, list[float]] = defaultdict(list)
    per_dim_na: dict[str, int] = defaultdict(int)
    n_scored = 0
    for gid, gen in enumerate(generations):
        if not gen["extraction_ok"]:
            continue
        b = by_gen.get(gid, {})
        d2 = (b.get("d2_rubric", {}) or {}).get("parsed")
        if not d2:
            continue
        n_scored += 1
        for k in NEW_ITEM_IDS:
            item = d2.get(k)
            if isinstance(item, dict):
                sev_raw = item.get("severity")
            else:
                sev_raw = item
            # explicit nulls allowed for conditional dims
            if sev_raw is None:
                per_dim_na[k] += 1
                continue
            sev = _clamp(sev_raw, 0.0, 5.0)
            if sev is None:
                continue
            per_dim_scores[k].append(sev)

    prevalence_rows = []
    for k, _, kind in NEW_RUBRIC:
        scores = per_dim_scores[k]
        na_count = per_dim_na[k]
        n_active = sum(1 for s in scores if s >= 1.0)
        n_total = len(scores)
        rate_nonzero = (n_active / n_total) if n_total else 0.0
        prevalence_rows.append({
            "dim": k, "kind": kind,
            "n_scored": n_total, "n_na": na_count, "n_nonzero": n_active,
            "rate_nonzero": rate_nonzero,
            "mean_sev": mean(scores) if scores else None,
            "median_sev": median(scores) if scores else None,
        })

    always_on_active = [
        r for r in prevalence_rows
        if r["kind"] == "always" and r["rate_nonzero"] >= 0.10
    ]
    phase_d2_summary = {
        "n_samples_scored": n_scored,
        "per_dim": prevalence_rows,
        "always_on_at_10pct": len(always_on_active),
        "always_on_total": len(ALWAYS_ON_IDS),
        "decision": "pass" if len(always_on_active) >= 3 else "fail_escalate",
    }

    return {"phase_c": phase_c_summary, "phase_d2": phase_d2_summary}


def write_report(generations: list[dict], analysis: dict) -> None:
    c = analysis["phase_c"]
    d = analysis["phase_d2"]
    n_gen = len(generations)
    n_ok = sum(1 for g in generations if g["extraction_ok"])
    total_cost = sum((g.get("cost") or 0.0) for g in generations)

    def _fmt(x: float | None, spec: str = "+.3f") -> str:
        return "(no data)" if x is None else format(x, spec)

    lines = [
        "# Re-probe report: Phase C + Phase D2",
        "",
        f"**Generations:** {n_ok}/{n_gen} extracted; total cost ${total_cost:.4f}",
        "",
        "## Phase C — anchored vs unanchored judge prompts (reasoning models)",
        "",
        f"- Pooled mean Δidiom (anch − unanch): {_fmt(c['pooled_mean_idiom_delta'])}",
        f"- Pooled mean Δcomment (anch − unanch): {_fmt(c['pooled_mean_comment_delta'])}",
        f"- Trigger dims (|Δ| > 0.5): {c['trigger_anchored']}",
        f"- **Decision: {c['decision']}**",
        "",
        "### Per-model deltas",
        "",
        "| Model | n | mean Δidiom | mean Δcomment | max |Δ| |",
        "|-------|---|-------------|----------------|---------|",
    ]
    for m, v in c["by_model"].items():
        di = "—" if v["idiom_mean_delta"] is None else f"{v['idiom_mean_delta']:+.3f}"
        dc = "—" if v["comment_mean_delta"] is None else f"{v['comment_mean_delta']:+.3f}"
        mx = f"{v['max_abs_delta']:.3f}"
        lines.append(f"| `{m}` | {v['n']} | {di} | {dc} | {mx} |")

    lines += [
        "",
        "## Phase D2 — prevalence audit of redesigned 11-dim rubric",
        "",
        f"- Samples scored: {d['n_samples_scored']}",
        f"- Always-on dims with non-zero rate ≥ 10%: "
        f"**{d['always_on_at_10pct']}/{d['always_on_total']}**",
        f"- Gate (≥3 of 9 always-on at ≥10%): **{d['decision']}**",
        "",
        "### Per-dimension prevalence",
        "",
        "| Dimension | kind | n | n_NA | n≥1 | rate≥1 | mean sev | median |",
        "|-----------|------|---|------|-----|--------|----------|--------|",
    ]
    for r in d["per_dim"]:
        ms = "—" if r["mean_sev"] is None else f"{r['mean_sev']:.2f}"
        md = "—" if r["median_sev"] is None else f"{r['median_sev']:.2f}"
        mark = "✓" if (r["kind"] == "always" and r["rate_nonzero"] >= 0.10) else " "
        lines.append(
            f"| {mark} `{r['dim']}` | {r['kind']} | {r['n_scored']} | {r['n_na']} | "
            f"{r['n_nonzero']} | {r['rate_nonzero']*100:.1f}% | {ms} | {md} |"
        )

    (OUTDIR / "REPORT.md").write_text("\n".join(lines))


# ----- main -----
async def main() -> int:
    print("=== Combined re-probe: Phase C (anchored vs unanchored) + Phase D2 (prevalence) ===")
    print(f"  models: {REASONING_MODELS}")
    print(f"  tasks: {[t['id'] for t in TASKS]}")
    print(f"  preambles: {list(PREAMBLES.keys())}  | reps: {REPLICATIONS}")

    if "OPENROUTER_API_KEY" not in os.environ:
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2

    # Build generation jobs
    gen_jobs = []
    for model in REASONING_MODELS:
        for preamble_id in PREAMBLES:
            for task in TASKS:
                for rep in range(REPLICATIONS):
                    gen_jobs.append((task, preamble_id, model, rep))
    print(f"  total generations: {len(gen_jobs)}")

    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as client:
        # Generate
        print(f"\n[1/2] generating {len(gen_jobs)} samples...")
        generations = await asyncio.gather(*[
            generate(client, sem, task=t, preamble_id=p, model=m, rep=r)
            for (t, p, m, r) in gen_jobs
        ])
        n_ok = sum(1 for g in generations if g["extraction_ok"])
        print(f"  extracted ok: {n_ok}/{len(generations)}")

        # Judge — 3 calls per OK generation (c_unanchored, c_anchored, d2_rubric)
        judge_jobs = []
        for idx, g in enumerate(generations):
            if not g["extraction_ok"]:
                continue
            judge_jobs.append((idx, "c_unanchored", g["code"], PHASE_C_UNANCHORED))
            judge_jobs.append((idx, "c_anchored",   g["code"], PHASE_C_ANCHORED))
            judge_jobs.append((idx, "d2_rubric",    g["code"], PHASE_D2_RUBRIC_JUDGE))
        print(f"\n[2/2] judging {len(judge_jobs)} (gen, prompt) pairs by {JUDGE_MODEL}...")

        async def _do_judge(idx, kind, code, prompt):
            j = await judge(client, sem, code=code, system_prompt=prompt, kind=kind)
            j["gen_idx"] = idx
            return j

        judgments = await asyncio.gather(*[
            _do_judge(idx, kind, code, prompt) for (idx, kind, code, prompt) in judge_jobs
        ])
        n_judge_ok = sum(1 for j in judgments if j.get("parsed"))
        print(f"  judge parses ok: {n_judge_ok}/{len(judgments)}")

    # Persist
    (OUTDIR / "generations.json").write_text(json.dumps(generations, indent=2, default=str))
    (OUTDIR / "judgments.json").write_text(json.dumps(judgments, indent=2, default=str))

    # Analyze + report
    analysis = analyze(generations, judgments)
    (OUTDIR / "analysis.json").write_text(json.dumps(analysis, indent=2, default=str))
    write_report(generations, analysis)

    c = analysis["phase_c"]
    d = analysis["phase_d2"]
    total_cost = sum((g.get("cost") or 0.0) for g in generations)
    print("\n=== summary ===")
    print(f"  total estimated cost from generations: ${total_cost:.4f}")
    print(f"  Phase C decision: {c['decision']}  triggers={c['trigger_anchored']}")
    print(f"    pooled Δidiom={c['pooled_mean_idiom_delta']}, "
          f"Δcomment={c['pooled_mean_comment_delta']}")
    print(f"  Phase D2 decision: {d['decision']}  "
          f"({d['always_on_at_10pct']}/{d['always_on_total']} always-on dims ≥ 10% non-zero)")
    print(f"  artifacts: {OUTDIR}/REPORT.md, generations.json, judgments.json, analysis.json")
    return 0 if (d["decision"] == "pass") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
