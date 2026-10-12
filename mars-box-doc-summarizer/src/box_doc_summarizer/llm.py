"""Leak-safe inference (playbook §5.8): direct HTTP ``/chat/completions`` with ``stream: false``.

Prefers HARNESS_INFERENCE_* env vars; falls back to OPENAI_*. Never uses
``llm.invoke`` so token streams cannot leak into MARS chat text.
"""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


def resolve_llm_env() -> dict[str, str | None]:
    base_url = os.environ.get("HARNESS_INFERENCE_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("HARNESS_INFERENCE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = (
        os.environ.get("HARNESS_INFERENCE_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or DEFAULT_MODEL
    )
    return {"base_url": base_url, "api_key": api_key, "model": model}


def harness_env_available() -> bool:
    if os.environ.get("BOX_SUMMARIZER_LLM", "1").strip() == "0":
        return False
    return bool(resolve_llm_env()["api_key"])


def chat_completion(
    system: str,
    user: str,
    *,
    max_tokens: int = 700,
    temperature: float = 0.2,
    timeout: float = 90.0,
) -> str | None:
    """Return assistant text or None on any failure (callers fall back to heuristics)."""
    if not harness_env_available():
        return None
    import requests

    env = resolve_llm_env()
    url = (env["base_url"] or DEFAULT_BASE_URL).rstrip("/") + "/chat/completions"
    payload: dict[str, Any] = {
        "model": env["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {env['api_key']}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=timeout,
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        content = data["choices"][0]["message"].get("content") or ""
        return content.strip() or None
    except Exception:  # noqa: BLE001 — offline fallback is the contract
        return None


def parse_json_object(text: str | None) -> dict[str, Any] | None:
    """Best-effort JSON object extraction from a model reply."""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(s[start : end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None
