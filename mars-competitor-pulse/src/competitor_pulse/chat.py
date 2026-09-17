"""Chat-facing helpers: parse operator text, format acks — never emit raw JSON."""

from __future__ import annotations

import re
from typing import Any

ASSISTANT_DISPLAY_NAME = "Competitor Pulse"

_MODULE_LABELS = {
    "site": "homepage",
    "pricing": "pricing",
    "changelog": "changelog",
    "careers": "careers",
}


def parse_track_message(text: str) -> list[dict[str, Any]] | None:
    """Extract a watchlist from natural language like 'track fedex' or 'watch FedEx'."""
    if not text or not text.strip():
        return None
    lowered = text.strip().lower()
    m = re.search(
        r"\b(?:track|watch|monitor|pulse|add)\s+([a-z0-9][a-z0-9\s&.\-]{0,40})",
        lowered,
        re.I,
    )
    if not m:
        return None
    raw = m.group(1).strip()
    raw = re.sub(r"\s+(please|now|today|for me)$", "", raw, flags=re.I)
    raw = re.sub(r"\s+competitors?$", "", raw, flags=re.I)
    if not raw:
        return None
    # Multi-unknown names should fall through to blocked intake, not guess URLs.
    if re.search(r"\s+and\s+", raw, flags=re.I):
        return None
    name = " ".join(part.capitalize() for part in raw.split())
    slug = re.sub(r"[^a-z0-9]+", "", name.lower())
    base = slug or "competitor"
    return [
        {
            "name": name,
            "urls": {
                "site": f"https://www.{base}.com/",
                "pricing": f"https://www.{base}.com/pricing",
                "changelog": f"https://www.{base}.com/changelog",
                "careers": f"https://www.{base}.com/careers",
            },
        }
    ]


def format_watch_ack(
    watchlist: list[dict[str, Any]],
    *,
    allow_net: bool,
    from_chat: bool = False,
) -> str:
    """Plain-English acknowledgment — never JSON."""
    if not watchlist:
        return "No competitors on the watchlist yet."
    names = [((w.get("name") or "").strip() or "Unknown") for w in watchlist]
    if len(names) == 1:
        lead = f"Got it — setting up a watch on **{names[0]}**."
    else:
        lead = f"Got it — watching **{', '.join(names)}**."
    pages: list[str] = []
    for item in watchlist:
        urls = item.get("urls") or {}
        mods = [_MODULE_LABELS.get(k, k) for k in urls if urls.get(k)]
        if mods:
            pages.append(f"{item.get('name')}: {', '.join(mods)}")
    pages_line = ""
    if pages:
        pages_line = "\nPublic pages: " + "; ".join(pages) + "."
    fetch_mode = (
        "Live public fetch is **on**."
        if allow_net
        else "Using offline fixtures (live fetch off)."
    )
    suffix = ""
    if from_chat:
        suffix = "\nI'll pull snapshots and compare against any saved baseline."
    return f"{lead}{pages_line}\n{fetch_mode}{suffix}"


def looks_like_watchlist_json(text: str) -> bool:
    """Detect raw planner / invoke JSON that must not surface in chat."""
    if not text:
        return False
    t = text.strip()
    return (
        t.startswith('{"watchlist"')
        or t.startswith('{"watchlist":')
        or t.startswith('{"competitors"')
        or t.startswith('{"competitors":')
    )


_STATE_LIST_JSON_RE = re.compile(
    r'\{\s*"(?:watchlist|competitors)"\s*:', re.IGNORECASE
)


def contains_watchlist_json(text: str) -> bool:
    """True when text includes raw watchlist/competitors state JSON (chat guards)."""
    if not text:
        return False
    return bool(_STATE_LIST_JSON_RE.search(text))
