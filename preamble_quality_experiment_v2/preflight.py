# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai",
#   "numpy",
# ]
# ///
"""
Pre-flight phases B, C, D — combined runner.

Run with: uv run preflight.py

Phase B (F2 gate pilot): score rewritten task_modeflag_sort under no-preamble
and python_coder_agent. Gate criterion: ≥40% no-preamble mode_flag_params
severity ≥3 → discriminative space open → main run includes the task.

Phase C (F4 style-directive probe): 3 tasks × 7 models × 2 preambles
(python_coder_agent, real_agent). Score each output twice — once with the
unanchored judge prompt (current) and once with a complexity-anchored
variant. Trigger: |Δ| > 0.5 comment_quality mean → amend judge prompt for
main run, log as pre-reg drift per SPEC §7.

Phase D (F5 prevalence audit): 30 no-preamble generations distributed across
9 tasks × ~4 models. Score with 11-dim rubric. Report per-dim non-zero
prevalence. Threshold: >10% to count as "active". Pass: ≥4 active dims.

All three phases share the same subject and judge call infrastructure; runs
in parallel under one semaphore to maximize throughput.

OUTPUT: preflight_results.json (single artifact summarizing all three phase
verdicts + raw data references).
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
# Configuration (locked from SPEC_V2.md / Gate 1 captured decisions)
# ============================================================

V2_DIR = Path(__file__).parent
RESULTS_DIR = V2_DIR / "preflight_results"
RESULTS_DIR.mkdir(exist_ok=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONCURRENCY = 50          # known-safe (v1 rubric run)
GEN_TIMEOUT = 120
JUDGE_TIMEOUT = 60
GEN_MAX_TOKENS = 3000
JUDGE_MAX_TOKENS = 900
GEN_TEMPERATURE = 0.3
JUDGE_TEMPERATURE = 0.1

# 7-model pool (grok-4.1-fast removed; SPEC_V2.md §6.3)
ALL_MODELS = [
    "deepseek/deepseek-v3.2",
    "google/gemma-4-31b-it",
    "minimax/minimax-m2.5",
    "mistralai/mistral-small-2603",
    "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-4o-mini",
    "qwen/qwen3.5-35b-a3b",
]
JUDGE_PANEL = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-v3.2",
    "mistralai/mistral-small-2603",
]

# Preambles needed in pre-flight
PYTHON_CODER_AGENT_PATH = Path(
    "/Users/chrissantiago/Dropbox/claude-config/plugins/chris-code/agents/python-coder.md"
)


def _load_python_coder_preamble() -> str:
    raw = PYTHON_CODER_AGENT_PATH.read_text()
    parts = raw.split("---\n", 2)
    return (parts[2] if len(parts) >= 3 and raw.startswith("---") else raw).strip()


REAL_AGENT_PREAMBLE = (
    "You are an expert software engineer. Write production-quality Python code. "
    "Use idiomatic patterns, type hints, defensive error handling, clear naming, "
    "and comments that explain why not what. Prefer dataclasses over dicts for "
    "structured data, explicit exceptions over sentinel returns, and small focused "
    "functions over large multipurpose ones."
)
PYTHON_CODER_AGENT_PREAMBLE = _load_python_coder_preamble()

# Phase B: rewritten task_modeflag_sort prompt (D2 captured choice, my proposed text)
TASK_MODEFLAG_SORT_REWRITE = (
    "Implement a function in Python that sorts an arbitrary sequence of comparable "
    "elements. Requirements:\n"
    "- Returns a new sorted list (does not mutate the input).\n"
    "- By default, preserves the relative order of equal elements.\n"
    "- Supports sorting in descending order on request.\n"
    "- Supports an optional callable to extract a comparison key.\n"
    "- Include type hints and 2-3 usage examples.\n"
    "\n"
    "(Choose any reasonable Python API. Document it.)"
)

# Phase C: 3 tasks used for the style-directive probe (existing v1 tasks)
# Use prompts already validated to generate parseable Python from gpt-4o-mini etc.
PHASE_C_TASKS = [
    {
        "id": "task_lru_ttl_cache",
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
        "id": "task_exception_pyramid",
        "prompt": (
            "Refactor the following Python code. It uses deeply nested try/except "
            "blocks with broad catches that silently swallow most errors. Requirements: "
            "max 1 level of nesting; no bare 'except Exception: pass'; every exception "
            "either re-raised, logged with full context, or converted to a specific typed "
            "exception. Preserve signature: load_and_merge_configs(primary_path, override_path=None). "
            "Return merged dict (or {} if primary missing). Callers must distinguish "
            "'primary missing' vs 'primary malformed' vs 'override malformed'. Type hints.\n\n"
            "```python\n"
            "def load_and_merge_configs(primary_path, override_path=None):\n"
            "    try:\n"
            "        try:\n"
            "            with open(primary_path) as f:\n"
            "                try:\n"
            "                    primary = json.load(f)\n"
            "                except:\n"
            "                    primary = {}\n"
            "        except:\n"
            "            primary = {}\n"
            "        if override_path:\n"
            "            try:\n"
            "                with open(override_path) as f:\n"
            "                    try:\n"
            "                        override = json.load(f)\n"
            "                    except:\n"
            "                        override = {}\n"
            "                primary.update(override)\n"
            "            except Exception: pass\n"
            "        return primary\n"
            "    except: return {}\n"
            "```\n\n"
            "Return the refactored code in a single ```python ... ``` block."
        ),
    },
]

# Phase D: 9 tasks for prevalence audit (8 SPEC tasks + 1 multi-file).
# Use a compact form here; main run will use full SPEC versions.
PHASE_D_TASKS = [
    {"id": "task_lru_ttl_cache",      "prompt": PHASE_C_TASKS[0]["prompt"]},
    {"id": "task_expr_parser",        "prompt": PHASE_C_TASKS[1]["prompt"]},
    {"id": "task_async_conn_pool",
     "prompt": "Write a Python async connection pool using asyncio. Max pool size configurable; pool blocks when exhausted; acquire() waits with exponential backoff + full jitter (not fixed sleep) up to a timeout; release(conn); health check on acquire (discard + recreate if unhealthy); async context manager support (async with pool.acquire() as conn:); user-supplied async connection factory and health checker. Use asyncio.Queue or equivalent. Type hints, brief usage example."},
    {"id": "task_modeflag_sort",      "prompt": TASK_MODEFLAG_SORT_REWRITE},
    {"id": "task_flag_class",
     "prompt": "Refactor a Python class that uses boolean mode-flags and module-global state. Eliminate boolean mode-flags (use composition/strategy/subclasses); remove module-globals (self-contained); preserve filtering/dedup/normalization/validation/caching/stats; safe for concurrent use across instances; add type hints.\n\n```python\n_cache = {}\n_stats = {'hits':0,'misses':0}\n\nclass Processor:\n    def __init__(self, dedupe=True, normalize=False, validate=True, cache=True):\n        self.dedupe=dedupe; self.normalize=normalize; self.validate=validate; self.cache=cache\n    def process(self, items):\n        if self.cache:\n            key=tuple(items)\n            if key in _cache: _stats['hits']+=1; return _cache[key]\n            _stats['misses']+=1\n        out=items\n        if self.dedupe: out=list(set(out))\n        if self.normalize: out=[s.lower() for s in out]\n        if self.validate: out=[s for s in out if s]\n        if self.cache: _cache[key]=out\n        return out\n```\n\nReturn the refactored code in a single ```python ... ``` block."},
    {"id": "task_exception_pyramid",  "prompt": PHASE_C_TASKS[2]["prompt"]},
    {"id": "task_mini_sql_engine",
     "prompt": "Implement a small in-memory SQL-like query engine in Python. A Table class holds a list of dict rows. Support: select(*columns), where(predicate), join(other_table, on=lambda l,r: bool), group_by(column), order_by(column, descending=False), limit(n). Composable fluent API. Include type hints and 2-3 usage examples."},
    {"id": "task_rate_limiter_family",
     "prompt": "Implement a family of rate limiters in Python behind a single interface: token bucket, leaky bucket, sliding-window-log, sliding-window-counter. All implement an `allow(client_id) -> bool` method. Each algorithm is its own class but they share an interface (base class or protocol). Include type hints, brief usage example showing each in use."},
    # Multi-file (D11): present as a meta-task. Even single-file extraction is OK for prevalence audit.
    {"id": "task_kv_store_package",
     "prompt": "Design and implement a small Python package for an in-memory key-value store with TTL, atomic updates, and bulk ops. Use stdlib only. Sketch the file layout (you may write each file as a separate ```python:path/file.py``` fenced block) — typical layout: a top-level package, a core module, an optional CLI module, and a tests file. Include type hints and a brief usage example."},
]

# Rubric (11 dims, 0-5 severity scale)
RUBRIC = [
    ("mode_flag_params",         "Boolean/mode-flag parameters on public (non-underscore) functions."),
    ("dict_domain_data",         "Dict-shaped domain data crossing a function boundary where dataclass/TypedDict/NamedTuple would clarify."),
    ("hidden_side_effects",      "Side effects (env reads, fs access, embedded logging, global mutation) inside functions that look pure from signature."),
    ("swallowed_excepts",        "Except clauses that swallow without re-raise or typed handling."),
    ("broad_except",             "Broad `except Exception` or bare `except:` at function/library boundary without specific re-raise or narrow typing."),
    ("dead_code",                "Unused imports, dead branches, unused sentinel returns."),
    ("orchestration_mixed_with_impl", "Single function both coordinates workflow AND does low-level transforms/I/O inline."),
    ("overgrown_class",          "Classes with many methods, weak invariants, vague catch-all names (Manager/Handler/Helper)."),
    ("return_shape_consistency", "Sibling functions return inconsistent shapes for similar operations."),
    ("type_hint_coverage",       "Public functions lacking type hints (inverse: 0 = full coverage, 5 = none)."),
    ("exception_drift",          "Similar failures raise different exception types within the same module."),
]
ITEM_IDS = [k for k, _ in RUBRIC]

UNANCHORED_JUDGE_PROMPT = (
    "You are a senior Python code reviewer evaluating code quality. For each item below, "
    "assign a severity score on a 0-5 scale (0=absent/clean, 5=dominant problem). "
    "Also score idiomaticity and comment_quality on a 1-10 scale.\n\n"
    "Items:\n"
    + "\n".join(f"  - {k}: {desc}" for k, desc in RUBRIC)
    + "\n\n"
    "Respond with ONLY a single JSON object, no markdown fences, no prose:\n{\n"
    '  "idiomaticity": <1-10>,\n  "comment_quality": <1-10>,\n  '
    + ",\n  ".join(f'"{k}": {{"severity": 0, "rationale": "<one sentence>"}}' for k in ITEM_IDS)
    + "\n}\n"
)

ANCHORED_JUDGE_PROMPT = (
    "You are a senior Python code reviewer evaluating code quality. For each item below, "
    "assign a severity score on a 0-5 scale (0=absent/clean, 5=dominant problem). "
    "Also score idiomaticity and comment_quality on a 1-10 scale.\n\n"
    "IMPORTANT for comment_quality: score relative to the INHERENT COMPLEXITY of the code, "
    "not its verbosity. A focused implementation with concise docstrings should score as "
    "well as a longer one with extensive documentation, if the documentation matches the "
    "code's needs.\n\n"
    "Items:\n"
    + "\n".join(f"  - {k}: {desc}" for k, desc in RUBRIC)
    + "\n\n"
    "Respond with ONLY a single JSON object, no markdown fences, no prose:\n{\n"
    '  "idiomaticity": <1-10>,\n  "comment_quality": <1-10>,\n  '
    + ",\n  ".join(f'"{k}": {{"severity": 0, "rationale": "<one sentence>"}}' for k in ITEM_IDS)
    + "\n}\n"
)


# ============================================================
# Helpers (kept self-contained — preflight is a one-shot)
# ============================================================

def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _clamp(value, lo, hi):
    f = _to_float(value)
    if f is None or f < lo or f > hi:
        return None
    return f


def extract_python_code(text: str) -> str:
    """Best-effort fenced extraction with progressive fallbacks.

    Order:
      1. Properly-closed ```python ... ``` fences (multi-file → concatenated).
      2. Opening fence without closing fence — salvages model truncation cases
         (e.g. minimax stopping mid-implementation without emitting the closer).
      3. Raw code (no fences) if the response starts with import/def/class/from.
    """
    if not text:
        return ""
    fences = re.findall(r"```(?:python(?::[\w./]+)?|py)?\s*\n(.*?)```", text, re.DOTALL)
    if fences:
        return "\n\n# --- file boundary ---\n\n".join(b.strip() for b in fences)
    # Fallback: opening fence, no closer (model truncated). Take everything after.
    unclosed = re.search(r"```(?:python(?::[\w./]+)?|py)?\s*\n(.*)$", text, re.DOTALL)
    if unclosed:
        candidate = unclosed.group(1).strip()
        # Sanity: must contain at least one top-level Python construct.
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


async def _call(client: AsyncOpenAI, sem: asyncio.Semaphore, *, model, system, user,
                temperature, max_tokens, timeout) -> tuple[str, str | None]:
    messages = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    async with sem:
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model, messages=messages,
                    temperature=temperature, max_tokens=max_tokens,
                ),
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001
            return "", f"{type(exc).__name__}: {exc}"
    text = (resp.choices[0].message.content or "").strip()
    return text, None


async def generate_one(client, sem, *, task: dict, preamble: str | None, model: str) -> dict:
    text, err = await _call(
        client, sem, model=model, system=preamble, user=task["prompt"],
        temperature=GEN_TEMPERATURE, max_tokens=GEN_MAX_TOKENS, timeout=GEN_TIMEOUT,
    )
    code = extract_python_code(text)
    return {
        "task_id": task["id"], "preamble": preamble[:40] if preamble else "none",
        "model": model, "code": code, "extraction_ok": bool(code), "error": err,
    }


async def judge_one(client, sem, *, code: str, judge_model: str, system_prompt: str) -> dict:
    user = f"Code under review:\n\n```python\n{code}\n```"
    text, err = await _call(
        client, sem, model=judge_model, system=system_prompt, user=user,
        temperature=JUDGE_TEMPERATURE, max_tokens=JUDGE_MAX_TOKENS, timeout=JUDGE_TIMEOUT,
    )
    if err:
        return {"judge_error": err, "idiomaticity": None, "comment_quality": None,
                **{k: None for k in ITEM_IDS}}
    parsed = _extract_json(text)
    if parsed is None:
        return {"judge_error": f"parse_fail: {text[:80]}",
                "idiomaticity": None, "comment_quality": None,
                **{k: None for k in ITEM_IDS}}
    out = {
        "judge_error": None,
        "idiomaticity": _clamp(parsed.get("idiomaticity"), 1.0, 10.0),
        "comment_quality": _clamp(parsed.get("comment_quality"), 1.0, 10.0),
    }
    for k in ITEM_IDS:
        item = parsed.get(k, {})
        sev = item.get("severity") if isinstance(item, dict) else item
        out[k] = _clamp(sev, 0.0, 5.0)
    return out


# ============================================================
# Phase B — F2 gate pilot
# ============================================================

async def run_phase_b(client, sem) -> dict:
    print("\n[Phase B] F2 gate pilot — task_modeflag_sort rewrite, 30 samples ===")
    task = {"id": "task_modeflag_sort", "prompt": TASK_MODEFLAG_SORT_REWRITE}
    # 15 × no-preamble + 15 × python_coder_agent, distributed across 7 models
    jobs = []
    for i in range(15):
        m = ALL_MODELS[i % len(ALL_MODELS)]
        jobs.append((task, None, m))
        jobs.append((task, PYTHON_CODER_AGENT_PREAMBLE, m))
    print(f"  generating {len(jobs)} samples...")
    samples = await asyncio.gather(*[
        generate_one(client, sem, task=t, preamble=p, model=m) for t, p, m in jobs
    ])
    ok_samples = [s for s in samples if s["extraction_ok"]]
    print(f"  {len(ok_samples)}/{len(samples)} samples extracted ok")

    # Judge with the 3-judge panel on mode_flag_params dim only (cheap focus)
    judge_jobs = [(s, j) for s in ok_samples for j in JUDGE_PANEL]
    print(f"  judging {len(judge_jobs)} judge calls...")
    judge_results = await asyncio.gather(*[
        judge_one(client, sem, code=s["code"], judge_model=j, system_prompt=UNANCHORED_JUDGE_PROMPT)
        for s, j in judge_jobs
    ])

    # Aggregate: per sample, mean mode_flag_params severity across cross-judges
    by_sample = []
    for s, jrs in zip(ok_samples, [judge_results[i*len(JUDGE_PANEL):(i+1)*len(JUDGE_PANEL)] for i in range(len(ok_samples))]):
        # cross-judge: exclude self-judge
        cross = [jr for jr, jm in zip(jrs, JUDGE_PANEL) if jm != s["model"] and jr.get("judge_error") is None]
        sevs = [jr["mode_flag_params"] for jr in cross if jr.get("mode_flag_params") is not None]
        mean_sev = float(np.mean(sevs)) if sevs else None
        by_sample.append({"preamble": s["preamble"], "model": s["model"],
                          "mean_mode_flag_severity": mean_sev,
                          "flagged_present": mean_sev is not None and mean_sev >= 3.0})

    # Gate: no-preamble samples must show ≥40% with mean severity ≥ 3
    np_samples = [r for r in by_sample if r["preamble"] == "none" and r["mean_mode_flag_severity"] is not None]
    np_rate = sum(1 for r in np_samples if r["flagged_present"]) / max(1, len(np_samples))
    pca_samples = [r for r in by_sample if r["preamble"] != "none" and r["mean_mode_flag_severity"] is not None]
    pca_rate = sum(1 for r in pca_samples if r["flagged_present"]) / max(1, len(pca_samples))

    GATE_THRESHOLD = 0.40
    pass_gate = np_rate >= GATE_THRESHOLD
    print(f"  no-preamble flag rate: {np_rate:.0%} ({sum(1 for r in np_samples if r['flagged_present'])}/{len(np_samples)})")
    print(f"  python_coder_agent flag rate: {pca_rate:.0%} ({sum(1 for r in pca_samples if r['flagged_present'])}/{len(pca_samples)})")
    print(f"  GATE ({GATE_THRESHOLD:.0%} req): {'PASS' if pass_gate else 'FAIL'}")

    (RESULTS_DIR / "phase_b_samples.jsonl").write_text(
        "\n".join(json.dumps(r) for r in by_sample) + "\n"
    )
    return {
        "phase": "B", "verdict": "PASS" if pass_gate else "FAIL",
        "gate_threshold": GATE_THRESHOLD,
        "no_preamble_rate": np_rate, "python_coder_agent_rate": pca_rate,
        "n_no_preamble": len(np_samples), "n_python_coder_agent": len(pca_samples),
    }


# ============================================================
# Phase C — F4 style-directive probe
# ============================================================

async def run_phase_c(client, sem) -> dict:
    print("\n[Phase C] F4 style-directive probe — 42 outputs, anchored vs unanchored ===")
    # 3 tasks × 7 models × 2 preambles (python_coder_agent, real_agent) = 42 outputs
    jobs = []
    for task in PHASE_C_TASKS:
        for model in ALL_MODELS:
            jobs.append((task, PYTHON_CODER_AGENT_PREAMBLE, "python_coder_agent", model))
            jobs.append((task, REAL_AGENT_PREAMBLE, "real_agent", model))
    print(f"  generating {len(jobs)} samples...")
    samples_raw = await asyncio.gather(*[
        generate_one(client, sem, task=t, preamble=p, model=m) for t, p, _label, m in jobs
    ])
    # Re-tag with the label
    samples = [{**s, "preamble_label": jobs[i][2]} for i, s in enumerate(samples_raw)]
    ok = [s for s in samples if s["extraction_ok"]]
    print(f"  {len(ok)}/{len(samples)} samples extracted ok")

    # Score each sample twice: unanchored and anchored, 3-judge panel
    print(f"  judging unanchored: {len(ok) * len(JUDGE_PANEL)} calls...")
    un_results = await asyncio.gather(*[
        judge_one(client, sem, code=s["code"], judge_model=j, system_prompt=UNANCHORED_JUDGE_PROMPT)
        for s in ok for j in JUDGE_PANEL
    ])
    print(f"  judging anchored:   {len(ok) * len(JUDGE_PANEL)} calls...")
    an_results = await asyncio.gather(*[
        judge_one(client, sem, code=s["code"], judge_model=j, system_prompt=ANCHORED_JUDGE_PROMPT)
        for s in ok for j in JUDGE_PANEL
    ])

    # Aggregate per-sample comment_quality, cross-judge (exclude self-judge)
    def cross_mean(samples_list, results_list, key):
        per_sample = []
        for i, s in enumerate(samples_list):
            jrs = results_list[i*len(JUDGE_PANEL):(i+1)*len(JUDGE_PANEL)]
            cross = [jr for jr, jm in zip(jrs, JUDGE_PANEL) if jm != s["model"] and jr.get("judge_error") is None and jr.get(key) is not None]
            vals = [jr[key] for jr in cross]
            per_sample.append({"preamble_label": s["preamble_label"], "task_id": s["task_id"],
                               "model": s["model"], f"mean_{key}": float(np.mean(vals)) if vals else None})
        return per_sample

    un_per_sample = cross_mean(ok, un_results, "comment_quality")
    an_per_sample = cross_mean(ok, an_results, "comment_quality")

    # Group by preamble label and compute means
    def group_mean(per_sample_list, key):
        out = {}
        for label in ("python_coder_agent", "real_agent"):
            vals = [r[key] for r in per_sample_list if r["preamble_label"] == label and r[key] is not None]
            out[label] = float(np.mean(vals)) if vals else None
        return out

    un_means = group_mean(un_per_sample, "mean_comment_quality")
    an_means = group_mean(an_per_sample, "mean_comment_quality")

    deltas = {label: (an_means.get(label) - un_means.get(label))
              if (un_means.get(label) is not None and an_means.get(label) is not None) else None
              for label in ("python_coder_agent", "real_agent")}

    TRIGGER = 0.5
    pca_delta = deltas.get("python_coder_agent")
    trigger_fired = pca_delta is not None and abs(pca_delta) > TRIGGER

    print(f"  comment_quality means (1-10 scale):")
    print(f"    python_coder_agent: unanchored={un_means.get('python_coder_agent'):.2f}, anchored={an_means.get('python_coder_agent'):.2f}, Δ={pca_delta:+.2f}" if pca_delta is not None else "    python_coder_agent: insufficient data")
    print(f"    real_agent:         unanchored={un_means.get('real_agent'):.2f}, anchored={an_means.get('real_agent'):.2f}, Δ={deltas.get('real_agent'):+.2f}" if deltas.get('real_agent') is not None else "    real_agent: insufficient data")
    print(f"  AMENDMENT trigger (|Δ|>{TRIGGER}): {'FIRED' if trigger_fired else 'NOT FIRED'}")

    (RESULTS_DIR / "phase_c_unanchored.jsonl").write_text("\n".join(json.dumps(r) for r in un_per_sample) + "\n")
    (RESULTS_DIR / "phase_c_anchored.jsonl").write_text("\n".join(json.dumps(r) for r in an_per_sample) + "\n")
    return {
        "phase": "C", "trigger_threshold": TRIGGER,
        "amendment_triggered": trigger_fired,
        "unanchored_means": un_means, "anchored_means": an_means, "deltas": deltas,
        "n_samples_python_coder_agent": sum(1 for s in ok if s["preamble_label"] == "python_coder_agent"),
        "n_samples_real_agent": sum(1 for s in ok if s["preamble_label"] == "real_agent"),
    }


# ============================================================
# Phase D — F5 prevalence audit
# ============================================================

async def run_phase_d(client, sem) -> dict:
    print("\n[Phase D] F5 prevalence audit — 30 no-preamble generations across 9 tasks ===")
    # Distribute 30 samples across 9 tasks × 7 models = balanced
    jobs = []
    for i, task in enumerate(PHASE_D_TASKS):
        # 3-4 samples per task, distributed across models
        n_for_task = 4 if i < 3 else 3   # 3*4 + 6*3 = 12+18 = 30
        for j in range(n_for_task):
            m = ALL_MODELS[(i + j) % len(ALL_MODELS)]
            jobs.append((task, None, m))
    print(f"  generating {len(jobs)} samples...")
    samples = await asyncio.gather(*[
        generate_one(client, sem, task=t, preamble=p, model=m) for t, p, m in jobs
    ])
    ok = [s for s in samples if s["extraction_ok"]]
    print(f"  {len(ok)}/{len(samples)} extracted ok")

    # Judge with 3-judge panel, unanchored prompt, single judge per sample (cost saving — D8 prevalence only)
    print(f"  judging {len(ok)} samples × 1 judge each = {len(ok)} calls...")
    # Use gpt-4o-mini as the single judge for prevalence (cheapest)
    SINGLE_JUDGE = "openai/gpt-4o-mini"
    judge_results = await asyncio.gather(*[
        judge_one(client, sem, code=s["code"], judge_model=SINGLE_JUDGE, system_prompt=UNANCHORED_JUDGE_PROMPT)
        for s in ok
    ])

    # Per-dim, count samples with severity >= 1
    PREVALENCE_THRESHOLD = 0.10  # >10%
    n_samples = len(judge_results)
    per_dim = {}
    for k in ITEM_IDS:
        n_active = sum(1 for jr in judge_results if jr.get(k) is not None and jr[k] >= 1.0)
        prevalence = n_active / n_samples if n_samples else 0
        per_dim[k] = {"n_active": n_active, "n_samples": n_samples, "prevalence": prevalence,
                      "active": prevalence > PREVALENCE_THRESHOLD}

    n_active_dims = sum(1 for d in per_dim.values() if d["active"])
    criterion_achievable = n_active_dims >= 4

    print(f"  per-dim prevalence (>10% threshold; * = active):")
    for k, d in per_dim.items():
        mark = " *" if d["active"] else ""
        print(f"    {k:<32} {d['n_active']:>2}/{d['n_samples']} ({d['prevalence']:.0%}){mark}")
    print(f"  ACTIVE DIMS: {n_active_dims}/11")
    print(f"  SECONDARY CRITERION (≥4 active req): {'ACHIEVABLE' if criterion_achievable else 'NOT ACHIEVABLE'}")

    (RESULTS_DIR / "phase_d_per_sample_judge.jsonl").write_text("\n".join(json.dumps({
        "task_id": s["task_id"], "model": s["model"], **jr
    }) for s, jr in zip(ok, judge_results)) + "\n")
    return {
        "phase": "D", "prevalence_threshold": PREVALENCE_THRESHOLD,
        "n_active_dims": n_active_dims, "criterion_achievable": criterion_achievable,
        "per_dim": per_dim, "n_samples": n_samples,
    }


# ============================================================
# Main
# ============================================================

async def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    sem = asyncio.Semaphore(CONCURRENCY)

    print("=" * 64)
    print("Pre-flight phases B, C, D (parallel where possible, single sem)")
    print("=" * 64)

    # Run all three phases concurrently — they share the same semaphore so
    # OpenRouter rate limits are honored across all phases simultaneously
    phase_b, phase_c, phase_d = await asyncio.gather(
        run_phase_b(client, sem),
        run_phase_c(client, sem),
        run_phase_d(client, sem),
    )

    summary = {
        "phase_b": phase_b,
        "phase_c": phase_c,
        "phase_d": phase_d,
        "all_pass": phase_b["verdict"] == "PASS" and phase_d["criterion_achievable"],
    }
    (RESULTS_DIR / "preflight_summary.json").write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 64)
    print("PRE-FLIGHT SUMMARY")
    print("=" * 64)
    print(f"  Phase B (F2 trap gate):       {phase_b['verdict']}")
    print(f"  Phase C (F4 amendment):       {'FIRED' if phase_c['amendment_triggered'] else 'NOT FIRED'}")
    print(f"  Phase D (F5 criterion):       {'ACHIEVABLE' if phase_d['criterion_achievable'] else 'NOT ACHIEVABLE'}")
    print(f"  Saved: preflight_results/preflight_summary.json")


if __name__ == "__main__":
    asyncio.run(main())
