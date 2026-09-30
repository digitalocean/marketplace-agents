"""Graph state for Nightly Repo Security Scan."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class InputState(TypedDict, total=False):
    """MARS / doctl chat input."""

    messages: Annotated[list[AnyMessage], add_messages]
    repo: str
    ref: str
    trigger: str
    area_hint: str
    fixture_path: str
    force_empty: bool
    force_blocked: bool


class OutputState(TypedDict, total=False):
    """Agent Server / doctl-visible output. Chat text lives in ``messages`` only."""

    messages: Annotated[list[AnyMessage], add_messages]
    status: str
    findings: list[dict[str, Any]]
    fixes: list[dict[str, Any]]
    patch_diff: str
    pr_title: str
    pr_body_md: str
    pr_url: str
    pr_number: int
    skipped: bool
    decision: str
    artifacts: list[str]
    next_hint: str
    stage_summaries: list[str]


class ScanState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: str  # chat | help | scan | scan_plan | other
    skip_plan_confirm: bool
    plan_confirmed: bool
    pending_scan: dict[str, Any]

    repo: str
    ref: str
    trigger: str  # cron | manual
    area_hint: str
    fixture_path: str
    force_empty: bool
    force_blocked: bool

    area: str
    rationale: str
    scope_limits: list[str]

    checkout_path: str
    files_touched_count: int
    commands_run: list[str]

    findings: list[dict[str, Any]]
    fixes: list[dict[str, Any]]
    self_check_pass: bool

    patch_summary: list[str]
    patch_diff: str
    diff_stat: str
    commit_message: str
    pr_title: str
    pr_body_md: str
    branch_name: str

    pending_action: str
    ask_payload: dict[str, Any]
    decision: str  # approve | deny
    pr_url: str
    pr_number: int
    skipped: bool

    status: str  # opened | denied | empty | blocked | error | ok | chat | help
    human_summary: str
    stage_summaries: list[str]
    artifacts: list[str]
    next_hint: str
