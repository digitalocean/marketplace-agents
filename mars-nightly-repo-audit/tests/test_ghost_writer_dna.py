"""Ghost Writer DNA: layered prompts, hygiene, question-first ask."""

from __future__ import annotations

from nightly_repo_audit.hygiene import hygiene_text
from nightly_repo_audit.persona import ask_title


def test_ask_title_question_first():
    assert (
        ask_title(repo="acme/widgets")
        == "Want me to open this cleanup PR on acme/widgets?"
    )


def test_hygiene_strips_stage_labels():
    raw = "draft: PR draft ready\nstatus: ok\nCertainly, opening PR."
    cleaned = hygiene_text(raw)
    assert "status: ok" not in cleaned.lower()
    assert "Certainly" not in cleaned
