# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai",
#   "matplotlib",
#   "numpy",
#   "scipy",
# ]
# ///
"""
Preamble Quality v2 — Minimal Proof-of-Concept.

End-to-end validation of the v2 design pinned in SPEC_V2.md:
  - The new 9th condition `python_coder_agent` (loads the real agent system prompt)
  - 0-5 severity rubric (replaces v1's binary rubric)
  - CQS-craft primary metric (LLM-judge-only, 10% rubric-hygiene cap)
  - Creation-vs-refactor task category labeling
  - Cross-judge panel with self-judge exclusion

DELIBERATELY OMITTED (PoC scope; full design in SPEC_V2.md):
  - All 7 subject models (PoC uses 1: gpt-4o-mini)
  - All 9 conditions (PoC uses 3: none, real_agent, python_coder_agent)
  - All 8 tasks (PoC uses 2: lru_ttl_cache [creation], modeflag_sort [refactor/trap])
  - n>=100/arm replication (PoC runs 1 per cell)
  - Multi-file task and the 3 multi-file-only rubric dimensions
  - Static-analysis diagnostic panel (radon/pylint/PEP8) — reported separately in full run
  - Bootstrap CIs and mixed-effects model (not informative at PoC scale)
  - F3 self-preference stratification (not informative at PoC scale)

Run with: uv run preamble_quality_v2_poc.py
Reads OPENROUTER_API_KEY from environment.
Outputs a single number per condition (CQS-craft) + one PNG.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
from pathlib import Path

import numpy as np
from openai import AsyncOpenAI

# ============================================================
# Paths and configuration
# ============================================================

POC_DIR = Path(__file__).parent
RESULTS_DIR = POC_DIR / "poc_results"
RESULTS_DIR.mkdir(exist_ok=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONCURRENCY = 12
GEN_TIMEOUT = 120
JUDGE_TIMEOUT = 60

# Subject pool (PoC subset). Full design uses 7 models.
SUBJECT_MODEL = "openai/gpt-4o-mini"

# Judge panel (PoC subset). Full design uses 7-judge cross-matrix.
JUDGE_PANEL = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-v3.2",
    "mistralai/mistral-small-2603",
]

# Path to the chris-code python-coder agent system prompt — source of truth
# for the new 9th condition. Loaded at runtime; if unavailable, the condition
# falls back to a documented stub so the PoC still exercises the pipeline.
PYTHON_CODER_AGENT_PATH = Path(
    "/Users/chrissantiago/Dropbox/claude-config/plugins/chris-code/agents/python-coder.md"
)

# CQS-craft pre-registered weights (locked by SPEC_V2.md §6.5)
W_IDIOM = 0.45
W_COMMENT = 0.45
W_HYGIENE = 0.10


# ============================================================
# Preamble conditions (PoC subset of the 9 in SPEC_V2.md §6.1)
# ============================================================

def _load_python_coder_preamble() -> str:
    """Load the chris-code python-coder agent's system prompt verbatim.

    Strips only the YAML frontmatter; preserves all operating principles,
    S3+ checklist, Pythonic design standards, refactoring heuristics, and
    workflow/boundaries sections. The agent's tool-mention lines (Read/Edit
    /Write/Bash) are left in place — they're harmless in a single-turn
    generation context.
    """
    if not PYTHON_CODER_AGENT_PATH.exists():
        return (
            "[python_coder_agent preamble unavailable at runtime — PoC fallback. "
            "Full design requires the actual agent system prompt from "
            f"{PYTHON_CODER_AGENT_PATH}.]"
        )
    raw = PYTHON_CODER_AGENT_PATH.read_text()
    # Strip YAML frontmatter between leading ---/--- delimiters
    parts = raw.split("---\n", 2)
    body = parts[2] if len(parts) >= 3 and raw.startswith("---") else raw
    return body.strip()


PREAMBLES: dict[str, str | None] = {
    "none": None,
    "real_agent": (
        "You are an expert software engineer. Write production-quality Python "
        "code. Use idiomatic patterns, type hints, defensive error handling, "
        "clear naming, and comments that explain why not what. Prefer "
        "dataclasses over dicts for structured data, explicit exceptions over "
        "sentinel returns, and small focused functions over large multipurpose "
        "ones."
    ),
    "python_coder_agent": _load_python_coder_preamble(),
}


# ============================================================
# Tasks (PoC subset: one creation + one trap-based refactor)
# ============================================================

# task_modeflag_sort is the v2 trap-based probe (SPEC_V2.md §6.2). The
# spec hands the model a sort signature that contains a boolean mode-flag
# parameter — a python-coder S3+ #1 violation. A well-primed model should
# resist or redesign; a weakly-primed model implements as-asked.

TASKS = [
    {
        "id": "task_lru_ttl_cache",
        "category": "creation",
        "prompt": (
            "Write a Python class implementing a thread-safe LRU cache with "
            "per-entry TTL expiry. Requirements:\n"
            "- O(1) get and put operations\n"
            "- Per-entry TTL: entries expire independently after TTL elapses\n"
            "- LRU eviction when over capacity (skip expired during selection)\n"
            "- Thread-safe for concurrent use\n"
            "- get(key) returns the value if present and unexpired, else None\n"
            "- put(key, value, ttl_seconds) stores the entry\n"
            "- size() returns the count of non-expired entries\n"
            "Include type hints and a brief usage example.\n"
            "Do not use functools.lru_cache or any third-party caching library."
        ),
    },
    {
        "id": "task_modeflag_sort",
        "category": "refactor",  # trap-based; spec-handed signature is the smell
        "prompt": (
            "Implement a sort function for arbitrary sequences with this exact "
            "signature:\n\n"
            "    def sort(items, key=None, reverse=False, stable=True): ...\n\n"
            "Requirements:\n"
            "- items: a sequence of comparable elements\n"
            "- key: optional callable to extract a comparison key (Python convention)\n"
            "- reverse: if True, sort in descending order\n"
            "- stable: if True, preserve the order of equal elements\n"
            "- Return: a new sorted list (do not mutate the input)\n"
            "- Include type hints and 2-3 usage examples.\n"
        ),
    },
]


# ============================================================
# 0-5 severity rubric (PoC: single-file dimensions only)
# ============================================================

RUBRIC = [
    ("mode_flag_params",
     "Boolean/mode-flag parameters on a non-underscore-prefixed function "
     "(e.g. def foo(x, *, verbose=False, dry_run=False)). Higher severity if "
     "multiple flags compound."),
    ("dict_domain_data",
     "Dict-shaped domain data crossing a function boundary where a dataclass, "
     "TypedDict, or NamedTuple would clarify the structure."),
    ("hidden_side_effects",
     "Side effects inside a function that looks pure from its signature: "
     "env-var reads, filesystem access, embedded logging in pure-looking "
     "helpers, mutating module-global state."),
    ("swallowed_excepts",
     "Except clauses that swallow without re-raise or typed handling "
     "(`except ...: pass`, or silent sentinel returns)."),
    ("broad_except",
     "Broad `except Exception` or bare `except:` at a function/library "
     "boundary without specific re-raise or narrowly typed handling."),
    ("dead_code",
     "Unused imports, dead code branches, or unused sentinel return values."),
    ("orchestration_mixed_with_impl",
     "A single function that both coordinates workflow AND performs low-level "
     "transforms or I/O inline."),
    ("overgrown_class",
     "Classes with many methods, weak invariants, or vague catch-all names "
     "(Manager/Handler/Helper/Processor)."),
    ("return_shape_consistency",
     "Sibling functions returning inconsistent shapes for similar operations "
     "(score 0 if there is only one function and N/A doesn't apply)."),
    ("type_hint_coverage",
     "Public functions lacking type hints. Score inversely: 0 = full coverage "
     "on public funcs, 5 = essentially none."),
    ("exception_drift",
     "Similar failures raising different exception types within the same "
     "module."),
]
ITEM_IDS = [k for k, _ in RUBRIC]

GENERATION_TEMPERATURE = 0.3
JUDGE_TEMPERATURE = 0.1
GEN_MAX_TOKENS = 3000
JUDGE_MAX_TOKENS = 900

JUDGE_SYSTEM_PROMPT = (
    "You are a senior Python code reviewer evaluating code quality. For each "
    "item below, assign a severity score on a 0-5 scale:\n"
    "  0 = absent / fully clean\n"
    "  1 = minor occurrence (1 instance, low impact)\n"
    "  2 = present (a few instances, noticeable)\n"
    "  3 = clearly violates (several instances or one severe instance)\n"
    "  4 = pervasive\n"
    "  5 = dominant problem of the file\n\n"
    "You will ALSO score idiomaticity and comment quality on a 1-10 scale.\n\n"
    "Rubric items:\n"
    + "\n".join(f"  - {k}: {desc}" for k, desc in RUBRIC)
    + "\n\n"
    "Respond with ONLY a single JSON object, no markdown fences, no prose:\n"
    "{\n"
    '  "idiomaticity": <1-10>,\n'
    '  "comment_quality": <1-10>,\n'
    "  "
    + ",\n  ".join(f'"{k}": {{"severity": 0, "rationale": "<one short sentence>"}}'
                   for k in ITEM_IDS)
    + "\n}\n"
)


# ============================================================
# Async dispatcher
# ============================================================

def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# Module-level structured counter for any out-of-range judge emissions (D13).
# Surfaces sentinel-style outputs (e.g. deepseek's -1) that would otherwise
# silently bias the cross-judge mean. Per-call entries persisted to disk.
OOR_LOG: list[dict] = []


def _clamp_judge_score(value, lo: float, hi: float, *, context: str) -> float | None:
    """Coerce to float, clamp to [lo, hi]. Out-of-range → None + structured log.

    F1 fix (D1): out-of-range values are treated as MISSING, not clipped — clipping
    would still inject artifactual bounds-valued scores. None is consistent with
    how parse failures are handled and naturally excludes from the cross-judge
    mean.
    """
    f = _to_float(value)
    if f is None:
        return None
    if f < lo or f > hi:
        OOR_LOG.append({"raw_value": f, "lo": lo, "hi": hi, "context": context})
        return None
    return f


async def _call_one(client: AsyncOpenAI, sem: asyncio.Semaphore,
                     model: str, system: str | None, user: str,
                     temperature: float, max_tokens: int, timeout: int,
                     label: str) -> tuple[str, str | None]:
    """One bounded async chat completion. Returns (text, error)."""
    messages = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    async with sem:
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - log & return, don't crash batch
            return "", f"{type(exc).__name__}: {exc}"
    choice = resp.choices[0]
    text = (choice.message.content or "").strip()
    return text, None


def extract_python_code(text: str) -> tuple[str, str]:
    """Best-effort fenced-code-block extraction."""
    if not text:
        return "", "extraction_failed"
    fenced = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip(), "fenced"
    # fallback: if the text looks like raw code (starts with def/class/import)
    first = text.lstrip().split("\n", 1)[0]
    if re.match(r"^(import |from |def |class |async def )", first):
        return text.strip(), "raw"
    return "", "extraction_failed"


def _extract_json_safe(text: str) -> dict | None:
    """Strip optional fences and parse the first JSON object."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ============================================================
# Generation + judging
# ============================================================

async def generate_code(client, sem, task: dict, condition: str) -> dict:
    preamble = PREAMBLES[condition]
    text, err = await _call_one(
        client, sem, SUBJECT_MODEL, preamble, task["prompt"],
        temperature=GENERATION_TEMPERATURE, max_tokens=GEN_MAX_TOKENS,
        timeout=GEN_TIMEOUT,
        label=f"gen|{task['id']}|{condition}",
    )
    code, method = extract_python_code(text)
    return {
        "task_id": task["id"], "category": task["category"],
        "preamble": condition, "model": SUBJECT_MODEL,
        "code": code, "raw_response": text,
        "extraction_method": method, "error": err,
    }


async def judge_one_sample(client, sem, sample: dict, judge_model: str) -> dict:
    user_msg = f"Code under review:\n\n```python\n{sample['code']}\n```"
    text, err = await _call_one(
        client, sem, judge_model, JUDGE_SYSTEM_PROMPT, user_msg,
        temperature=JUDGE_TEMPERATURE, max_tokens=JUDGE_MAX_TOKENS,
        timeout=JUDGE_TIMEOUT,
        label=f"judge|{sample['task_id']}|{sample['preamble']}|{judge_model}",
    )
    base = {
        "task_id": sample["task_id"], "preamble": sample["preamble"],
        "subject_model": sample["model"], "judge_model": judge_model,
    }
    if err:
        return {**base, "judge_error": err, "idiomaticity": None,
                "comment_quality": None,
                **{k: None for k in ITEM_IDS}}
    parsed = _extract_json_safe(text)
    if parsed is None:
        return {**base, "judge_error": f"parse_fail: {text[:80]}",
                "idiomaticity": None, "comment_quality": None,
                **{k: None for k in ITEM_IDS}}
    ctx = f"{sample['task_id']}|{sample['preamble']}|{sample['model']}|judge={judge_model}"
    out = {
        **base, "judge_error": None,
        # F1 fix: clamp to [1,10]; out-of-range → None (dropped, not clipped).
        "idiomaticity": _clamp_judge_score(parsed.get("idiomaticity"), 1.0, 10.0, context=ctx),
        "comment_quality": _clamp_judge_score(parsed.get("comment_quality"), 1.0, 10.0, context=ctx),
    }
    for k in ITEM_IDS:
        item = parsed.get(k, {})
        sev = item.get("severity") if isinstance(item, dict) else item
        sv = _to_float(sev)
        # Clamp to [0, 5]; None if unparseable
        out[k] = max(0.0, min(5.0, sv)) if sv is not None else None
    return out


# ============================================================
# CQS-craft computation (pre-registered formula)
# ============================================================

def compute_cqs_craft_for_sample(judge_records: list[dict]) -> dict:
    """Aggregate cross-judge scores for one (task, preamble, model) sample."""
    if not judge_records:
        return {"cqs_craft": None, "idiom": None, "comment": None,
                "rubric_severity_mean": None, "n_judges": 0}

    idiom = [r["idiomaticity"] for r in judge_records if r.get("idiomaticity") is not None]
    comment = [r["comment_quality"] for r in judge_records if r.get("comment_quality") is not None]
    if not idiom or not comment:
        return {"cqs_craft": None, "idiom": None, "comment": None,
                "rubric_severity_mean": None, "n_judges": len(judge_records)}

    # Mean rubric severity per sample = mean over (judge × item)
    sev_vals = []
    for r in judge_records:
        for k in ITEM_IDS:
            v = r.get(k)
            if v is not None:
                sev_vals.append(v)
    sev_mean = float(np.mean(sev_vals)) if sev_vals else 0.0  # 0 if no judges scored items

    idiom_unit = float(np.mean(idiom)) / 10.0
    comment_unit = float(np.mean(comment)) / 10.0
    hygiene_unit = 1.0 - sev_mean / 5.0  # 0 severity -> 1.0 hygiene

    cqs = W_IDIOM * idiom_unit + W_COMMENT * comment_unit + W_HYGIENE * hygiene_unit
    return {
        "cqs_craft": round(cqs, 4),
        "idiom": round(idiom_unit, 4),
        "comment": round(comment_unit, 4),
        "rubric_severity_mean": round(sev_mean, 4),
        "n_judges": len(judge_records),
    }


# ============================================================
# Visualization
# ============================================================

def plot_cqs_craft_by_condition(per_condition: dict[str, dict], out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    conds = list(PREAMBLES.keys())
    cqs = [per_condition[c]["cqs_craft"] if per_condition[c]["cqs_craft"] else 0.0
           for c in conds]
    idiom = [per_condition[c]["idiom"] if per_condition[c]["idiom"] else 0.0
             for c in conds]
    comment = [per_condition[c]["comment"] if per_condition[c]["comment"] else 0.0
               for c in conds]

    x = np.arange(len(conds))
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.25
    ax.bar(x - width, idiom, width, label="idiom (45%)", color="#1f77b4")
    ax.bar(x, comment, width, label="comment (45%)", color="#ff7f0e")
    ax.bar(x + width, cqs, width, label="CQS-craft (overall)", color="#2ca02c")
    ax.set_xticks(x)
    ax.set_xticklabels(conds, fontsize=9)
    ax.set_ylabel("score (0-1)")
    ax.set_title("PoC: CQS-craft by preamble condition (1 model × 2 tasks)")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


# ============================================================
# Main
# ============================================================

async def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment")
    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    sem = asyncio.Semaphore(CONCURRENCY)

    print("=" * 60)
    print(f"PoC: 1 model × {len(PREAMBLES)} conditions × {len(TASKS)} tasks")
    print(f"     {sum(1 for c in PREAMBLES.values() if c is not None)} preamble texts loaded; "
          f"python_coder_agent preamble = "
          f"{len(PREAMBLES['python_coder_agent']) if PREAMBLES['python_coder_agent'] else 0} chars")
    print("=" * 60)

    # ---- 1. Generate code (1 sample per cell) ----
    gen_jobs = [(t, c) for t in TASKS for c in PREAMBLES]
    print(f"\n[1/3] Generating {len(gen_jobs)} samples...")
    samples = await asyncio.gather(
        *[generate_code(client, sem, t, c) for t, c in gen_jobs]
    )
    for s in samples:
        code_ok = bool(s["code"]) and not s["error"]
        print(f"  [{s['task_id']:<22} | {s['preamble']:<20}] "
              f"{'ok' if code_ok else 'FAIL'}  ({len(s['code'])} chars)")
    with open(RESULTS_DIR / "poc_generation_results.jsonl", "w") as fh:
        for s in samples:
            fh.write(json.dumps(s) + "\n")

    valid_samples = [s for s in samples if s["code"] and not s["error"]
                     and s["extraction_method"] != "extraction_failed"]
    print(f"  {len(valid_samples)}/{len(samples)} samples have valid extracted code.")

    # ---- 2. Judge with cross-panel (self-judge filter applied at aggregation) ----
    judge_jobs = [(s, j) for s in valid_samples for j in JUDGE_PANEL]
    print(f"\n[2/3] Judging: {len(judge_jobs)} judge calls "
          f"({len(valid_samples)} samples × {len(JUDGE_PANEL)} judges)...")
    judge_records = await asyncio.gather(
        *[judge_one_sample(client, sem, s, j) for s, j in judge_jobs]
    )
    ok = sum(1 for r in judge_records if r.get("judge_error") is None)
    print(f"  {ok}/{len(judge_records)} judge calls successful.")
    with open(RESULTS_DIR / "poc_judge_records.jsonl", "w") as fh:
        for r in judge_records:
            fh.write(json.dumps(r) + "\n")

    # ---- 3. Compute CQS-craft per (task, condition) and per condition ----
    print(f"\n[3/3] CQS-craft (pre-registered weights: {W_IDIOM}/{W_COMMENT}/{W_HYGIENE})")
    # Index judge records by (task, preamble, subject_model)
    by_sample_key: dict[tuple, list[dict]] = {}
    for jr in judge_records:
        if jr["judge_model"] == jr["subject_model"]:
            continue  # self-judge exclusion (F3 hygiene)
        if jr.get("judge_error") is not None:
            continue
        key = (jr["task_id"], jr["preamble"], jr["subject_model"])
        by_sample_key.setdefault(key, []).append(jr)

    per_sample_results = []
    for s in valid_samples:
        key = (s["task_id"], s["preamble"], s["model"])
        agg = compute_cqs_craft_for_sample(by_sample_key.get(key, []))
        per_sample_results.append({
            "task_id": s["task_id"], "category": s["category"],
            "preamble": s["preamble"], "model": s["model"], **agg,
        })

    # Per-condition mean (across tasks) on the valid samples
    per_condition: dict[str, dict] = {c: {"cqs_craft": None, "idiom": None,
                                          "comment": None, "rubric_severity_mean": None,
                                          "n_samples": 0}
                                      for c in PREAMBLES}
    for c in PREAMBLES:
        vals_cqs = [r["cqs_craft"] for r in per_sample_results
                    if r["preamble"] == c and r["cqs_craft"] is not None]
        vals_idiom = [r["idiom"] for r in per_sample_results
                      if r["preamble"] == c and r["idiom"] is not None]
        vals_comment = [r["comment"] for r in per_sample_results
                        if r["preamble"] == c and r["comment"] is not None]
        vals_sev = [r["rubric_severity_mean"] for r in per_sample_results
                    if r["preamble"] == c and r["rubric_severity_mean"] is not None]
        per_condition[c] = {
            "cqs_craft": float(np.mean(vals_cqs)) if vals_cqs else None,
            "idiom": float(np.mean(vals_idiom)) if vals_idiom else None,
            "comment": float(np.mean(vals_comment)) if vals_comment else None,
            "rubric_severity_mean": float(np.mean(vals_sev)) if vals_sev else None,
            "n_samples": len(vals_cqs),
        }

    # Print summary
    print(f"\n  {'condition':<22} {'n':<4} {'CQS-craft':<12} {'idiom':<10} "
          f"{'comment':<10} {'rubric_sev':<12}")
    print("  " + "-" * 70)
    for c in PREAMBLES:
        pc = per_condition[c]
        cqs = f"{pc['cqs_craft']:.4f}" if pc['cqs_craft'] is not None else "n/a"
        idiom = f"{pc['idiom']:.4f}" if pc['idiom'] is not None else "n/a"
        comment = f"{pc['comment']:.4f}" if pc['comment'] is not None else "n/a"
        sev = f"{pc['rubric_severity_mean']:.4f}" if pc['rubric_severity_mean'] is not None else "n/a"
        print(f"  {c:<22} {pc['n_samples']:<4} {cqs:<12} {idiom:<10} {comment:<10} {sev:<12}")

    # Save per-sample + summary
    with open(RESULTS_DIR / "poc_per_sample_results.jsonl", "w") as fh:
        for r in per_sample_results:
            fh.write(json.dumps(r) + "\n")
    with open(RESULTS_DIR / "poc_summary.json", "w") as fh:
        json.dump({
            "weights": {"idiom": W_IDIOM, "comment": W_COMMENT, "hygiene": W_HYGIENE},
            "subject_model": SUBJECT_MODEL,
            "judge_panel": JUDGE_PANEL,
            "conditions": list(PREAMBLES.keys()),
            "tasks": [{"id": t["id"], "category": t["category"]} for t in TASKS],
            "per_condition": per_condition,
            "per_sample_results": per_sample_results,
        }, fh, indent=2)

    plot_cqs_craft_by_condition(per_condition, RESULTS_DIR / "poc_cqs_craft.png")

    # F1/D13: persist any out-of-range judge emissions for the run report.
    oor_path = RESULTS_DIR / "poc_oor_judge_emissions.jsonl"
    with open(oor_path, "w") as fh:
        for rec in OOR_LOG:
            fh.write(json.dumps(rec) + "\n")
    print(f"\n[F1/D13] Out-of-range judge emissions: {len(OOR_LOG)} → {oor_path.name}")
    if OOR_LOG:
        from collections import Counter
        by_ctx = Counter(rec["context"].split("|")[-1] for rec in OOR_LOG)
        print(f"         by judge: {dict(by_ctx)}")

    print(f"\nSaved to {RESULTS_DIR.name}/: poc_summary.json, "
          f"poc_per_sample_results.jsonl, poc_cqs_craft.png, plus raw gen/judge JSONLs.")


if __name__ == "__main__":
    asyncio.run(main())
