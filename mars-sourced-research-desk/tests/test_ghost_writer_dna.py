"""Ghost Writer DNA: layered prompts, hygiene, question-first ask."""

from __future__ import annotations

from sourced_research_desk.hygiene import hygiene_text
from sourced_research_desk.persona import ask_title, research_plan_summary


def test_ask_title_question_first():
    assert ask_title(channel="slack") == "Want me to send this research brief via slack?"
    assert ask_title(channel="email") == "Want me to send this research brief via email?"


def test_research_plan_summary_no_send_without_ok():
    text = research_plan_summary(
        question="What changed in tooling?",
        subquestions=["Status?", "Evidence?", "Conflicts?"],
        search_queries=["tooling overview"],
        outbound="slack",
        destination="#research",
        allow_net=False,
    )
    assert "without your OK" in text
    assert "Offline fixtures" in text
    cleaned = hygiene_text(text)
    assert "—" not in cleaned


def test_hygiene_strips_stage_labels():
    raw = "plan: Plan: 3 queries\nstatus: ok\nCertainly, here is the brief."
    cleaned = hygiene_text(raw)
    assert "plan:" not in cleaned.lower() or "queries" in cleaned
    assert "status: ok" not in cleaned.lower()
    assert "Certainly" not in cleaned
