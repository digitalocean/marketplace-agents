"""Shared helpers for Nightly Repo Audit graph tests."""

from __future__ import annotations

from typing import Any

from nightly_repo_audit.mars_text import last_assistant_text


def assistant_summary(result: dict[str, Any]) -> str:
    text = last_assistant_text(result)
    if text:
        return text
    return (result.get("human_summary") or "").strip()
