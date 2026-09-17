"""Compiled Competitor Pulse graph (MARS / LangGraph Agent Server export)."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from competitor_pulse.nodes import (
    act,
    ask,
    execute_pulse,
    report,
    should_ask,
)
from competitor_pulse.state import PulseState


def build_graph() -> StateGraph:
    """Construct the uncompiled StateGraph.

    intake→draft run inside ``execute_pulse`` so MARS stream updates never
    include raw ``watchlist`` JSON. Only ``report`` appends chat messages.
    """
    builder: StateGraph = StateGraph(PulseState)
    builder.add_node("execute_pulse", execute_pulse)
    builder.add_node("ask", ask)
    builder.add_node("act", act)
    builder.add_node("report", report)

    builder.add_edge(START, "execute_pulse")
    builder.add_conditional_edges(
        "execute_pulse",
        should_ask,
        {"ask": "ask", "report": "report"},
    )
    builder.add_edge("ask", "act")
    builder.add_edge("act", "report")
    builder.add_edge("report", END)
    return builder


def compile_graph(checkpointer: Any = None):
    """Compile with optional checkpointer (required for interrupt resume locally)."""
    builder = build_graph()
    kwargs: dict[str, Any] = {"name": "Competitor Pulse"}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    return builder.compile(**kwargs)


# Module-level compiled export for langgraph.json / Agent Server
graph = compile_graph()
