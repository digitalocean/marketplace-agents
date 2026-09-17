"""Outbound path: interrupt ask; deny skips send; approve stub-sends."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from sourced_research_desk.graph import compile_graph


FIXTURE_SOURCES = [
    {
        "url": "https://example.com/report",
        "title": "Report",
        "ok": True,
        "claim": "Outbound research must pause for human approval before send.",
        "quote": "pause for human approval",
        "published_date": "2026-09-15",
        "text": "Outbound research must pause for human approval before send.",
    }
]


def _run_to_interrupt(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "outbound-test"}}
    result = g.invoke(
        {
            "question": "Should we ask before sending a brief?",
            "outbound": "slack",
            "destination": "#research",
            "subject": "Test brief",
            "fixture_sources": FIXTURE_SOURCES,
        },
        cfg,
    )
    return g, cfg, result


def test_outbound_reaches_interrupt(monkeypatch):
    _g, _cfg, result = _run_to_interrupt(monkeypatch)
    assert "__interrupt__" in result
    interrupts = result["__interrupt__"]
    assert interrupts
    payload = interrupts[0].value
    assert payload.get("title") == "Want me to send this research brief via slack?"
    assert payload.get("pending_action") == "send_outbound"
    assert "approve" in payload.get("choices", [])


def test_resume_deny_no_send(monkeypatch):
    g, cfg, result = _run_to_interrupt(monkeypatch)
    assert "__interrupt__" in result

    final = g.invoke(Command(resume="deny"), cfg)
    assert "__interrupt__" not in final
    assert final.get("sent") is not True
    assert final.get("skipped") is True
    assert final.get("status") == "denied"
    assert final.get("brief_md"), "brief should remain in artifacts"


def test_resume_approve_stub_send(monkeypatch):
    g, cfg, result = _run_to_interrupt(monkeypatch)
    assert "__interrupt__" in result

    final = g.invoke(Command(resume="approve"), cfg)
    assert "__interrupt__" not in final
    assert final.get("sent") is True
    assert final.get("skipped") is not True
    assert final.get("message_id", "").startswith("stub-")
