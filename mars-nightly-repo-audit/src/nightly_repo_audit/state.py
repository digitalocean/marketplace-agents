"""Graph state for Nightly Repo Audit."""

from __future__ import annotations

from typing import Any, TypedDict


class FindingRecord(TypedDict, total=False):
    id: str
    severity: str
    path: str
    evidence: str


class AuditState(TypedDict, total=False):
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
    status: str  # opened | denied | empty | blocked | error | ok
    human_summary: str
    stage_summaries: list[str]
    artifacts: list[str]
    next_hint: str
