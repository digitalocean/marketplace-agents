"""Ask payload Sol contract; resume approve/deny."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from nightly_repo_audit.graph import compile_graph
from nightly_repo_audit.repo_scan import default_fixture_path

FIXTURE = str(default_fixture_path())


def _run_to_interrupt(monkeypatch, thread_id: str = "nightly-ask"):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": thread_id}}
    result = g.invoke(
        {
            "repo": "acme/widgets",
            "ref": "main",
            "trigger": "cron",
            "area_hint": "src",
            "fixture_path": FIXTURE,
        },
        cfg,
    )
    return g, cfg, result


def test_ask_payload_contract(monkeypatch):
    _g, _cfg, result = _run_to_interrupt(monkeypatch, "ask-contract")
    assert "__interrupt__" in result
    payload = result["__interrupt__"][0].value
    assert payload.get("title") == "Want me to open this cleanup PR on acme/widgets?"
    assert payload.get("pending_action") == "open_pr"
    assert payload.get("choices") == ["approve", "deny"]
    body = payload.get("body") or ""
    assert "Branch:" in body
    assert "Title:" in body
    assert "Scope:" in body
    assert "Changes:" in body
    assert "What it does:" in body
    assert "What it will not do:" in body
    assert "Evidence:" in body
    assert "approve" in payload.get("choices", [])
    assert "deny" in payload.get("choices", [])


def test_resume_deny_no_pr(monkeypatch):
    g, cfg, result = _run_to_interrupt(monkeypatch, "deny-path")
    assert "__interrupt__" in result

    final = g.invoke(Command(resume="deny"), cfg)
    assert "__interrupt__" not in final
    assert final.get("status") == "denied"
    assert final.get("skipped") is True
    assert not final.get("pr_url")
    assert final.get("decision") == "deny"


def test_resume_approve_stub_pr(monkeypatch):
    g, cfg, result = _run_to_interrupt(monkeypatch, "approve-path")
    assert "__interrupt__" in result

    final = g.invoke(Command(resume="approve"), cfg)
    assert "__interrupt__" not in final
    assert final.get("status") == "opened"
    assert final.get("skipped") is not True
    assert final.get("decision") == "approve"
    assert final.get("pr_title")
    assert final.get("pr_body_md")
    assert final.get("pr_url", "").startswith("https://")
    assert final.get("pr_number") == 9001
