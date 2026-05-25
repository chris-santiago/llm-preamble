# System prompt vs user message — the channel-asymmetry between preamble and plan

> A natural worry about v2 is that the experiment measured preambles
> delivered as `system=` via OpenRouter, but production agent workflows
> might deliver agent instructions in some other channel. This page
> documents the wire-format verification: the production Claude Code
> subagent-dispatch path puts the agent definition's prose into the
> **system prompt** slot, exactly the same slot v2 measured. v2's
> findings transfer to production at the channel level.

## Why the channel matters

The [attention-allocation mechanism](attention-allocation-mechanism.md)
relies on the preamble functioning as *directive content*. Directive
content has stronger instruction-following authority when delivered in
the system slot than when delivered as user-message text. If v2's
preambles were in the system slot but production "preambles" actually
landed in user-message content, the v2 effect sizes could systematically
mis-estimate the production effect — possibly by a large factor.

The verification below confirms that this concern does not apply for
Claude Code subagent dispatch. The two wire formats match.

## v2's wire format (measured)

In `preamble_quality_v2_main.py`, every subject-side generation call
delivers the preamble in the OpenAI/OpenRouter `system` role:

```python
messages = [
    {"role": "system", "content": preamble_text},
    {"role": "user",   "content": task_prompt},
]
```

This is the standard OpenAI-format `messages` array. The `system` role
corresponds to the API's system-prompt slot — the channel with the
strongest instruction-following authority on every commercial LLM API
that supports the role distinction.

## Production wire format (Claude Code subagent dispatch)

The Anthropic documentation for Claude Code subagents and the Agent
SDK is explicit about which slot the agent definition's prose
occupies. Two pages are load-bearing:

- <https://code.claude.com/docs/en/sub-agents>
- <https://code.claude.com/docs/en/agent-sdk/subagents>

### Agent SDK reference: `prompt` is the agent's system prompt

The Agent SDK `AgentDefinition` reference table is unambiguous. The
`prompt` field is documented verbatim as:

> **`prompt`** — *The agent's system prompt defining its role and
> behavior.*

This is the same field that an agent definition fills with its prose
instructions (the persona, role, behavioral directives, dimension
enumeration, and so on). On dispatch, this field's contents become the
**subagent's system prompt** — not user-message content, not appended
to a parent prompt, but the system slot of the subagent's own
conversation.

### "What subagents inherit": parent system prompt is **not** passed down

The same Agent SDK page documents inheritance for subagent dispatches.
The "What subagents inherit" table is explicit:

> A subagent receives its **own system prompt** (`AgentDefinition.prompt`).
> A subagent **does NOT receive the parent's system prompt**.

This is the structural fact that pins the channel mapping. Each
subagent runs in its own conversation context. Its system prompt is
exactly the `prompt` field from its `AgentDefinition` — nothing more
on the system side. The parent's instructions, however carefully
written, are not concatenated, prepended, or otherwise leaked into
the subagent's system slot.

### Plan content is delivered as user-message content

When the parent dispatches a subagent via the Agent tool, the
`prompt` parameter on the Agent tool call (which is distinct from the
`AgentDefinition.prompt` field) carries the task description — the
"do this work" content. That parameter lands in the subagent's
**user-message** slot, not its system slot. It is read by the
subagent as the first user turn of a fresh conversation, with the
agent definition's `prompt` field sitting above it as the system
prompt.

This is the same shape as v2's wire format: agent prose in `system`,
task content in `user`.

## The channel mapping, summarized

| Component | v2 measurement (OpenRouter) | Production (Claude Code subagent) |
|---|---|---|
| Preamble / agent role prose | `messages[0]` with `role: "system"` | Subagent system prompt (`AgentDefinition.prompt`) |
| Task / plan content | `messages[1]` with `role: "user"` | Subagent user message (Agent tool's `prompt` parameter) |

The two columns match at the channel level. v2's preambles were
delivered in exactly the slot that production subagent dispatches use
for agent-role content. The instruction-following weight v2 measured
is the same instruction-following weight an `AgentDefinition.prompt`
field carries on dispatch.

## The asymmetry: preamble channel vs plan channel

The channel mapping has a sharper consequence than just "v2 transfers".
It also clarifies a structural asymmetry between two things that
agentic workflows often treat as interchangeable.

**Preamble channel (system slot, strong authority).** The agent
definition's `prompt` field, delivered in the subagent's system
prompt, carries the full instruction-following weight of the system
slot. This is the channel where v2 measured preamble effects.

**Plan channel (user slot, weaker authority).** Content delivered via
the Agent tool's `prompt` parameter — the task description, the
implementation plan, the step-by-step guidance — lands in the
subagent's user-message slot. User-message content has weaker
instruction-following authority than system-prompt content. The model
treats it as the current request, not as standing role-level
directives.

This is the wire-format basis for the
[enumeration vs demonstration](enumeration-vs-demonstration.md) claim:
a planner's structural choices, embedded in a plan, reach the executor
through the user channel; the executor's craft-dimension enumeration
reaches the executor through the system channel. The two channels are
not equivalent at the API level, and the v2 evidence on attention
allocation operates on the system channel.

The practical implication is concrete. If you want an executor's craft
dimensions to move, the lever is the agent definition's `prompt` field
(which becomes the subagent's system prompt). Pouring more directive
content into the plan — which lands in the user slot — does not give
the model the same signal.

## What this does not establish

The wire-format match is necessary but not sufficient for full
production transfer. The match guarantees the channel is the same; it
does not guarantee the absolute effect sizes are the same. Several
factors could still drift between v2 and production:

- **Model.** v2's pool was 10 OpenRouter-routed models; production
  Claude Code subagents typically run on a specific Anthropic model.
  Effect sizes vary across models even within v2 (see the model RE
  variance in `CONCLUSIONS.md`).
- **Tasks.** v2 measured on 7 single-file (mostly) tasks; production
  agentic work is multi-turn and multi-file.
- **Context length.** Production preambles can be much longer than v2's
  tested preambles (the `python_coder_agent` condition was the largest
  v2 tested, at ~3,000 tokens).
- **Tool use.** v2 was single-turn code generation; production
  subagents use tools.

What the channel match *does* establish is that the v2 findings are
not invalidated by a wire-format mismatch. The same effect mechanism
(attention allocation on preamble content) operates in the same slot
(the system prompt) in both v2 and production subagent dispatch.

## Sources

- Anthropic Claude Code documentation:
  <https://code.claude.com/docs/en/sub-agents>
- Anthropic Agent SDK subagents documentation:
  <https://code.claude.com/docs/en/agent-sdk/subagents>
- `preamble_quality_experiment_v2/preamble_quality_v2_main.py` — v2 wire
  format (system+user messages array on every subject-side call).
- The [attention-allocation mechanism](attention-allocation-mechanism.md)
  page, which depends on the system-slot delivery this page verifies.
- The [enumeration vs demonstration](enumeration-vs-demonstration.md)
  page, which uses the system-vs-user channel asymmetry as its
  structural premise.
