"""Harness-native ChatOpenAI factory.

Prefers HARNESS_INFERENCE_* env vars; falls back to OPENAI_*.
The pinned model for this agent is Grok 4.7.
"""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_MODEL = "grok-4.7"


def resolve_llm_env() -> dict[str, str | None]:
    """Resolve base_url, api_key, model from harness env first, then OPENAI_*."""
    base_url = os.environ.get("HARNESS_INFERENCE_BASE_URL") or os.environ.get(
        "OPENAI_BASE_URL"
    )
    api_key = os.environ.get("HARNESS_INFERENCE_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    model = (
        os.environ.get("HARNESS_INFERENCE_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or DEFAULT_MODEL
    )
    return {"base_url": base_url, "api_key": api_key, "model": model}


def harness_env_available() -> bool:
    """True when a usable API key is present (harness or OpenAI)."""
    return bool(
        os.environ.get("HARNESS_INFERENCE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


def get_llm(**kwargs: Any):
    """Return a ChatOpenAI client wired for MARS harness or local OpenAI-compatible."""
    from langchain_openai import ChatOpenAI

    resolved = resolve_llm_env()
    if not resolved["api_key"]:
        raise RuntimeError(
            "No inference API key set. Export HARNESS_INFERENCE_API_KEY "
            "(preferred) or OPENAI_API_KEY."
        )
    params: dict[str, Any] = {
        "model": resolved["model"],
        "api_key": resolved["api_key"],
    }
    if resolved["base_url"]:
        params["base_url"] = resolved["base_url"]
    params.update(kwargs)
    return ChatOpenAI(**params)


def _review_enabled() -> bool:
    flag = os.environ.get("SECURITY_SCAN_LLM_REVIEW", "").strip().lower()
    if flag not in {"1", "true", "yes"}:
        return False
    if os.environ.get("ALLOW_NET") == "0":
        return False
    return harness_env_available()


def draft_review_note(findings: list[dict[str, Any]]) -> str:
    """Optional Grok review note for the PR body.

    Fixes stay deterministic. This only writes a short summary when
    ``SECURITY_SCAN_LLM_REVIEW`` is on and an inference key is set.
    Failures return an empty string so the scan still drafts.
    """
    if not _review_enabled() or not findings:
        return ""
    brief = [
        {
            "kind": item.get("kind"),
            "path": item.get("path"),
            "fix": item.get("fix"),
        }
        for item in findings[:12]
    ]
    prompt = (
        "You are Nightly Repo Security Scan. Write two short sentences "
        "summarizing these defensive fixes for a draft pull request. "
        "Do not describe how to exploit anything. No em dashes.\n"
        f"{json.dumps(brief)}"
    )
    try:
        response = get_llm(temperature=0).invoke(prompt)
    except Exception:
        return ""
    content = getattr(response, "content", "")
    return content if isinstance(content, str) else str(content)
