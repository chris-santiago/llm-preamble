# Generation protocol

How the v2 main run produces one code sample per (preamble × task × model × rep) cell.

**Source of truth:** [`preamble_quality_v2_main.py` lines 474–483](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L474) (constants), [`_post()` at lines 568–632](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L568) (HTTP call), [`generate_one()` at lines 649–675](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L649).

---

## Generation constants

```python
GEN_TEMPERATURE      = 0.3
TRIVIAL_TEMPERATURE  = 1.0
GEN_MAX_TOKENS       = 10000
GEN_TIMEOUT          = 300.0
JUDGE_TEMPERATURE    = 0.0
JUDGE_MAX_TOKENS     = 1800
JUDGE_TIMEOUT        = 120.0
CONCURRENCY          = 50
RETRY_ATTEMPTS       = 2
REPLICATIONS_DEFAULT = 2
```

| Constant | Value | Applies to |
|----------|-------|------------|
| `GEN_TEMPERATURE` | `0.3` | All subject generation except `trivial_baseline` |
| `TRIVIAL_TEMPERATURE` | `1.0` | The `trivial_baseline` condition only (user message is just the task name; needs higher temperature for any coherent response) |
| `GEN_MAX_TOKENS` | `10000` | All subject generation (large enough to fit multi-file `task_kv_store_package` outputs) |
| `GEN_TIMEOUT` | `300.0 s` | Subject request timeout |
| `JUDGE_TEMPERATURE` | `0.0` | All judge calls |
| `JUDGE_MAX_TOKENS` | `1800` | All judge calls |
| `JUDGE_TIMEOUT` | `120.0 s` | Judge request timeout |
| `CONCURRENCY` | `50` | Single `asyncio.Semaphore` shared by all generation and judging tasks. This is the repo-wide default for OpenRouter async scripts; see [project CLAUDE.md](https://github.com/chris-santiago/llm-preamble/blob/main/CLAUDE.md). |
| `RETRY_ATTEMPTS` | `2` | Per `_post()` call, with `1.5 × (attempt + 1)` second backoff |
| `REPLICATIONS_DEFAULT` | `2` | Reps per (preamble × task × model) cell |

---

## Reasoning-effort gating

The reasoning parameter is set per-call based on whether the model is in `REASONING_MODELS`:

```python
# generation
mode = "high" if model in REASONING_MODELS else "off"
# judging
mode = "exclude" if judge_model in REASONING_MODELS else "off"
```

`_post()` then translates `mode` into the wire-level body:

| `mode` | Body field added |
|--------|------------------|
| `"high"` | `"reasoning": {"effort": "high"}` |
| `"exclude"` | `"reasoning": {"exclude": True}` |
| `"off"` | (no `reasoning` field sent) |

This makes reasoning-effort an explicit, audit-logged parameter rather than letting OpenRouter's routing layer choose silently. It was introduced as Amendment A4 after a routing-variability audit. See [models page](models.md#reasoning-parameter-handling).

---

## Retry semantics

`_post()` wraps each request in a retry loop within the `CONCURRENCY` semaphore:

```python
async with sem:
    for attempt in range(RETRY_ATTEMPTS):
        try:
            r = await client.post(...)
            resp = r.json()
            if r.status_code != 200 or "error" in resp:
                last_err = f"HTTP {r.status_code}: ..."
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            # success path
            return { "content": ..., "provider": ..., "cost": ..., "error": None }
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {str(exc)[:150]}"
            await asyncio.sleep(1.5 * (attempt + 1))
return {"content": "", ..., "error": last_err}
```

Failures (HTTP non-200, `error` key in response, or raised exception) trigger a 1.5s × (attempt + 1) sleep and a retry. After `RETRY_ATTEMPTS = 2`, a failure record is returned with `error` populated. **Extraction failures are excluded from scoring; they are never zero-imputed** — see [project CLAUDE.md "Known gotchas"](https://github.com/chris-santiago/llm-preamble/blob/main/CLAUDE.md).

---

## User-message construction

For a normal preamble, the user message is the task prompt verbatim. For `trivial_baseline`, the user message is **only the task name** (e.g. `"task_expr_parser"`):

```python
def build_user_prompt(preamble_id: str, task: dict) -> str:
    if preamble_id == "trivial_baseline":
        return task["name"]
    return task["prompt"]
```

This is what makes `trivial_baseline` a true lower anchor: no system context, no task description — only a label.

---

## Extraction

The model's `content` is passed through [`extract_python_code()` at line 518](../../preamble_quality_experiment_v2/preamble_quality_v2_main.py#L518), which:

1. Tries fenced blocks (` ```python ... ``` ` with optional `:path/file.py` suffix or `py`).
2. Falls back to an unclosed fence.
3. Falls back to raw code starting with `import`/`from`/`def`/`class`/`async def`.
4. Otherwise returns `""` and the sample is marked `extraction_ok=False`.

Multiple fenced blocks (multi-file outputs from `task_kv_store_package`) are joined with `# --- file boundary ---`.

---

## Persistence

Each completed generation is appended to `experiment_v2_results/generations.jsonl` immediately:

```python
async def _one(task, preamble_id, model, rep):
    rec = await generate_one(...)
    _append_jsonl(GEN_FILE, rec)
```

`--resume` re-loads the JSONL and skips any `gen_key` already done. The same pattern applies to `judgments.jsonl`. See [results schema](results-schema.md) for the field-level contents.

Related: [judge protocol](judge-protocol.md) covers the inverse — what the judge sees.
