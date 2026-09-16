"""Graph state for Sourced Research Desk."""

from __future__ import annotations

from typing import Any, TypedDict


class SourceRecord(TypedDict, total=False):
    url: str
    title: str
    fetched_at: str
    ok: bool
    text: str
    published_date: str
    error: str


class ClaimRecord(TypedDict, total=False):
    claim: str
    url: str
    date: str
    quote: str
    confidence: str


class ConflictRecord(TypedDict, total=False):
    topic: str
    summary: str
    urls: list[str]


class ResearchState(TypedDict, total=False):
    # Intake
    question: str
    audience: str
    outbound: str  # none | slack | email
    freshness_days: int
    destination: str
    subject: str
    seed_urls: list[str]
    fixture_sources: list[dict[str, Any]]

    # Plan
    subquestions: list[str]
    search_queries: list[str]

    # Gather / analyze / draft
    sources: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    brief_md: str
    claim_count: int
    oldest_source_date: str
    newest_source_date: str
    unsourced: bool

    # Ask / act
    pending_action: str
    channel: str
    draft_message: str
    ask_payload: dict[str, Any]
    decision: str  # approve | deny
    message_id: str
    skipped: bool
    sent: bool

    # Report
    status: str  # ok | blocked | denied | empty | error
    human_summary: str
    stage_summaries: list[str]
