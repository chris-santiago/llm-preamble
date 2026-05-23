# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Probe the 3 candidate reasoning models at max_tokens=8000.

Confirms each emits parseable content (not pure reasoning) on one hard task.
"""
import asyncio, os, re
import httpx

MODELS = [
    "google/gemini-3.1-flash-lite",
    "qwen/qwen3.6-flash",
    "minimax/minimax-m2.5",
]

PROMPT = (
    "Implement a small in-memory SQL-like query engine in Python. A Table class holds "
    "a list of dict rows. Support: select(*columns), where(predicate), join(other, "
    "on=lambda l,r: bool), group_by(column), order_by(column, descending=False), "
    "limit(n). Fluent composable API. Type hints, 2-3 usage examples."
)

MAX_TOKENS = 8000


async def probe(client, model):
    print(f"\n=== {model} (max_tokens={MAX_TOKENS}) ===")
    try:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": PROMPT}],
                "temperature": 0.3,
                "max_tokens": MAX_TOKENS,
            },
            timeout=120,
        )
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}: {r.text[:300]}")
            return
        body = r.json()
        if "error" in body:
            print(f"  API error: {body['error']}")
            return
        choice = body.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        finish = choice.get("finish_reason")
        usage = body.get("usage", {})
        rt = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        ct = usage.get("completion_tokens", 0)
        cost = usage.get("cost", 0)

        fences = re.findall(r"```(?:python(?::[\w./]+)?|py)?\s*\n(.*?)```", content, re.DOTALL)
        print(f"  finish_reason: {finish}")
        print(f"  content len: {len(content)} chars, fenced blocks: {len(fences)}")
        print(f"  reasoning len: {len(reasoning)} chars")
        print(f"  completion_tokens: {ct} (reasoning: {rt}, content: {ct - rt})")
        print(f"  cost: ${cost:.4f}")
        if content:
            print(f"  content preview: {content[:200]}")
        else:
            print(f"  NO CONTENT — reasoning preview: {reasoning[:200]}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {str(e)[:300]}")


async def main():
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[probe(client, m) for m in MODELS])


asyncio.run(main())
