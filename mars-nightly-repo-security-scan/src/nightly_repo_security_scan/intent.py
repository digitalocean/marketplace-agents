"""Early intent routing for MARS chat, before gather / scan."""

from __future__ import annotations

import re

_CHAT_RE = re.compile(
    r"^(?:"
    r"hi|hello|hey|yo|sup|howdy|hiya|"
    r"good\s+(?:morning|afternoon|evening)|"
    r"what'?s\s+up|whats\s+up|"
    r"please|thanks|thank\s+you|thx|cheers|nice|cool|"
    r"lol|haha|ha|"
    r"bye|goodbye|see\s+ya|later"
    r")\s*[!.?]*$",
    re.IGNORECASE,
)

_PLAN_CONFIRM_RE = re.compile(
    r"^(?:"
    r"yes|y|go|run\s+it|do\s+it|looks\s+good|ok|okay|"
    r"approve|approved"
    r")\s*[!.?]*$",
    re.IGNORECASE,
)

_DECISION_DENY_RE = re.compile(
    r"^(?:deny|denied|no|n)\s*[!.?]*$",
    re.IGNORECASE,
)

_SCAN_REQUEST_RE = re.compile(
    r"(?:"
    r"^\s*scan\b|"
    r"^\s*audit\b|"
    r"nightly\s+security\b|"
    r"security\s+scan\b|"
    r"\bscan\s+(?:the\s+)?(?:repo|slice|area|src)\b|"
    r"\brun\s+(?:an?\s+)?(?:scan|audit)\b|"
    r"\bprepare\s+(?:a\s+)?draft\s+pr\b|"
    r"\b(?:scan|audit)\s+[\w.-]+/"
    r")",
    re.IGNORECASE,
)

_HELP_RE = re.compile(
    r"\b("
    r"what\s+do\s+you\s+do|"
    r"who\s+are\s+you|"
    r"what\s+are\s+you|"
    r"how\s+does\s+(?:this|it)\s+work|"
    r"how\s+do\s+(?:i|we)\s+(?:use|scan|audit|open|start|run)|"
    r"what\s+can\s+you\s+do|"
    r"help(?:\s+me)?|"
    r"explain|"
    r"capabilities|"
    r"limitations?|limits?|"
    r"getting\s+started|"
    r"instructions?"
    r")\b",
    re.IGNORECASE,
)

_SLUG_RE = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b")
_REF_RE = re.compile(r"\bon\s+([A-Za-z0-9_.-]+)(?![\w./-])")
_AREA_RE = re.compile(r"\barea\s+([A-Za-z0-9_./-]+)")


def is_chat_message(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return bool(_CHAT_RE.match(stripped))


def is_scan_request(text: str) -> bool:
    """Domain run language. Route to scan_plan before meta help."""
    stripped = (text or "").strip()
    if not stripped:
        return False
    return bool(_SCAN_REQUEST_RE.search(stripped))


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


def is_decision_deny(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return bool(_DECISION_DENY_RE.match(stripped))


def is_decision_token(text: str) -> bool:
    return is_plan_confirm(text) or is_decision_deny(text)


def parse_scan_target(text: str) -> dict[str, str]:
    """Pull owner/name, ref, and area out of a chat line when present."""
    raw = text or ""
    slug = _SLUG_RE.search(raw)
    ref_match = _REF_RE.search(raw)
    area_match = _AREA_RE.search(raw)
    ref = ""
    if ref_match and "/" not in ref_match.group(1):
        ref = ref_match.group(1).strip(".,")
    area = ""
    if area_match:
        area = area_match.group(1).strip(".,")
    return {
        "repo": slug.group(1) if slug else "",
        "ref": ref,
        "area": area,
    }


def classify_intent(
    human_text: str,
    *,
    programmatic_scan: bool = False,
    pending_scan: dict | None = None,
) -> str:
    """Return chat | help | scan | scan_plan | plan_denied | other."""
    text = (human_text or "").strip()
    if pending_scan:
        if is_plan_confirm(text):
            return "scan"
        if is_decision_deny(text):
            return "plan_denied"
    if is_decision_token(text) and not pending_scan:
        return "other"
    if is_scan_request(text):
        return "scan_plan"
    if is_help_message(text):
        return "help"
    if is_chat_message(text):
        return "chat"
    if text:
        return "scan_plan"
    if programmatic_scan:
        return "scan"
    return "other"
