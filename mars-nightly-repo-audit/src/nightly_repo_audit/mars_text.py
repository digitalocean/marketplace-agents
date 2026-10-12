"""Helpers for MARS / doctl prompt ``text`` assembly (production-shaped guards)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

_STREAM_PROSE_KEYS = ("human_summary", "converse_reply", "chat_ack")


def assemble_doctl_prompt_text(graph: Any, payload: dict[str, Any]) -> str:
    """Best-effort model of how ``doctl agent prompt -o json`` builds ``text``."""
    text = ""
    seen_ai: set[str] = set()

    for chunk in graph.stream(payload, stream_mode="updates"):
        for _node, update in chunk.items():
            u = update or {}
            for key in _STREAM_PROSE_KEYS:
                val = u.get(key)
                if val:
                    text += str(val)
            for msg in u.get("messages") or []:
                if isinstance(msg, AIMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if content not in seen_ai:
                        text += content
                        seen_ai.add(content)

    final_state = graph.invoke(payload)
    for msg in (final_state or {}).get("messages") or []:
        if isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if content not in seen_ai:
                text += content
                seen_ai.add(content)
    return text


def last_assistant_text(result: dict[str, Any]) -> str:
    for msg in reversed(result.get("messages") or []):
        if isinstance(msg, AIMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
    return ""


def hi_chat_payload() -> dict[str, Any]:
    return {"messages": [HumanMessage(content="hi")]}
