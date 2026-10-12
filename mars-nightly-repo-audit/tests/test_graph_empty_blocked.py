"""Empty findings skip ask; blocked checkout never asks."""

from __future__ import annotations

from pathlib import Path

from audit_helpers import assistant_summary
from nightly_repo_audit.graph import compile_graph
from nightly_repo_audit.repo_scan import default_fixture_path

FIXTURE = str(default_fixture_path())


def test_empty_findings_no_interrupt(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

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
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

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


def test_fixture_scan_finds_bait(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert Path(FIXTURE).is_dir()

    g = compile_graph()
    # Run only through analyze by using force path that still scans —
    # full graph will interrupt; use checkpointer-free invoke until ask
    from langgraph.checkpoint.memory import MemorySaver

    g2 = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "bait-scan"}}
    result = g2.invoke(
        {
            "repo": "acme/sample",
            "ref": "main",
            "area_hint": "src",
            "fixture_path": FIXTURE,
        },
        cfg,
    )
    assert "__interrupt__" in result
    # State before resume should have findings; peek via get_state
    snap = g2.get_state(cfg)
    values = snap.values
    findings = values.get("findings") or []
    assert len(findings) >= 1
    evidence_blob = " ".join(f.get("evidence", "") + f.get("path", "") for f in findings)
    assert "TODO" in evidence_blob or "FIXME" in evidence_blob or "legacy" in evidence_blob.lower()
