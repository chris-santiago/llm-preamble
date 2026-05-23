# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Full-diagnostic probe of google/gemini-3.1-flash-lite at max_tokens=8000.

Runs the same call twice to see if behavior is variable.
Prints the FULL response shape for inspection.
"""
import asyncio, os, re, json
import httpx

MODEL = "google/gemini-3.1-flash-lite"
PROMPT = (
    "Implement a small in-memory SQL-like query engine in Python. A Table class holds "
    "a list of dict rows. Support: select(*columns), where(predicate), join(other, "
    "on=lambda l,r: bool), group_by(column), order_by(column, descending=False), "
    "limit(n). Fluent composable API. Type hints, 2-3 usage examples."
)


async def one_call(client, label):
    r = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0.3,
            "max_tokens": 8000,
        },
        timeout=120,
    )
    print(f"\n========== call {label} ==========")
    print(f"HTTP status: {r.status_code}")
    body = r.json()

    # Top-level shape (without burying us in reasoning text)
    print(f"top-level keys: {list(body.keys())}")
    if "error" in body:
        print(f"ERROR: {body['error']}")
        return

    print(f"model returned: {body.get('model')}")
    print(f"provider: {body.get('provider')}")

    choice = body.get("choices", [{}])[0]
    print(f"finish_reason: {choice.get('finish_reason')}")
    print(f"native_finish_reason: {choice.get('native_finish_reason')}")

    msg = choice.get("message", {})
    msg_keys = list(msg.keys())
    print(f"message keys: {msg_keys}")
    content = msg.get("content")
    reasoning = msg.get("reasoning")
    print(f"content: {'<NULL>' if content is None else f'{len(content)} chars'}")
    print(f"reasoning: {'<NULL>' if reasoning is None else f'{len(reasoning)} chars'}")
    if content:
        fences = re.findall(r"```(?:python(?::[\w./]+)?|py)?\s*\n(.*?)```", content, re.DOTALL)
        print(f"content has {len(fences)} fenced code block(s)")
        print(f"--- content first 300 chars ---")
        print(content[:300])
        print(f"--- content last 200 chars ---")
        print(content[-200:])

    usage = body.get("usage", {})
    print(f"usage: completion={usage.get('completion_tokens')}, "
          f"reasoning={usage.get('completion_tokens_details', {}).get('reasoning_tokens')}, "
          f"cost=${usage.get('cost'):.4f}")


async def main():
    async with httpx.AsyncClient() as client:
        await one_call(client, "1")
        await one_call(client, "2")


asyncio.run(main())
