"""Graph state for Competitor Pulse."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class WatchItem(TypedDict, total=False):
    name: str
    urls: dict[str, str]


class PulseState(TypedDict, total=False):
    # MARS chat passes messages; intake parses JSON from HumanMessage
    messages: Annotated[list[AnyMessage], add_messages]

    # Chat / intake (tests and legacy invoke)
    user_message: str
    chat_ack: str
    intent: str  # chat | help | pulse | other

    # Intake
    watchlist: list[dict[str, Any]]
    notify: bool
    channel: str
    fixture_dir: str
    baseline_path: str
    snapshot_dir: str
    allow_net: bool
    force_empty: bool  # test: treat as non-material
    force_material: bool  # test helper (unused if baseline diverges)
    force_blocked: bool

    # Plan
    modules: list[str]
    run_id: str

    # Gather
    snapshots: list[dict[str, Any]]

    # Analyze
    deltas: list[dict[str, Any]]
    baseline_captures: list[dict[str, Any]]
    first_run: bool
    material: bool

    # Draft
    brief_md: str
    counterpositions: list[str]
    delta_count: int
    notify_draft: str

    # Ask / act
    pending_action: str
    ask_payload: dict[str, Any]
    decision: str  # approve | deny
    notified: bool
    notify_id: str
    skipped: bool
    baseline_updated: bool

    # Report
    status: str  # empty | notified | denied | blocked | error | ok | baseline
    human_summary: str
    stage_summaries: list[str]
    artifacts: list[str]
    next_hint: str
