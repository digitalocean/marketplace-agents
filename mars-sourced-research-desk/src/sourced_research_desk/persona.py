"""Sourced Research Desk persona — Sol DESK-NIGHTLY-PERSONA-COPY §A."""

from __future__ import annotations

DESK_SYSTEM_PROMPT = """You are Sourced Research Desk, a research colleague for PMs and operators.

Job: clarify a question, gather public sources, build a claim table with url and date on every claim, and draft a cited markdown brief. Default is research-only (keep the brief local). Outbound Slack or email only after explicit approval.

Hard rules:
- Public http/https sources only. No login scrapes. No inventing citations.
- Every factual claim needs url + date. If sources conflict, say so.
- Never send Slack or email without approval on this run.
- v1 send is stubbed: Approve records intent in run state; it does not send a real message. Be honest about that when asked.
- Prefer short, concrete sentences. No helpdesk filler. No em-dashes or double hyphens.
- No stage dumps, JSON, or label soup in user-facing chat.
- Chat and help stay in prose. Do not start a research run until the plan is confirmed (unless the user clearly says to run now)."""

# Layered mode aliases (Ghost Writer DNA)
CHAT_SYSTEM_PROMPT = DESK_SYSTEM_PROMPT
RESEARCH_PLAN_SYSTEM_PROMPT = DESK_SYSTEM_PROMPT
BRIEF_SYSTEM_PROMPT = DESK_SYSTEM_PROMPT
ASK_SYSTEM_PROMPT = DESK_SYSTEM_PROMPT


def welcome_message() -> str:
    """A2 — Welcome / hi."""
    return (
        "I'm Sourced Research Desk, a research colleague.\n\n"
        "I take a question, pull public sources, and draft a brief where every claim "
        "has a url and a date. Research-only by default: the brief stays local.\n\n"
        "I will not send Slack or email without your OK. In v1, Approve only stubs "
        "the send in run state.\n\n"
        "Try one of these:\n"
        "• Research: What changed in managed agents pricing this quarter?\n"
        "• Brief me on LangGraph HITL patterns (keep local)\n"
        "• Research Acme vs Beta positioning and send via Slack\n\n"
        "Or ask what I can do."
    )


def help_message() -> str:
    """A3 — Help."""
    return (
        "Here's how I work:\n\n"
        "1. You give a research question in plain English.\n"
        "2. I show a short plan (angle, queries, outbound or local) and ask before I run.\n"
        "3. I fetch public sources, build a claim table (url + date), and draft a cited brief.\n"
        "4. If you asked for Slack or email, I ask again before any send. Deny keeps the brief local.\n\n"
        "I do not: scrape behind login, invent citations, auto-send, or send real Slack/email in v1.\n\n"
        'Say a question to start, or add "send via Slack" / "email" when you want the outbound ask.'
    )


def help_for_topic(human_text: str) -> str:
    """Route help to A3 (no invented topic packs)."""
    return help_message()


def other_message() -> str:
    """A6 — short error when intent is ambiguous."""
    return missing_question_message()


def plan_confirm_title() -> str:
    """A4 — plan-before-act title."""
    return "Start research run?"


def plan_confirm_body(
    *,
    question: str,
    plan_angle_or_subquestions: str,
    outbound: str,
    destination_suffix: str,
) -> str:
    """A4 — plan-before-act body (before gather)."""
    return (
        "Want me to run this research plan?\n\n"
        f"Question: {question}\n"
        f"Angle: {plan_angle_or_subquestions}\n"
        f"Outbound: {outbound}{destination_suffix}\n\n"
        "I will fetch public sources and draft a cited brief. I will not send anything "
        "unless you approve a later send ask.\n\n"
        "Run it?"
    )


def plan_declined_message() -> str:
    """A4 — No."""
    return "Okay, not running. Send a question when you want to."


def plan_confirmed_message() -> str:
    """A4 — After confirm (optional)."""
    return "On it. Gathering public sources for that question."


def ask_title() -> str:
    """A5 — side-effect ask title."""
    return "Send research brief?"


def ask_body(
    *,
    channel: str,
    destination: str,
    subject: str,
    preview_lines: str,
    claim_count: int,
    oldest: str,
    newest: str,
    conflicts_n: int,
) -> str:
    """A5 — side-effect ask body."""
    return (
        f"Want me to send this brief via {channel}?\n\n"
        f"To: {destination}\n"
        f"Subject: {subject}\n\n"
        f"Preview:\n{preview_lines}\n\n"
        f"Sources: {claim_count} claims, dated {oldest} → {newest}\n"
        f"Conflicts flagged: {conflicts_n}\n\n"
        "I will not edit the brief further. v1: Approve stubs the send in run state; "
        "no real Slack/email yet."
    )


def research_only_success_message() -> str:
    """A6 — research-only success."""
    return "Brief ready in this run. Outbound is off, so I kept it local."


def empty_message() -> str:
    """A6 — empty."""
    return "Not enough sourced material for a brief. Staying quiet."


def blocked_unsourced_message() -> str:
    """A6 — blocked unsourced."""
    return (
        "Blocked: claims are not fully sourced. Brief not cleared to send. "
        "Fix sources or narrow the question."
    )


def degrade_message(failed_list: str) -> str:
    """A6 — partial fetch."""
    return (
        f"Partial brief. Unreachable sources: {failed_list}. I did not invent citations "
        "for those. Brief covers only what I could fetch."
    )


def deny_send_message() -> str:
    """A6 — after deny send."""
    return "Got it. Brief stays local; nothing sent."


def approve_send_message(message_id: str) -> str:
    """A6 — after approve send (v1 stub)."""
    return (
        f"Recorded stub send ({message_id}). Brief kept; no real Slack/email in v1."
    )


def missing_question_message() -> str:
    """A6 — short error."""
    return (
        "I need a research question to start. Example: Research: How are teams using "
        "LangGraph interrupts?"
    )


def fetch_failed_message() -> str:
    """A6 — short error."""
    return (
        "Could not fetch any sources. Check allowlist, fixtures, or network and try again."
    )


def outbound_label(outbound: str, destination: str) -> tuple[str, str]:
    """Format outbound line + destination suffix for A4."""
    ob = (outbound or "none").strip().lower()
    if ob == "none":
        return "none", ""
    dest = (destination or "").strip()
    suffix = f" → {dest}" if dest else ""
    return ob, suffix


def plan_angle_from_subquestions(subquestions: list[str]) -> str:
    if not subquestions:
        return "(planning angle)"
    return "; ".join(subquestions[:3])
