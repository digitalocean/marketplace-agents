"""Plan-before-act confirm before gather."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from nightly_repo_security_scan.graph import compile_graph
from nightly_repo_security_scan.mars_text import last_assistant_text
from nightly_repo_security_scan.security_scan import default_fixture_path
from scan_helpers import assistant_summary

FIXTURE = str(default_fixture_path())


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_plan_confirm_interrupt_before_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "security-plan-confirm"}}
    result = g.invoke(
        {
            "messages": [HumanMessage(content="Scan acme/widgets on main, area src")],
            "repo": "acme/widgets",
            "ref": "main",
            "area_hint": "src",
            "fixture_path": FIXTURE,
        },
        cfg,
    )
    assert "__interrupt__" in result
    payload = result["__interrupt__"][0].value
    assert payload.get("title") == "Start security scan?"
    body = payload.get("body") or ""
    assert body.startswith("Want me to run this security scan?")
    assert "Run it?" in body
    visible = last_assistant_text(result)
    assert visible.startswith("Want me to run this security scan?")
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "gather:" not in summaries


def test_plan_confirm_resume_harness_approved_true(monkeypatch):
    _offline(monkeypatch)
    for resume_val in ({"approved": True}, True, "approve"):
        g = compile_graph(checkpointer=MemorySaver())
        cfg = {"configurable": {"thread_id": f"security-hitl-{type(resume_val).__name__}"}}
        g.invoke(
            {
                "messages": [HumanMessage(content="Scan acme/widgets on main")],
                "repo": "acme/widgets",
                "ref": "main",
                "fixture_path": FIXTURE,
            },
            cfg,
        )
        final = g.invoke(Command(resume=resume_val), cfg)
        assert final.get("status") != "plan_denied"
        snap = g.get_state(cfg).values
        assert snap.get("plan_confirmed") is True
        summaries = " ".join(snap.get("stage_summaries") or [])
        assert "gather:" in summaries


def test_plan_confirm_deny_no_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "security-plan-deny"}}
    result = g.invoke(
        {
            "messages": [HumanMessage(content="Scan acme/widgets on main")],
            "repo": "acme/widgets",
            "ref": "main",
            "fixture_path": FIXTURE,
        },
        cfg,
    )
    assert "__interrupt__" in result
    final = g.invoke(Command(resume="deny"), cfg)
    assert final.get("status") == "plan_denied"
    assert "not scanning" in assistant_summary(final).lower()
    summaries = " ".join(final.get("stage_summaries") or [])
    assert "gather:" not in summaries


def test_programmatic_scan_skips_plan_confirm(monkeypatch):
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


def test_chat_parses_repo_slug(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "parse-slug"}}
    result = g.invoke(
        {"messages": [HumanMessage(content="Scan acme/billing on main, area src")]},
        cfg,
    )
    assert "__interrupt__" in result
    snap = g.get_state(cfg).values
    assert snap.get("repo") == "acme/billing"
    assert snap.get("ref") == "main"
    assert snap.get("area") == "src"
