# /// script
# requires-python = ">=3.11"
# dependencies = ["openai"]
# ///
"""Probe minimax and qwen on the 3 most complex tasks to see what they emit."""
import asyncio, os, re
from openai import AsyncOpenAI

CLIENT = AsyncOpenAI(api_key=os.environ["OPENROUTER_API_KEY"],
                     base_url="https://openrouter.ai/api/v1")

TASKS = {
    "mini_sql_engine": "Implement a small in-memory SQL-like query engine in Python. A Table class holds a list of dict rows. Support: select(*columns), where(predicate), join(other_table, on=lambda l,r: bool), group_by(column), order_by(column, descending=False), limit(n). Composable fluent API. Include type hints and 2-3 usage examples.",
    "kv_store_package": "Design and implement a small Python package for an in-memory key-value store with TTL, atomic updates, and bulk ops. Use stdlib only. Sketch the file layout (you may write each file as a separate ```python:path/file.py``` fenced block) — typical layout: a top-level package, a core module, an optional CLI module, and a tests file. Include type hints and a brief usage example.",
}
MODELS = ["minimax/minimax-m2.5", "qwen/qwen3.5-35b-a3b"]


async def probe(model, task_id, prompt):
    resp = await CLIENT.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=3000,
    )
    text = resp.choices[0].message.content or ""
    fences = re.findall(r"```(?:python(?::[\w./]+)?|py)?\s*\n(.*?)```", text, re.DOTALL)
    return {"model": model, "task": task_id, "len": len(text),
            "fence_count": len(fences), "preview": text[:400]}


async def main():
    jobs = [(m, t, p) for m in MODELS for t, p in TASKS.items()]
    results = await asyncio.gather(*[probe(m, t, p) for m, t, p in jobs])
    for r in results:
        print(f"\n=== {r['model'].split('/')[-1]} | {r['task']} ===")
        print(f"response len: {r['len']} chars, fenced code blocks: {r['fence_count']}")
        print(f"preview:\n{r['preview']}")
        print(f"...({r['len']-400} more chars)" if r['len'] > 400 else "")


asyncio.run(main())
