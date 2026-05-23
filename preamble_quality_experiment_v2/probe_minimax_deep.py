# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Deep diagnostic on minimax/minimax-m2.5 reasoning behavior.

Three calls:
  A. No reasoning param specified (current default behavior).
  B. Explicitly enable reasoning via OpenRouter's `reasoning: {"effort": "high"}` param.
  C. Explicitly disable reasoning via `reasoning: {"exclude": true}`.

Dumps full message shape so we can see if reasoning is hidden in any field.
"""
import asyncio, os, re, json
import httpx

PROMPT = (
    "Implement a small in-memory SQL-like query engine in Python. A Table class holds "
    "a list of dict rows. Support: select(*columns), where(predicate), join(other, "
    "on=lambda l,r: bool), group_by(column), order_by(column, descending=False), "
    "limit(n). Fluent composable API. Type hints, 2-3 usage examples."
)


async def call_with(client, label, body_extra):
    print(f"\n=========== {label} ===========", flush=True)
    print(f"extra body: {json.dumps(body_extra)}", flush=True)
    base = {
        "model": "minimax/minimax-m2.5",
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.3,
        "max_tokens": 10000,
    }
    base.update(body_extra)
    try:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
            },
            json=base,
            timeout=180,
        )
        body = r.json()
        if r.status_code != 200 or "error" in body:
            print(f"HTTP {r.status_code}: {body.get('error', body)}", flush=True)
            return
        print(f"model returned: {body.get('model')}", flush=True)
        print(f"provider: {body.get('provider')}", flush=True)
        c = body["choices"][0]
        msg = c["message"]
        print(f"message keys: {list(msg.keys())}", flush=True)
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        reasoning_details = msg.get("reasoning_details")
        u = body.get("usage", {})
        ctd = u.get("completion_tokens_details", {})
        fences = re.findall(r"```(?:python)?\s*\n(.*?)```", content, re.DOTALL)
        print(f"finish: {c['finish_reason']}", flush=True)
        print(f"content: {len(content)}c, {len(fences)} fences", flush=True)
        print(f"reasoning field: {len(reasoning)}c", flush=True)
        if reasoning_details is not None:
            print(f"reasoning_details: {type(reasoning_details).__name__} = {str(reasoning_details)[:300]}", flush=True)
        else:
            print(f"reasoning_details: <not present>", flush=True)
        print(f"usage: completion_tokens={u.get('completion_tokens')}, reasoning_tokens={ctd.get('reasoning_tokens', 0)}, cost=${u.get('cost', 0):.4f}", flush=True)
        if content:
            print(f"content preview: {content[:200]}", flush=True)
        if reasoning:
            print(f"reasoning preview: {reasoning[:200]}", flush=True)
    except Exception as e:
        print(f"EXC: {type(e).__name__}: {e}", flush=True)


async def main():
    async with httpx.AsyncClient() as client:
        await call_with(client, "A. default (no reasoning param)", {})
        await call_with(client, "B. reasoning effort=high", {"reasoning": {"effort": "high"}})
        await call_with(client, "C. reasoning exclude=true", {"reasoning": {"exclude": True}})


asyncio.run(main())
