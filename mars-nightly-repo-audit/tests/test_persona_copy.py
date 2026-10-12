"""Persona golden copy: welcome and help voice."""

from __future__ import annotations

from nightly_repo_audit.hygiene import hygiene_text
from nightly_repo_audit.persona import help_message, welcome_message


def test_welcome_message_voice():
    text = hygiene_text(welcome_message())
    assert "Nightly Repo Audit" in text
    assert "without your OK" in text
    assert "eng leads" in text
    assert "—" not in text


def test_help_message_voice():
    text = hygiene_text(help_message())
    assert "here's how i work" in text.lower()
    assert "ask before i scan" in text.lower()
    assert "—" not in text
