"""Chat intent + Box folder id parsing (regex fast path; no LLM needed)."""

from __future__ import annotations

import re

_FOLDER_URL_RE = re.compile(r"box\.com/(?:folder|s/[^/\s]+/folder)/(\d+)", re.I)
_FOLDER_ID_RE = re.compile(r"\bfolder\s*(?:id\s*)?[:#]?\s*(\d{3,})\b", re.I)
_BARE_ID_RE = re.compile(r"\b(\d{6,})\b")
_HELP_RE = re.compile(r"^\s*(help|\?|what can you do|how does (this|it) work)", re.I)
_HI_RE = re.compile(r"^\s*(hi|hey|hello|yo|good (morning|afternoon|evening))\b[\s!.]*$", re.I)
_SUMMARIZE_RE = re.compile(r"\b(summari[sz]e|brief|digest|exec(utive)? summary|refresh|re-?run|run)\b", re.I)


def parse_folder_id(text: str) -> str:
    if not text:
        return ""
    for rx in (_FOLDER_URL_RE, _FOLDER_ID_RE, _BARE_ID_RE):
        m = rx.search(text)
        if m:
            return m.group(1)
    return ""


def classify_intent(text: str) -> str:
    """Return chat | help | summarize."""
    t = (text or "").strip()
    if not t or _HI_RE.match(t):
        return "chat"
    if _HELP_RE.match(t):
        return "help"
    if parse_folder_id(t) or _SUMMARIZE_RE.search(t):
        return "summarize"
    return "chat"
