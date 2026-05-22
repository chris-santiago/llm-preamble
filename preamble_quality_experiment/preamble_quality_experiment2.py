# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai",
#   "radon",
#   "pylint",
#   "flake8",
#   "flake8-cognitive-complexity",
#   "matplotlib",
#   "scipy",
#   "numpy",
#   "statsmodels",
# ]
# ///
"""
Preamble Quality Experiment 2 — Full-scale empirical test.

Hypothesis: Expert coding preambles cause LLMs to produce measurably higher-quality
code than no/minimal preamble, detectable as a statistically significant main effect
of preamble condition after controlling for model and task variance.

Debate modifications applied vs PoC:
- F5 fix: REPLACED identifier-entropy with PEP 8 name-compliance ratio (directional)
- F6 fix: REPLACED fixed normalization ceilings with data-driven [5th, 95th] percentile bounds
- F1 embedded: Metric sensitivity probe (3 synthetic samples with known quality ordering)
- F2 embedded: persona_only + long_directive conditions added to separate priming from instruction
- F3 embedded: Full cross-judge matrix; self-vs-cross judge stratification reported
- F4 fix: 3 trivial tasks DROPPED; replaced with 6 HARD tasks (3 creation, 3 refactoring)
- Trivial baseline: always-required floor condition (temp=1.0, no system, prompt=task-name only)
- F8 fix: Full generated code saved to results JSONL (no truncation)
- Code-extraction failures: logged and counted, not silently scored 0

Deliberately omitted:
- Sensitivity analysis across prompt-temperature variations
- Human rater validation of LLM judge scores
- Cross-organization replication
- Cost-optimal model routing per task type
- Long-term consistency (single-shot experiment only)
- Retrieval-augmented preambles
- Fine-tuned baseline comparison

Run with: uv run preamble_quality_experiment2.py [--dry-run | --sanity | --full]
  --sanity: 1 model x 2 conditions x 1 task (default; fast smoke-test before full run)
  --dry-run: print job counts only, no API calls
  --full: all 8 models x 8 conditions x 6 tasks (full experiment)
"""

import argparse
import ast
import asyncio
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Optional

# Same Python interpreter so radon/pylint installed by uv are available
PYTHON = sys.executable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from openai import AsyncOpenAI
from scipy import stats

# ============================================================
# Paths
# ============================================================

EXPERIMENT_DIR = Path(__file__).parent
RESULTS_DIR = EXPERIMENT_DIR / "experiment2_results"
RESULTS_DIR.mkdir(exist_ok=True)

# ============================================================
# API configuration
# ============================================================

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONCURRENCY = 12   # async semaphore for both generation and judging
MAX_RETRIES = 4
BASE_RETRY_DELAY = 2.0   # seconds; exponential backoff
GEN_TIMEOUT = 120        # generation (hard tasks need more tokens)
JUDGE_TIMEOUT = 60

# ============================================================
# Models
# ============================================================

# All 8 models used as both subjects AND judges (full cross-judge matrix)
ALL_MODELS = [
    "deepseek/deepseek-v3.2",
    "google/gemma-4-31b-it",
    "minimax/minimax-m2.5",
    "mistralai/mistral-small-2603",
    "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-4o-mini",
    "qwen/qwen3.5-35b-a3b",
    "x-ai/grok-4.1-fast",
]

SUBJECT_MODELS = ALL_MODELS
JUDGE_MODELS = ALL_MODELS

# ============================================================
# CQS weights (from HYPOTHESIS.md)
# ============================================================

WEIGHTS = {
    "static_score": 0.45,
    "ast_score": 0.20,
    "llm_idiom_score": 0.20,
    "llm_comment_score": 0.15,
}

# ============================================================
# Preamble conditions (8 total)
# ============================================================

PREAMBLES: dict[str, Optional[str]] = {
    # --- Original 5 conditions from PoC ---
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
    # --- F2 new conditions: separate distributional priming from instruction-following ---
    # Tests whether adopting an expert persona alone (no explicit directives) shifts output
    "persona_only": (
        "You are a senior staff software engineer at a top-tier tech company."
    ),
    # Tests whether adding more behavioral constraints to real_agent amplifies the effect
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
    # --- Trivial baseline: always-required floor condition ---
    # No system prompt, prompt is only the task name, temp=1.0
    # Tests: can any preamble condition beat a completely degenerate input?
    "trivial_baseline": None,  # System prompt: None; prompt = task name only; temp=1.0
}

# Conditions to include in the main CQS analysis (excludes trivial_baseline which is floor)
MAIN_CONDITIONS = [c for c in PREAMBLES if c != "trivial_baseline"]

# Display order for plots
PREAMBLE_ORDER = [
    "trivial_baseline", "none", "negative_control", "minimal",
    "generic_coding", "persona_only", "real_agent", "long_directive",
]

PREAMBLE_LABELS = {
    "none": "None",
    "minimal": "Minimal",
    "generic_coding": "Generic Coding",
    "real_agent": "Real Agent",
    "negative_control": "Negative Control",
    "persona_only": "Persona Only",
    "long_directive": "Long Directive",
    "trivial_baseline": "Trivial Baseline",
}

CONDITION_COLORS = {
    "trivial_baseline": "#333333",
    "none": "#888888",
    "negative_control": "#9C27B0",
    "minimal": "#4CAF50",
    "generic_coding": "#2196F3",
    "persona_only": "#FF9800",
    "real_agent": "#FF5722",
    "long_directive": "#E91E63",
}

# ============================================================
# Hard coding tasks (6 total)
# ============================================================

# Task 4 "before" snippet — god function (deliberately bad, ~100 lines)
TASK4_BEFORE = '''\
import argparse
import csv
import json
import sys

def process(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--format', choices=['csv','json'], default='csv')
    p.add_argument('--filter-col', default=None)
    p.add_argument('--filter-val', default=None)
    p.add_argument('--transform', choices=['upper','lower','strip'], default=None)
    args = p.parse_args(argv)

    rows = []
    if args.format == 'csv':
        with open(args.input, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if args.filter_col and args.filter_val:
                    if row.get(args.filter_col) != args.filter_val:
                        continue
                if args.transform:
                    for k in row:
                        if args.transform == 'upper':
                            row[k] = row[k].upper()
                        elif args.transform == 'lower':
                            row[k] = row[k].lower()
                        elif args.transform == 'strip':
                            row[k] = row[k].strip()
                rows.append(row)
    elif args.format == 'json':
        with open(args.input) as f:
            data = json.load(f)
        for row in data:
            if args.filter_col and args.filter_val:
                if str(row.get(args.filter_col)) != args.filter_val:
                    continue
            if args.transform:
                for k in row:
                    if isinstance(row[k], str):
                        if args.transform == 'upper':
                            row[k] = row[k].upper()
                        elif args.transform == 'lower':
                            row[k] = row[k].lower()
                        elif args.transform == 'strip':
                            row[k] = row[k].strip()
            rows.append(row)

    if not rows:
        print("No rows after filtering.", file=sys.stderr)
        sys.exit(1)

    if args.output.endswith('.csv'):
        with open(args.output, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    elif args.output.endswith('.json'):
        with open(args.output, 'w') as f:
            json.dump(rows, f, indent=2)
    else:
        print("Unknown output format.", file=sys.stderr)
        sys.exit(1)

    print(f"Wrote {len(rows)} rows to {args.output}")

if __name__ == '__main__':
    process()
'''

# Task 5 "before" snippet — boolean flag hell + global state (~90 lines)
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

# Task 6 "before" snippet — nested try/except pyramid with swallowed exceptions (~80 lines)
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
    # ---- Hard Creation Tasks ----
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
        "id": "task_async_conn_pool",
        "name": "Async connection pool with health-check and exponential backoff",
        "category": "creation",
        "prompt": (
            "Write a Python async connection pool using asyncio.\n"
            "Requirements:\n"
            "- Max pool size: configurable; pool blocks (does not expand) when exhausted\n"
            "- acquire(): returns a connection; if pool is exhausted, waits with "
            "  exponential backoff + full jitter (not fixed sleep) up to a configurable timeout\n"
            "- release(conn): returns connection to pool\n"
            "- Health check on acquire: if a connection fails the health check, "
            "  discard it and create a new one (up to max_size connections total)\n"
            "- async context manager support (async with pool.acquire() as conn:)\n"
            "- Connection factory: user supplies an async callable that creates a connection\n"
            "- Health checker: user supplies an async callable that returns True if healthy\n"
            "Use asyncio.Queue or equivalent for the pool store. "
            "Include type hints. Include a brief usage example."
        ),
    },
    # ---- Hard Refactoring Tasks ----
    {
        "id": "task_god_function",
        "name": "Refactor god function: separate CLI, I/O, and business logic",
        "category": "refactor",
        "prompt": (
            "Refactor the following Python code. It mixes CLI argument parsing, "
            "file I/O (CSV and JSON input/output), filtering logic, and string transformation "
            "in a single monolithic function. Separate these into cohesive units "
            "with clear boundaries and single responsibilities.\n\n"
            "Requirements:\n"
            "- CLI parsing must be in its own unit\n"
            "- File I/O (reading inputs, writing outputs) must be in its own unit\n"
            "- Filtering and transformation must be in their own unit(s)\n"
            "- The main orchestrator must be thin\n"
            "- Preserve all existing CLI flags and behavior exactly\n"
            "- Add type hints where missing\n"
            "- Improve error messages and exit codes where appropriate\n\n"
            f"```python\n{TASK4_BEFORE}```\n\n"
            "Return the refactored code in a single ```python ... ``` block."
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
]

# Trivial baseline prompt: only the task name
TRIVIAL_BASELINE_PROMPTS = {t["id"]: t["name"] for t in TASKS}

# ============================================================
# Synthetic samples for F1 metric sensitivity probe
# ============================================================

# Three hand-written samples with a known quality ordering:
# POOR < AVERAGE < EXCELLENT
# CQS range >= 0.10 → metric can see quality (refutes critique)
# CQS range < 0.05 → metric is blind (confirms critique)
# 0.05–0.10 → ambiguous

SYNTHETIC_POOR = '''\
def calc(x, y, z):
    # do the thing
    try:
        r = x + y
        r2 = r * z
        try:
            if r2 == 0:
                return 0
            else:
                return r / r2
        except:
            pass
    except:
        pass
    return -1
'''

SYNTHETIC_AVERAGE = '''\
import threading
from collections import OrderedDict


class SimpleCache:
    """Basic LRU cache, not thread-safe."""

    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
'''

SYNTHETIC_EXCELLENT = '''\
"""Thread-safe LRU cache with per-entry TTL using a min-heap for expiry tracking."""

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class _Entry:
    value: Any
    expires_at: float  # monotonic clock


class TTLLRUCache:
    """Thread-safe LRU cache with per-entry TTL expiry.

    Eviction policy: least-recently-used among non-expired entries.
    Expired entries are reaped lazily on access.

    Args:
        capacity: Maximum number of live entries.
        default_ttl: Default TTL in seconds if not specified per entry.
    """

    def __init__(self, capacity: int, default_ttl: float = 60.0) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Return cached value, or None if absent or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() >= entry.expires_at:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return entry.value

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a value with an optional TTL override."""
        ttl = ttl if ttl is not None else self._default_ttl
        if ttl <= 0:
            raise ValueError(f"ttl must be positive, got {ttl}")
        expires_at = time.monotonic() + ttl
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = _Entry(value=value, expires_at=expires_at)
            self._evict_if_needed()

    def size(self) -> int:
        """Return count of non-expired entries."""
        now = time.monotonic()
        with self._lock:
            expired = [k for k, e in self._store.items() if now >= e.expires_at]
            for k in expired:
                del self._store[k]
            return len(self._store)

    def _evict_if_needed(self) -> None:
        """Evict LRU entry if over capacity. Must be called with lock held."""
        while len(self._store) > self._capacity:
            self._store.popitem(last=False)
'''

SENSITIVITY_SAMPLES = [
    ("poor", SYNTHETIC_POOR),
    ("average", SYNTHETIC_AVERAGE),
    ("excellent", SYNTHETIC_EXCELLENT),
]

# ============================================================
# API key
# ============================================================


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment")
    return key


# ============================================================
# Async LLM dispatcher
# ============================================================


async def _call_one(
    client: AsyncOpenAI,
    sem: asyncio.Semaphore,
    model: str,
    system_prompt: Optional[str],
    user_msg: str,
    label: str,
    temperature: float = 0.3,
    max_tokens: int = 3000,
    timeout: float = GEN_TIMEOUT,
) -> tuple[str, Optional[str]]:
    """Single async LLM call with exponential backoff retry.

    Returns (text, error_or_None).
    """
    messages: list[dict] = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_msg})

    last_err: Optional[str] = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with sem:
                resp = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout,
                )
            text = resp.choices[0].message.content or ""
            return text, None
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_RETRIES:
                delay = BASE_RETRY_DELAY * (2.0 ** attempt)
                await asyncio.sleep(delay)
                continue
    return "", last_err or "Exhausted retries"


# ============================================================
# Code extraction (robust — handles missing fences, prose wrap)
# ============================================================


def extract_python_code(text: str) -> tuple[str, str]:
    """Extract Python code from LLM response.

    Returns (code, extraction_method) where extraction_method indicates
    how the code was extracted.
    """
    text = text.strip()
    if not text:
        return "", "empty_response"

    # 1. Try ```python ... ``` fence
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip(), "python_fence"

    # 2. Try generic ``` ... ``` fence
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        if any(kw in candidate for kw in ("def ", "class ", "import ", "return ", "async ")):
            return candidate, "generic_fence"

    # 3. Prose-wrapped: look for contiguous lines that look like Python code
    lines = text.splitlines()
    code_lines = []
    in_code = False
    for line in lines:
        stripped = line.rstrip()
        if any(kw in stripped for kw in ("def ", "class ", "import ", "async def ")):
            in_code = True
        if in_code:
            code_lines.append(line)

    if code_lines:
        candidate = "\n".join(code_lines).strip()
        if len(candidate) > 50:
            return candidate, "prose_extract"

    # 4. Fallback: return full text if it looks like code
    if any(kw in text for kw in ("def ", "class ", "import ")):
        return text.strip(), "full_text_fallback"

    return "", "extraction_failed"


# ============================================================
# PEP 8 name-compliance ratio (F5 fix — replaces identifier entropy)
# ============================================================

# Conventional loop counters: single-letter names that are acceptable per PEP 8
CONVENTIONAL_SINGLE_LETTER = frozenset("ijkn_")


def compute_pep8_name_compliance(tree: ast.AST) -> float:
    """Compute PEP 8 name-compliance ratio.

    Rules enforced:
    - Function/method names: must be snake_case (all lower, underscores allowed)
    - Variable/argument names: must be snake_case
    - Class names: must be CapWords (no underscores, starts with uppercase)
    - Single-letter names: only conventional loop counters (i, j, k, n, _) are allowed;
      all other single-letter names are violations

    Returns proportion of checked identifiers that pass, in [0, 1].
    Higher = better PEP 8 compliance.
    """
    violations = 0
    total = 0

    def is_snake_case(name: str) -> bool:
        return name == name.lower() and not name.startswith("__")

    def is_capwords(name: str) -> bool:
        # CapWords: starts with uppercase, no underscores (except dunder)
        return (
            len(name) > 0
            and name[0].isupper()
            and "_" not in name
        )

    for node in ast.walk(tree):
        # Function/method names
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if name.startswith("__") and name.endswith("__"):
                continue  # dunder methods exempt
            total += 1
            if len(name) == 1 and name not in CONVENTIONAL_SINGLE_LETTER:
                violations += 1
            elif not is_snake_case(name):
                violations += 1

        # Class names
        elif isinstance(node, ast.ClassDef):
            name = node.name
            total += 1
            if not is_capwords(name):
                violations += 1

        # Variable assignments (simple Name targets only)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if name == "_" or (name.startswith("__") and name.endswith("__")):
                        continue
                    total += 1
                    if len(name) == 1 and name not in CONVENTIONAL_SINGLE_LETTER:
                        violations += 1
                    elif not is_snake_case(name):
                        violations += 1

        # Function/method arguments
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pass  # handled above via args loop below

    # Also check function arguments separately (not caught by FunctionDef walk above)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                name = arg.arg
                if name in ("self", "cls"):
                    continue
                total += 1
                if len(name) == 1 and name not in CONVENTIONAL_SINGLE_LETTER:
                    violations += 1
                elif not is_snake_case(name):
                    violations += 1

    if total == 0:
        return 0.5  # no identifiers to check → neutral
    return 1.0 - (violations / total)


# ============================================================
# Static analysis
# ============================================================


def compute_static_metrics(code: str) -> dict:
    """Run radon + pylint + AST analysis on a code snippet.

    Returns raw metrics. Normalization is deferred until the full generation
    distribution is available (for F6 data-driven percentile bounds).
    """
    metrics: dict = {}

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        # --- Radon: cyclomatic complexity ---
        result = subprocess.run(
            [PYTHON, "-m", "radon", "cc", "--json", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        complexities: list[float] = []
        if result.returncode == 0 and result.stdout.strip():
            try:
                cc_data = json.loads(result.stdout)
                for file_results in cc_data.values():
                    if not isinstance(file_results, list):
                        continue
                    for item in file_results:
                        if isinstance(item, dict):
                            complexities.append(float(item.get("complexity", 1)))
                            for method in item.get("methods", []):
                                if isinstance(method, dict):
                                    complexities.append(float(method.get("complexity", 1)))
            except (json.JSONDecodeError, TypeError):
                pass
        avg_cc = float(np.mean(complexities)) if complexities else 1.0
        max_cc = float(max(complexities)) if complexities else 1.0
        metrics["avg_cyclomatic"] = avg_cc
        metrics["max_cyclomatic"] = max_cc

        # --- Radon: maintainability index ---
        result = subprocess.run(
            [PYTHON, "-m", "radon", "mi", "--json", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        mi_score = 50.0
        if result.returncode == 0 and result.stdout.strip():
            try:
                mi_data = json.loads(result.stdout)
                for file_data in mi_data.values():
                    mi_score = float(file_data.get("mi", 50.0))
                    break
            except (json.JSONDecodeError, TypeError):
                pass
        metrics["maintainability_index"] = mi_score

        # --- Radon: Halstead metrics ---
        result = subprocess.run(
            [PYTHON, "-m", "radon", "hal", "--json", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        hal_volume = 0.0
        hal_difficulty = 0.0
        if result.returncode == 0 and result.stdout.strip():
            try:
                hal_data = json.loads(result.stdout)
                for file_data in hal_data.values():
                    if isinstance(file_data, dict):
                        total_section = file_data.get("total", file_data)
                        hal_volume = float(total_section.get("volume", 0.0) or 0.0)
                        hal_difficulty = float(total_section.get("difficulty", 0.0) or 0.0)
                    break
            except (json.JSONDecodeError, TypeError):
                pass
        metrics["halstead_volume"] = hal_volume
        metrics["halstead_difficulty"] = hal_difficulty

        # --- Pylint: message count by severity ---
        result = subprocess.run(
            [PYTHON, "-m", "pylint", "--output-format=json", "--disable=all",
             "--enable=E,W,C,R", tmp_path],
            capture_output=True, text=True, timeout=15,
        )
        pylint_counts: dict[str, int] = {"E": 0, "W": 0, "C": 0, "R": 0}
        if result.stdout.strip():
            try:
                messages = json.loads(result.stdout)
                for msg in messages:
                    cat = msg.get("type", "")[:1].upper()
                    if cat in pylint_counts:
                        pylint_counts[cat] += 1
            except (json.JSONDecodeError, TypeError):
                pass
        metrics["pylint_errors"] = pylint_counts["E"]
        metrics["pylint_warnings"] = pylint_counts["W"]
        metrics["pylint_conventions"] = pylint_counts["C"]
        metrics["pylint_refactor"] = pylint_counts["R"]

        # --- flake8-cognitive-complexity ---
        result = subprocess.run(
            [PYTHON, "-m", "flake8", "--select=CCR001",
             "--max-cognitive-complexity=30",
             "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
             tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        cog_violations = len([ln for ln in result.stdout.splitlines() if "CCR001" in ln])
        metrics["cognitive_complexity_violations"] = cog_violations

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # --- AST analysis (in-process) ---
    ast_metrics = compute_ast_metrics(code)
    metrics.update(ast_metrics)

    return metrics


def compute_ast_metrics(code: str) -> dict:
    """AST-based code quality metrics.

    F5 fix: identifier_entropy REPLACED by pep8_name_compliance_ratio (directional).
    """
    metrics: dict = {
        "bare_except_count": 0,
        "pep8_name_compliance": 0.5,    # F5: replaces identifier_entropy
        "max_nesting_depth": 0,
        "has_type_hints": False,
        "class_count": 0,
        "function_count": 0,
        # raw sub-scores (pre-normalization)
        "ast_bare_except_raw": 0,
        "ast_nesting_raw": 0,
        "ast_score_raw": 0.5,
    }

    try:
        tree = ast.parse(code)
    except SyntaxError:
        metrics["ast_score_raw"] = 0.0
        return metrics

    # Bare except count
    bare_excepts = sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.type is None
    )
    metrics["bare_except_count"] = bare_excepts
    metrics["ast_bare_except_raw"] = bare_excepts

    # PEP 8 name compliance ratio (F5 fix — directional, not bidirectional)
    pep8_ratio = compute_pep8_name_compliance(tree)
    metrics["pep8_name_compliance"] = round(pep8_ratio, 4)

    # Max nesting depth
    nesting = _compute_max_nesting(tree)
    metrics["max_nesting_depth"] = nesting
    metrics["ast_nesting_raw"] = nesting

    # Type hints presence
    has_hints = any(
        (node.returns is not None
         or any(a.annotation is not None for a in node.args.args))
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    metrics["has_type_hints"] = has_hints

    # Counts
    metrics["class_count"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    metrics["function_count"] = sum(
        1 for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )

    # ast_score_raw: raw sub-score before data-driven normalization
    # Components:
    #   - pep8_name_compliance (higher = better, already in [0,1])
    #   - bare_except_penalty (lower bare_excepts = better)
    #   - nesting_penalty (lower nesting = better)
    #   - type_hints bonus
    bare_except_penalty = min(bare_excepts / 3.0, 1.0)
    nesting_penalty = min(nesting / 8.0, 1.0)
    hints_bonus = 0.1 if has_hints else 0.0

    ast_score_raw = (
        0.35 * pep8_ratio +                     # F5 fix: directional naming quality
        0.30 * (1.0 - bare_except_penalty) +
        0.25 * (1.0 - nesting_penalty) +
        0.10 * (1.0 + hints_bonus)
    )
    metrics["ast_score_raw"] = round(min(ast_score_raw, 1.0), 4)
    return metrics


def _compute_max_nesting(tree: ast.AST) -> int:
    """Compute maximum nesting depth of control structures."""
    NESTING_NODES = (
        ast.If, ast.For, ast.While, ast.With, ast.Try,
        ast.ExceptHandler, ast.AsyncFor, ast.AsyncWith,
    )

    def depth(node: ast.AST, current: int = 0) -> int:
        max_d = current
        for child in ast.iter_child_nodes(node):
            if isinstance(child, NESTING_NODES):
                max_d = max(max_d, depth(child, current + 1))
            else:
                max_d = max(max_d, depth(child, current))
        return max_d

    return depth(tree)


# ============================================================
# Data-driven normalization (F6 fix)
# ============================================================


def compute_percentile_bounds(
    all_metrics: list[dict],
    metric_keys: list[str],
    p_low: float = 5.0,
    p_high: float = 95.0,
) -> dict[str, tuple[float, float]]:
    """Compute [p_low, p_high] percentile bounds across the full generation distribution.

    F6 fix: replaces fixed ceilings (CC/20, difficulty/50, pylint_penalty/20, etc.)
    with data-driven bounds computed from the actual run's metric distribution.
    """
    bounds: dict[str, tuple[float, float]] = {}
    for key in metric_keys:
        vals = [m[key] for m in all_metrics if key in m and m[key] is not None]
        if len(vals) < 2:
            bounds[key] = (0.0, 1.0)
            continue
        lo = float(np.percentile(vals, p_low))
        hi = float(np.percentile(vals, p_high))
        if hi <= lo:
            hi = lo + 1e-6  # prevent division by zero
        bounds[key] = (lo, hi)
    return bounds


def normalize_with_bounds(
    value: float,
    lo: float,
    hi: float,
    higher_is_better: bool = True,
) -> float:
    """Clip and normalize value to [0,1] using provided bounds."""
    clamped = max(lo, min(hi, value))
    normalized = (clamped - lo) / (hi - lo)
    if not higher_is_better:
        normalized = 1.0 - normalized
    return round(normalized, 4)


def compute_static_score_normalized(metrics: dict, bounds: dict) -> float:
    """Compute static_score using data-driven [5th,95th] percentile normalization.

    F6 fix: all fixed ceilings replaced by data-driven bounds.
    """
    mi_norm = normalize_with_bounds(
        metrics["maintainability_index"],
        *bounds.get("maintainability_index", (0.0, 100.0)),
        higher_is_better=True,
    )
    cc_norm = normalize_with_bounds(
        metrics["avg_cyclomatic"],
        *bounds.get("avg_cyclomatic", (1.0, 20.0)),
        higher_is_better=False,  # lower complexity = better
    )
    hal_diff_norm = normalize_with_bounds(
        metrics["halstead_difficulty"],
        *bounds.get("halstead_difficulty", (0.0, 50.0)),
        higher_is_better=False,
    )
    pylint_penalty = (
        metrics["pylint_errors"] * 1.0
        + metrics["pylint_warnings"] * 0.5
        + metrics["pylint_conventions"] * 0.2
        + metrics["pylint_refactor"] * 0.3
    )
    pylint_norm = normalize_with_bounds(
        pylint_penalty,
        *bounds.get("pylint_penalty", (0.0, 20.0)),
        higher_is_better=False,
    )
    cog_norm = normalize_with_bounds(
        float(metrics["cognitive_complexity_violations"]),
        *bounds.get("cognitive_complexity_violations", (0.0, 5.0)),
        higher_is_better=False,
    )

    static_score = (
        0.30 * mi_norm
        + 0.25 * cc_norm
        + 0.20 * hal_diff_norm
        + 0.15 * pylint_norm
        + 0.10 * cog_norm
    )
    return round(static_score, 4)


def compute_ast_score_normalized(metrics: dict, bounds: dict) -> float:
    """Compute ast_score using data-driven normalization (F6 fix)."""
    pep8_norm = metrics["pep8_name_compliance"]  # already in [0,1]; higher = better

    bare_except_norm = normalize_with_bounds(
        float(metrics["bare_except_count"]),
        *bounds.get("bare_except_count", (0.0, 3.0)),
        higher_is_better=False,
    )
    nesting_norm = normalize_with_bounds(
        float(metrics["max_nesting_depth"]),
        *bounds.get("max_nesting_depth", (0.0, 8.0)),
        higher_is_better=False,
    )
    hints_bonus = 0.1 if metrics["has_type_hints"] else 0.0

    ast_score = (
        0.35 * pep8_norm
        + 0.30 * bare_except_norm
        + 0.25 * nesting_norm
        + 0.10 * (1.0 + hints_bonus)
    )
    return round(min(ast_score, 1.0), 4)


# ============================================================
# LLM-as-judge
# ============================================================

JUDGE_SYSTEM_PROMPT = """You are a senior Python code reviewer evaluating code quality on two specific dimensions.

Your task: score the provided Python code on a 1-10 scale for each dimension.

IDIOMATICITY (1-10):
- 10: Exemplary Python — uses built-ins and stdlib perfectly, follows PEP8 philosophy, reads like well-known open source
- 7-9: Clearly idiomatic — recognizable Python patterns, occasional stylistic gap
- 4-6: Mixed — some idiomatic sections, some awkward or verbose patterns
- 1-3: Non-idiomatic — Java/C-style Python, verbose where Python has clean idioms

COMMENT QUALITY (1-10):
- 10: Comments explain *why* and add genuine insight; zero redundant comments
- 7-9: Mostly explains why, occasional what-comment, no noise
- 4-6: Mix of why and what; some redundant; some missing where needed
- 1-3: Comments only describe what the code does (readable from code itself), or are absent where needed

Respond in JSON only:
{"idiomaticity": <int 1-10>, "comment_quality": <int 1-10>, "idiomaticity_rationale": "<1 sentence>", "comment_quality_rationale": "<1 sentence>"}"""


def _extract_json_safe(text: str) -> Optional[dict]:
    """Robustly extract a JSON object from LLM text output."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try JSON fence
    m = re.search(r"```(?:json)?\s*\n(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try brace extraction
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except json.JSONDecodeError:
            pass
    return None


# ============================================================
# CQS computation
# ============================================================


def compute_cqs(
    static_score: float,
    ast_score: float,
    judge_scores: list[dict],
) -> dict:
    """Compute Composite Quality Score from normalized component scores."""
    valid_idiom = [
        j["idiomaticity"] / 10.0
        for j in judge_scores
        if j.get("idiomaticity") is not None
    ]
    valid_comment = [
        j["comment_quality"] / 10.0
        for j in judge_scores
        if j.get("comment_quality") is not None
    ]

    llm_idiom_score = float(np.mean(valid_idiom)) if valid_idiom else 0.5
    llm_comment_score = float(np.mean(valid_comment)) if valid_comment else 0.5

    cqs = (
        WEIGHTS["static_score"] * static_score
        + WEIGHTS["ast_score"] * ast_score
        + WEIGHTS["llm_idiom_score"] * llm_idiom_score
        + WEIGHTS["llm_comment_score"] * llm_comment_score
    )
    return {
        "cqs": round(cqs, 4),
        "static_score": round(static_score, 4),
        "ast_score": round(ast_score, 4),
        "llm_idiom_score": round(llm_idiom_score, 4),
        "llm_comment_score": round(llm_comment_score, 4),
    }


# ============================================================
# Statistics
# ============================================================


def bootstrap_ci(
    values: list[float],
    n_boot: int = 1000,
    ci: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval."""
    if len(values) < 2:
        v = values[0] if values else 0.0
        return float(v), float(v)
    rng = rng or np.random.default_rng(42)
    arr = np.array(values)
    boot_means = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    alpha = 1.0 - ci
    lo = float(np.percentile(boot_means, 100 * alpha / 2))
    hi = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return lo, hi


def compute_spearman_rank_stability(
    per_model_cqs: dict[str, dict[str, float]],
    condition_order: list[str],
) -> float:
    """Mean pairwise Spearman rho of preamble condition rankings across models."""
    model_ranks = []
    for model, cqs_by_preamble in per_model_cqs.items():
        scores = [cqs_by_preamble.get(p, 0.0) for p in condition_order]
        if all(s == scores[0] for s in scores):
            continue  # skip degenerate (all-same) rank vectors
        model_ranks.append(stats.rankdata(scores))

    if len(model_ranks) < 2:
        return 0.0

    rhos = []
    for i in range(len(model_ranks)):
        for j in range(i + 1, len(model_ranks)):
            rho, _ = stats.spearmanr(model_ranks[i], model_ranks[j])
            if not math.isnan(rho):
                rhos.append(rho)
    return float(np.mean(rhos)) if rhos else 0.0


def run_mixed_effects_model(full_results: list[dict]) -> dict:
    """Run CQS ~ preamble_condition + (1|model) + (1|task) mixed-effects model.

    Uses statsmodels MixedLM. Falls back gracefully if convergence fails.
    Returns dict of results including fixed effects and fit diagnostics.
    """
    try:
        import pandas as pd
        from statsmodels.formula.api import mixedlm
    except ImportError:
        return {"error": "statsmodels or pandas not available"}

    # Restrict to main conditions: trivial_baseline is excluded from the model
    # (it is a degenerate floor, not a preamble condition). Including it would
    # produce NaN categoricals — categories=MAIN_CONDITIONS — while groups still
    # carried every row, causing a design-matrix/groups length mismatch.
    rows = [
        {
            "cqs": r["cqs"],
            "preamble": r["preamble"],
            "model": r["model"],
            "task_id": r["task_id"],
        }
        for r in full_results
        if r.get("cqs") is not None and r["preamble"] in MAIN_CONDITIONS
    ]
    if len(rows) < 20:
        return {"error": f"Too few observations: {len(rows)}"}

    df = pd.DataFrame(rows)
    # Preamble as categorical; "none" as reference level
    df["preamble"] = pd.Categorical(df["preamble"], categories=MAIN_CONDITIONS)
    # Simple random effects: group by model
    try:
        model = mixedlm("cqs ~ C(preamble, Treatment(reference='none'))",
                         df, groups=df["model"])
        result = model.fit(reml=True, method="lbfgs")
        fe = {k: {"coef": float(v), "pval": float(result.pvalues[k])}
              for k, v in result.fe_params.items()}
        return {
            "aic": float(result.aic),
            "bic": float(result.bic),
            "llf": float(result.llf),
            "fixed_effects": fe,
            "n_obs": len(df),
            "converged": True,
        }
    except Exception as exc:
        return {"error": str(exc), "converged": False}


# ============================================================
# F1 metric sensitivity probe
# ============================================================


def run_sensitivity_probe(experiment_bounds: dict) -> dict:
    """Score the 3 synthetic samples (poor / average / excellent) with CQS.

    Uses static metrics only (no LLM judging) for speed and reproducibility.

    Bounds: the probe computes its own internal bounds from the 3 synthetic
    samples (not from experiment_bounds). This avoids the degenerate-bounds
    problem when run_sensitivity_probe is called before the full generation
    distribution exists (e.g. sanity mode). experiment_bounds is retained as
    a parameter for API compatibility but is NOT used for scoring here.

    Returns probe result dict including verdict.
    """
    print("\n[F1-PROBE] Running metric sensitivity probe on 3 synthetic samples...")

    # Collect raw metrics for all 3 samples
    raw_metrics_list: list[dict] = []
    for label, code in SENSITIVITY_SAMPLES:
        metrics = compute_static_metrics(code)
        metrics["pylint_penalty"] = (
            metrics["pylint_errors"] * 1.0
            + metrics["pylint_warnings"] * 0.5
            + metrics["pylint_conventions"] * 0.2
            + metrics["pylint_refactor"] * 0.3
        )
        raw_metrics_list.append(metrics)

    # Compute probe-specific bounds from the 3 samples themselves.
    # Use p_low=0, p_high=100 so min/max of the 3 samples define the range,
    # giving maximum sensitivity for the ordering test.
    probe_bound_keys = [
        "maintainability_index", "avg_cyclomatic", "halstead_difficulty",
        "pylint_penalty", "cognitive_complexity_violations",
        "bare_except_count", "max_nesting_depth",
    ]
    probe_bounds = compute_percentile_bounds(raw_metrics_list, probe_bound_keys, p_low=0, p_high=100)

    sample_scores: list[tuple[str, float]] = []
    for (label, _code), metrics in zip(SENSITIVITY_SAMPLES, raw_metrics_list):
        static_score = compute_static_score_normalized(metrics, probe_bounds)
        ast_score = compute_ast_score_normalized(metrics, probe_bounds)
        # Use neutral LLM scores (0.5) so only static+AST components are tested
        cqs_dict = compute_cqs(static_score, ast_score, [])
        cqs = cqs_dict["cqs"]
        print(f"  [{label}] static={static_score:.3f} ast={ast_score:.3f} cqs={cqs:.3f}")
        sample_scores.append((label, cqs))

    poor_cqs = next(s for lbl, s in sample_scores if lbl == "poor")
    avg_cqs = next(s for lbl, s in sample_scores if lbl == "average")
    exc_cqs = next(s for lbl, s in sample_scores if lbl == "excellent")

    cqs_range = exc_cqs - poor_cqs
    order_preserved = poor_cqs < avg_cqs < exc_cqs

    # Order dominates range: a metric that mis-ranks known-quality samples
    # (e.g. excellent < average) is not validly measuring quality, however
    # wide its numeric spread. This directly tests F1's mechanism — static
    # metrics that reward simplicity will score sophisticated "excellent" code
    # below simpler "average" code.
    if not order_preserved:
        verdict = "confirms_critique"
        verdict_text = (
            f"Order VIOLATED (poor={poor_cqs:.3f}, avg={avg_cqs:.3f}, "
            f"exc={exc_cqs:.3f}): metric mis-ranks quality direction"
        )
    elif cqs_range >= 0.10:
        verdict = "refutes_critique"
        verdict_text = f"Order preserved and range={cqs_range:.3f} >= 0.10: metric is sensitive to quality"
    elif cqs_range < 0.05:
        verdict = "confirms_critique"
        verdict_text = f"CQS range={cqs_range:.3f} < 0.05: metric cannot distinguish quality levels"
    else:
        verdict = "ambiguous"
        verdict_text = f"Order preserved but range={cqs_range:.3f} in [0.05, 0.10): partial sensitivity"

    print(f"  [F1-PROBE] Range={cqs_range:.3f}, Order={'preserved' if order_preserved else 'VIOLATED'}")
    print(f"  [F1-PROBE] Verdict: {verdict_text}")

    return {
        "poor_cqs": round(poor_cqs, 4),
        "average_cqs": round(avg_cqs, 4),
        "excellent_cqs": round(exc_cqs, 4),
        "cqs_range": round(cqs_range, 4),
        "order_preserved": order_preserved,
        "verdict": verdict,
        "verdict_text": verdict_text,
    }


# ============================================================
# F3 self-preference stratification
# ============================================================


def compute_self_preference_stratification(judge_records: list[dict]) -> dict:
    """Stratify LLM judge scores by judge_model == subject_model vs !=.

    F3 empirical test: detects and quantifies self-preference bias.
    Returns mean scores and Cohen's d effect size for idiomaticity.
    """
    self_judge: list[float] = []
    cross_judge: list[float] = []

    for rec in judge_records:
        idiom = rec.get("idiomaticity")
        if idiom is None:
            continue
        if rec["judge_model"] == rec["subject_model"]:
            self_judge.append(float(idiom))
        else:
            cross_judge.append(float(idiom))

    if not self_judge or not cross_judge:
        return {
            "self_judge_n": len(self_judge),
            "cross_judge_n": len(cross_judge),
            "self_judge_mean_idiom": None,
            "cross_judge_mean_idiom": None,
            "delta": None,
            "cohen_d": None,
            "p_value_mannwhitney": None,
            "verdict": "insufficient_data",
        }

    self_mean = float(np.mean(self_judge))
    cross_mean = float(np.mean(cross_judge))
    delta = self_mean - cross_mean

    # Cohen's d
    pooled_std = float(np.sqrt(
        (np.std(self_judge, ddof=1) ** 2 + np.std(cross_judge, ddof=1) ** 2) / 2
    )) if len(self_judge) > 1 and len(cross_judge) > 1 else 0.0
    cohen_d = delta / pooled_std if pooled_std > 0 else 0.0

    # Mann-Whitney U test (non-parametric)
    u_stat, p_val = stats.mannwhitneyu(self_judge, cross_judge, alternative="two-sided")

    # Verdict: bias confirmed if |delta| > 0.5 points and p < 0.05
    if abs(delta) > 0.5 and p_val < 0.05:
        verdict = "self_preference_confirmed"
    elif p_val > 0.05:
        verdict = "no_significant_bias"
    else:
        verdict = "marginal_bias"

    return {
        "self_judge_n": len(self_judge),
        "cross_judge_n": len(cross_judge),
        "self_judge_mean_idiom": round(self_mean, 4),
        "cross_judge_mean_idiom": round(cross_mean, 4),
        "delta": round(delta, 4),
        "cohen_d": round(cohen_d, 4),
        "p_value_mannwhitney": round(p_val, 6),
        "verdict": verdict,
    }


# ============================================================
# Generation pipeline
# ============================================================


async def run_code_generation_batch(
    tasks: list[dict],
    preambles: dict[str, Optional[str]],
    subject_models: list[str],
    client: AsyncOpenAI,
    dry_run: bool = False,
) -> list[dict]:
    """Generate code for all (task, preamble, model) combinations."""
    sem = asyncio.Semaphore(CONCURRENCY)
    jobs = []
    for task in tasks:
        for preamble_name, preamble_text in preambles.items():
            for model in subject_models:
                jobs.append((task, preamble_name, preamble_text, model))

    print(f"[generation] {len(jobs)} generation calls queued...")
    if dry_run:
        print("[dry-run] Skipping API calls.")
        return []

    extraction_failures: list[dict] = []

    async def dispatch(task: dict, pname: str, ptext: Optional[str], model: str) -> dict:
        # Trivial baseline: prompt = task name only, temp=1.0
        if pname == "trivial_baseline":
            user_msg = task["name"]
            temp = 1.0
        else:
            user_msg = task["prompt"]
            temp = 0.3

        text, err = await _call_one(
            client, sem, model, ptext, user_msg,
            label=f"{task['id']}|{pname}|{model}",
            temperature=temp,
            max_tokens=3000,
            timeout=GEN_TIMEOUT,
        )
        code, extraction_method = extract_python_code(text)
        if extraction_method == "extraction_failed":
            extraction_failures.append({
                "task_id": task["id"],
                "preamble": pname,
                "model": model,
                "raw_response_preview": text[:300],
            })
        return {
            "task_id": task["id"],
            "preamble": pname,
            "model": model,
            "code": code,
            "raw_response": text,    # Full response saved (F8 fix)
            "extraction_method": extraction_method,
            "error": err,
        }

    results = await asyncio.gather(*[dispatch(*j) for j in jobs])
    results_list = list(results)

    # Report extraction failures
    if extraction_failures:
        print(f"\n[WARNING] {len(extraction_failures)} code extraction failures (logged, not scored 0):")
        for f_item in extraction_failures[:5]:
            print(f"  {f_item['task_id']}|{f_item['preamble']}|{f_item['model']}")
        failures_path = RESULTS_DIR / "extraction_failures.jsonl"
        with open(failures_path, "a") as fh:
            for f_item in extraction_failures:
                fh.write(json.dumps(f_item) + "\n")

    ok = sum(1 for r in results_list if r["code"] and not r["error"])
    fail = sum(1 for r in results_list if r["error"])
    extr_fail = sum(1 for r in results_list if r["extraction_method"] == "extraction_failed")
    print(f"[generation] Done: {ok} ok, {fail} API errors, {extr_fail} extraction failures")
    return results_list


async def run_llm_judge_batch(
    generation_results: list[dict],
    judge_models: list[str],
    client: AsyncOpenAI,
    dry_run: bool = False,
) -> list[dict]:
    """Run full cross-judge matrix: every sample judged by every judge model."""
    sem = asyncio.Semaphore(CONCURRENCY)

    # Only judge samples with valid extracted code
    valid = [r for r in generation_results if r["code"] and not r["error"]
             and r["extraction_method"] != "extraction_failed"]

    jobs = [
        (gen_result, judge_model)
        for gen_result in valid
        for judge_model in judge_models
    ]
    print(f"[judging] {len(jobs)} judge calls queued (cross-judge matrix)...")
    if dry_run:
        print("[dry-run] Skipping judge API calls.")
        return []

    async def judge_one(gen_result: dict, judge_model: str) -> dict:
        code = gen_result["code"]
        user_msg = f"Please evaluate this Python code:\n\n```python\n{code}\n```"
        text, err = await _call_one(
            client, sem, judge_model,
            JUDGE_SYSTEM_PROMPT, user_msg,
            label=f"judge|{gen_result['task_id']}|{gen_result['preamble']}|{gen_result['model']}|{judge_model}",
            temperature=0.1,
            max_tokens=512,
            timeout=JUDGE_TIMEOUT,
        )
        base = {
            "task_id": gen_result["task_id"],
            "preamble": gen_result["preamble"],
            "subject_model": gen_result["model"],
            "judge_model": judge_model,
        }
        if err:
            return {**base, "idiomaticity": None, "comment_quality": None, "judge_error": err}
        parsed = _extract_json_safe(text)
        if parsed is None:
            return {**base, "idiomaticity": None, "comment_quality": None,
                    "judge_error": f"Parse failure: {text[:100]}"}
        return {
            **base,
            "idiomaticity": parsed.get("idiomaticity"),
            "comment_quality": parsed.get("comment_quality"),
            "idiomaticity_rationale": parsed.get("idiomaticity_rationale", ""),
            "comment_quality_rationale": parsed.get("comment_quality_rationale", ""),
            "judge_error": None,
        }

    results = await asyncio.gather(*[judge_one(g, j) for g, j in jobs])
    results_list = list(results)

    ok = sum(1 for r in results_list if r.get("idiomaticity") is not None)
    fail = sum(1 for r in results_list if r.get("judge_error") is not None)
    print(f"[judging] Done: {ok} ok, {fail} failed")
    return results_list


# ============================================================
# Visualization
# ============================================================


def plot_cqs_by_condition(
    cqs_by_condition: dict[str, list[float]],
    out_path: Path,
    title: str = "CQS by Preamble Condition",
) -> None:
    """Bar chart of mean CQS by condition with 95% bootstrap CI."""
    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(13, 6))

    means, lowers, uppers, labels, colors = [], [], [], [], []
    for cond in PREAMBLE_ORDER:
        vals = cqs_by_condition.get(cond, [])
        if not vals:
            continue
        mean = float(np.mean(vals))
        lo, hi = bootstrap_ci(vals, rng=rng)
        means.append(mean)
        lowers.append(mean - lo)
        uppers.append(hi - mean)
        labels.append(PREAMBLE_LABELS[cond])
        colors.append(CONDITION_COLORS.get(cond, "#999999"))

    x = np.arange(len(labels))
    bars = ax.bar(x, means, color=colors, alpha=0.8, edgecolor="black", linewidth=0.7)
    ax.errorbar(x, means, yerr=[lowers, uppers], fmt="none", color="black",
                capsize=5, capthick=1.5, linewidth=1.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, rotation=20, ha="right")
    ax.set_ylabel("CQS (Composite Quality Score)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylim(0, 1.0)
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.grid(axis="y", alpha=0.3)
    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                f"{mean:.3f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] {out_path.name}")


def plot_sensitivity_probe(probe_result: dict, out_path: Path) -> None:
    """Bar chart for F1 metric sensitivity probe."""
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["Poor", "Average", "Excellent"]
    vals = [probe_result["poor_cqs"], probe_result["average_cqs"], probe_result["excellent_cqs"]]
    colors = ["#E53935", "#FB8C00", "#43A047"]
    bars = ax.bar(labels, vals, color=colors, alpha=0.85, edgecolor="black", linewidth=0.7)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{v:.3f}", ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("CQS (static+AST components only)", fontsize=11)
    ax.set_title(
        f"F1 Sensitivity Probe — Verdict: {probe_result['verdict']}\n"
        f"Range={probe_result['cqs_range']:.3f}, Order={'preserved' if probe_result['order_preserved'] else 'VIOLATED'}",
        fontsize=12, fontweight="bold",
    )
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] {out_path.name}")


def plot_self_preference(strat: dict, out_path: Path) -> None:
    """Bar chart for F3 self-preference stratification."""
    self_mean = strat.get("self_judge_mean_idiom")
    cross_mean = strat.get("cross_judge_mean_idiom")
    if self_mean is None or cross_mean is None:
        return

    fig, ax = plt.subplots(figsize=(6, 5))
    labels = [f"Self-judge\n(n={strat['self_judge_n']})", f"Cross-judge\n(n={strat['cross_judge_n']})"]
    vals = [self_mean, cross_mean]
    colors = ["#1565C0", "#6A1B9A"]
    bars = ax.bar(labels, vals, color=colors, alpha=0.85, edgecolor="black", linewidth=0.7)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{v:.3f}", ha="center", va="bottom", fontsize=11)
    ax.set_ylim(0, 10)
    ax.set_ylabel("Mean Idiomaticity Score (1–10)", fontsize=11)
    ax.set_title(
        f"F3 Self-Preference Stratification\n"
        f"Delta={strat['delta']:+.3f}, Cohen's d={strat['cohen_d']:.3f}, "
        f"p={strat['p_value_mannwhitney']:.4f}\nVerdict: {strat['verdict']}",
        fontsize=11, fontweight="bold",
    )
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] {out_path.name}")


def plot_per_model_heatmap(
    per_model_cqs: dict[str, dict[str, float]],
    condition_order: list[str],
    out_path: Path,
) -> None:
    """Heatmap of CQS by (model, preamble_condition)."""
    valid_conditions = [c for c in condition_order if any(
        c in per_model_cqs[m] for m in per_model_cqs
    )]
    models = list(per_model_cqs.keys())
    model_short = [m.split("/")[-1][:20] for m in models]

    data = np.array([
        [per_model_cqs[m].get(c, np.nan) for c in valid_conditions]
        for m in models
    ])

    fig, ax = plt.subplots(figsize=(max(10, len(valid_conditions) * 1.3), max(4, len(models) * 0.7 + 2)))
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0.3, vmax=0.8)

    ax.set_xticks(range(len(valid_conditions)))
    ax.set_xticklabels([PREAMBLE_LABELS[c] for c in valid_conditions], fontsize=9, rotation=30, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(model_short, fontsize=9)
    ax.set_title("CQS by Model and Preamble Condition (mean over tasks)", fontsize=13, fontweight="bold")

    plt.colorbar(im, ax=ax, label="CQS")
    for i in range(len(models)):
        for j in range(len(valid_conditions)):
            val = data[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=8, color="black" if 0.35 < val < 0.75 else "white")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] {out_path.name}")


def plot_component_breakdown(
    component_by_condition: dict[str, dict[str, list[float]]],
    out_path: Path,
) -> None:
    """Grouped bar chart of CQS component scores by condition."""
    components = ["static_score", "ast_score", "llm_idiom_score", "llm_comment_score"]
    comp_labels = ["Static (45%)", "AST (20%)", "Idiomaticity (20%)", "Comments (15%)"]
    comp_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]

    valid_conditions = [c for c in PREAMBLE_ORDER if c in component_by_condition]
    x = np.arange(len(valid_conditions))
    width = 0.18

    fig, ax = plt.subplots(figsize=(14, 7))
    for i, (comp, label, color) in enumerate(zip(components, comp_labels, comp_colors)):
        means = [float(np.mean(component_by_condition[cond].get(comp, [0.5])))
                 for cond in valid_conditions]
        offset = (i - 1.5) * width
        ax.bar(x + offset, means, width, label=label, color=color, alpha=0.82,
               edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels([PREAMBLE_LABELS[c] for c in valid_conditions], fontsize=10, rotation=20, ha="right")
    ax.set_ylabel("Score (0–1)", fontsize=12)
    ax.set_title("CQS Component Breakdown by Preamble Condition", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] {out_path.name}")


def plot_f2_mechanism(
    cqs_by_condition: dict[str, list[float]],
    out_path: Path,
) -> None:
    """F2 mechanism figure: persona_only vs real_agent vs long_directive vs none."""
    target_conditions = ["none", "persona_only", "real_agent", "long_directive"]
    rng = np.random.default_rng(42)

    fig, ax = plt.subplots(figsize=(9, 5))
    x_pos = []
    x_labels = []
    for i, cond in enumerate(target_conditions):
        vals = cqs_by_condition.get(cond, [])
        if not vals:
            continue
        mean = float(np.mean(vals))
        lo, hi = bootstrap_ci(vals, rng=rng)
        color = CONDITION_COLORS.get(cond, "#999999")
        ax.bar(i, mean, color=color, alpha=0.85, edgecolor="black", linewidth=0.7)
        ax.errorbar(i, mean, yerr=[[mean - lo], [hi - mean]],
                    fmt="none", color="black", capsize=5, linewidth=1.5)
        ax.text(i, mean + 0.015, f"{mean:.3f}", ha="center", va="bottom", fontsize=9)
        x_pos.append(i)
        x_labels.append(PREAMBLE_LABELS[cond])

    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, fontsize=11)
    ax.set_ylabel("CQS", fontsize=12)
    ax.set_title(
        "F2 Mechanism: Distributional Priming vs Instruction-Following\n"
        "(None → Persona Only → Real Agent → Long Directive)",
        fontsize=12, fontweight="bold",
    )
    ax.set_ylim(0, 1.0)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] {out_path.name}")


# ============================================================
# Main pipeline
# ============================================================


async def main(mode: str = "sanity") -> None:
    print("=" * 70)
    print(f"Preamble Quality Experiment 2  (mode={mode})")
    print("=" * 70)

    api_key = get_api_key()
    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)

    dry_run = (mode == "dry-run")

    # Mode-specific subsets
    if mode == "sanity":
        sanity_models = ["openai/gpt-4o-mini"]
        sanity_conditions = ["none", "real_agent"]
        sanity_tasks = [TASKS[0]]   # lru_ttl_cache only
        active_models = sanity_models
        active_preambles = {k: v for k, v in PREAMBLES.items() if k in sanity_conditions}
        active_tasks = sanity_tasks
        sanity_judge_models = ["openai/gpt-4o-mini"]
    else:
        active_models = SUBJECT_MODELS
        active_preambles = PREAMBLES
        active_tasks = TASKS
        sanity_judge_models = JUDGE_MODELS

    print(f"\nScope: {len(active_models)} models x {len(active_preambles)} conditions x {len(active_tasks)} tasks")
    expected_gen = len(active_models) * len(active_preambles) * len(active_tasks)
    expected_judge = expected_gen * len(sanity_judge_models if mode == "sanity" else JUDGE_MODELS)
    print(f"Expected calls: {expected_gen} generation + {expected_judge} judge = {expected_gen + expected_judge} total")

    if dry_run:
        print("\n[dry-run] Job counts computed. Exiting.")
        return

    # ---- 1. Generate code ----
    print(f"\n{'='*30} [1/8] Code Generation {'='*30}")
    generation_results = await run_code_generation_batch(
        active_tasks, active_preambles, active_models, client, dry_run=False,
    )

    # Save raw generation results with FULL code (F8 fix — no truncation)
    gen_path = RESULTS_DIR / "generation_results.jsonl"
    with open(gen_path, "w") as fh:
        for r in generation_results:
            fh.write(json.dumps(r) + "\n")  # full raw_response included
    print(f"[1/8] Generation results saved to {gen_path.name}")

    # ---- 2. Static analysis ----
    print(f"\n{'='*30} [2/8] Static Analysis {'='*30}")
    static_results: list[dict] = []
    all_raw_metrics: list[dict] = []

    for r in generation_results:
        if r["error"] or not r["code"] or r["extraction_method"] == "extraction_failed":
            static_results.append({**r, "static_metrics": None})
            continue
        metrics = compute_static_metrics(r["code"])
        static_results.append({**r, "static_metrics": metrics})
        all_raw_metrics.append(metrics)
        print(
            f"  [{r['task_id'][:20]}|{r['preamble'][:12]}|{r['model'].split('/')[-1][:15]}] "
            f"MI={metrics['maintainability_index']:.1f} "
            f"CC={metrics['avg_cyclomatic']:.1f} "
            f"PEP8={metrics['pep8_name_compliance']:.2f}"
        )

    # ---- 3. Compute data-driven normalization bounds (F6 fix) ----
    print(f"\n{'='*30} [3/8] Data-Driven Normalization Bounds (F6) {'='*30}")
    # Compute pylint_penalty for each record so it can enter bounds computation
    for m in all_raw_metrics:
        m["pylint_penalty"] = (
            m["pylint_errors"] * 1.0
            + m["pylint_warnings"] * 0.5
            + m["pylint_conventions"] * 0.2
            + m["pylint_refactor"] * 0.3
        )

    bound_keys = [
        "maintainability_index", "avg_cyclomatic", "halstead_difficulty",
        "pylint_penalty", "cognitive_complexity_violations",
        "bare_except_count", "max_nesting_depth",
    ]

    if all_raw_metrics:
        bounds = compute_percentile_bounds(all_raw_metrics, bound_keys)
    else:
        # Fallback to sensible defaults for sanity/dry-run
        bounds = {
            "maintainability_index": (20.0, 100.0),
            "avg_cyclomatic": (1.0, 10.0),
            "halstead_difficulty": (0.0, 30.0),
            "pylint_penalty": (0.0, 15.0),
            "cognitive_complexity_violations": (0.0, 3.0),
            "bare_except_count": (0.0, 3.0),
            "max_nesting_depth": (0.0, 6.0),
        }

    print("  Percentile bounds computed:")
    for k, (lo, hi) in bounds.items():
        print(f"    {k}: [{lo:.2f}, {hi:.2f}]")

    # Save bounds
    bounds_path = RESULTS_DIR / "normalization_bounds.json"
    with open(bounds_path, "w") as fh:
        json.dump({k: list(v) for k, v in bounds.items()}, fh, indent=2)

    # ---- 4. F1 Sensitivity Probe ----
    print(f"\n{'='*30} [4/8] F1 Metric Sensitivity Probe {'='*30}")
    # Add pylint_penalty to synthetic metric dicts as well
    probe_result = run_sensitivity_probe(bounds)
    probe_path = RESULTS_DIR / "f1_sensitivity_probe.json"
    with open(probe_path, "w") as fh:
        json.dump(probe_result, fh, indent=2)
    print(f"  [F1-PROBE] Saved to {probe_path.name}")

    # ---- 5. LLM-as-judge (full cross-judge matrix) ----
    print(f"\n{'='*30} [5/8] LLM Judge (cross-judge matrix) {'='*30}")
    judge_models_active = sanity_judge_models if mode == "sanity" else JUDGE_MODELS
    judge_results_raw = await run_llm_judge_batch(
        generation_results, judge_models_active, client,
    )

    # Save raw judge results
    judge_path = RESULTS_DIR / "judge_results.jsonl"
    with open(judge_path, "w") as fh:
        for r in judge_results_raw:
            fh.write(json.dumps(r) + "\n")

    # ---- 6. F3 Self-preference stratification ----
    print(f"\n{'='*30} [6/8] F3 Self-Preference Stratification {'='*30}")
    # For F3: cross-judge records already have subject_model and judge_model
    self_pref = compute_self_preference_stratification(judge_results_raw)
    self_pref_path = RESULTS_DIR / "f3_self_preference.json"
    with open(self_pref_path, "w") as fh:
        json.dump(self_pref, fh, indent=2)
    print(f"  [F3] Verdict: {self_pref['verdict']}, delta={self_pref.get('delta')}, "
          f"p={self_pref.get('p_value_mannwhitney')}")

    # Build cross-judge-only judge scores (exclude self-judgments for primary CQS)
    cross_judge_by_key: dict[tuple, list[dict]] = {}
    all_judge_by_key: dict[tuple, list[dict]] = {}
    for jr in judge_results_raw:
        key = (jr["task_id"], jr["preamble"], jr["subject_model"])
        all_judge_by_key.setdefault(key, []).append(jr)
        if jr["subject_model"] != jr["judge_model"]:
            cross_judge_by_key.setdefault(key, []).append(jr)

    # ---- 7. CQS computation (with normalized scores) ----
    print(f"\n{'='*30} [7/8] CQS Computation {'='*30}")
    full_results: list[dict] = []

    for sr in static_results:
        if sr["static_metrics"] is None:
            continue
        raw_m = sr["static_metrics"]
        # Apply pylint_penalty field
        raw_m.setdefault("pylint_penalty", (
            raw_m["pylint_errors"] * 1.0
            + raw_m["pylint_warnings"] * 0.5
            + raw_m["pylint_conventions"] * 0.2
            + raw_m["pylint_refactor"] * 0.3
        ))
        static_score = compute_static_score_normalized(raw_m, bounds)
        ast_score = compute_ast_score_normalized(raw_m, bounds)

        key = (sr["task_id"], sr["preamble"], sr["model"])
        cross_judges = cross_judge_by_key.get(key, [])
        all_judges = all_judge_by_key.get(key, [])

        # Primary CQS: cross-judge only (F3 fix)
        cqs_dict = compute_cqs(static_score, ast_score, cross_judges)
        # Also compute with all judges (for comparison)
        cqs_all_judges = compute_cqs(static_score, ast_score, all_judges)

        full_results.append({
            "task_id": sr["task_id"],
            "preamble": sr["preamble"],
            "model": sr["model"],
            "extraction_method": sr["extraction_method"],
            # Primary metrics (cross-judge only)
            **cqs_dict,
            # All-judge CQS for comparison
            "cqs_all_judges": cqs_all_judges["cqs"],
            "llm_idiom_score_all_judges": cqs_all_judges["llm_idiom_score"],
            # Raw static metrics (for audit)
            **{f"raw_{k}": v for k, v in raw_m.items()},
        })

    # Save full results
    results_path = RESULTS_DIR / "full_results.jsonl"
    with open(results_path, "w") as fh:
        for r in full_results:
            fh.write(json.dumps(r) + "\n")
    print(f"[7/8] {len(full_results)} scored results saved.")

    # ---- 8. Statistics and reporting ----
    print(f"\n{'='*30} [8/8] Statistics {'='*30}")

    # Aggregate CQS by preamble condition
    cqs_by_condition: dict[str, list[float]] = {}
    component_by_condition: dict[str, dict[str, list[float]]] = {}
    per_model_cqs_raw: dict[str, dict[str, list[float]]] = {}

    for r in full_results:
        cond = r["preamble"]
        cqs_val = r["cqs"]
        cqs_by_condition.setdefault(cond, []).append(cqs_val)

        if cond not in component_by_condition:
            component_by_condition[cond] = {}
        for comp in ["static_score", "ast_score", "llm_idiom_score", "llm_comment_score"]:
            component_by_condition[cond].setdefault(comp, []).append(r[comp])

        model = r["model"]
        per_model_cqs_raw.setdefault(model, {}).setdefault(cond, []).append(cqs_val)

    per_model_cqs_mean: dict[str, dict[str, float]] = {
        model: {c: float(np.mean(vals)) for c, vals in cond_dict.items()}
        for model, cond_dict in per_model_cqs_raw.items()
    }

    # Print summary table
    rng = np.random.default_rng(42)
    print(f"\n{'Condition':<22} {'N':<5} {'Mean CQS':<12} {'95% CI':<24} {'MI mean':<10}")
    print("-" * 75)
    for cond in PREAMBLE_ORDER:
        vals = cqs_by_condition.get(cond, [])
        if not vals:
            continue
        mean = float(np.mean(vals))
        lo, hi = bootstrap_ci(vals, rng=rng)
        mi_vals = [r.get("raw_maintainability_index", 0.0) for r in full_results if r["preamble"] == cond]
        mi_mean = float(np.mean(mi_vals)) if mi_vals else 0.0
        print(f"{PREAMBLE_LABELS[cond]:<22} {len(vals):<5} {mean:.4f}       [{lo:.4f}, {hi:.4f}]    {mi_mean:.1f}")

    # Kruskal-Wallis (main conditions only, excluding trivial_baseline)
    main_groups = [cqs_by_condition.get(c, []) for c in MAIN_CONDITIONS
                   if cqs_by_condition.get(c)]
    if len(main_groups) >= 2 and all(len(g) >= 2 for g in main_groups):
        kw_stat, kw_p = stats.kruskal(*main_groups)
        print(f"\nKruskal-Wallis (main conditions): H={kw_stat:.3f}, p={kw_p:.4f}")
        print(f"  -> {'Significant' if kw_p < 0.05 else 'NOT significant'} (alpha=0.05)")
    else:
        kw_stat, kw_p = 0.0, 1.0
        print("\nKruskal-Wallis: insufficient data")

    # Spearman rank stability (main conditions only)
    main_per_model = {
        model: {c: v for c, v in conds.items() if c in MAIN_CONDITIONS}
        for model, conds in per_model_cqs_mean.items()
    }
    rho = compute_spearman_rank_stability(main_per_model, MAIN_CONDITIONS)
    print(f"\nSpearman rank stability (main conditions, mean pairwise rho): {rho:.4f}")
    print(f"  -> {'PASSES' if rho >= 0.6 else 'FAILS'} threshold (>= 0.6)")

    # expert vs. none delta
    expert_vals = cqs_by_condition.get("real_agent", [])
    none_vals = cqs_by_condition.get("none", [])
    delta_expert_none = (
        float(np.mean(expert_vals)) - float(np.mean(none_vals))
        if expert_vals and none_vals else None
    )
    print(f"\nReal Agent vs None delta: {delta_expert_none:+.4f}" if delta_expert_none is not None else "\nReal Agent vs None: no data")

    # Trivial baseline comparison
    trivial_vals = cqs_by_condition.get("trivial_baseline", [])
    if trivial_vals and expert_vals:
        trivial_mean = float(np.mean(trivial_vals))
        expert_mean = float(np.mean(expert_vals))
        print(f"Trivial baseline mean CQS: {trivial_mean:.4f}")
        print(f"Best condition (real_agent) mean CQS: {expert_mean:.4f}")
        print(f"Beat trivial baseline? {'YES' if expert_mean > trivial_mean else 'NO'}")

    # Mixed-effects model (skip for sanity mode — too few observations)
    if mode == "full":
        print("\nRunning mixed-effects model...")
        me_result = run_mixed_effects_model(full_results)
        if "error" in me_result:
            print(f"  Mixed-effects failed: {me_result['error']}")
        else:
            print(f"  AIC={me_result['aic']:.1f}, BIC={me_result['bic']:.1f}, N={me_result['n_obs']}")
            for fe_name, fe in me_result.get("fixed_effects", {}).items():
                print(f"  {fe_name}: coef={fe['coef']:+.4f}, p={fe['pval']:.4f}")
    else:
        me_result = {"skipped": f"mode={mode}, need full run for mixed-effects"}

    # F2 mechanism: persona_only vs real_agent vs long_directive vs none
    print("\nF2 Mechanism (priming vs instruction):")
    for cond in ["none", "persona_only", "real_agent", "long_directive"]:
        vals = cqs_by_condition.get(cond, [])
        if vals:
            print(f"  {PREAMBLE_LABELS[cond]:<20}: {np.mean(vals):.4f} (n={len(vals)})")

    # ---- Save stats JSON ----
    stats_summary: dict = {
        "mode": mode,
        "kruskal_wallis_H": float(kw_stat),
        "kruskal_wallis_p": float(kw_p),
        "spearman_rank_stability_rho": float(rho),
        "spearman_passes_threshold": rho >= 0.6,
        "real_agent_vs_none_delta": delta_expert_none,
        "f1_sensitivity_probe": probe_result,
        "f3_self_preference": self_pref,
        "normalization_bounds": {k: list(v) for k, v in bounds.items()},
        "mixed_effects_model": me_result,
        "cqs_by_condition": {
            cond: {
                "n": len(vals),
                "mean": float(np.mean(vals)),
                "ci_95_lower": float(bootstrap_ci(vals, rng=np.random.default_rng(42))[0]),
                "ci_95_upper": float(bootstrap_ci(vals, rng=np.random.default_rng(42))[1]),
            }
            for cond, vals in cqs_by_condition.items() if vals
        },
        "per_model_cqs_mean": per_model_cqs_mean,
    }
    stats_path = RESULTS_DIR / "stats_results.json"
    with open(stats_path, "w") as fh:
        json.dump(stats_summary, fh, indent=2)
    print(f"\nStats saved to {stats_path.name}")

    # ---- Figures ----
    print("\n[viz] Generating figures...")

    plot_cqs_by_condition(
        cqs_by_condition,
        RESULTS_DIR / "finding_all_conditions_cqs.png",
        "Experiment 2: CQS by Preamble Condition (all models, all tasks)",
    )

    if mode != "sanity":
        plot_component_breakdown(
            component_by_condition,
            RESULTS_DIR / "finding_component_breakdown.png",
        )
        if len(per_model_cqs_mean) >= 2:
            plot_per_model_heatmap(
                per_model_cqs_mean,
                PREAMBLE_ORDER,
                RESULTS_DIR / "finding_per_model_heatmap.png",
            )

    plot_sensitivity_probe(
        probe_result,
        RESULTS_DIR / "finding_f1_sensitivity_probe.png",
    )
    plot_self_preference(
        self_pref,
        RESULTS_DIR / "finding_f3_self_preference.png",
    )
    plot_f2_mechanism(
        cqs_by_condition,
        RESULTS_DIR / "finding_f2_mechanism.png",
    )

    if mode != "sanity":
        plot_cqs_by_condition(
            cqs_by_condition,
            RESULTS_DIR / "summary_all_conditions.png",
            "Summary: CQS by Condition (cross-judge; data-driven normalization)",
        )

    print("\n" + "=" * 70)
    print(f"Experiment 2 complete (mode={mode}).")
    print(f"Results in: {RESULTS_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preamble Quality Experiment 2")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sanity", action="store_true", default=True,
                       help="Quick smoke-test: 1 model x 2 conditions x 1 task")
    group.add_argument("--dry-run", action="store_true",
                       help="Print job counts only, no API calls")
    group.add_argument("--full", action="store_true",
                       help="Full experiment: 8 models x 8 conditions x 6 tasks")
    args = parser.parse_args()

    if args.dry_run:
        mode = "dry-run"
    elif args.full:
        mode = "full"
    else:
        mode = "sanity"

    asyncio.run(main(mode))
