"""Intake parses JSON from MARS chat HumanMessage."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

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
    assert result["watchlist"] == custom
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
    assert result["watchlist"] == spacexai_watchlist()
    assert len(result["watchlist"]) >= 4
    assert result["allow_net"] is True
    assert result["notify"] is False


def test_intake_prefers_state_watchlist_over_message_json():
    state_watchlist = [{"name": "InState", "urls": {"site": "https://example.com/in/"}}]
    result = intake(
        {
            "watchlist": state_watchlist,
            "messages": [
                HumanMessage(
                    content='{"watchlist": [{"name": "FromMsg", "urls": {"site": "https://example.com/msg/"}}]}'
                )
            ],
        }
    )
    assert result["watchlist"] == state_watchlist


def test_intake_spacexai_token_without_json_preset():
    result = intake(
        {
            "messages": [HumanMessage(content="Run SPACEXAI_PRESET pulse please")]
        }
    )
    assert result["watchlist"] == spacexai_watchlist()
