"""Empty findings skip ask; blocked checkout never asks."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from nightly_repo_security_scan.graph import compile_graph
from nightly_repo_security_scan.security_scan import default_fixture_path
from scan_helpers import assistant_summary

FIXTURE = str(default_fixture_path())


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")
    monkeypatch.delenv("SECURITY_SCAN_LLM_REVIEW", raising=False)


def test_empty_findings_no_interrupt(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {
            "repo": "local/sample",
            "ref": "main",
            "trigger": "manual",
            "fixture_path": FIXTURE,
            "force_empty": True,
        }
    )
    assert "__interrupt__" not in result
    assert result.get("status") == "empty"
    assert not result.get("findings")
    assert "staying quiet" in assistant_summary(result).lower()
    summaries = result.get("stage_summaries") or []
    assert any("analyze" in s for s in summaries)
    assert any("report" in s for s in summaries)


def test_blocked_no_interrupt(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {
            "repo": "local/sample",
            "ref": "main",
            "force_blocked": True,
        }
    )
    assert "__interrupt__" not in result
    assert result.get("status") == "blocked"
    assert "ask" not in " ".join(result.get("stage_summaries") or [])


def test_fixture_scan_finds_bait_and_patch(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "bait-scan"}}
    result = g.invoke(
        {
            "repo": "acme/sample",
            "ref": "main",
            "area_hint": "src",
            "fixture_path": FIXTURE,
        },
        cfg,
    )
    assert "__interrupt__" in result
    values = g.get_state(cfg).values
    findings = values.get("findings") or []
    assert len(findings) >= 3
    kinds = {item.get("kind") for item in findings}
    assert "dependency" in kinds
    assert "app" in kinds
    body = values.get("pr_body_md") or ""
    assert "yaml.safe_load" in body
    assert "ast.literal_eval" in body
    assert "requests==2.32.3" in body
    assert "lodash" in body
    assert values.get("branch_name") == "nightly/security-src"
