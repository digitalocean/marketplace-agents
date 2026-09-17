"""Graph state for Nightly Repo Audit."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class FindingRecord(TypedDict, total=False):
    id: str
    severity: str
    path: str
    evidence: str


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
    """Agent Server / doctl-visible output — chat text lives in ``messages`` only."""

    messages: Annotated[list[AnyMessage], add_messages]
    status: str
    findings: list[dict[str, Any]]
    pr_title: str
    pr_body_md: str
    pr_url: str
    pr_number: int
    skipped: bool
    decision: str
    artifacts: list[str]
    next_hint: str
    stage_summaries: list[str]


class AuditState(TypedDict, total=False):
    # MARS chat
    messages: Annotated[list[AnyMessage], add_messages]
    intent: str  # chat | help | audit | other

    # Intake
    repo: str
    ref: str
    trigger: str  # cron | manual
    area_hint: str
    fixture_path: str  # v1: in-repo fixtures/sample_repo
    force_empty: bool  # test helper: skip findings
    force_blocked: bool  # test helper: simulate checkout failure

    # Plan
    area: str
    rationale: str
    scope_limits: list[str]

    # Gather
    checkout_path: str
    files_touched_count: int
    commands_run: list[str]

    # Analyze
    findings: list[dict[str, Any]]
    self_check_pass: bool

    # Draft
    patch_summary: list[str]
    diff_stat: str
    commit_message: str
    pr_title: str
    pr_body_md: str
    branch_name: str

    # Ask / act
    pending_action: str
    ask_payload: dict[str, Any]
    decision: str  # approve | deny
    pr_url: str
    pr_number: int
    skipped: bool

    # Report
    status: str  # opened | denied | empty | blocked | error | ok | chat | help
    human_summary: str
    stage_summaries: list[str]
    artifacts: list[str]
    next_hint: str
