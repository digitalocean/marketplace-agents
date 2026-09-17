"""Ghost Writer DNA: Sol persona copy, hygiene, question-first ask."""

from __future__ import annotations

from sourced_research_desk.hygiene import hygiene_text
from sourced_research_desk.persona import (
    ask_body,
    ask_title,
    plan_confirm_body,
    plan_confirm_title,
    welcome_message,
)


def test_ask_title_question_first():
    assert ask_title() == "Send research brief?"


def test_plan_confirm_title_and_body():
    assert plan_confirm_title() == "Start research run?"
    text = plan_confirm_body(
        question="What changed in tooling?",
        plan_angle_or_subquestions="Status?; Evidence?",
        outbound="none",
        destination_suffix="",
    )
    assert text.startswith("Want me to run this research plan?")
    assert "Run it?" in text
    assert "without your OK" not in text.lower() or "send ask" in text.lower()
    cleaned = hygiene_text(text)
    assert "—" not in cleaned


def test_welcome_no_send_without_ok():
    text = hygiene_text(welcome_message())
    assert "without your OK" in text
    assert "—" not in text


def test_ask_body_leads_with_question():
    body = ask_body(
        channel="slack",
        destination="#research",
        subject="Test",
        preview_lines="line one",
        claim_count=2,
        oldest="2026-01-01",
        newest="2026-02-01",
        conflicts_n=0,
    )
    assert body.startswith("Want me to send this brief via slack?")
    assert "—" not in body


def test_hygiene_strips_stage_labels():
    raw = "plan: Plan: 3 queries\nstatus: ok\nCertainly, here is the brief."
    cleaned = hygiene_text(raw)
    assert "status: ok" not in cleaned.lower()
    assert "Certainly" not in cleaned
