"""Shared helpers for Competitor Pulse graph tests."""

from __future__ import annotations

from typing import Any

from competitor_pulse.mars_text import (
    last_assistant_text,
    prepare_programmatic_payload,
    summary_from_assistant_text,
)
from competitor_pulse.pulse_diff import default_watchlist


def invoke_graph(graph: Any, state: dict[str, Any], config: dict[str, Any] | None = None):
    """Invoke with optional watchlist encoded as a silent JSON HumanMessage."""
    payload = prepare_programmatic_payload(state)
    if config is not None:
        return graph.invoke(payload, config)
    return graph.invoke(payload)


def invoke_graph_full(
    graph: Any,
    state: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the final internal state snapshot (for stage_summaries, deltas, etc.)."""
    payload = prepare_programmatic_payload(state)
    stream_kwargs: dict[str, Any] = {"stream_mode": "values"}
    if config is not None:
        stream_kwargs["config"] = config
    last: dict[str, Any] | None = None
    for snapshot in graph.stream(payload, **stream_kwargs):
        last = snapshot
    assert last is not None
    return last


def assistant_summary(result: dict[str, Any]) -> str:
    return summary_from_assistant_text(last_assistant_text(result))


def default_pulse_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "watchlist": default_watchlist(),
        "notify": False,
        "allow_net": False,
    }
    base.update(overrides)
    return base
