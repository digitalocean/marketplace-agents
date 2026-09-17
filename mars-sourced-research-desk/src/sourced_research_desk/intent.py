"""Early intent routing for MARS chat — before gather / research workflow."""

from __future__ import annotations

import re

_CHAT_RE = re.compile(
    r"^(?:"
    r"hi|hello|hey|yo|sup|howdy|hiya|"
    r"good\s+(?:morning|afternoon|evening)|"
    r"what'?s\s+up|whats\s+up|"
    r"run|go|start|"
    r"please|thanks|thank\s+you|thx|cheers|nice|cool|"
    r"lol|haha|ha|"
    r"bye|goodbye|see\s+ya|later"
    r")\s*[!.?]*$",
    re.IGNORECASE,
)

_PLAN_CONFIRM_RE = re.compile(
    r"^(?:yes|y|go|run\s+it|do\s+it|looks\s+good|ok|okay)\s*[!.?]*$",
    re.IGNORECASE,
)

_HELP_RE = re.compile(
    r"\b("
    r"what\s+do\s+you\s+do|"
    r"who\s+are\s+you|"
    r"what\s+are\s+you|"
    r"how\s+does\s+(?:this|it)\s+work|"
    r"how\s+do\s+(?:i|we)\s+(?:use|research|send|start|run)|"
    r"what\s+can\s+you\s+do|"
    r"help(?:\s+me)?|"
    r"explain|"
    r"capabilities|"
    r"limitations?|limits?|"
    r"getting\s+started|"
    r"instructions?|"
    r"sources?|"
    r"citations?|"
    r"outbound|"
    r"approve|"
    r"deny"
    r")\b",
    re.IGNORECASE,
)


def is_chat_message(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return bool(_CHAT_RE.match(stripped))


def is_help_message(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return bool(_HELP_RE.search(stripped))


def is_plan_confirm(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return bool(_PLAN_CONFIRM_RE.match(stripped))


def classify_intent(
    human_text: str,
    *,
    has_question: bool = False,
    pending_research: dict | None = None,
) -> str:
    """Return chat | help | research | research_plan | other."""
    text = (human_text or "").strip()
    if pending_research and is_plan_confirm(text):
        return "research"
    if is_help_message(text):
        return "help"
    if is_chat_message(text):
        return "chat"
    if text:
        return "research_plan"
    if has_question:
        return "research"
    return "other"
