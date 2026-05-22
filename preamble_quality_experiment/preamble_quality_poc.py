# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai",
#   "radon",
#   "flake8",
#   "flake8-cognitive-complexity",
#   "pylint",
#   "matplotlib",
#   "scipy",
#   "numpy",
# ]
# ///
"""
Preamble Quality PoC — Minimal end-to-end script.

Tests the hypothesis: Expert coding preambles cause LLMs to produce measurably
higher-quality code than no/minimal preamble, as measured by a Composite Quality
Score (CQS) combining static analysis metrics and LLM-as-judge dimensions.

Deliberately omitted (PoC scope):
- Full 8-model subject/judge pools (uses 3 subject + 2 judge for speed)
- Production retry hardening (basic retry only)
- Sensitivity analysis across task set
- Mixed-effects statistical model (Spearman rank only)
- Multiple task domains (uses 3 tasks)
- Full Halstead metric suite (uses radon's subset)
- Ruff-based AST analysis (uses radon + pylint + stdlib AST)

Run with: uv run preamble_quality_poc.py
Reads OPENROUTER_API_KEY from environment.
"""

import ast
import asyncio
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Use the same Python interpreter that is running this script,
# so radon/pylint/flake8 installed by uv are available.
PYTHON = sys.executable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from openai import AsyncOpenAI
from scipy import stats

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPERIMENT_DIR = Path(__file__).parent
RESULTS_DIR = EXPERIMENT_DIR / "poc_results"
RESULTS_DIR.mkdir(exist_ok=True)

# Subject models (subset for PoC)
SUBJECT_MODELS = [
    "deepseek/deepseek-v3.2",
    "openai/gpt-4o-mini",
    "mistralai/mistral-small-2603",
]

# Judge models (subset for PoC)
JUDGE_MODELS = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-v3.2",
]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONCURRENCY = 6
MAX_RETRIES = 3
TIMEOUT = 90

# CQS weights (from HYPOTHESIS.md)
WEIGHTS = {
    "static_score": 0.45,
    "ast_score": 0.20,
    "llm_idiom_score": 0.20,
    "llm_comment_score": 0.15,
}

# ---------------------------------------------------------------------------
# Preamble conditions
# ---------------------------------------------------------------------------

PREAMBLES = {
    "none": None,  # No system prompt
    "minimal": "You are a helpful assistant.",
    "generic_coding": (
        "You are an expert software engineer with deep knowledge of Python. "
        "Write clean, efficient, and maintainable code."
    ),
    "real_agent": (
        # Condensed real coding-agent preamble (Claude Code style)
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
}

# ---------------------------------------------------------------------------
# Coding tasks
# ---------------------------------------------------------------------------

TASKS = [
    {
        "id": "task_rate_limiter",
        "name": "Token Bucket Rate Limiter",
        "prompt": (
            "Write a Python class implementing a token bucket rate limiter. "
            "It should support: configurable rate (tokens/second) and burst capacity, "
            "a method to consume tokens (returning True if allowed, False if denied), "
            "and thread-safe operation. Include a brief usage example at the bottom."
        ),
    },
    {
        "id": "task_csv_processor",
        "name": "Streaming CSV Processor",
        "prompt": (
            "Write a Python function that streams a large CSV file row by row, "
            "applies a user-supplied transformation function to each row, "
            "filters out rows where a specified column matches a predicate, "
            "and writes results to an output file. "
            "Handle malformed rows gracefully. Include type hints."
        ),
    },
    {
        "id": "task_retry_decorator",
        "name": "Retry Decorator with Exponential Backoff",
        "prompt": (
            "Write a Python decorator that retries a function on specified exceptions "
            "with exponential backoff and jitter. Parameters: max_retries, base_delay, "
            "max_delay, exceptions tuple. The decorator should log each retry attempt "
            "using the standard logging module. Include a usage example."
        ),
    },
]

# ---------------------------------------------------------------------------
# LLM dispatch
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment")
    return key


async def _call_one(
    client: AsyncOpenAI,
    sem: asyncio.Semaphore,
    model: str,
    system_prompt: Optional[str],
    user_msg: str,
    label: str,
) -> tuple[str, str | None]:
    """Single async LLM call. Returns (text, error_or_none)."""
    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_msg})

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with sem:
                resp = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.3,
                        max_tokens=2048,
                    ),
                    timeout=TIMEOUT,
                )
            return resp.choices[0].message.content or "", None
        except Exception as exc:
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2.0 ** attempt)
                continue
            return "", f"{type(exc).__name__}: {exc}"
    return "", "Exhausted retries"


async def run_code_generation_batch(
    tasks: list[dict],
    preambles: dict[str, Optional[str]],
    subject_models: list[str],
    client: AsyncOpenAI,
) -> list[dict]:
    """Generate code for all (task, preamble, model) combinations."""
    sem = asyncio.Semaphore(CONCURRENCY)
    jobs = []
    for task in tasks:
        for preamble_name, preamble_text in preambles.items():
            for model in subject_models:
                jobs.append((task, preamble_name, preamble_text, model))

    print(f"[generation] Dispatching {len(jobs)} code generation calls...")

    async def dispatch(task, pname, ptext, model):
        label = f"{task['id']}|{pname}|{model}"
        text, err = await _call_one(client, sem, model, ptext, task["prompt"], label)
        return {
            "task_id": task["id"],
            "preamble": pname,
            "model": model,
            "code": text,
            "error": err,
        }

    results = await asyncio.gather(*[dispatch(*j) for j in jobs])
    return list(results)


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

def extract_python_code(text: str) -> str:
    """Extract Python code from LLM response (strip markdown fences)."""
    # Try fenced code block first
    fence = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    # Fallback: return as-is if it looks like code
    if "def " in text or "class " in text or "import " in text:
        return text.strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Static analysis
# ---------------------------------------------------------------------------

def compute_static_metrics(code: str) -> dict:
    """
    Run radon + pylint + AST analysis on a code snippet.
    Returns a dict of raw metrics and a normalized static_score [0,1].
    """
    metrics = {}

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        # --- Radon: cyclomatic complexity ---
        result = subprocess.run(
            [PYTHON, "-m", "radon", "cc", "--json", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        cc_data = {}
        if result.returncode == 0 and result.stdout.strip():
            try:
                cc_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        complexities = []
        for file_results in cc_data.values():
            if not isinstance(file_results, list):
                continue
            for item in file_results:
                if isinstance(item, dict):
                    complexities.append(item.get("complexity", 1))
                    # Also include method-level complexity if present
                    for method in item.get("methods", []):
                        if isinstance(method, dict):
                            complexities.append(method.get("complexity", 1))
        avg_cc = sum(complexities) / len(complexities) if complexities else 1
        max_cc = max(complexities) if complexities else 1
        metrics["avg_cyclomatic"] = avg_cc
        metrics["max_cyclomatic"] = max_cc

        # --- Radon: maintainability index ---
        result = subprocess.run(
            [PYTHON, "-m", "radon", "mi", "--json", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        mi_score = 50.0  # default neutral
        if result.returncode == 0 and result.stdout.strip():
            try:
                mi_data = json.loads(result.stdout)
                for file_data in mi_data.values():
                    mi_score = file_data.get("mi", 50.0)
                    break
            except json.JSONDecodeError:
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
                        # radon hal --json returns {"file": {"total": {...}, "functions": {...}}}
                        total_section = file_data.get("total", file_data)
                        hal_volume = total_section.get("volume", 0.0) or 0.0
                        hal_difficulty = total_section.get("difficulty", 0.0) or 0.0
                    break
            except json.JSONDecodeError:
                pass
        metrics["halstead_volume"] = hal_volume
        metrics["halstead_difficulty"] = hal_difficulty

        # --- Pylint: message count by severity ---
        result = subprocess.run(
            [PYTHON, "-m", "pylint", "--output-format=json", "--disable=all",
             "--enable=E,W,C,R", tmp_path],
            capture_output=True, text=True, timeout=15,
        )
        pylint_counts = {"E": 0, "W": 0, "C": 0, "R": 0}
        if result.stdout.strip():
            try:
                messages = json.loads(result.stdout)
                for msg in messages:
                    cat = msg.get("type", "")[:1].upper()
                    if cat in pylint_counts:
                        pylint_counts[cat] += 1
            except json.JSONDecodeError:
                pass
        metrics["pylint_errors"] = pylint_counts["E"]
        metrics["pylint_warnings"] = pylint_counts["W"]
        metrics["pylint_conventions"] = pylint_counts["C"]
        metrics["pylint_refactor"] = pylint_counts["R"]

        # --- flake8-cognitive-complexity ---
        result = subprocess.run(
            [PYTHON, "-m", "flake8",
             "--select=CCR001",
             "--max-cognitive-complexity=30",
             "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
             tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        cog_violations = len([l for l in result.stdout.splitlines() if "CCR001" in l])
        metrics["cognitive_complexity_violations"] = cog_violations

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # --- AST analysis (in-process) ---
    ast_metrics = compute_ast_metrics(code)
    metrics.update(ast_metrics)

    # --- Normalize to static_score [0,1] (higher = better quality) ---
    # Maintainability Index: 0-100, higher = better → normalize directly
    mi_norm = min(metrics["maintainability_index"], 100) / 100.0

    # Cyclomatic complexity: lower = better. Score = 1 - clamp(avg_cc/20, 0, 1)
    cc_norm = 1.0 - min(avg_cc / 20.0, 1.0)

    # Halstead difficulty: lower = better. Score = 1 - clamp(diff/50, 0, 1)
    hal_diff_norm = 1.0 - min(hal_difficulty / 50.0, 1.0)

    # Pylint: weighted penalty score
    pylint_penalty = (
        pylint_counts["E"] * 1.0 +
        pylint_counts["W"] * 0.5 +
        pylint_counts["C"] * 0.2 +
        pylint_counts["R"] * 0.3
    )
    pylint_norm = 1.0 - min(pylint_penalty / 20.0, 1.0)

    # Cognitive complexity violations: 0 = good
    cog_norm = 1.0 - min(cog_violations / 5.0, 1.0)

    # static_score: weighted combination
    static_score = (
        0.30 * mi_norm +
        0.25 * cc_norm +
        0.20 * hal_diff_norm +
        0.15 * pylint_norm +
        0.10 * cog_norm
    )
    metrics["static_score"] = round(static_score, 4)

    return metrics


def compute_ast_metrics(code: str) -> dict:
    """AST-based code quality metrics."""
    metrics = {
        "bare_except_count": 0,
        "identifier_entropy": 0.0,
        "max_nesting_depth": 0,
        "has_type_hints": False,
        "class_count": 0,
        "function_count": 0,
        "ast_score": 0.5,
    }

    try:
        tree = ast.parse(code)
    except SyntaxError:
        metrics["ast_score"] = 0.0
        return metrics

    # Bare except count
    bare_excepts = sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.type is None
    )
    metrics["bare_except_count"] = bare_excepts

    # Identifier entropy (lexical diversity of names)
    names = [
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    ] + [
        node.arg for node in ast.walk(tree)
        if isinstance(node, ast.arg)
    ]
    if names:
        from collections import Counter
        counts = Counter(names)
        total = sum(counts.values())
        entropy = -sum(
            (c / total) * math.log2(c / total)
            for c in counts.values()
        )
        metrics["identifier_entropy"] = round(entropy, 4)

    # Max nesting depth
    metrics["max_nesting_depth"] = _compute_max_nesting(tree)

    # Type hints presence
    has_hints = any(
        (node.returns is not None or
         any(arg.annotation is not None for arg in node.args.args))
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    )
    metrics["has_type_hints"] = has_hints

    # Class and function counts
    metrics["class_count"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    metrics["function_count"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))

    # Normalize ast_score
    bare_except_penalty = min(bare_excepts / 3.0, 1.0)
    entropy_norm = min(metrics["identifier_entropy"] / 4.0, 1.0)
    nesting_penalty = min(metrics["max_nesting_depth"] / 8.0, 1.0)
    hints_bonus = 0.1 if has_hints else 0.0

    ast_score = (
        0.30 * (1.0 - bare_except_penalty) +
        0.30 * entropy_norm +
        0.30 * (1.0 - nesting_penalty) +
        0.10 * (1.0 + hints_bonus)  # small bonus for hints
    )
    metrics["ast_score"] = round(min(ast_score, 1.0), 4)
    return metrics


def _compute_max_nesting(tree: ast.AST) -> int:
    """Compute maximum nesting depth of control structures."""
    NESTING_NODES = (ast.If, ast.For, ast.While, ast.With, ast.Try,
                     ast.ExceptHandler, ast.AsyncFor, ast.AsyncWith)

    def depth(node, current=0):
        max_d = current
        for child in ast.iter_child_nodes(node):
            if isinstance(child, NESTING_NODES):
                max_d = max(max_d, depth(child, current + 1))
            else:
                max_d = max(max_d, depth(child, current))
        return max_d

    return depth(tree)


# ---------------------------------------------------------------------------
# LLM-as-judge
# ---------------------------------------------------------------------------

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


async def run_llm_judge_batch(
    generation_results: list[dict],
    judge_models: list[str],
    client: AsyncOpenAI,
) -> list[dict]:
    """Run LLM-as-judge scoring for idiomaticity and comment quality."""
    sem = asyncio.Semaphore(CONCURRENCY)

    def extract_json_safe(text: str) -> dict | None:
        text = text.strip()
        # Try direct
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try fence extraction
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
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

    async def judge_one(gen_result: dict, judge_model: str):
        code = gen_result["code"]
        if not code or gen_result["error"]:
            return {
                **gen_result,
                "judge_model": judge_model,
                "idiomaticity": None,
                "comment_quality": None,
                "judge_error": gen_result["error"],
            }

        user_msg = f"Please evaluate this Python code:\n\n```python\n{code}\n```"
        text, err = await _call_one(
            client, sem, judge_model,
            JUDGE_SYSTEM_PROMPT, user_msg,
            f"judge|{gen_result['task_id']}|{gen_result['preamble']}|{gen_result['model']}|{judge_model}",
        )
        if err:
            return {
                **gen_result,
                "judge_model": judge_model,
                "idiomaticity": None,
                "comment_quality": None,
                "judge_error": err,
            }
        parsed = extract_json_safe(text)
        if parsed is None:
            return {
                **gen_result,
                "judge_model": judge_model,
                "idiomaticity": None,
                "comment_quality": None,
                "judge_error": f"Parse failure: {text[:100]}",
            }
        return {
            **gen_result,
            "judge_model": judge_model,
            "idiomaticity": parsed.get("idiomaticity"),
            "comment_quality": parsed.get("comment_quality"),
            "idiomaticity_rationale": parsed.get("idiomaticity_rationale", ""),
            "comment_quality_rationale": parsed.get("comment_quality_rationale", ""),
            "judge_error": None,
        }

    # Only judge successfully generated code
    valid_results = [r for r in generation_results if r["code"] and not r["error"]]
    jobs = [
        judge_one(gen_result, judge_model)
        for gen_result in valid_results
        for judge_model in judge_models
    ]
    print(f"[judging] Dispatching {len(jobs)} judge calls...")
    results = await asyncio.gather(*jobs)
    return list(results)


# ---------------------------------------------------------------------------
# CQS computation
# ---------------------------------------------------------------------------

def compute_cqs(static_metrics: dict, judge_scores: list[dict]) -> dict:
    """Compute Composite Quality Score from components."""
    static_score = static_metrics.get("static_score", 0.5)
    ast_score = static_metrics.get("ast_score", 0.5)

    # Average judge scores across models (normalize 1-10 → 0-1)
    valid_idiom = [j["idiomaticity"] / 10.0 for j in judge_scores
                   if j.get("idiomaticity") is not None]
    valid_comment = [j["comment_quality"] / 10.0 for j in judge_scores
                     if j.get("comment_quality") is not None]

    llm_idiom_score = sum(valid_idiom) / len(valid_idiom) if valid_idiom else 0.5
    llm_comment_score = sum(valid_comment) / len(valid_comment) if valid_comment else 0.5

    cqs = (
        WEIGHTS["static_score"] * static_score +
        WEIGHTS["ast_score"] * ast_score +
        WEIGHTS["llm_idiom_score"] * llm_idiom_score +
        WEIGHTS["llm_comment_score"] * llm_comment_score
    )
    return {
        "cqs": round(cqs, 4),
        "static_score": round(static_score, 4),
        "ast_score": round(ast_score, 4),
        "llm_idiom_score": round(llm_idiom_score, 4),
        "llm_comment_score": round(llm_comment_score, 4),
    }


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def compute_bootstrap_ci(values: list[float], n_boot: int = 1000, ci: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap CI."""
    if len(values) < 2:
        v = values[0] if values else 0.0
        return v, v
    arr = np.array(values)
    boot_means = [np.mean(np.random.choice(arr, size=len(arr), replace=True)) for _ in range(n_boot)]
    alpha = 1 - ci
    lower = np.percentile(boot_means, 100 * alpha / 2)
    upper = np.percentile(boot_means, 100 * (1 - alpha / 2))
    return lower, upper


def compute_spearman_rank_stability(
    per_model_rankings: dict[str, dict[str, float]]
) -> float:
    """
    Compute mean pairwise Spearman correlation of preamble condition rankings
    across subject models. Returns mean rho.
    """
    preamble_order = list(PREAMBLES.keys())
    model_ranks = []
    for model, cqs_by_preamble in per_model_rankings.items():
        scores = [cqs_by_preamble.get(p, 0.0) for p in preamble_order]
        ranks = stats.rankdata(scores)
        model_ranks.append(ranks)

    if len(model_ranks) < 2:
        return 0.0

    rhos = []
    for i in range(len(model_ranks)):
        for j in range(i + 1, len(model_ranks)):
            rho, _ = stats.spearmanr(model_ranks[i], model_ranks[j])
            rhos.append(rho)
    return float(np.mean(rhos))


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

PREAMBLE_ORDER = ["none", "minimal", "generic_coding", "real_agent", "negative_control"]
PREAMBLE_LABELS = {
    "none": "No Prompt",
    "minimal": "Minimal",
    "generic_coding": "Generic Coding",
    "real_agent": "Real Agent",
    "negative_control": "Negative Control",
}
CONDITION_COLORS = {
    "none": "#888888",
    "minimal": "#4CAF50",
    "generic_coding": "#2196F3",
    "real_agent": "#FF5722",
    "negative_control": "#9C27B0",
}


def plot_cqs_by_condition(
    aggregated: dict[str, list[float]],
    out_path: Path,
    title: str = "CQS by Preamble Condition",
) -> None:
    """Bar chart of mean CQS by preamble condition with 95% CI."""
    fig, ax = plt.subplots(figsize=(10, 6))

    means = []
    lowers = []
    uppers = []
    labels = []
    colors = []

    for cond in PREAMBLE_ORDER:
        vals = aggregated.get(cond, [])
        if not vals:
            continue
        mean = np.mean(vals)
        lo, hi = compute_bootstrap_ci(vals)
        means.append(mean)
        lowers.append(mean - lo)
        uppers.append(hi - mean)
        labels.append(PREAMBLE_LABELS[cond])
        colors.append(CONDITION_COLORS[cond])

    x = np.arange(len(labels))
    bars = ax.bar(x, means, color=colors, alpha=0.8, edgecolor="black", linewidth=0.8)
    ax.errorbar(x, means, yerr=[lowers, uppers], fmt="none", color="black",
                capsize=5, capthick=1.5, linewidth=1.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Composite Quality Score (CQS)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylim(0, 1.0)
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.grid(axis="y", alpha=0.3)

    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{mean:.3f}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] Saved: {out_path}")


def plot_component_breakdown(
    component_data: dict[str, dict[str, list[float]]],
    out_path: Path,
) -> None:
    """Grouped bar chart showing all CQS components by condition."""
    components = ["static_score", "ast_score", "llm_idiom_score", "llm_comment_score"]
    comp_labels = ["Static (45%)", "AST (20%)", "Idiomaticity (20%)", "Comments (15%)"]
    comp_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]

    valid_conditions = [c for c in PREAMBLE_ORDER if c in component_data]
    x = np.arange(len(valid_conditions))
    width = 0.2

    fig, ax = plt.subplots(figsize=(12, 7))

    for i, (comp, label, color) in enumerate(zip(components, comp_labels, comp_colors)):
        means = [np.mean(component_data[cond].get(comp, [0.5])) for cond in valid_conditions]
        offset = (i - 1.5) * width
        ax.bar(x + offset, means, width, label=label, color=color, alpha=0.8,
               edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels([PREAMBLE_LABELS[c] for c in valid_conditions], fontsize=10)
    ax.set_ylabel("Score (0-1)", fontsize=12)
    ax.set_title("CQS Component Breakdown by Preamble Condition", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[viz] Saved: {out_path}")


def plot_per_model_heatmap(
    per_model_cqs: dict[str, dict[str, float]],
    out_path: Path,
) -> None:
    """Heatmap of CQS by (model, preamble_condition)."""
    valid_conditions = [c for c in PREAMBLE_ORDER if any(
        c in per_model_cqs[m] for m in per_model_cqs
    )]
    models = list(per_model_cqs.keys())
    model_short = [m.split("/")[-1] for m in models]

    data = np.array([
        [per_model_cqs[m].get(c, np.nan) for c in valid_conditions]
        for m in models
    ])

    fig, ax = plt.subplots(figsize=(10, max(4, len(models) * 0.7 + 2)))
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0.3, vmax=0.8)

    ax.set_xticks(range(len(valid_conditions)))
    ax.set_xticklabels([PREAMBLE_LABELS[c] for c in valid_conditions], fontsize=10)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(model_short, fontsize=9)
    ax.set_title("CQS by Model and Preamble Condition", fontsize=14, fontweight="bold")

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
    print(f"[viz] Saved: {out_path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("Preamble Quality PoC")
    print("=" * 60)

    api_key = get_api_key()
    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)

    # ---- Step 1: Generate code ----
    print("\n[1/5] Generating code for all (task, preamble, model) combinations...")
    generation_results = await run_code_generation_batch(
        TASKS, PREAMBLES, SUBJECT_MODELS, client
    )
    gen_success = sum(1 for r in generation_results if not r["error"])
    gen_fail = sum(1 for r in generation_results if r["error"])
    print(f"[1/5] Generation complete: {gen_success} ok, {gen_fail} failed")

    # Save raw generation results
    gen_path = RESULTS_DIR / "generation_results.jsonl"
    with open(gen_path, "w") as f:
        for r in generation_results:
            f.write(json.dumps({**r, "code": r["code"][:200] + "..." if len(r.get("code","")) > 200 else r["code"]}) + "\n")

    # ---- Step 2: Static analysis ----
    print("\n[2/5] Running static analysis...")
    static_results = []
    for r in generation_results:
        if r["error"] or not r["code"]:
            static_results.append({**r, "static_metrics": None})
            continue
        code = extract_python_code(r["code"])
        metrics = compute_static_metrics(code)
        static_results.append({**r, "static_metrics": metrics})
        print(f"  [{r['task_id']}|{r['preamble'][:8]}|{r['model'].split('/')[-1][:12]}] "
              f"MI={metrics['maintainability_index']:.1f} "
              f"CC={metrics['avg_cyclomatic']:.1f} "
              f"static={metrics['static_score']:.3f} "
              f"ast={metrics['ast_score']:.3f}")

    # ---- Step 3: LLM-as-judge ----
    print("\n[3/5] Running LLM-as-judge scoring...")
    judge_inputs = [r for r in generation_results if not r["error"] and r["code"]]
    judge_results_raw = await run_llm_judge_batch(judge_inputs, JUDGE_MODELS, client)

    # Group judge results by (task_id, preamble, model)
    judge_by_key: dict[tuple, list] = {}
    for jr in judge_results_raw:
        key = (jr["task_id"], jr["preamble"], jr["model"])
        judge_by_key.setdefault(key, []).append(jr)

    # ---- Step 4: CQS computation ----
    print("\n[4/5] Computing CQS...")
    full_results = []
    for sr in static_results:
        if sr["static_metrics"] is None:
            continue
        key = (sr["task_id"], sr["preamble"], sr["model"])
        judges = judge_by_key.get(key, [])
        cqs_dict = compute_cqs(sr["static_metrics"], judges)
        full_results.append({
            "task_id": sr["task_id"],
            "preamble": sr["preamble"],
            "model": sr["model"],
            **cqs_dict,
            **sr["static_metrics"],
        })

    # Save full results
    results_path = RESULTS_DIR / "full_results.jsonl"
    with open(results_path, "w") as f:
        for r in full_results:
            f.write(json.dumps(r) + "\n")
    print(f"[4/5] Saved {len(full_results)} scored results to {results_path}")

    # ---- Step 5: Aggregation and stats ----
    print("\n[5/5] Aggregating results and computing statistics...")

    # CQS by preamble condition (across all models and tasks)
    cqs_by_condition: dict[str, list[float]] = {}
    for r in full_results:
        cqs_by_condition.setdefault(r["preamble"], []).append(r["cqs"])

    # Component scores by condition
    component_by_condition: dict[str, dict[str, list[float]]] = {}
    for r in full_results:
        cond = r["preamble"]
        if cond not in component_by_condition:
            component_by_condition[cond] = {}
        for comp in ["static_score", "ast_score", "llm_idiom_score", "llm_comment_score"]:
            component_by_condition[cond].setdefault(comp, []).append(r[comp])

    # CQS per model × condition (averaged over tasks)
    per_model_cqs: dict[str, dict[str, float]] = {}
    for r in full_results:
        model = r["model"]
        preamble = r["preamble"]
        per_model_cqs.setdefault(model, {})
        per_model_cqs[model].setdefault(preamble, [])
        per_model_cqs[model][preamble].append(r["cqs"])
    per_model_cqs_mean = {
        model: {p: float(np.mean(vals)) for p, vals in cond_dict.items()}
        for model, cond_dict in per_model_cqs.items()
    }

    # Summary table
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"\n{'Condition':<20} {'N':<5} {'Mean CQS':<12} {'95% CI':<20} {'MI mean':<10}")
    print("-" * 70)
    for cond in PREAMBLE_ORDER:
        vals = cqs_by_condition.get(cond, [])
        if not vals:
            continue
        mean = np.mean(vals)
        lo, hi = compute_bootstrap_ci(vals)
        mi_vals = [r["maintainability_index"] for r in full_results if r["preamble"] == cond]
        mi_mean = np.mean(mi_vals) if mi_vals else 0.0
        print(f"{PREAMBLE_LABELS[cond]:<20} {len(vals):<5} {mean:.4f}       [{lo:.4f}, {hi:.4f}]  {mi_mean:.1f}")

    # Kruskal-Wallis test
    groups = [cqs_by_condition.get(c, []) for c in PREAMBLE_ORDER if cqs_by_condition.get(c)]
    if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
        kw_stat, kw_p = stats.kruskal(*groups)
        print(f"\nKruskal-Wallis H={kw_stat:.3f}, p={kw_p:.4f}")
        print(f"  -> {'Significant' if kw_p < 0.05 else 'NOT significant'} difference across conditions (alpha=0.05)")
    else:
        print("\nKruskal-Wallis: insufficient data")
        kw_stat, kw_p = 0.0, 1.0

    # Spearman rank stability
    rho = compute_spearman_rank_stability(per_model_cqs_mean)
    print(f"\nSpearman rank stability (mean pairwise rho): {rho:.4f}")
    print(f"  -> {'PASSES' if rho >= 0.6 else 'FAILS'} threshold (>= 0.6)")

    # Expert vs no-preamble delta
    expert_vals = cqs_by_condition.get("real_agent", [])
    none_vals = cqs_by_condition.get("none", [])
    if expert_vals and none_vals:
        delta = np.mean(expert_vals) - np.mean(none_vals)
        print(f"\nExpert preamble vs. no preamble delta: {delta:+.4f}")

    # Save stats summary
    stats_summary = {
        "kruskal_wallis_H": float(kw_stat),
        "kruskal_wallis_p": float(kw_p),
        "spearman_rank_stability_rho": float(rho),
        "spearman_passes_threshold": rho >= 0.6,
        "expert_vs_none_delta": float(np.mean(expert_vals) - np.mean(none_vals)) if expert_vals and none_vals else None,
        "cqs_by_condition": {
            cond: {
                "n": len(vals),
                "mean": float(np.mean(vals)),
                "ci_95_lower": float(compute_bootstrap_ci(vals)[0]),
                "ci_95_upper": float(compute_bootstrap_ci(vals)[1]),
            }
            for cond, vals in cqs_by_condition.items() if vals
        },
    }
    stats_path = RESULTS_DIR / "stats_results.json"
    with open(stats_path, "w") as f:
        json.dump(stats_summary, f, indent=2)
    print(f"\nStats saved to {stats_path}")

    # ---- Visualizations ----
    print("\n[viz] Generating figures...")
    plot_cqs_by_condition(
        cqs_by_condition,
        RESULTS_DIR / "poc_cqs_by_condition.png",
        "PoC: CQS by Preamble Condition (all models, all tasks)",
    )
    plot_component_breakdown(
        component_by_condition,
        RESULTS_DIR / "poc_component_breakdown.png",
    )
    if len(per_model_cqs_mean) >= 2:
        plot_per_model_heatmap(
            per_model_cqs_mean,
            RESULTS_DIR / "poc_per_model_heatmap.png",
        )

    print("\n" + "=" * 60)
    print("PoC complete.")
    print(f"Results in: {RESULTS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
