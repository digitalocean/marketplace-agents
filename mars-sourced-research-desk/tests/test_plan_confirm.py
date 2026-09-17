"""Plan-before-act confirm (Sol A4) before gather."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from desk_helpers import assistant_summary
from sourced_research_desk.graph import compile_graph
from sourced_research_desk.mars_text import last_assistant_text


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_plan_confirm_interrupt_before_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "desk-plan-confirm"}}
    result = g.invoke(
        {
            "messages": [
                HumanMessage(content="Research: What changed in managed agents pricing?")
            ],
            "outbound": "none",
            "allow_net": False,
        },
        cfg,
    )
    assert "__interrupt__" in result
    payload = result["__interrupt__"][0].value
    assert payload.get("title") == "Start research run?"
    body = payload.get("body") or ""
    assert body.startswith("Want me to run this research plan?")
    assert "Run it?" in body
    visible = last_assistant_text(result)
    assert visible.startswith("Want me to run this research plan?")
    assert "Run it?" in visible
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "gather:" not in summaries


def test_plan_confirm_resume_harness_approved_true(monkeypatch):
    """MARS --on-hitl approve may resume {approved: true} or bare True."""
    _offline(monkeypatch)
    fixture = [
        {
            "url": "https://example.com/a",
            "ok": True,
            "claim": "A claim.",
            "published_date": "2026-09-01",
            "text": "A claim.",
        }
    ]
    for resume_val in ({"approved": True}, True, "approve"):
        g = compile_graph(checkpointer=MemorySaver())
        cfg = {"configurable": {"thread_id": f"desk-hitl-{type(resume_val).__name__}"}}
        g.invoke(
            {
                "messages": [HumanMessage(content="Research: LangGraph HITL patterns")],
                "outbound": "none",
                "fixture_sources": fixture,
            },
            cfg,
        )
        final = g.invoke(Command(resume=resume_val), cfg)
        assert final.get("status") != "plan_denied"
        assert final.get("brief_md")
        snap = g.get_state(cfg).values
        assert snap.get("plan_confirmed") is True
        summaries = " ".join(snap.get("stage_summaries") or [])
        assert "gather:" in summaries


def test_plan_confirm_deny_no_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "desk-plan-deny"}}
    result = g.invoke(
        {
            "messages": [HumanMessage(content="Research: LangGraph HITL patterns")],
            "outbound": "none",
        },
        cfg,
    )
    assert "__interrupt__" in result
    final = g.invoke(Command(resume="deny"), cfg)
    assert "__interrupt__" not in final
    assert final.get("status") == "plan_denied"
    assert "not running" in assistant_summary(final).lower()
    summaries = " ".join(final.get("stage_summaries") or [])
    assert "gather:" not in summaries


def test_programmatic_question_skips_plan_confirm(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {
            "question": "Citation quality check",
            "outbound": "none",
            "fixture_sources": [
                {
                    "url": "https://example.com/a",
                    "ok": True,
                    "claim": "A claim.",
                    "published_date": "2026-09-01",
                    "text": "A claim.",
                }
            ],
        }
    )
    assert "__interrupt__" not in result
    assert result.get("brief_md") or result.get("claim_count", 0) >= 1
