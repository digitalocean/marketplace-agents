"""Compiled Sourced Research Desk graph (MARS / LangGraph Agent Server export)."""

from __future__ import annotations

from typing import Any, Optional

from langgraph.graph import END, START, StateGraph

from sourced_research_desk.nodes import (
    act,
    analyze,
    ask,
    draft,
    gather,
    intake,
    plan,
    report,
    should_ask,
)
from sourced_research_desk.state import ResearchState


def build_graph() -> StateGraph:
    """Construct the uncompiled StateGraph."""
    builder: StateGraph = StateGraph(ResearchState)
    builder.add_node("intake", intake)
    builder.add_node("plan", plan)
    builder.add_node("gather", gather)
    builder.add_node("analyze", analyze)
    builder.add_node("draft", draft)
    builder.add_node("ask", ask)
    builder.add_node("act", act)
    builder.add_node("report", report)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "plan")
    builder.add_edge("plan", "gather")
    builder.add_edge("gather", "analyze")
    builder.add_edge("analyze", "draft")
    builder.add_conditional_edges(
        "draft",
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
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


# Module-level compiled export for langgraph.json / Agent Server
graph = compile_graph()
