"""Natural-language watchlist intake (offline alias map, no network)."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from competitor_pulse.intake_parse import parse_watchlist_from_message
from competitor_pulse.nodes import intake
from competitor_pulse.pulse_diff import default_watchlist


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_parse_nl_known_aliases():
    parsed = parse_watchlist_from_message(
        "Track OpenAI, Anthropic, and Google for SpaceXAI"
    )
    names = [item["name"] for item in parsed["watchlist"]]
    assert names == ["OpenAI", "Anthropic", "Google AI"]
    assert parsed["source"] == "offline"
    assert parsed["notify"] is None


def test_parse_pulse_on_cursor_and_perplexity():
    parsed = parse_watchlist_from_message("Pulse on Cursor and Perplexity")
    names = [item["name"] for item in parsed["watchlist"]]
    assert names == ["Cursor", "Perplexity"]
    assert parsed["is_tracking_request"] is True


def test_intake_nl_watchlist_sets_allow_net(monkeypatch):
    _offline(monkeypatch)
    result = intake(
        {
            "messages": [
                HumanMessage(
                    content="Track OpenAI, Anthropic, and Google for SpaceXAI"
                )
            ]
        }
    )
    names = {item["name"] for item in result["watchlist"]}
    assert "OpenAI" in names
    assert "Anthropic" in names
    assert "Google AI" in names
    assert result["allow_net"] is True
    assert result["notify"] is False
    assert result["status"] == "ok"


def test_intake_json_still_works(monkeypatch):
    _offline(monkeypatch)
    custom = [{"name": "RivalCo", "urls": {"site": "https://example.com/rival/"}}]
    payload = {"watchlist": custom, "notify": False, "allow_net": False}
    result = intake(
        {
            "messages": [
                HumanMessage(
                    content=f"```json\n{json.dumps(payload)}\n```"
                )
            ]
        }
    )
    assert result["watchlist"] == custom
    assert result["allow_net"] is False


def test_intake_generic_message_routes_to_chat(monkeypatch):
    _offline(monkeypatch)
    result = intake({"messages": [HumanMessage(content="hi")]})
    assert result.get("intent") == "chat"
    assert result["watchlist"] == []
    assert result["status"] == "chat"


def test_intake_no_message_uses_acme_default(monkeypatch):
    _offline(monkeypatch)
    result = intake({})
    assert result["watchlist"] == default_watchlist()


def test_intake_unresolved_track_request_blocked(monkeypatch):
    _offline(monkeypatch)
    result = intake(
        {
            "messages": [
                HumanMessage(content="Track FooBar and BazQuux competitors please")
            ]
        }
    )
    assert result["status"] == "blocked"
    assert result["watchlist"] == []
    assert "resolve" in (result.get("human_summary") or "").lower()
    names = {item["name"] for item in default_watchlist()}
    assert "Acme" not in names or "Acme" not in {
        item["name"] for item in result["watchlist"]
    }


def test_intake_notify_from_nl(monkeypatch):
    _offline(monkeypatch)
    result = intake(
        {
            "messages": [
                HumanMessage(content="Track Cursor and alert on Slack when changes happen")
            ]
        }
    )
    assert result["notify"] is True
    assert any(item["name"] == "Cursor" for item in result["watchlist"])
