# /// script
# requires-python = ">=3.11"
# dependencies = ["openai", "httpx"]
# ///
"""Probe qwen/qwen3.6-flash: is it a reasoning model? Does it emit code?"""
import asyncio, os, json, re
import httpx

MODEL = "qwen/qwen3.6-flash"

TASKS = {
    "lru_ttl_cache": "Write a Python class implementing a thread-safe LRU cache with per-entry TTL. O(1) get/put, thread-safe, type hints, brief usage example. Don't use functools.lru_cache.",
    "mini_sql_engine": "Implement a small in-memory SQL-like query engine in Python. Table class holds list of dict rows. Support: select(*columns), where(predicate), join(other, on=lambda l,r: bool), group_by(column), order_by(column, descending=False), limit(n). Fluent composable API. Type hints, 2-3 examples.",
}


async def call_one(client, task_id, prompt):
    r = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 3000,
        },
        timeout=60,
    )
    body = r.json()
    print(f"\n=== {MODEL} / {task_id} ===")
    print(f"HTTP status: {r.status_code}")
    if "error" in body:
        print(f"API error: {body['error']}")
        return
    choice = body.get("choices", [{}])[0]
    msg = choice.get("message", {})
    content = msg.get("content")
    reasoning = msg.get("reasoning")
    finish = choice.get("finish_reason")
    print(f"finish_reason: {finish}")
    print(f"content present: {content is not None and len(content) > 0}")
    print(f"reasoning present: {reasoning is not None and len(reasoning) > 0}")
    if content:
        fences = re.findall(r"```(?:python)?\s*\n(.*?)```", content, re.DOTALL)
        print(f"content len: {len(content)} chars, fenced code blocks: {len(fences)}")
        print(f"content preview:\n{content[:400]}")
    if reasoning:
        print(f"reasoning len: {len(reasoning)} chars")
        print(f"reasoning preview: {reasoning[:200]}")
    print(f"usage: {body.get('usage')}")


async def main():
    async with httpx.AsyncClient() as client:
        for t, p in TASKS.items():
            try:
                await call_one(client, t, p)
            except Exception as e:
                print(f"\n=== {MODEL} / {t} ===")
                print(f"EXCEPTION: {type(e).__name__}: {e}")


asyncio.run(main())
