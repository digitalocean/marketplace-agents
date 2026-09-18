"""Compiled Sourced Research Desk graph (MARS / LangGraph Agent Server export)."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from sourced_research_desk.nodes import (
    act_node,
    analyze_node,
    ask_node,
    confirm_plan_node,
    draft_node,
    gather_node,
    intake_node,
    plan_node,
    report_node,
    route_after_confirm_plan,
    route_after_intake,
    should_ask,
    should_confirm_plan,
)
from sourced_research_desk.state import InputState, OutputState, ResearchState


def build_graph() -> StateGraph:
    """Construct the uncompiled StateGraph.

    Chat/help/other: ``intake`` emits a single ``AIMessage`` and routes to END.
    Research: ``intake`` → plan → gather → analyze → draft → optional ask → report.
    """
    builder: StateGraph = StateGraph(
        ResearchState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    builder.add_node("intake", intake_node)
    builder.add_node("plan", plan_node)
    builder.add_node("confirm_plan", confirm_plan_node)
    builder.add_node("gather", gather_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("draft", draft_node)
    builder.add_node("ask", ask_node)
    builder.add_node("act", act_node)
    builder.add_node("report", report_node)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {"end": END, "plan": "plan"},
    )
    builder.add_conditional_edges(
        "plan",
        should_confirm_plan,
        {"confirm_plan": "confirm_plan", "gather": "gather"},
    )
    builder.add_conditional_edges(
        "confirm_plan",
        route_after_confirm_plan,
        {"gather": "gather", "report": "report"},
    )
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
    kwargs: dict[str, Any] = {"name": "Sourced Research Desk"}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    return builder.compile(**kwargs)


# Module-level compiled export for langgraph.json / Agent Server
graph = compile_graph()
