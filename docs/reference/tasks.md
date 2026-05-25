# Tasks

The v2 main run uses **7 Python coding tasks**: 5 creation (one of which is multi-file) and 2 refactor. Each task is run under every (preamble × model × rep) cell.

**Source of truth:** [`preamble_quality_v2_main.py` lines 278–399](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L278) (the `TASKS` list).

The task `task_modeflag_sort` was dropped during pre-flight Phase B (Amendment A2) after a behavior-only spec eliminated the smell across all conditions, leaving no discriminative space.

---

## Tasks at a glance

| ID | Category | Short description |
|----|----------|-------------------|
| `task_lru_ttl_cache` | creation | Thread-safe LRU cache with per-entry TTL |
| `task_expr_parser` | creation | Recursive-descent arithmetic expression parser |
| `task_mini_sql_engine` | creation | In-memory SQL-like query engine with fluent API |
| `task_rate_limiter_family` | creation | Four rate-limiter algorithms behind one interface |
| `task_kv_store_package` | multifile_creation | Multi-file KV store package (stdlib only) |
| `task_flag_class` | refactor | Refactor boolean-flag class with global state |
| `task_exception_pyramid` | refactor | Flatten nested try/except pyramids |

---

## Creation tasks (5)

### `task_lru_ttl_cache`

**Name.** Thread-safe LRU cache with per-entry TTL.

> Write a Python class implementing a thread-safe LRU cache with per-entry TTL expiry.
> Requirements: O(1) get and put; per-entry TTL (entries expire independently); LRU eviction (among non-expired entries; expired entries opportunistically reaped); thread-safe; `get(key)` returns value if present and not expired, else None; `put(key, value, ttl_seconds)` stores the entry; `size()` returns the count of non-expired entries. Include type hints and a brief usage example at the bottom. Do not use `functools.lru_cache` or any third-party caching library.

Activates `concurrency_safety` and `example_quality` rubric dimensions.

### `task_expr_parser`

**Name.** Recursive-descent arithmetic expression parser and evaluator.

> Write a Python recursive-descent parser and evaluator for arithmetic expressions. Supports integers and floats, `+`, `-`, `*`, `/`, `**` (right-associative), unary minus. Correct operator precedence: `**` > unary minus > `*` `/` > `+` `-`. Parentheses for grouping. Tokenizer + parser + evaluator. Public API: `evaluate(expression: str) -> float`. Include type hints. Include at least 3 usage examples covering precedence, parentheses, and unary minus.

Activates `example_quality`; does not activate `concurrency_safety`. This is the single task used for all three confound probes (see [`confound_probes.py`](../../preamble_quality_experiment_v2/confound_probes.py)).

### `task_mini_sql_engine`

**Name.** In-memory SQL-like query engine with fluent composable API.

> Implement a small in-memory SQL-like query engine in Python. A `Table` class holds a list of dict rows. Support: `select(*columns)`, `where(predicate)`, `join(other_table, on=lambda l,r: bool)`, `group_by(column)`, `order_by(column, descending=False)`, `limit(n)`. Composable fluent API. Include type hints and 2–3 usage examples.

Activates `example_quality`.

### `task_rate_limiter_family`

**Name.** Family of rate limiters behind a single interface.

> Implement a family of rate limiters in Python behind a single interface: token bucket, leaky bucket, sliding-window-log, sliding-window-counter. All implement an `allow(client_id) -> bool` method. Each algorithm is its own class but they share an interface (base class or protocol). Include type hints, brief usage example showing each in use.

Activates `example_quality`; `concurrency_safety` is plausible but not stated.

### `task_kv_store_package`

**Name.** Multi-file KV store package. **Category: `multifile_creation`** (not `creation`).

> Design and implement a small Python package for an in-memory key-value store with TTL, atomic updates, and bulk ops. Use stdlib only. Sketch the file layout (you may write each file as a separate ```python:path/file.py``` fenced block) — typical layout: a top-level package, a core module, an optional CLI module, and a tests file. Include type hints and a brief usage example.

The only multi-file task. Extraction joins fenced blocks on `# --- file boundary ---` (see [`extract_python_code()` at line 518](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L518)).

---

## Refactor tasks (2)

Both refactor tasks ship a "before" code block (`TASK5_BEFORE`, `TASK6_BEFORE`) embedded in the prompt and demand the model return a single refactored block.

### `task_flag_class`

**Name.** Refactor boolean-flag class with global state into clean design.

> Refactor the following Python code. The class uses boolean mode-flags to select behavior variants at runtime, and relies on hidden module-global state for caching and statistics. […]
> - Eliminate boolean mode-flags; use composition, strategy pattern, or explicit subclasses
> - Remove all module-global state; the class must be fully self-contained and independently testable
> - Preserve all observable behaviors (filtering, deduplication, normalization, validation, caching, statistics)
> - The refactored code must be importable and safe for concurrent use across multiple instances
> - Add type hints where missing

The "before" code is `TASK5_BEFORE`, defined in [`preamble_quality_v2_main.py`](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py) above the `TASKS` list.

### `task_exception_pyramid`

**Name.** Flatten exception pyramid: make errors explicit and loud.

> Refactor the following Python code. It uses deeply nested try/except blocks with broad exception catches and silently swallows most errors. […]
> - Eliminate all nested try/except structures — maximum 1 level of nesting
> - Remove all bare `except Exception: pass` clauses; every exception must either be re-raised, logged with full context, or converted to a specific typed exception
> - Preserve the function signature: `load_and_merge_configs(primary_path, override_path=None)`
> - The function should still return a merged dict (or `{}` on missing primary)
> - Make all error conditions visible: callers should be able to distinguish 'primary config missing' from 'primary config malformed' from 'override malformed'
> - Add type hints

The "before" code is `TASK6_BEFORE`.

---

## Creation vs. refactor stratification

The v2 hypothesis predicts a **larger preamble effect on creation tasks than on refactor tasks** — refactor prompts are tightly constrained by the input code and leave less surface for preamble-driven craft choices. The per-task and category-stratified CQS tables are in [`experiment_v2_results/REPORT.md`](../../preamble_quality_experiment_v2/experiment_v2_results/REPORT.md) §3.

For the user-message construction (including the `trivial_baseline` override where the user message is just the task name), see [`build_user_prompt()` at line 642](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L642).
