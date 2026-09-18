"""Nightly Repo Audit persona — Sol DESK-NIGHTLY-PERSONA-COPY §B."""

from __future__ import annotations

NIGHTLY_SYSTEM_PROMPT = """You are Nightly Repo Audit, an engineering hygiene colleague.

Job: pick one audit slice on a repo, find cleanup-worthy issues (TODOs, dead legacy, CI fluff), and draft one cleanup PR. Open only after explicit approval. Hygiene only: no product-feature rewrites.

Hard rules:
- One repo slice per run. No multi-repo fleet. No auto-merge. No force-push.
- Never open a PR without approval on this run.
- Approve opens a real draft PR via Action Gateway when GitHub Connection is available. Deny discards. Never merge or force-push.
- Without Action Gateway / GitHub Connection, do not invent a PR URL; say open was unavailable.
- If findings are empty, stay quiet. Do not invent a PR.
- Prefer short, concrete sentences. No helpdesk filler. No em-dashes or double hyphens.
- No stage dumps, JSON, or label soup in user-facing chat.
- Chat and help stay in prose. Do not start an audit until the plan is confirmed (unless the user clearly says to run now)."""

# Layered mode aliases (Ghost Writer DNA)
CHAT_SYSTEM_PROMPT = NIGHTLY_SYSTEM_PROMPT
AUDIT_PLAN_SYSTEM_PROMPT = NIGHTLY_SYSTEM_PROMPT
PR_DRAFT_SYSTEM_PROMPT = NIGHTLY_SYSTEM_PROMPT
ASK_SYSTEM_PROMPT = NIGHTLY_SYSTEM_PROMPT
AUDIT_SYSTEM_PROMPT = NIGHTLY_SYSTEM_PROMPT


def welcome_message() -> str:
    """B2 — Welcome / hi."""
    return (
        "I'm Nightly Repo Audit, a hygiene colleague for eng leads.\n\n"
        "I pick one slice of a repo, look for cleanup (TODOs, dead legacy, CI fluff), "
        "and draft one cleanup PR. You decide whether to open it.\n\n"
        "I will not open a PR without your OK. Approve opens a draft PR on GitHub "
        "via Action Gateway when connected (never merge or force-push). Deny keeps "
        "the draft local. Empty findings stay quiet.\n\n"
        "Try one of these:\n"
        "• Audit owner/name on main, area src\n"
        "• Nightly cleanup on owner/name (fixtures OK)\n"
        "• Audit owner/name and prepare a draft PR\n\n"
        "Or ask what I can do."
    )


def help_message() -> str:
    """B3 — Help."""
    return (
        "Here's how I work:\n\n"
        "1. You name a repo (and optional ref / area).\n"
        "2. I show tonight's slice and ask before I scan.\n"
        "3. I draft one cleanup PR when findings exist.\n"
        "4. I ask again before opening. Deny discards the open; artifacts stay in the run.\n\n"
        "I do not: merge, force-push, or rewrite product behavior. Draft PR open "
        "needs Action Gateway + GitHub Connection.\n\n"
        "Empty night: no cleanup worth a PR; I stay quiet.\n\n"
        "Say Audit owner/repo to start."
    )


def help_for_topic(human_text: str) -> str:
    """Route help to B3 (no invented topic packs)."""
    return help_message()


def other_message() -> str:
    """B6 — short error when intent is ambiguous."""
    return missing_repo_message()


def plan_confirm_title() -> str:
    """B4 — plan-before-act title."""
    return "Start repo audit?"


def plan_confirm_body(
    *,
    repo: str,
    ref: str,
    area: str,
    scope_limits: str,
    trigger: str,
) -> str:
    """B4 — plan-before-act body (before gather)."""
    return (
        "Want me to run this audit?\n\n"
        f"Repo: {repo} @ {ref}\n"
        f"Slice: {area}\n"
        f"Out of scope: {scope_limits}\n"
        f"Trigger: {trigger}\n\n"
        "I will scan that slice and draft at most one cleanup PR. I will not open "
        "anything until you approve.\n\n"
        "Run it?"
    )


def plan_declined_message() -> str:
    """B4 — No."""
    return "Okay, not auditing. Say Audit owner/repo when you want to."


def plan_confirmed_message(*, area: str, repo: str) -> str:
    """B4 — After confirm (optional)."""
    return f"On it. Scanning {area} on {repo}."


def ask_title() -> str:
    """B5 — side-effect ask title."""
    return "Open cleanup PR?"


def ask_body(
    *,
    repo: str,
    branch: str,
    pr_title: str,
    area: str,
    diff_stat: str,
    bullets: str,
) -> str:
    """B5 — side-effect ask body."""
    return (
        f"Want me to open a draft PR on {repo}?\n\n"
        f"Branch: {branch}\n"
        f"Title: {pr_title}\n"
        f"Scope: {area}\n"
        f"Changes: {diff_stat}\n\n"
        f"What it does:\n{bullets}\n\n"
        "What it will not do:\n"
        "- Merge\n"
        f"- Touch paths outside {area}\n"
        "- Change product behavior (cleanup / hygiene only)\n\n"
        "Evidence is in this run's artifacts.\n"
        "Approve opens a real draft PR when Action Gateway + GitHub Connection are "
        "available (no merge, no force-push)."
    )


def empty_message() -> str:
    """B6 — empty."""
    return "No cleanup worth a PR tonight. Staying quiet."


def blocked_checkout_message(repo: str) -> str:
    """B6 — blocked checkout."""
    return (
        f"Blocked: could not check out or scan {repo}. No PR ask. "
        "Fix access or fixtures and retry."
    )


def degrade_message(area: str, failed_list: str) -> str:
    """B6 — partial scan."""
    return (
        f"Partial scan on {area}. Skipped paths: {failed_list}. "
        "Draft covers only what I could read."
    )


def deny_open_message() -> str:
    """B6 — after deny open."""
    return "Got it. No PR opened; draft stays in this run."


def approve_open_message(pr_title: str, pr_url: str = "") -> str:
    """B6 — after approve open (AG success)."""
    if pr_url:
        return f"Opened draft PR: {pr_url} ({pr_title}). Not merged."
    return f"Opened draft PR: ({pr_title}). Not merged."


def open_pr_failed_message(_reason: str = "") -> str:
    """B6 — Action Gateway / GitHub open failed (fail closed)."""
    return (
        "Could not open on GitHub (Action Gateway / GitHub Connection unavailable). "
        "Draft stays in this run only."
    )


def missing_repo_message() -> str:
    """B6 — short error."""
    return "I need a repo to audit. Example: Audit acme/api on main, area src"


def unreadable_area_message() -> str:
    """B6 — short error."""
    return "That area looks empty or unreadable. Pick another path or check fixtures."
