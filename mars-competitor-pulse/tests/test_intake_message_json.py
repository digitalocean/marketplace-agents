"""Intake parses JSON from MARS chat HumanMessage."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from competitor_pulse.mars_text import watchlist_from_state
from competitor_pulse.nodes import intake
from competitor_pulse.pulse_diff import spacexai_watchlist


def test_intake_applies_watchlist_from_human_message_json():
    custom = [{"name": "RivalCo", "urls": {"site": "https://example.com/rival/"}}]
    payload = {"watchlist": custom, "notify": False, "allow_net": False}
    result = intake(
        {
            "messages": [
                HumanMessage(
                    content=f"Run pulse with ```json\n{json.dumps(payload)}\n```"
                )
            ]
        }
    )
    assert watchlist_from_state(result) == custom
    assert result["notify"] is False
    assert result["allow_net"] is False
    assert result["status"] == "ok"


def test_intake_spacexai_preset_from_json():
    result = intake(
        {
            "messages": [
                HumanMessage(
                    content='{"preset": "spacexai", "allow_net": true, "notify": false}'
                )
            ]
        }
    )
    wl = watchlist_from_state(result)
    assert wl == spacexai_watchlist()
    assert len(wl) >= 4
    assert result["allow_net"] is True
    assert result["notify"] is False


def test_intake_prefers_state_competitors_over_message_json():
    state_competitors = [{"name": "InState", "urls": {"site": "https://example.com/in/"}}]
    result = intake(
        {
            "internal": {"competitors": state_competitors},
            "messages": [
                HumanMessage(
                    content='{"watchlist": [{"name": "FromMsg", "urls": {"site": "https://example.com/msg/"}}]}'
                )
            ],
        }
    )
    assert watchlist_from_state(result) == state_competitors


def test_intake_accepts_legacy_watchlist_json_key():
    custom = [{"name": "Legacy", "urls": {"site": "https://example.com/legacy/"}}]
    result = intake(
        {
            "messages": [
                HumanMessage(
                    content=json.dumps({"watchlist": custom, "allow_net": False})
                )
            ]
        }
    )
    assert watchlist_from_state(result) == custom


def test_intake_spacexai_token_without_json_preset():
    result = intake(
        {
            "messages": [HumanMessage(content="Run SPACEXAI_PRESET pulse please")]
        }
    )
    assert watchlist_from_state(result) == spacexai_watchlist()
