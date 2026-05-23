# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Probe deepseek/deepseek-v4-flash + google/gemini-2.5-flash, 2 calls each."""
import asyncio, os, re
import httpx

MODELS = [
    "deepseek/deepseek-v4-flash",
    "google/gemini-2.5-flash",
]

PROMPT = (
    "Implement a small in-memory SQL-like query engine in Python. A Table class holds "
    "a list of dict rows. Support: select(*columns), where(predicate), join(other, "
    "on=lambda l,r: bool), group_by(column), order_by(column, descending=False), "
    "limit(n). Fluent composable API. Type hints, 2-3 usage examples."
)


async def one_call(client, model, label):
    print(f"\n========== {model} | call {label} ==========")
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
                "max_tokens": 8000,
            },
            timeout=120,
        )
        body = r.json()
        if r.status_code != 200 or "error" in body:
            print(f"HTTP {r.status_code}: {body.get('error', body)}")
            return
        print(f"model returned: {body.get('model')}")
        print(f"provider: {body.get('provider')}")
        choice = body.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        finish = choice.get("finish_reason")
        usage = body.get("usage", {})
        rt = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        ct = usage.get("completion_tokens", 0)
        cost = usage.get("cost", 0)
        fences = re.findall(r"```(?:python)?\s*\n(.*?)```", content, re.DOTALL)
        print(f"finish: {finish} | content: {len(content)} chars, {len(fences)} fences "
              f"| reasoning: {len(reasoning)} chars | completion_tokens: {ct} "
              f"(reasoning: {rt}) | cost: ${cost:.4f}")
        if content:
            print(f"content preview: {content[:200]}")
        else:
            print(f"NO CONTENT — reasoning preview: {reasoning[:200]}")
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {str(e)[:300]}")


async def main():
    async with httpx.AsyncClient() as client:
        for m in MODELS:
            await one_call(client, m, "1")
            await one_call(client, m, "2")


asyncio.run(main())
