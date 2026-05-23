# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Probe deepseek/deepseek-v4-flash at max_tokens=10000, 2 calls."""
import asyncio, os, re
import httpx

PROMPT = (
    "Implement a small in-memory SQL-like query engine in Python. A Table class holds "
    "a list of dict rows. Support: select(*columns), where(predicate), join(other, "
    "on=lambda l,r: bool), group_by(column), order_by(column, descending=False), "
    "limit(n). Fluent composable API. Type hints, 2-3 usage examples."
)


async def call_one(client, label):
    print(f"\n=== deepseek-v4-flash call {label} ===", flush=True)
    try:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek/deepseek-v4-flash",
                "messages": [{"role": "user", "content": PROMPT}],
                "temperature": 0.3,
                "max_tokens": 10000,
            },
            timeout=180,
        )
        body = r.json()
        if "error" in body:
            print(f"  API error: {body['error']}", flush=True)
            return
        print(f"  model returned: {body.get('model')}", flush=True)
        c = body["choices"][0]
        msg = c["message"]
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        u = body.get("usage", {})
        rt = u.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        ct = u.get("completion_tokens", 0)
        cost = u.get("cost", 0)
        fences = re.findall(r"```(?:python)?\s*\n(.*?)```", content, re.DOTALL)
        print(f"  finish={c['finish_reason']} content={len(content)}c {len(fences)}fences "
              f"reasoning={len(reasoning)}c tokens={ct} (reasoning={rt}) cost=${cost:.4f}",
              flush=True)
        if content:
            print(f"  content preview: {content[:200]}", flush=True)
        elif reasoning:
            print(f"  NO CONTENT — reasoning preview: {reasoning[:200]}", flush=True)
    except Exception as e:
        print(f"  EXC: {type(e).__name__}: {e}", flush=True)


async def main():
    async with httpx.AsyncClient() as client:
        await call_one(client, "1")
        await call_one(client, "2")


asyncio.run(main())
