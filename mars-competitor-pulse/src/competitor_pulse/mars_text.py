"""Helpers for MARS / doctl prompt ``text`` assembly (production-shaped guards)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from competitor_pulse.chat import contains_watchlist_json

_WATCHLIST_OVERLAY_KEY = "watchlist"


def assemble_doctl_prompt_text(
    graph: Any,
    payload: dict[str, Any],
) -> str:
    """Best-effort model of how ``doctl agent prompt -o json`` builds ``text``.

    Observed production behavior concatenates:
    1. Serialized input ``watchlist`` when the exported input schema includes it
       (often ``[]`` from schema defaults — fixed by omitting ``watchlist`` from
       ``input_schema``)
    2. Each node update's ``human_summary`` (stream bubbles)
    3. Each streamed ``AIMessage`` content
    """
    text = ""
    input_props = (graph.get_input_jsonschema().get("properties") or {})
    if "watchlist" in input_props and "watchlist" in payload:
        text += json.dumps({"watchlist": payload["watchlist"]}, separators=(",", ":"))

    for chunk in graph.stream(payload, stream_mode="updates"):
        for _node, update in chunk.items():
            u = update or {}
            summary = u.get("human_summary")
            if summary:
                text += str(summary)
            for msg in u.get("messages") or []:
                if isinstance(msg, AIMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    text += content
    return text


def last_assistant_text(result: dict[str, Any]) -> str:
    """Plain assistant copy from final ``messages`` (output-schema safe)."""
    for msg in reversed(result.get("messages") or []):
        if isinstance(msg, AIMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
    return ""


def summary_from_assistant_text(text: str) -> str:
    """Human summary portion before optional ``---`` brief separator."""
    if "\n\n---\n\n" in text:
        return text.split("\n\n---\n\n", 1)[0]
    return text


def prepare_programmatic_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Encode ``watchlist`` as a silent JSON HumanMessage (not in ``input_schema``).

    Other invoke keys (``baseline_path``, ``notify``, …) stay top-level because
    they remain in ``InputState``.
    """
    payload = dict(state)
    watchlist = payload.pop("watchlist", None)
    if watchlist is not None:
        existing = payload.get("messages") or []
        msgs = [HumanMessage(content=json.dumps({"watchlist": watchlist}))]
        user_msg = (payload.get("user_message") or "").strip()
        if user_msg:
            msgs.append(HumanMessage(content=user_msg))
        payload["messages"] = [*msgs, *existing]
    return payload


def hi_chat_payload(*, include_empty_watchlist: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "messages": [HumanMessage(content="hi")],
        "allow_net": False,
    }
    if include_empty_watchlist:
        payload["watchlist"] = []
    return payload
