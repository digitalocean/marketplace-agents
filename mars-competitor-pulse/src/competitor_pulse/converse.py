"""Warm conversational replies for chat / help — no pulse fetch."""

from __future__ import annotations

_TEMPLATE_CHAT = (
    "Hey — I'm **Competitor Pulse**, your slightly obsessive GTM researcher.\n\n"
    "Name a company (or a few) and I'll watch their public pages — site, pricing, "
    "changelog, careers — and diff them against a baseline.\n\n"
    "Try `track FedEx`, `Pulse on Cursor and Perplexity`, or ask **how this works**."
)

_TEMPLATE_HELP = (
    "I'm **Competitor Pulse** — sharp, dry, and allergic to noisy alerts.\n\n"
    "**What I do:** you name competitors → I fetch public pages → diff against a saved "
    "baseline → send you a plain-English brief when something actually moves.\n\n"
    "**How to use it:**\n"
    "- `track OpenAI and Anthropic` — add companies to your watchlist\n"
    "- `track Cursor and alert on Slack` — opt into the notify gate (approval required)\n"
    "- Re-run later to see real diffs; first run is a **first look** baseline, not a crisis\n\n"
    "**v1 limits (honest):** public web only, no competitor logins, notify is a stub until "
    "you approve on material changes. Offline fixtures work when live fetch is off."
)

_TEMPLATE_OTHER = (
    "Didn't quite catch that — want a pulse or a quick how-to?\n\n"
    "Name companies to watch (e.g. `track FedEx`) or ask **what do you do?**"
)


def _llm_reply(intent: str, human_text: str) -> str | None:
    try:
        from competitor_pulse.llm import get_llm, harness_env_available

        if not harness_env_available():
            return None

        intent_guide = {
            "chat": "Greet warmly, invite them to name companies to track.",
            "help": "Explain capabilities, how to track/notify/baselines, and v1 limits.",
            "other": "Ask a short clarifying question in character.",
        }.get(intent, "Reply helpfully.")

        llm = get_llm(temperature=0.4)
        prompt = (
            "You are Competitor Pulse — a sharp, dry product/GTM researcher embedded in "
            "MARS chat. Helpful, not corporate. Contractions OK. No 'Certainly!' or "
            "helpdesk filler. Stay honest about v1: public web only, stub notify, no "
            "competitor logins.\n\n"
            f"Intent: {intent}. {intent_guide}\n"
            "Keep it under 120 words. Markdown OK. Do not invent competitor deltas or "
            "fetch results.\n\n"
            f"User: {human_text}\n\n"
            "Reply:"
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
        if isinstance(content, list):
            content = " ".join(str(part) for part in content)
        text = str(content).strip()
        return text or None
    except Exception:
        return None


def template_reply(intent: str) -> str:
    if intent == "help":
        return _TEMPLATE_HELP
    if intent == "other":
        return _TEMPLATE_OTHER
    return _TEMPLATE_CHAT


def conversational_reply(intent: str, human_text: str) -> str:
    """Harness LLM when available; solid templates offline for tests."""
    llm_text = _llm_reply(intent, human_text)
    if llm_text:
        return llm_text
    return template_reply(intent)
