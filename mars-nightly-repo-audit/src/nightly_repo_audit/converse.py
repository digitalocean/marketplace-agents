"""Warm conversational replies for chat / help / other — no repo scan.

MARS/doctl concatenates harness ``llm.invoke`` token streams into prompt
``text``. Never call ``get_llm()`` / ``llm.invoke`` here. Offline → persona
templates so chat stays prose-once and leak-safe.
"""

from __future__ import annotations

from nightly_repo_audit.hygiene import hygiene_text
from nightly_repo_audit.intent import is_chat_message, is_help_message
from nightly_repo_audit.persona import (
    help_for_topic,
    other_message,
    plan_declined_message,
    welcome_message,
)


def template_reply(intent: str, human_text: str = "") -> str:
    if intent == "plan_denied":
        return plan_declined_message()
    if intent == "help":
        return help_for_topic(human_text)
    if intent == "other":
        return other_message()
    return welcome_message()


def conversational_reply(intent: str, human_text: str) -> str:
    """Persona templates for MARS chat (no LangChain llm.invoke on this path)."""
    text = human_text or ""
    if intent == "help" and text and is_help_message(text):
        return hygiene_text(template_reply(intent, text))
    if intent == "chat" and text and is_chat_message(text):
        return hygiene_text(template_reply(intent, text))
    if intent in {"chat", "help"}:
        return hygiene_text(template_reply(intent, text))
    return hygiene_text(template_reply(intent, text))
