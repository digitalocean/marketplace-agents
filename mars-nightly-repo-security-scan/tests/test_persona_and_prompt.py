"""Persona copy and doctl prompt text."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from nightly_repo_security_scan.graph import compile_graph
from nightly_repo_security_scan.hygiene import hygiene_text
from nightly_repo_security_scan.mars_text import assemble_doctl_prompt_text, hi_chat_payload
from nightly_repo_security_scan.persona import (
    ask_body,
    ask_title,
    help_message,
    plan_confirm_body,
    plan_confirm_title,
    welcome_message,
)


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_welcome_and_help_voice():
    welcome = hygiene_text(welcome_message())
    assert "Nightly Repo Security Scan" in welcome
    assert "without your OK" in welcome
    assert "Grok 4.7" in welcome
    assert "—" not in welcome
    help_text = hygiene_text(help_message())
    assert "here's how i work" in help_text.lower()
    assert "ask before i scan" in help_text.lower()
    assert "—" not in help_text


def test_ask_and_plan_are_questions():
    assert ask_title() == "Open security fix PR?"
    assert plan_confirm_title() == "Start security scan?"
    plan = plan_confirm_body(
        repo="acme/widgets",
        ref="main",
        area="src",
        scope_limits="No merge and no force-push",
        trigger="manual",
    )
    assert plan.startswith("Want me to run this security scan?")
    assert "—" not in hygiene_text(plan)
    body = ask_body(
        repo="acme/widgets",
        branch="nightly/security-src",
        pr_title="fix: nightly security scan",
        area="src",
        diff_stat="+4 / −2 across 1 files",
        bullets="- bump requests",
    )
    assert body.startswith("Want me to open a draft PR on acme/widgets?")
    assert "—" not in body


def test_hygiene_strips_stage_labels():
    raw = "draft: PR draft ready\nstatus: ok\nCertainly, opening PR."
    cleaned = hygiene_text(raw)
    assert "status: ok" not in cleaned.lower()
    assert "Certainly" not in cleaned


def test_doctl_text_hi_non_empty(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    raw = assemble_doctl_prompt_text(g, hi_chat_payload())
    assert "Nightly Repo Security Scan" in raw
    props = g.get_output_jsonschema().get("properties") or {}
    assert "messages" in props
    assert "human_summary" not in props


def test_hi_stream_emits_aimessage_once(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    ai_chunks: list[str] = []
    for chunk in g.stream(hi_chat_payload(), stream_mode="updates"):
        for node, update in chunk.items():
            u = update or {}
            assert "human_summary" not in u
            if node == "intake":
                for msg in u.get("messages") or []:
                    if isinstance(msg, AIMessage):
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        ai_chunks.append(content)
    assert len(ai_chunks) == 1
    assert "—" not in ai_chunks[0]


def test_help_prompt_text(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    raw = assemble_doctl_prompt_text(
        g, {"messages": [HumanMessage(content="what do you do?")]}
    )
    assert "how i work" in raw.lower() or "nightly repo security scan" in raw.lower()
