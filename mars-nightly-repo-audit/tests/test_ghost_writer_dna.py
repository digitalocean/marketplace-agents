"""Ghost Writer DNA: Sol persona copy, hygiene, question-first ask."""

from __future__ import annotations

from nightly_repo_audit.hygiene import hygiene_text
from nightly_repo_audit.persona import (
    ask_body,
    ask_title,
    plan_confirm_body,
    plan_confirm_title,
    welcome_message,
)


def test_ask_title_question_first():
    assert ask_title() == "Open cleanup PR?"


def test_plan_confirm_title_and_body():
    assert plan_confirm_title() == "Start repo audit?"
    text = plan_confirm_body(
        repo="acme/widgets",
        ref="main",
        area="src",
        scope_limits="No merge",
        trigger="manual",
    )
    assert text.startswith("Want me to run this audit?")
    assert "Run it?" in text
    cleaned = hygiene_text(text)
    assert "—" not in cleaned


def test_welcome_no_open_without_ok():
    text = hygiene_text(welcome_message())
    assert "without your OK" in text
    assert "—" not in text


def test_ask_body_leads_with_question():
    body = ask_body(
        repo="acme/widgets",
        branch="nightly/cleanup",
        pr_title="chore: cleanup",
        area="src",
        diff_stat="+10 / −5",
        bullets="- fix TODO",
    )
    assert body.startswith("Want me to open a draft PR on acme/widgets?")
    assert "—" not in body


def test_hygiene_strips_stage_labels():
    raw = "draft: PR draft ready\nstatus: ok\nCertainly, opening PR."
    cleaned = hygiene_text(raw)
    assert "status: ok" not in cleaned.lower()
    assert "Certainly" not in cleaned
