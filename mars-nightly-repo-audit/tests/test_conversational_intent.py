"""Conversational intent routing: chat, help, audit path unchanged."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from audit_helpers import assistant_summary
from nightly_repo_audit.graph import compile_graph
from nightly_repo_audit.intent import (
    classify_intent,
    is_audit_request,
    is_chat_message,
    is_help_message,
)
from nightly_repo_audit.persona import help_message
from nightly_repo_audit.nodes import intake
from nightly_repo_audit.repo_scan import default_fixture_path

FIXTURE = str(default_fixture_path())


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_classify_chat_and_help():
    assert classify_intent("hi") == "chat"
    assert classify_intent("what do you do?") == "help"
    assert classify_intent("", programmatic_audit=True) == "audit"
    assert is_chat_message("hello") is True
    assert is_help_message("how does this work") is True


def test_intake_hi_emits_chat_aimessage(monkeypatch):
    _offline(monkeypatch)
    result = intake({"messages": [HumanMessage(content="hi")]})
    assert result.get("intent") == "chat"
    assert result.get("messages")
    summary = assistant_summary(result)
    assert "Nightly Repo Audit" in summary
    assert "without your ok" in summary.lower()


def test_hi_full_graph_no_gather(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke({"messages": [HumanMessage(content="hi")]})
    summary = assistant_summary(result)
    assert result.get("status") == "chat"
    assert "Nightly Repo Audit" in summary
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "gather:" not in summaries
    assert "plan:" not in summaries


def test_help_full_graph(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke({"messages": [HumanMessage(content="what do you do?")]})
    summary = assistant_summary(result)
    assert result.get("status") == "help"
    assert "how i work" in summary.lower() or "hygiene" in summary.lower()


def test_b2_starter_intent_matrix():
    """Each B2 welcome starter must enter audit_plan, never help."""
    starters = [
        "Audit owner/name on main, area src",
        "Nightly cleanup on owner/name (fixtures OK)",
        "Audit owner/name and prepare a draft PR",
    ]
    help_copy = help_message()
    for text in starters:
        assert classify_intent(text) == "audit_plan"
        assert is_audit_request(text)
        assert classify_intent(text) != "help"
        assert help_copy not in text


def test_audit_nl_not_help():
    """Domain audit prompts must not route to help (Reed MARS smoke)."""
    samples = [
        "Audit acme/widgets on main, area src",
        "Audit owner/name on main, area src",
        "Nightly cleanup on owner/name (fixtures OK)",
        "Audit owner/name and prepare a draft PR",
        "cleanup src on acme/widgets",
        "Run audit on acme/widgets",
    ]
    for text in samples:
        assert classify_intent(text) == "audit_plan"
        assert is_audit_request(text)
        assert classify_intent(text) != "help"


def test_approve_deny_with_pending_audit():
    pending = {"repo": "acme/widgets", "area": "src"}
    assert classify_intent("approve", pending_audit=pending) == "audit"
    assert classify_intent("deny", pending_audit=pending) == "plan_denied"
    assert classify_intent("yes", pending_audit=pending) == "audit"
    assert classify_intent("approve") == "other"
    assert classify_intent("deny") == "other"
    assert is_help_message("approve") is False
    assert is_help_message("deny") is False


def test_audit_nl_full_graph_plan_confirm_not_help(monkeypatch):
    """Audit NL via messages should hit plan confirm, not help prose."""
    _offline(monkeypatch)
    g = compile_graph()
    for msg in (
        "Audit acme/widgets on main, area src",
        "Nightly cleanup on owner/name (fixtures OK)",
    ):
        result = g.invoke(
            {
                "messages": [HumanMessage(content=msg)],
                "repo": "acme/widgets",
                "ref": "main",
                "fixture_path": FIXTURE,
            }
        )
        summary = assistant_summary(result)
        assert result.get("status") != "help"
        assert "here's how i work" not in summary.lower()
        assert "__interrupt__" in result
        payload = result["__interrupt__"][0].value
        assert payload.get("title") == "Start repo audit?"
        assert (payload.get("body") or "").startswith("Want me to run this audit?")


def test_programmatic_audit_still_runs(monkeypatch):
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
    assert result.get("status") == "empty"
    summaries = " ".join(result.get("stage_summaries") or [])
    assert "analyze:" in summaries
