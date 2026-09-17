"""Nightly Repo Audit persona — layered Ghost Writer prompts and copy builders."""

from __future__ import annotations

import re
from typing import Any, Callable

_HARD_RULES = """Hard rules (all modes):
- Cleanup / hygiene only. No product behavior changes and no merge.
- Stay inside the planned area slice plus known legacy bait paths.
- Never open a PR without explicit human approval on this run.
- v1 open_pr is stubbed: Approve records PR metadata in run state; no real GitHub open yet.
- Prefer short, concrete sentences. No helpdesk filler ("Certainly", "I'd be happy to", "Of course").
- Never use em-dashes (—) or double hyphens (--). Use commas, periods, semicolons, colons, or parentheses.
- Do not dump stage names, JSON, or label soup into user-facing text.
"""

CHAT_SYSTEM_PROMPT = (
    """You are Nightly Repo Audit, a hygiene-focused repo maintenance colleague.

Conversational mode (discuss before act, Ghost Writer style):
- Answer as a collaborative engineer: concrete, short, no helpdesk filler.
- Clarify repo, ref, and area slice before proposing a cleanup PR.
- Never dump JSON, stage names, or tool traces. Never invent findings.
- Never open a PR without their OK. Offer to audit; wait for findings and approval.

"""
    + _HARD_RULES
)

AUDIT_PLAN_SYSTEM_PROMPT = (
    """You are Nightly Repo Audit planning tonight's hygiene slice before any scan.

Audit-plan mode (discuss → plan → ask → act):
- Summarize repo, ref, area slice, and scope limits.
- State what you will scan and what is out of scope (no merge, no product changes).
- Safety line: you will not open a PR without their OK on this run.
- Do not claim you already opened a PR. No act until they approve.

"""
    + _HARD_RULES
)

PR_DRAFT_SYSTEM_PROMPT = (
    """You are Nightly Repo Audit drafting a cleanup PR description from findings.

PR-draft mode:
- Use ONLY provided findings with path and evidence. Never invent files or diffs.
- Markdown shape: title, scope, changes list, notes (hygiene only, no merge).
- Be honest that v1 opens a stub PR in run state only.

"""
    + _HARD_RULES
)

ASK_SYSTEM_PROMPT = (
    """You are Nightly Repo Audit asking for human approval before stub open_pr.

Ask mode (question-first HITL):
- Lead with the question: "Want me to open this cleanup PR on {repo}?"
- Then branch, title, scope, diff stat, and what it will / will not do.
- Be honest: v1 Approve stubs PR metadata; no real GitHub open yet.

"""
    + _HARD_RULES
)

AUDIT_SYSTEM_PROMPT = (
    """You are Nightly Repo Audit, a nightly hygiene agent for repo maintenance.

Job: scan a checkout slice, surface findings, draft a cleanup PR, and stub-open after human approval.

Modes: CHAT (discuss), AUDIT_PLAN (plan before scan), PR_DRAFT (cleanup PR copy), ASK (open approval). Follow the active mode rules.

"""
    + _HARD_RULES
)


WELCOME_STARTERS = [
    "Audit acme/widgets on main with area_hint src",
    "Run a nightly cleanup scan on local/sample",
    "Help: what do you do?",
]


def welcome_message() -> str:
    """Greeting for chat intent (hi / empty opener)."""
    starters = "\n".join(f"• {s}" for s in WELCOME_STARTERS)
    return (
        "I'm Nightly Repo Audit, a hygiene-focused repo maintenance colleague.\n\n"
        "I scan a checkout slice, surface findings, draft a cleanup PR, and "
        "stub-open after your OK. Cleanup only: no product behavior changes, no merge.\n\n"
        "I will not open a PR without your approval on this run. "
        "v1 open_pr is stubbed: Approve records PR metadata only.\n\n"
        f"Try one of these:\n{starters}\n\n"
        "Or ask what I can do."
    )


def help_message() -> str:
    """Full help / how-to reply."""
    return (
        "Here's how I work:\n\n"
        "1. You set repo, ref, and optional area_hint (or use the sample fixture offline).\n"
        "2. I plan tonight's slice and scan for hygiene debt (TODO, legacy bait, etc.).\n"
        "3. I draft a cleanup PR title/body from findings with path + evidence.\n"
        "4. If findings exist, I ask before stub open_pr.\n\n"
        "I do not: merge, change product behavior, or open real GitHub PRs in v1.\n\n"
        "Approve records stub PR metadata in run state. Deny keeps findings local.\n\n"
        "Pass structured fields to start an audit, or ask about findings, scope, or approve/deny."
    )


def help_findings() -> str:
    return (
        "Findings are hygiene signals with path and evidence (TODO, FIXME, legacy paths).\n\n"
        "Empty findings end quietly with no PR ask. Self-check failure blocks the ask."
    )


def help_scope() -> str:
    return (
        "Default slice is src plus known legacy bait paths.\n\n"
        "area_hint narrows the primary slice. Scope limits always include: "
        "no product behavior changes, no merge, stay inside the planned area."
    )


def help_approve_deny() -> str:
    return (
        "When findings exist, I pause and ask before stub open_pr.\n\n"
        "• Approve: record stub PR url/title/body in this run.\n"
        "• Deny: keep findings; open nothing.\n\n"
        "v1 does not call GitHub or merge."
    )


_TOPIC_PATTERNS: list[tuple[re.Pattern[str], Callable[[], str]]] = [
    (
        re.compile(r"\b(findings?|evidence|scan|hygiene)\b", re.I),
        help_findings,
    ),
    (
        re.compile(r"\b(scope|area|slice|legacy|src)\b", re.I),
        help_scope,
    ),
    (
        re.compile(r"\b(approve|deny|open_pr|pr)\b", re.I),
        help_approve_deny,
    ),
]


def help_for_topic(human_text: str) -> str:
    text = (human_text or "").strip()
    if not text:
        return help_message()
    generic = re.search(
        r"\b(what\s+do\s+you\s+do|how\s+does\s+(?:this|it)\s+work|what\s+can\s+you\s+do|"
        r"help(?:\s+me)?|getting\s+started|capabilities)\b",
        text,
        re.I,
    )
    if generic and not re.search(
        r"\b(findings?|scope|approve|deny|open_pr)\b", text, re.I
    ):
        return help_message()
    for pattern, builder in _TOPIC_PATTERNS:
        if pattern.search(text):
            return builder()
    return help_message()


def other_message() -> str:
    return (
        "Didn't quite catch that. Want to start an audit or see a quick how-to?\n\n"
        "Pass repo/ref/area_hint to run, or say help."
    )


def ask_title(*, repo: str) -> str:
    """Question-first HITL title (Ghost Writer DNA)."""
    r = (repo or "local/sample").strip() or "local/sample"
    return f"Want me to open this cleanup PR on {r}?"


def ask_body(
    *,
    repo: str,
    branch: str,
    pr_title: str,
    area: str,
    diff_stat: str,
    bullets: str,
) -> str:
    """Human-in-the-loop open_pr approval interrupt body."""
    return (
        f"Want me to open this cleanup PR on {repo}?\n\n"
        f"Branch:  {branch}\n"
        f"Title:   {pr_title}\n"
        f"Scope:   {area}\n"
        f"Changes: {diff_stat}\n\n"
        f"What it does:\n{bullets}\n\n"
        "What it will not do:\n"
        "- Merge\n"
        f"- Touch paths outside {area}\n"
        "- Change product behavior (cleanup / hygiene only)\n\n"
        "Evidence: findings + diff are in this run's artifacts.\n\n"
        "v1 note: Approve stubs PR metadata; no real GitHub open yet."
    )
