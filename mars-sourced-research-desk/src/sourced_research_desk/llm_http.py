"""Direct HTTP inference for plan/gather LLM paths (MARS leak-safe §5.8).

Never use LangChain ``llm.invoke`` for user-visible chat/intent/parse on these paths.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from sourced_research_desk.llm import harness_env_available, resolve_llm_env
from sourced_research_desk.persona import RESEARCH_PLAN_SYSTEM_PROMPT


def chat_completions(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.0,
    max_tokens: int = 400,
    timeout_s: float = 20.0,
) -> str | None:
    """POST /chat/completions with stream:false. Returns content or None."""
    if not harness_env_available():
        return None
    resolved = resolve_llm_env()
    api_key = resolved.get("api_key")
    if not api_key:
        return None
    base = (resolved.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model = resolved.get("model") or "gpt-4o-mini"
    url = f"{base}/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
        choices = payload.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = " ".join(
                part.get("text", str(part)) if isinstance(part, dict) else str(part)
                for part in content
            )
        text = str(content or "").strip()
        return text or None
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
    ):
        return None
    except Exception:
        return None


def plan_from_llm(question: str) -> str | None:
    """LLM research plan text; None → caller uses deterministic plan."""
    prompt = (
        "You plan web research. Given a question, return exactly two lines:\n"
        "SUBQUESTIONS: pipe-separated short subquestions (3 max)\n"
        "QUERIES: pipe-separated search queries (3 max)\n"
        f"Question: {question}"
    )
    return chat_completions(
        [
            {"role": "system", "content": RESEARCH_PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=300,
    )


def suggest_urls_from_llm(question: str) -> str | None:
    """LLM-suggested public URLs (one per line). None → skip."""
    prompt = (
        "Suggest up to 3 public https URLs (one per line, URL only) that "
        f"would help research: {question}\n"
        "Prefer well-known docs, news, or official sites. No commentary."
    )
    return chat_completions(
        [
            {"role": "system", "content": RESEARCH_PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=200,
    )
