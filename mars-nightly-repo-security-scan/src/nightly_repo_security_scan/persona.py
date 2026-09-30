"""Nightly Repo Security Scan persona."""

from __future__ import annotations

SCAN_SYSTEM_PROMPT = """You are Nightly Repo Security Scan, a security-fix colleague for eng leads.

Job: pick one slice of a repo, find application problems, bugs, and dependency pins below a patched release, apply those fixes, and draft one pull request. Open only after explicit approval.

Hard rules:
- One repo slice per run. No multi-repo fleet. No auto-merge. No force-push.
- Never open a PR without approval on this run.
- Approve opens a real draft PR via Action Gateway when GitHub Connection is available. Deny discards. Never merge or force-push.
- Fixes are defensive: patch the code and bump vulnerable pins. Do not describe how to exploit a finding.
- Without Action Gateway / GitHub Connection, do not invent a PR URL; say open was unavailable.
- If findings are empty, stay quiet. Do not invent a PR.
- Prefer short, concrete sentences. No helpdesk filler. No em-dashes or double hyphens.
- No stage dumps, JSON, or label soup in user-facing chat.
- Chat and help stay in prose. Do not start a scan until the plan is confirmed (unless the user clearly says to run now)."""

CHAT_SYSTEM_PROMPT = SCAN_SYSTEM_PROMPT
SCAN_PLAN_SYSTEM_PROMPT = SCAN_SYSTEM_PROMPT
PR_DRAFT_SYSTEM_PROMPT = SCAN_SYSTEM_PROMPT
ASK_SYSTEM_PROMPT = SCAN_SYSTEM_PROMPT


def welcome_message() -> str:
    return (
        "I'm Nightly Repo Security Scan, a security-fix colleague for eng leads.\n\n"
        "I pick one slice of a repo, look for application problems, bugs, and "
        "dependency pins that are still on a vulnerable release, apply the fixes, "
        "and draft one pull request. You decide whether to open it.\n\n"
        "I will not open a PR without your OK. Approve opens a draft PR on GitHub "
        "via Action Gateway when connected (never merge or force-push). Deny keeps "
        "the draft local. Empty findings stay quiet.\n\n"
        "I use Grok 4.7 for the review note when inference is configured. "
        "The fixes themselves are deterministic.\n\n"
        "Try one of these:\n"
        "• Scan owner/name on main, area src\n"
        "• Nightly security scan on owner/name (fixtures OK)\n"
        "• Scan owner/name and prepare a draft PR\n\n"
        "Or ask what I can do."
    )


def help_message() -> str:
    return (
        "Here's how I work:\n\n"
        "1. You name a repo (and optional ref / area).\n"
        "2. I show the slice and ask before I scan.\n"
        "3. I fix application problems, bugs, and vulnerable dependency pins, "
        "then draft one PR when findings exist.\n"
        "4. I ask again before opening. Deny discards the open; artifacts stay in the run.\n\n"
        "I do not: merge, force-push, or rewrite product features. Draft PR open "
        "needs Action Gateway + GitHub Connection.\n\n"
        "Empty night: nothing to fix; I stay quiet.\n\n"
        "Say Scan owner/repo to start."
    )


def help_for_topic(human_text: str) -> str:
    return help_message()


def other_message() -> str:
    return missing_repo_message()


def plan_confirm_title() -> str:
    return "Start security scan?"


def plan_confirm_body(
    *,
    repo: str,
    ref: str,
    area: str,
    scope_limits: str,
    trigger: str,
) -> str:
    return (
        "Want me to run this security scan?\n\n"
        f"Repo: {repo} @ {ref}\n"
        f"Slice: {area}\n"
        f"Out of scope: {scope_limits}\n"
        f"Trigger: {trigger}\n\n"
        "I will scan that slice for application problems, bugs, and vulnerable "
        "dependency pins, apply fixes, and draft at most one PR. I will not open "
        "anything until you approve.\n\n"
        "Run it?"
    )


def plan_declined_message() -> str:
    return "Okay, not scanning. Say Scan owner/repo when you want to."


def plan_confirmed_message(*, area: str, repo: str) -> str:
    return f"On it. Scanning {area} on {repo}."


def ask_title() -> str:
    return "Open security fix PR?"


def ask_body(
    *,
    repo: str,
    branch: str,
    pr_title: str,
    area: str,
    diff_stat: str,
    bullets: str,
) -> str:
    return (
        f"Want me to open a draft PR on {repo}?\n\n"
        f"Branch: {branch}\n"
        f"Title: {pr_title}\n"
        f"Scope: {area}\n"
        f"Changes: {diff_stat}\n\n"
        f"What it does:\n{bullets}\n\n"
        "What it will not do:\n"
        "- Merge\n"
        "- Force-push\n"
        f"- Touch paths outside {area} except root dependency manifests\n"
        "- Rewrite product features (security fixes only)\n\n"
        "Evidence is in this run's artifacts.\n"
        "Approve opens a real draft PR when Action Gateway + GitHub Connection are "
        "available (no merge, no force-push)."
    )


def empty_message() -> str:
    return "No security fixes worth a PR tonight. Staying quiet."


def blocked_checkout_message(repo: str) -> str:
    return (
        f"Blocked: could not check out or scan {repo}. No PR ask. "
        "Fix access or fixtures and retry."
    )


def deny_open_message() -> str:
    return "Got it. No PR opened; draft stays in this run."


def approve_open_message(pr_title: str, pr_url: str = "") -> str:
    if pr_url:
        return f"Opened draft PR: {pr_url} ({pr_title}). Not merged."
    return f"Opened draft PR: ({pr_title}). Not merged."


def open_pr_failed_message(_reason: str = "") -> str:
    return (
        "Could not open on GitHub (Action Gateway / GitHub Connection unavailable). "
        "Draft stays in this run only."
    )


def missing_repo_message() -> str:
    return "I need a repo to scan. Example: Scan acme/api on main, area src"
