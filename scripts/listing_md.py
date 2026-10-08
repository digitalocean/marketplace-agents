"""Parse Marketplace catalog copy from listings/<slug>.md."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_LOGO_RE = re.compile(r"^logo:\s*(\S+)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ListingFields:
    name: Optional[str]
    logo_url: Optional[str]
    summary: str
    description: str
    getting_started: Optional[str]


def parse_listing_md(text: str) -> ListingFields:
    """Extract Vendor Portal fields from a listing markdown file."""
    lines = text.replace("\r\n", "\n").split("\n")

    logo_url: Optional[str] = None
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped:
            idx += 1
            continue
        if stripped.startswith("# "):
            break
        match = _LOGO_RE.match(stripped)
        if match:
            logo_url = match.group(1)
            idx += 1
            continue
        break

    name: Optional[str] = None
    if idx < len(lines) and lines[idx].startswith("# "):
        name = lines[idx][2:].strip()
        idx += 1

    body = "\n".join(lines[idx:]).lstrip("\n")
    sections = _split_h2_sections(body)

    summary = sections.get("Summary", "").strip()
    description_block = sections.get("Description", "").strip()
    description, getting_started = _split_description(description_block)

    return ListingFields(
        name=name,
        logo_url=logo_url,
        summary=summary,
        description=description,
        getting_started=getting_started,
    )


def listing_fields_to_custom_data(fields: ListingFields) -> dict[str, str]:
    """Map parsed fields to Vendor Portal customData string keys."""
    out: dict[str, str] = {
        "summary": fields.summary,
        "description": fields.description,
    }
    if fields.logo_url:
        out["logoUrl"] = fields.logo_url
    if fields.getting_started:
        out["gettingStarted"] = fields.getting_started
    return out


def _split_h2_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: Optional[str] = None
    buf: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        else:
            buf.append(line)

    if current is not None:
        sections[current] = "\n".join(buf).strip()

    return sections


def _split_description(description: str) -> tuple[str, Optional[str]]:
    if not description:
        return "", None

    intro: list[str] = []
    chunks: list[tuple[str, list[str]]] = []
    current_h3: Optional[str] = None
    buf: list[str] = []

    for line in description.splitlines():
        if line.startswith("### "):
            if current_h3 is None:
                intro = buf[:]
            else:
                chunks.append((current_h3, buf[:]))
            current_h3 = line[4:].strip()
            buf = []
        else:
            buf.append(line)

    if current_h3 is None:
        return description.strip(), None

    chunks.append((current_h3, buf[:]))

    getting_started: Optional[str] = None
    desc_parts: list[str] = []
    if intro:
        intro_text = "\n".join(intro).strip()
        if intro_text:
            desc_parts.append(intro_text)

    for title, lines in chunks:
        body = "\n".join(lines).strip()
        if title.casefold() == "getting started":
            getting_started = body or None
        else:
            desc_parts.append(f"### {title}\n\n{body}" if body else f"### {title}")

    return "\n\n".join(desc_parts).strip(), getting_started
