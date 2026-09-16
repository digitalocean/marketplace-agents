"""Final state exposes assistant-visible AIMessage for Agent Server / MARS UI."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from competitor_pulse.graph import compile_graph
from competitor_pulse.pulse_diff import (
    default_baseline_path,
    default_watchlist,
    material_baseline_path,
    quiet_baseline_path,
)


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def _last_ai_message(result: dict) -> AIMessage:
    msgs = result.get("messages") or []
    assert msgs, "expected at least one message in final state"
    last = msgs[-1]
    assert isinstance(last, AIMessage)
    return last


def test_quiet_run_emits_assistant_message(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {
            "watchlist": default_watchlist(),
            "notify": True,
            "baseline_path": str(quiet_baseline_path()),
            "allow_net": False,
        }
    )
    ai = _last_ai_message(result)
    assert "no material" in ai.content.lower()
    assert ai.content == result.get("human_summary")


def test_material_notify_off_includes_brief(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {
            "watchlist": default_watchlist(),
            "notify": False,
            "baseline_path": str(material_baseline_path()),
            "allow_net": False,
        }
    )
    ai = _last_ai_message(result)
    assert "Competitor Pulse" in ai.content
    assert result.get("brief_md")
    assert result["brief_md"] in ai.content
    assert ai.content.startswith(result.get("human_summary") or "")


def test_resume_approve_emits_assistant_message(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "messages-approve"}}
    mid = g.invoke(
        {
            "watchlist": default_watchlist(),
            "notify": True,
            "baseline_path": str(default_baseline_path()),
            "allow_net": False,
        },
        cfg,
    )
    assert "__interrupt__" in mid

    final = g.invoke(Command(resume="approve"), cfg)
    ai = _last_ai_message(final)
    assert final.get("status") == "notified"
    assert "notified" in ai.content.lower()
    assert final.get("brief_md") in ai.content
