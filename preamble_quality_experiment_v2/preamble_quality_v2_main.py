# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "numpy",
#   "scipy",
#   "statsmodels",
#   "radon",
#   "pylint",
#   "flake8",
#   "flake8-cognitive-complexity",
# ]
# ///
"""Preamble Quality Experiment v2 — main run.

Implements SPEC_V2.md as amended through Amendment A5 (see SPEC §12). The
pre-flight Steps 1-5 produced this design; the script executes it.

Design (locked):
  - Subjects: 10 models (3 reasoning + 7 non-reasoning), reasoning models
    receive `reasoning: {effort: "high"}` and max_tokens=10000.
  - Judges: all 10 models (full v1-equivalent cross-judge matrix). Reasoning
    judges receive `reasoning: {exclude: true}` (judge-side reasoning is not
    the variable under test). Self-judge exclusion for primary CQS.
  - Tasks: 7 (4 v1 + 3 new). task_modeflag_sort dropped (A2).
  - Preambles: 9 (v1's 8 + python_coder_agent verbatim).
  - Reps: 2 → 1260 generations, ~11,340 cross-judge calls.
  - Rubric: 11 algorithmic-code dimensions (A1), 0-5 severity, calibrated
    judge prompt with anchor (A5). Idiom + comment scored unanchored
    (Phase C resolved keep_unanchored).
  - CQS-craft = 0.45·idiom + 0.45·comment + 0.10·(1 - mean_rubric_sev/5).
  - Static analysis (radon/pylint/flake8) reported as a separate diagnostic
    panel; never an input to CQS.

Persistence:
  - Generations and judgments are appended to JSONL files as they complete.
  - Re-running with `--resume` skips already-done work.
  - `--slice` runs a small subset for smoke testing.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from scipy import stats

ROOT = Path(__file__).parent
PYTHON = sys.executable

# =============================================================================
# Pool — SPEC §6.3 (Amendment A3/A4)
# =============================================================================
REASONING_MODELS = [
    "qwen/qwen3.6-flash",
    "deepseek/deepseek-v4-flash",
    "minimax/minimax-m2.5",
]
NON_REASONING_MODELS = [
    "deepseek/deepseek-v3.2",
    "google/gemma-4-31b-it",
    "mistralai/mistral-small-2603",
    "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-4o-mini",
    "google/gemini-3.1-flash-lite",
    "google/gemini-2.5-flash",
]
ALL_MODELS = REASONING_MODELS + NON_REASONING_MODELS
SUBJECT_MODELS = ALL_MODELS
JUDGE_MODELS = ALL_MODELS   # full cross-judge matrix (v1 design)

# Model-family helper for the self-judgment-exclusion rule. Provider prefix
# is the family — sample-of-deepseek-v3.2 judged by deepseek-v4-flash counts
# as a self-judgment for F3 hygiene.
def model_family(model: str) -> str:
    return model.split("/", 1)[0]


# =============================================================================
# Preambles — SPEC §6.1
# =============================================================================
PYTHON_CODER_AGENT_PATH = Path(
    "/Users/chrissantiago/Dropbox/claude-config/plugins/chris-code/agents/python-coder.md"
)


def _load_python_coder_preamble() -> str:
    raw = PYTHON_CODER_AGENT_PATH.read_text()
    parts = raw.split("---\n", 2)
    return (parts[2] if len(parts) >= 3 and raw.startswith("---") else raw).strip()


PREAMBLES: dict[str, str | None] = {
    "none": None,
    "minimal": "You are a helpful assistant.",
    "generic_coding": (
        "You are an expert software engineer with deep knowledge of Python. "
        "Write clean, efficient, and maintainable code."
    ),
    "real_agent": (
        "You are an expert autonomous coding agent. Your code must: "
        "(1) Be idiomatic Python — use built-ins, standard library, and established patterns. "
        "(2) Have appropriate abstraction — no over-engineering, no under-engineering. "
        "(3) Include defensive programming: validate inputs, handle edge cases, fail clearly. "
        "(4) Use precise naming — variables, functions, and classes should be self-documenting. "
        "(5) Add comments only where they explain *why*, never *what*. "
        "(6) Be maintainable: prefer explicit over implicit, simple over clever. "
        "Do not add unused code. Do not optimize prematurely. "
        "Write as if the next engineer maintaining this code is skilled but unfamiliar with context."
    ),
    "negative_control": (
        "You are a junior developer still learning Python. "
        "Write code that works but don't worry too much about style or best practices."
    ),
    "persona_only": (
        "You are a senior staff software engineer at a top-tier tech company."
    ),
    "long_directive": (
        "You are an expert autonomous coding agent. Your code must: "
        "(1) Be idiomatic Python — use built-ins, standard library, and established patterns. "
        "(2) Have appropriate abstraction — no over-engineering, no under-engineering. "
        "(3) Include defensive programming: validate inputs, handle edge cases, fail clearly. "
        "(4) Use precise naming — variables, functions, and classes should be self-documenting. "
        "(5) Add comments only where they explain *why*, never *what*. "
        "(6) Be maintainable: prefer explicit over implicit, simple over clever. "
        "(7) Handle all concurrency and thread-safety concerns explicitly. "
        "(8) Prefer composition over inheritance; avoid deep class hierarchies. "
        "(9) Make all side effects and I/O boundaries explicit. "
        "(10) Write tests or testable interfaces — prefer dependency injection over globals. "
        "(11) Log errors at the right severity — never swallow exceptions silently. "
        "(12) Document public interfaces with docstrings; skip obvious internal comments. "
        "Do not add unused code. Do not optimize prematurely. "
        "Write as if the next engineer maintaining this code is a senior developer unfamiliar with this codebase."
    ),
    "trivial_baseline": None,   # special: no system prompt, prompt = task name, temp=1.0
    "python_coder_agent": _load_python_coder_preamble(),
}
MAIN_CONDITIONS = [c for c in PREAMBLES if c != "trivial_baseline"]
PREAMBLE_ORDER = [
    "trivial_baseline", "none", "negative_control", "minimal",
    "generic_coding", "persona_only", "real_agent", "long_directive",
    "python_coder_agent",
]


# =============================================================================
# Tasks — SPEC §6.2 (Amendment A2: 7 tasks; modeflag_sort dropped)
# =============================================================================
TASK5_BEFORE = '''\
_global_cache = {}
_global_stats = {"hits": 0, "misses": 0, "errors": 0}

class DataProcessor:
    def __init__(self, strict=False, verbose=False, cache=False,
                 normalize=False, dedupe=False, validate=False):
        self.strict = strict
        self.verbose = verbose
        self.cache = cache
        self.normalize = normalize
        self.dedupe = dedupe
        self.validate = validate

    def process(self, data):
        if self.cache and id(data) in _global_cache:
            _global_stats["hits"] += 1
            return _global_cache[id(data)]
        _global_stats["misses"] += 1

        result = []
        seen = set()
        for item in data:
            if self.validate:
                if not isinstance(item, dict):
                    _global_stats["errors"] += 1
                    if self.strict:
                        raise ValueError(f"Expected dict, got {type(item)}")
                    if self.verbose:
                        print(f"Skipping invalid item: {item}")
                    continue
            if self.dedupe:
                key = str(sorted(item.items()) if isinstance(item, dict) else item)
                if key in seen:
                    continue
                seen.add(key)
            if self.normalize and isinstance(item, dict):
                item = {k: (v.strip().lower() if isinstance(v, str) else v)
                        for k, v in item.items()}
            result.append(item)

        if self.cache:
            _global_cache[id(data)] = result
        return result

    def get_stats(self):
        return dict(_global_stats)

    def reset(self):
        global _global_cache, _global_stats
        _global_cache = {}
        _global_stats = {"hits": 0, "misses": 0, "errors": 0}
'''

TASK6_BEFORE = '''\
import json
import logging
from pathlib import Path

def load_and_merge_configs(primary_path, override_path=None):
    result = {}
    try:
        try:
            with open(primary_path) as f:
                try:
                    primary = json.load(f)
                    try:
                        if not isinstance(primary, dict):
                            logging.warning("Primary config is not a dict")
                        else:
                            result.update(primary)
                    except Exception:
                        pass
                except json.JSONDecodeError as e:
                    try:
                        logging.error(f"JSON parse error in primary: {e}")
                    except Exception:
                        pass
        except FileNotFoundError:
            try:
                logging.warning(f"Primary config not found: {primary_path}")
            except Exception:
                pass
        except PermissionError:
            pass

        if override_path:
            try:
                with open(override_path) as f:
                    try:
                        override = json.load(f)
                        try:
                            if isinstance(override, dict):
                                for k, v in override.items():
                                    try:
                                        result[k] = v
                                    except Exception:
                                        pass
                        except Exception:
                            logging.debug("Could not merge override")
                    except json.JSONDecodeError:
                        try:
                            logging.error("JSON parse error in override")
                        except Exception:
                            pass
            except FileNotFoundError:
                pass
            except Exception as e:
                try:
                    logging.warning(f"Unexpected error loading override: {e}")
                except Exception:
                    pass
    except Exception:
        pass

    return result
'''

TASKS = [
    {
        "id": "task_lru_ttl_cache",
        "name": "Thread-safe LRU cache with per-entry TTL",
        "category": "creation",
        "prompt": (
            "Write a Python class implementing a thread-safe LRU cache with per-entry TTL expiry.\n"
            "Requirements:\n"
            "- O(1) get and put operations\n"
            "- Per-entry TTL: entries expire independently after their TTL elapses\n"
            "- Eviction: when capacity is exceeded, evict the least-recently-used entry\n"
            "  (among non-expired entries; expired entries should be opportunistically reaped)\n"
            "- Thread-safe: all operations must be safe for concurrent use\n"
            "- get(key) returns the value if present and not expired, else None\n"
            "- put(key, value, ttl_seconds) stores the entry\n"
            "- size() returns the count of non-expired entries\n"
            "Include type hints and a brief usage example at the bottom.\n"
            "Do not use functools.lru_cache or any third-party caching library."
        ),
    },
    {
        "id": "task_expr_parser",
        "name": "Recursive-descent arithmetic expression parser and evaluator",
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
    },
    {
        "id": "task_flag_class",
        "name": "Refactor boolean-flag class with global state into clean design",
        "category": "refactor",
        "prompt": (
            "Refactor the following Python code. The class uses boolean mode-flags "
            "to select behavior variants at runtime, and relies on hidden module-global "
            "state for caching and statistics. Both patterns make the class hard to test "
            "and reason about.\n\n"
            "Requirements:\n"
            "- Eliminate boolean mode-flags; use composition, strategy pattern, or "
            "  explicit subclasses — choose whichever is cleanest\n"
            "- Remove all module-global state; the class must be fully self-contained "
            "  and independently testable\n"
            "- Preserve all observable behaviors (filtering, deduplication, normalization, "
            "  validation, caching, statistics)\n"
            "- The refactored code must be importable and safe for concurrent use "
            "  across multiple instances\n"
            "- Add type hints where missing\n\n"
            f"```python\n{TASK5_BEFORE}```\n\n"
            "Return the refactored code in a single ```python ... ``` block."
        ),
    },
    {
        "id": "task_exception_pyramid",
        "name": "Flatten exception pyramid: make errors explicit and loud",
        "category": "refactor",
        "prompt": (
            "Refactor the following Python code. It uses deeply nested try/except blocks "
            "with broad exception catches and silently swallows most errors. "
            "This makes it impossible to debug failures and hides real problems.\n\n"
            "Requirements:\n"
            "- Eliminate all nested try/except structures — maximum 1 level of nesting\n"
            "- Remove all bare `except Exception: pass` clauses; every exception must "
            "  either be re-raised, logged with full context, or converted to a "
            "  specific typed exception\n"
            "- Preserve the function signature: load_and_merge_configs(primary_path, override_path=None)\n"
            "- The function should still return a merged dict (or {} on missing primary)\n"
            "- Make all error conditions visible: callers should be able to distinguish "
            "  'primary config missing' from 'primary config malformed' from 'override malformed'\n"
            "- Add type hints\n\n"
            f"```python\n{TASK6_BEFORE}```\n\n"
            "Return the refactored code in a single ```python ... ``` block."
        ),
    },
    {
        "id": "task_mini_sql_engine",
        "name": "In-memory SQL-like query engine with fluent composable API",
        "category": "creation",
        "prompt": (
            "Implement a small in-memory SQL-like query engine in Python. A Table class "
            "holds a list of dict rows. Support: select(*columns), where(predicate), "
            "join(other_table, on=lambda l,r: bool), group_by(column), "
            "order_by(column, descending=False), limit(n). Composable fluent API.\n"
            "Include type hints and 2-3 usage examples."
        ),
    },
    {
        "id": "task_rate_limiter_family",
        "name": "Family of rate limiters behind a single interface",
        "category": "creation",
        "prompt": (
            "Implement a family of rate limiters in Python behind a single interface: "
            "token bucket, leaky bucket, sliding-window-log, sliding-window-counter. "
            "All implement an `allow(client_id) -> bool` method. Each algorithm is its "
            "own class but they share an interface (base class or protocol). "
            "Include type hints, brief usage example showing each in use."
        ),
    },
    {
        "id": "task_kv_store_package",
        "name": "Multi-file KV store package",
        "category": "multifile_creation",
        "prompt": (
            "Design and implement a small Python package for an in-memory key-value store "
            "with TTL, atomic updates, and bulk ops. Use stdlib only. Sketch the file layout "
            "(you may write each file as a separate ```python:path/file.py``` fenced block) — "
            "typical layout: a top-level package, a core module, an optional CLI module, "
            "and a tests file. Include type hints and a brief usage example."
        ),
    },
]


# =============================================================================
# Rubric & judge prompts — SPEC §6.4 (Amendment A1 + A5)
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
ALWAYS_ON_IDS = [k for k, _, kind in RUBRIC if kind == "always"]

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


def _build_rubric_judge_prompt() -> str:
    lines = "\n".join(f"  - {k}: {desc}" for k, desc, _ in RUBRIC)
    schema_inner = ",\n  ".join(
        f'"{k}": {{"severity": <0-5 or null>, "rationale": "<one sentence>"}}'
        for k in RUBRIC_IDS
    )
    return (
        "You are a senior Python code reviewer scoring an algorithmic Python sample on "
        "11 specific quality dimensions on a 0-5 severity scale "
        "(0=clean / no detectable issue, 5=severe / pervasive).\n\n"
        + CALIBRATION_ANCHOR +
        "\nFor the two CONDITIONAL dimensions (concurrency_safety, example_quality), "
        "return null only if the dimension does not apply to this code (no concurrency "
        "requirement; no examples requested in the task).\n\n"
        "Dimensions:\n" + lines + "\n\n"
        "Respond with ONLY a single JSON object, no markdown fences, no prose:\n"
        "{\n  " + schema_inner + "\n}\n"
    )


# Phase C resolved: keep unanchored idiom/comment prompt for main run.
IDIOM_COMMENT_PROMPT = (
    "You are a senior Python code reviewer evaluating code quality. Assign "
    "idiomaticity and comment_quality scores on a 1-10 integer scale "
    "(1=worst, 10=best).\n\n"
    "Respond with ONLY a single JSON object, no markdown fences, no prose:\n"
    '{\n  "idiomaticity": <1-10>,\n  "comment_quality": <1-10>\n}\n'
)
RUBRIC_JUDGE_PROMPT = _build_rubric_judge_prompt()


# =============================================================================
# Generation parameters (locked at SPEC §6.3 A4 + §6.5)
# =============================================================================
GEN_TEMPERATURE = 0.3
TRIVIAL_TEMPERATURE = 1.0
GEN_MAX_TOKENS = 10000
GEN_TIMEOUT = 300.0
JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_TOKENS = 1800
JUDGE_TIMEOUT = 120.0
CONCURRENCY = 50
RETRY_ATTEMPTS = 2
REPLICATIONS_DEFAULT = 2

# CQS weights (SPEC §6.5)
W_IDIOM = 0.45
W_COMMENT = 0.45
W_HYGIENE = 0.10


# =============================================================================
# Outputs
# =============================================================================
RESULTS_DIR = ROOT / "experiment_v2_results"
RESULTS_DIR.mkdir(exist_ok=True)
GEN_FILE = RESULTS_DIR / "generations.jsonl"
JUDGE_FILE = RESULTS_DIR / "judgments.jsonl"
STATIC_FILE = RESULTS_DIR / "static_analysis.jsonl"


# =============================================================================
# Helpers
# =============================================================================
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


def _append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(obj, default=str) + "\n")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# =============================================================================
# Raw HTTP call (reasoning param + provider field + retry)
# =============================================================================
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
    reasoning_mode: str,   # "high" | "exclude" | "off"
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
    if reasoning_mode == "high":
        body["reasoning"] = {"effort": "high"}
    elif reasoning_mode == "exclude":
        body["reasoning"] = {"exclude": True}
    # "off" → don't pass anything

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
                    last_err = f"HTTP {r.status_code}: {str(resp.get('error', resp))[:200]}"
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                msg = resp["choices"][0]["message"]
                u = resp.get("usage", {}) or {}
                ctd = u.get("completion_tokens_details", {}) or {}
                return {
                    "content": (msg.get("content") or "").strip(),
                    "provider": resp.get("provider"),
                    "model_returned": resp.get("model"),
                    "completion_tokens": u.get("completion_tokens"),
                    "reasoning_tokens": ctd.get("reasoning_tokens", 0),
                    "cost": u.get("cost", 0.0),
                    "error": None,
                }
            except Exception as exc:   # noqa: BLE001
                last_err = f"{type(exc).__name__}: {str(exc)[:150]}"
                await asyncio.sleep(1.5 * (attempt + 1))
    return {
        "content": "", "provider": None, "model_returned": None,
        "completion_tokens": 0, "reasoning_tokens": 0, "cost": 0.0, "error": last_err,
    }


# =============================================================================
# Generation
# =============================================================================
def gen_key(task_id: str, preamble_id: str, model: str, rep: int) -> str:
    return f"{task_id}|{preamble_id}|{model}|r{rep}"


def build_user_prompt(preamble_id: str, task: dict) -> str:
    # trivial_baseline overrides: prompt = task name only
    if preamble_id == "trivial_baseline":
        return task["name"]
    return task["prompt"]


async def generate_one(
    client, sem, *, task: dict, preamble_id: str, model: str, rep: int,
) -> dict:
    preamble = PREAMBLES[preamble_id]
    user = build_user_prompt(preamble_id, task)
    temp = TRIVIAL_TEMPERATURE if preamble_id == "trivial_baseline" else GEN_TEMPERATURE
    mode = "high" if model in REASONING_MODELS else "off"
    result = await _post(
        client, sem, model=model, system=preamble, user=user,
        temperature=temp, max_tokens=GEN_MAX_TOKENS, timeout=GEN_TIMEOUT,
        reasoning_mode=mode,
    )
    code = extract_python_code(result["content"])
    return {
        "key": gen_key(task["id"], preamble_id, model, rep),
        "task_id": task["id"], "category": task["category"],
        "preamble_id": preamble_id,
        "model": model, "rep": rep,
        "code": code, "extraction_ok": bool(code),
        "raw_preview": result["content"][:400],
        "provider": result["provider"],
        "model_returned": result["model_returned"],
        "completion_tokens": result["completion_tokens"],
        "reasoning_tokens": result["reasoning_tokens"],
        "cost": result["cost"],
        "error": result["error"],
    }


# =============================================================================
# Judging
# =============================================================================
def judge_key(gen_key_str: str, judge_model: str, kind: str) -> str:
    return f"{gen_key_str}|judge={judge_model}|kind={kind}"


async def judge_one(
    client, sem, *, gen_record: dict, judge_model: str, kind: str,
) -> dict:
    prompt = RUBRIC_JUDGE_PROMPT if kind == "rubric" else IDIOM_COMMENT_PROMPT
    user = f"Code under review:\n\n```python\n{gen_record['code']}\n```"
    mode = "exclude" if judge_model in REASONING_MODELS else "off"
    result = await _post(
        client, sem, model=judge_model, system=prompt, user=user,
        temperature=JUDGE_TEMPERATURE, max_tokens=JUDGE_MAX_TOKENS,
        timeout=JUDGE_TIMEOUT, reasoning_mode=mode,
    )
    out: dict = {
        "jkey": judge_key(gen_record["key"], judge_model, kind),
        "gen_key": gen_record["key"],
        "task_id": gen_record["task_id"], "category": gen_record["category"],
        "preamble_id": gen_record["preamble_id"],
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


# =============================================================================
# Static analysis (subprocess; never enters CQS — diagnostic panel only)
# =============================================================================
def compute_static_metrics(code: str) -> dict:
    metrics: dict[str, float] = {}
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        # radon cc
        complexities: list[float] = []
        r = subprocess.run([PYTHON, "-m", "radon", "cc", "--json", tmp],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            try:
                data = json.loads(r.stdout)
                for items in data.values():
                    if isinstance(items, list):
                        for it in items:
                            if isinstance(it, dict):
                                complexities.append(float(it.get("complexity", 1)))
                                for m in it.get("methods", []):
                                    if isinstance(m, dict):
                                        complexities.append(float(m.get("complexity", 1)))
            except (json.JSONDecodeError, TypeError):
                pass
        metrics["avg_cyclomatic"] = float(np.mean(complexities)) if complexities else 1.0
        metrics["max_cyclomatic"] = float(max(complexities)) if complexities else 1.0

        # radon mi
        mi = 50.0
        r = subprocess.run([PYTHON, "-m", "radon", "mi", "--json", tmp],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            try:
                data = json.loads(r.stdout)
                for fd in data.values():
                    if isinstance(fd, dict):
                        mi = float(fd.get("mi", 50.0))
                        break
            except (json.JSONDecodeError, TypeError):
                pass
        metrics["maintainability_index"] = mi

        # radon halstead
        vol = diff = 0.0
        r = subprocess.run([PYTHON, "-m", "radon", "hal", "--json", tmp],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            try:
                data = json.loads(r.stdout)
                for fd in data.values():
                    if isinstance(fd, dict):
                        total = fd.get("total", fd)
                        vol = float(total.get("volume", 0.0) or 0.0)
                        diff = float(total.get("difficulty", 0.0) or 0.0)
                    break
            except (json.JSONDecodeError, TypeError):
                pass
        metrics["halstead_volume"] = vol
        metrics["halstead_difficulty"] = diff

        # pylint counts
        counts = {"E": 0, "W": 0, "C": 0, "R": 0}
        r = subprocess.run(
            [PYTHON, "-m", "pylint", "--output-format=json", "--disable=all",
             "--enable=E,W,C,R", tmp],
            capture_output=True, text=True, timeout=20,
        )
        if r.stdout.strip():
            try:
                for msg in json.loads(r.stdout):
                    cat = msg.get("type", "")[:1].upper()
                    if cat in counts:
                        counts[cat] += 1
            except (json.JSONDecodeError, TypeError):
                pass
        metrics["pylint_errors"] = float(counts["E"])
        metrics["pylint_warnings"] = float(counts["W"])
        metrics["pylint_conventions"] = float(counts["C"])
        metrics["pylint_refactor"] = float(counts["R"])

        # cognitive complexity
        cog = 0
        r = subprocess.run(
            [PYTHON, "-m", "flake8", "--select=CCR001",
             "--max-cognitive-complexity=30",
             "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s", tmp],
            capture_output=True, text=True, timeout=10,
        )
        cog = sum(1 for ln in r.stdout.splitlines() if "CCR001" in ln)
        metrics["cognitive_complexity_violations"] = float(cog)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return metrics


# =============================================================================
# CQS-craft computation
# =============================================================================
def compute_sample_cqs(gen_record: dict, judgments_for_gen: list[dict]) -> dict:
    """Compute panel-mean idiom, comment, rubric severity for one sample.

    Self-judgments excluded from primary CQS. Self-vs-cross stratification
    retained for F3 hygiene reporting (caller's responsibility).
    """
    cross_idioms: list[float] = []
    cross_comments: list[float] = []
    cross_rubric_means: list[float] = []
    cross_per_dim: dict[str, list[float]] = defaultdict(list)

    for j in judgments_for_gen:
        if j["is_self_judge"]:
            continue
        if not j.get("parsed"):
            continue
        if j["kind"] == "idiom_comment":
            i = _clamp(j["parsed"].get("idiomaticity"), 1, 10)
            c = _clamp(j["parsed"].get("comment_quality"), 1, 10)
            if i is not None:
                cross_idioms.append(i)
            if c is not None:
                cross_comments.append(c)
        elif j["kind"] == "rubric":
            sevs: list[float] = []
            for k in RUBRIC_IDS:
                item = j["parsed"].get(k)
                if isinstance(item, dict):
                    sev_raw = item.get("severity")
                else:
                    sev_raw = item
                if sev_raw is None:
                    continue
                sev = _clamp(sev_raw, 0.0, 5.0)
                if sev is None:
                    continue
                cross_per_dim[k].append(sev)
                sevs.append(sev)
            if sevs:
                cross_rubric_means.append(float(np.mean(sevs)))

    idiom_score = float(np.mean(cross_idioms)) if cross_idioms else None
    comment_score = float(np.mean(cross_comments)) if cross_comments else None
    rubric_sev_mean = float(np.mean(cross_rubric_means)) if cross_rubric_means else None

    cqs: float | None = None
    if idiom_score is not None and comment_score is not None and rubric_sev_mean is not None:
        cqs = (
            W_IDIOM * (idiom_score / 10.0)
            + W_COMMENT * (comment_score / 10.0)
            + W_HYGIENE * (1.0 - rubric_sev_mean / 5.0)
        )

    return {
        "gen_key": gen_record["key"],
        "n_cross_idiom": len(cross_idioms),
        "n_cross_comment": len(cross_comments),
        "n_cross_rubric": len(cross_rubric_means),
        "idiom_score": idiom_score,
        "comment_score": comment_score,
        "rubric_sev_mean": rubric_sev_mean,
        "per_dim_means": {k: float(np.mean(v)) if v else None for k, v in cross_per_dim.items()},
        "cqs_craft": cqs,
    }


# =============================================================================
# Aggregation / stats
# =============================================================================
def bootstrap_ci(values: list[float], n_boot: int = 2000, alpha: float = 0.05) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) < 2:
        m = float(arr.mean()) if len(arr) else float("nan")
        return m, m, m
    rng = np.random.default_rng(2026_05_22)
    boot = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    lo = float(np.quantile(boot, alpha / 2))
    hi = float(np.quantile(boot, 1 - alpha / 2))
    return float(arr.mean()), lo, hi


def kruskal_across_conditions(by_cond: dict[str, list[float]]) -> dict:
    groups = [v for v in by_cond.values() if len(v) >= 2]
    if len(groups) < 2:
        return {"H": None, "p": None, "n_groups": len(groups)}
    H, p = stats.kruskal(*groups)
    return {"H": float(H), "p": float(p), "n_groups": len(groups)}


# =============================================================================
# Main pipeline
# =============================================================================
async def run_phase_generation(client, sem, *, jobs: list[tuple], done_keys: set[str]) -> int:
    pending = [j for j in jobs if gen_key(j[0]["id"], j[1], j[2], j[3]) not in done_keys]
    print(f"[gen] {len(pending)}/{len(jobs)} generations to run "
          f"({len(jobs) - len(pending)} already done)")
    if not pending:
        return 0

    done = 0
    t0 = time.time()

    async def _one(task, preamble_id, model, rep):
        nonlocal done
        rec = await generate_one(client, sem, task=task, preamble_id=preamble_id,
                                  model=model, rep=rep)
        _append_jsonl(GEN_FILE, rec)
        done += 1
        if done % 25 == 0 or done == len(pending):
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed else 0
            eta = (len(pending) - done) / rate if rate else float("inf")
            print(f"  [gen] {done}/{len(pending)} ({rate:.2f}/s, eta {eta:.0f}s)",
                  flush=True)
        return rec

    await asyncio.gather(*[_one(t, p, m, r) for (t, p, m, r) in pending])
    return len(pending)


async def run_phase_judging(client, sem, generations: list[dict], done_jkeys: set[str]) -> int:
    jobs: list[tuple[dict, str, str]] = []
    for g in generations:
        if not g["extraction_ok"]:
            continue
        for jm in JUDGE_MODELS:
            for kind in ("idiom_comment", "rubric"):
                if judge_key(g["key"], jm, kind) in done_jkeys:
                    continue
                jobs.append((g, jm, kind))
    print(f"[judge] {len(jobs)} judge calls to run "
          f"({len(done_jkeys)} already done)")
    if not jobs:
        return 0

    done = 0
    t0 = time.time()

    async def _one(g, jm, kind):
        nonlocal done
        rec = await judge_one(client, sem, gen_record=g, judge_model=jm, kind=kind)
        _append_jsonl(JUDGE_FILE, rec)
        done += 1
        if done % 100 == 0 or done == len(jobs):
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed else 0
            eta = (len(jobs) - done) / rate if rate else float("inf")
            print(f"  [judge] {done}/{len(jobs)} ({rate:.2f}/s, eta {eta:.0f}s)",
                  flush=True)
        return rec

    await asyncio.gather(*[_one(g, jm, k) for (g, jm, k) in jobs])
    return len(jobs)


def run_phase_static(generations: list[dict], done_keys: set[str]) -> int:
    pending = [g for g in generations if g["extraction_ok"] and g["key"] not in done_keys]
    if not pending:
        return 0
    print(f"[static] {len(pending)} samples to analyze")
    for i, g in enumerate(pending, 1):
        try:
            metrics = compute_static_metrics(g["code"])
        except Exception as exc:    # noqa: BLE001
            metrics = {"error": f"{type(exc).__name__}: {exc}"}
        _append_jsonl(STATIC_FILE, {"key": g["key"], **metrics})
        if i % 50 == 0 or i == len(pending):
            print(f"  [static] {i}/{len(pending)}", flush=True)
    return len(pending)


def write_report(
    generations: list[dict],
    judgments: list[dict],
    static_records: list[dict],
    sample_cqs: list[dict],
) -> None:
    by_key = {g["key"]: g for g in generations}

    # Per-condition CQS
    cqs_by_cond: dict[str, list[float]] = defaultdict(list)
    cqs_by_cond_tier: dict[tuple[str, str], list[float]] = defaultdict(list)
    cqs_by_cond_cat: dict[tuple[str, str], list[float]] = defaultdict(list)
    for s in sample_cqs:
        if s["cqs_craft"] is None:
            continue
        g = by_key.get(s["gen_key"])
        if not g:
            continue
        cond = g["preamble_id"]
        tier = "reasoning" if g["model"] in REASONING_MODELS else "non_reasoning"
        cqs_by_cond[cond].append(s["cqs_craft"])
        cqs_by_cond_tier[(cond, tier)].append(s["cqs_craft"])
        cqs_by_cond_cat[(cond, g["category"])].append(s["cqs_craft"])

    # Per-dim severity by condition
    per_dim_by_cond: dict[str, dict[str, list[float]]] = {k: defaultdict(list) for k in RUBRIC_IDS}
    for s in sample_cqs:
        g = by_key.get(s["gen_key"])
        if not g:
            continue
        for dim, mean_val in s["per_dim_means"].items():
            if mean_val is None:
                continue
            per_dim_by_cond[dim][g["preamble_id"]].append(mean_val)

    # Static metrics by condition
    static_by_cond_metric: dict[tuple[str, str], list[float]] = defaultdict(list)
    static_by_key = {s["key"]: s for s in static_records}
    for g in generations:
        if not g["extraction_ok"]:
            continue
        sm = static_by_key.get(g["key"])
        if not sm:
            continue
        for k, v in sm.items():
            if k == "key" or k == "error" or v is None:
                continue
            try:
                static_by_cond_metric[(g["preamble_id"], k)].append(float(v))
            except (TypeError, ValueError):
                continue

    # F3: self vs cross stratification on idiom + comment
    self_idioms: list[float] = []
    cross_idioms: list[float] = []
    self_comments: list[float] = []
    cross_comments: list[float] = []
    for j in judgments:
        if j["kind"] != "idiom_comment" or not j.get("parsed"):
            continue
        i = _clamp(j["parsed"].get("idiomaticity"), 1, 10)
        c = _clamp(j["parsed"].get("comment_quality"), 1, 10)
        if i is not None:
            (self_idioms if j["is_self_judge"] else cross_idioms).append(i)
        if c is not None:
            (self_comments if j["is_self_judge"] else cross_comments).append(c)

    # ---- Build report ----
    lines: list[str] = []
    lines.append("# Preamble Quality Experiment v2 — Main Run Report")
    lines.append("")
    lines.append(f"**Total generations:** {len(generations)}  |  "
                 f"**extracted ok:** {sum(1 for g in generations if g['extraction_ok'])}")
    lines.append(f"**Judge calls:** {len(judgments)}  |  "
                 f"**parse ok:** {sum(1 for j in judgments if j.get('parsed'))}")
    lines.append(f"**Samples with CQS-craft:** "
                 f"{sum(1 for s in sample_cqs if s['cqs_craft'] is not None)}")
    total_cost = (sum(g.get("cost") or 0 for g in generations)
                  + sum(j.get("cost") or 0 for j in judgments))
    lines.append(f"**Total cost:** ${total_cost:.4f}")
    lines.append("")
    lines.append("## 1. Primary — CQS-craft by preamble (pooled across pool)")
    lines.append("")
    lines.append("| Preamble | n | mean | 95% CI |")
    lines.append("|----------|---|------|--------|")
    for cond in PREAMBLE_ORDER:
        vals = cqs_by_cond.get(cond, [])
        if not vals:
            lines.append(f"| `{cond}` | 0 | — | — |")
            continue
        m, lo, hi = bootstrap_ci(vals)
        lines.append(f"| `{cond}` | {len(vals)} | {m:.4f} | [{lo:.4f}, {hi:.4f}] |")
    kw = kruskal_across_conditions({c: v for c, v in cqs_by_cond.items() if c in MAIN_CONDITIONS})
    lines.append("")
    lines.append(f"**Kruskal–Wallis (main conditions, pooled):** H = {kw['H']}, p = {kw['p']}")

    lines.append("")
    lines.append("## 2. Tier stratification — CQS-craft")
    lines.append("")
    for tier in ("reasoning", "non_reasoning"):
        lines.append(f"### {tier}")
        lines.append("")
        lines.append("| Preamble | n | mean | 95% CI |")
        lines.append("|----------|---|------|--------|")
        kw_data = {}
        for cond in PREAMBLE_ORDER:
            vals = cqs_by_cond_tier.get((cond, tier), [])
            if not vals:
                lines.append(f"| `{cond}` | 0 | — | — |")
                continue
            m, lo, hi = bootstrap_ci(vals)
            lines.append(f"| `{cond}` | {len(vals)} | {m:.4f} | [{lo:.4f}, {hi:.4f}] |")
            if cond in MAIN_CONDITIONS:
                kw_data[cond] = vals
        kw_t = kruskal_across_conditions(kw_data)
        lines.append(f"\n**KW within {tier}:** H = {kw_t['H']}, p = {kw_t['p']}\n")

    lines.append("## 3. Task-category stratification — CQS-craft")
    lines.append("")
    for cat in ("creation", "refactor", "multifile_creation"):
        any_data = any(cqs_by_cond_cat.get((c, cat)) for c in PREAMBLE_ORDER)
        if not any_data:
            continue
        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| Preamble | n | mean | 95% CI |")
        lines.append("|----------|---|------|--------|")
        for cond in PREAMBLE_ORDER:
            vals = cqs_by_cond_cat.get((cond, cat), [])
            if not vals:
                lines.append(f"| `{cond}` | 0 | — | — |")
                continue
            m, lo, hi = bootstrap_ci(vals)
            lines.append(f"| `{cond}` | {len(vals)} | {m:.4f} | [{lo:.4f}, {hi:.4f}] |")
        lines.append("")

    lines.append("## 4. Per-dimension severity by preamble (cross-judge means)")
    lines.append("")
    lines.append("| Dimension | KW p |  " + "  |  ".join(PREAMBLE_ORDER) + "  |")
    lines.append("|---|---|" + "|".join(["---"] * len(PREAMBLE_ORDER)) + "|")
    for dim in RUBRIC_IDS:
        by_c = per_dim_by_cond.get(dim, {})
        kw = kruskal_across_conditions({c: v for c, v in by_c.items() if c in MAIN_CONDITIONS})
        kwp = "—" if kw["p"] is None else f"{kw['p']:.4f}"
        cells = []
        for c in PREAMBLE_ORDER:
            vals = by_c.get(c, [])
            cells.append("—" if not vals else f"{np.mean(vals):.2f} (n={len(vals)})")
        lines.append(f"| `{dim}` | {kwp} | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("## 5. F3 hygiene — self vs cross judge")
    lines.append("")
    def _f3_block(label, self_vals, cross_vals):
        s_m, _, _ = bootstrap_ci(self_vals) if self_vals else (None, None, None)
        c_m, _, _ = bootstrap_ci(cross_vals) if cross_vals else (None, None, None)
        delta = (s_m - c_m) if (s_m is not None and c_m is not None) else None
        try:
            _, p = stats.mannwhitneyu(self_vals, cross_vals, alternative="two-sided")
            p_s = f"{p:.4f}"
        except Exception:
            p_s = "—"
        lines.append(f"### {label}")
        lines.append(f"- self  : n={len(self_vals)}, mean={s_m}")
        lines.append(f"- cross : n={len(cross_vals)}, mean={c_m}")
        lines.append(f"- Δ(self − cross) = {delta}; Mann-Whitney p = {p_s}")
        lines.append("")
    _f3_block("idiomaticity", self_idioms, cross_idioms)
    _f3_block("comment_quality", self_comments, cross_comments)

    lines.append("## 6. Static analysis diagnostic panel (NOT in CQS)")
    lines.append("")
    diag_metrics = ["maintainability_index", "avg_cyclomatic", "max_cyclomatic",
                    "halstead_difficulty", "pylint_errors", "pylint_warnings",
                    "pylint_conventions", "pylint_refactor",
                    "cognitive_complexity_violations"]
    lines.append("| Metric | KW p across preambles | mean (none) | mean (real_agent) | mean (python_coder_agent) | mean (negative_control) |")
    lines.append("|---|---|---|---|---|---|")
    for mname in diag_metrics:
        by_c = {cond: static_by_cond_metric.get((cond, mname), []) for cond in MAIN_CONDITIONS}
        kw = kruskal_across_conditions(by_c)
        kwp = "—" if kw["p"] is None else f"{kw['p']:.4f}"
        def _mn(c):
            v = static_by_cond_metric.get((c, mname), [])
            return "—" if not v else f"{np.mean(v):.3f}"
        lines.append(f"| {mname} | {kwp} | {_mn('none')} | {_mn('real_agent')} | "
                     f"{_mn('python_coder_agent')} | {_mn('negative_control')} |")

    (RESULTS_DIR / "REPORT.md").write_text("\n".join(lines))


# =============================================================================
# Entrypoint
# =============================================================================
def build_jobs(slice_mode: bool) -> list[tuple]:
    if slice_mode:
        models = [REASONING_MODELS[0], NON_REASONING_MODELS[0]]
        preambles = ["none", "python_coder_agent"]
        tasks = TASKS[:1]
        reps = 1
    else:
        models = ALL_MODELS
        preambles = list(PREAMBLES.keys())
        tasks = TASKS
        reps = REPLICATIONS_DEFAULT
    jobs = []
    for task in tasks:
        for p in preambles:
            for m in models:
                for r in range(reps):
                    jobs.append((task, p, m, r))
    return jobs


async def main_async(args) -> int:
    if "OPENROUTER_API_KEY" not in os.environ:
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2

    print("=== Preamble Quality v2 — Main Run ===")
    print(f"  subjects (10): {ALL_MODELS}")
    print(f"  judges (10):   {JUDGE_MODELS}")
    print(f"  preambles ({len(PREAMBLES)}): {list(PREAMBLES.keys())}")
    print(f"  tasks ({len(TASKS)}): {[t['id'] for t in TASKS]}")
    print(f"  reps: {REPLICATIONS_DEFAULT}, slice={args.slice}, resume={args.resume}")

    # Reset persistence if not resuming
    if not args.resume:
        for f in (GEN_FILE, JUDGE_FILE, STATIC_FILE):
            if f.exists():
                f.unlink()

    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as client:
        # ---- Generation ----
        existing_gen = _load_jsonl(GEN_FILE)
        done_gen_keys = {g["key"] for g in existing_gen}
        jobs = build_jobs(args.slice)
        new_gens = await run_phase_generation(client, sem, jobs=jobs, done_keys=done_gen_keys)
        generations = _load_jsonl(GEN_FILE)
        ok = sum(1 for g in generations if g["extraction_ok"])
        print(f"  → {len(generations)} total gens; {ok} extracted ok ({new_gens} new)")

        if args.gen_only:
            return 0

        # ---- Judging ----
        existing_judge = _load_jsonl(JUDGE_FILE)
        done_jkeys = {j["jkey"] for j in existing_judge}
        new_j = await run_phase_judging(client, sem, generations, done_jkeys)
        judgments = _load_jsonl(JUDGE_FILE)
        print(f"  → {len(judgments)} total judgments ({new_j} new)")

    # ---- Static analysis (sync subprocess; no event loop needed) ----
    existing_static = _load_jsonl(STATIC_FILE)
    done_static = {s["key"] for s in existing_static}
    if not args.skip_static:
        new_s = run_phase_static(generations, done_static)
        static_records = _load_jsonl(STATIC_FILE)
        print(f"  → {len(static_records)} total static analyses ({new_s} new)")
    else:
        static_records = existing_static

    # ---- Aggregation ----
    print("\n[analyze] computing per-sample CQS-craft...")
    judg_by_gen: dict[str, list[dict]] = defaultdict(list)
    for j in judgments:
        judg_by_gen[j["gen_key"]].append(j)
    sample_cqs = []
    for g in generations:
        if not g["extraction_ok"]:
            continue
        sample_cqs.append(compute_sample_cqs(g, judg_by_gen.get(g["key"], [])))
    n_cqs = sum(1 for s in sample_cqs if s["cqs_craft"] is not None)
    print(f"  computed {n_cqs}/{len(sample_cqs)} CQS-craft scores")

    (RESULTS_DIR / "sample_cqs.json").write_text(
        json.dumps(sample_cqs, indent=2, default=str)
    )

    print("[analyze] writing report...")
    write_report(generations, judgments, static_records, sample_cqs)
    print(f"  → {RESULTS_DIR}/REPORT.md")

    print("\n=== done ===")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", action="store_true",
                        help="Small smoke-test slice (2 models × 2 preambles × 1 task × 1 rep).")
    parser.add_argument("--resume", action="store_true",
                        help="Resume — skip already-completed work in JSONL files.")
    parser.add_argument("--gen-only", action="store_true",
                        help="Stop after generation phase (no judging, no analysis).")
    parser.add_argument("--skip-static", action="store_true",
                        help="Skip static-analysis diagnostic panel.")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
