"""Plan-before-act confirm (Sol B4) before gather."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from audit_helpers import assistant_summary
from nightly_repo_audit.graph import compile_graph
from nightly_repo_audit.repo_scan import default_fixture_path

FIXTURE = str(default_fixture_path())


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_plan_confirm_interrupt_before_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "nightly-plan-confirm"}}
    result = g.invoke(
        {
            "messages": [HumanMessage(content="Audit acme/widgets on main, area src")],
            "repo": "acme/widgets",
            "ref": "main",
            "area_hint": "src",
            "fixture_path": FIXTURE,
        },
        cfg,
    )
    assert "__interrupt__" in result
    payload = result["__interrupt__"][0].value
    assert payload.get("title") == "Start repo audit?"
    body = payload.get("body") or ""
    assert body.startswith("Want me to run this audit?")
    assert "Run it?" in body
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "gather:" not in summaries


def test_plan_confirm_deny_no_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "nightly-plan-deny"}}
    result = g.invoke(
        {
            "messages": [HumanMessage(content="Audit acme/widgets on main")],
            "repo": "acme/widgets",
            "ref": "main",
            "fixture_path": FIXTURE,
        },
        cfg,
    )
    assert "__interrupt__" in result
    final = g.invoke(Command(resume="deny"), cfg)
    assert "__interrupt__" not in final
    assert final.get("status") == "plan_denied"
    assert "not auditing" in assistant_summary(final).lower()
    summaries = " ".join(final.get("stage_summaries") or [])
    assert "gather:" not in summaries


def test_programmatic_audit_skips_plan_confirm(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {
            "repo": "local/sample",
            "ref": "main",
            "fixture_path": FIXTURE,
            "force_empty": True,
        }
    )
    assert "__interrupt__" not in result
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "analyze:" in summaries
