"""Conversational intent routing."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from nightly_repo_security_scan.graph import compile_graph
from nightly_repo_security_scan.intent import (
    classify_intent,
    is_chat_message,
    is_help_message,
    is_scan_request,
    parse_scan_target,
)
from nightly_repo_security_scan.nodes import intake
from nightly_repo_security_scan.persona import help_message
from scan_helpers import assistant_summary


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_classify_chat_and_help():
    assert classify_intent("hi") == "chat"
    assert classify_intent("what do you do?") == "help"
    assert classify_intent("", programmatic_scan=True) == "scan"
    assert is_chat_message("hello") is True
    assert is_help_message("how does this work") is True
    assert is_help_message("how do I scan") is True


def test_parse_scan_target():
    parsed = parse_scan_target("Scan acme/billing on main, area src")
    assert parsed == {"repo": "acme/billing", "ref": "main", "area": "src"}
    nightly = parse_scan_target("Nightly security scan on owner/name (fixtures OK)")
    assert nightly["repo"] == "owner/name"
    assert nightly["ref"] == ""


def test_intake_hi_emits_chat(monkeypatch):
    _offline(monkeypatch)
    result = intake({"messages": [HumanMessage(content="hi")]})
    assert result.get("intent") == "chat"
    summary = assistant_summary(result)
    assert "Nightly Repo Security Scan" in summary
    assert "without your ok" in summary.lower()
    assert "grok 4.7" in summary.lower()


def test_hi_full_graph_no_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke({"messages": [HumanMessage(content="hi")]})
    assert result.get("status") == "chat"
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "gather:" not in summaries
    assert "plan:" not in summaries


def test_help_full_graph(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke({"messages": [HumanMessage(content="what do you do?")]})
    summary = assistant_summary(result)
    assert result.get("status") == "help"
    assert "how i work" in summary.lower()


def test_starter_intent_matrix():
    starters = [
        "Scan owner/name on main, area src",
        "Nightly security scan on owner/name (fixtures OK)",
        "Scan owner/name and prepare a draft PR",
    ]
    help_copy = help_message()
    for text in starters:
        assert classify_intent(text) == "scan_plan"
        assert is_scan_request(text)
        assert help_copy not in text


def test_approve_deny_with_pending_scan():
    pending = {"repo": "acme/widgets", "area": "src"}
    assert classify_intent("approve", pending_scan=pending) == "scan"
    assert classify_intent("deny", pending_scan=pending) == "plan_denied"
    assert classify_intent("approve") == "other"
    assert is_help_message("approve") is False
