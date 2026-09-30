"""Warm conversational replies for chat / help / other. No repo scan.

MARS/doctl concatenates harness ``llm.invoke`` token streams into prompt
``text``. Never call ``get_llm()`` / ``llm.invoke`` here.
"""

from __future__ import annotations

from nightly_repo_security_scan.hygiene import hygiene_text
from nightly_repo_security_scan.persona import (
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
    return hygiene_text(template_reply(intent, human_text or ""))
