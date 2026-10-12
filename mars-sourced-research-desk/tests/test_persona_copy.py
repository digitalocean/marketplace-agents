"""Persona golden copy: welcome and help voice."""

from __future__ import annotations

from sourced_research_desk.hygiene import hygiene_text
from sourced_research_desk.persona import help_message, welcome_message


def test_welcome_message_voice():
    text = hygiene_text(welcome_message())
    assert "Sourced Research Desk" in text
    assert "without your OK" in text
    assert "managed agents pricing" in text
    assert "—" not in text


def test_help_message_voice():
    text = hygiene_text(help_message())
    assert "here's how i work" in text.lower()
    assert "ask before i run" in text.lower()
    assert "—" not in text
