"""Conversational intent routing: chat, help, research path unchanged."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from desk_helpers import assistant_summary
from sourced_research_desk.graph import compile_graph
from sourced_research_desk.intent import classify_intent, is_chat_message, is_help_message
from sourced_research_desk.nodes import intake


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_classify_chat_and_help():
    assert classify_intent("hi") == "chat"
    assert classify_intent("what do you do?") == "help"
    assert classify_intent("What changed in cloud pricing?") == "research_plan"
    assert is_chat_message("hey") is True
    assert is_help_message("how does this work") is True


def test_research_sources_not_help():
    """Natural research NL must not route to meta help."""
    text = "Research sources for LangGraph interrupts"
    assert classify_intent(text) == "research_plan"
    assert is_help_message(text) is False


def test_approve_deny_with_pending_research():
    pending = {"question": "LangGraph HITL patterns"}
    assert classify_intent("approve", pending_research=pending) == "research"
    assert classify_intent("deny", pending_research=pending) == "plan_denied"
    assert classify_intent("yes", pending_research=pending) == "research"
    assert classify_intent("approve") == "other"
    assert classify_intent("deny") == "other"
    assert is_help_message("approve") is False
    assert is_help_message("deny") is False


def test_intake_hi_emits_chat_aimessage(monkeypatch):
    _offline(monkeypatch)
    result = intake({"messages": [HumanMessage(content="hi")]})
    assert result.get("intent") == "chat"
    assert result.get("messages")
    summary = assistant_summary(result)
    assert "Sourced Research Desk" in summary
    assert "without your ok" in summary.lower()


def test_hi_full_graph_no_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke({"messages": [HumanMessage(content="hi")], "allow_net": False})
    summary = assistant_summary(result)
    assert result.get("status") == "chat"
    assert "Sourced Research Desk" in summary
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "gather:" not in summaries
    assert "plan:" not in summaries


def test_help_full_graph(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {"messages": [HumanMessage(content="what do you do?")], "allow_net": False}
    )
    summary = assistant_summary(result)
    assert result.get("status") == "help"
    assert "how i work" in summary.lower() or "research" in summary.lower()
