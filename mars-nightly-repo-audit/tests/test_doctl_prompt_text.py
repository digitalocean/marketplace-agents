"""doctl agent prompt ``text`` shape: non-empty AIMessage on hi/help."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from nightly_repo_audit.graph import compile_graph
from nightly_repo_audit.mars_text import assemble_doctl_prompt_text, hi_chat_payload


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_doctl_text_hi_non_empty(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    raw = assemble_doctl_prompt_text(g, hi_chat_payload())
    assert raw.strip()
    assert "Nightly Repo Audit" in raw


def test_doctl_text_help_non_empty(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    payload = {"messages": [HumanMessage(content="what do you do?")]}
    raw = assemble_doctl_prompt_text(g, payload)
    assert raw.strip()
    assert "here's how i work" in raw.lower() or "nightly repo audit" in raw.lower()


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
    assert ai_chunks[0].strip()


def test_output_schema_messages_only_for_chat_text(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    props = g.get_output_jsonschema().get("properties") or {}
    assert "messages" in props
    assert "human_summary" not in props


def test_audit_stream_no_human_summary_or_emdash(monkeypatch):
    """Self-check / draft interim summaries must not leak em-dashes into stream text."""
    _offline(monkeypatch)
    from nightly_repo_audit.repo_scan import default_fixture_path

    g = compile_graph()
    payload = {
        "repo": "local/sample",
        "ref": "main",
        "fixture_path": str(default_fixture_path()),
        "force_empty": True,
    }
    streamed = ""
    for chunk in g.stream(payload, stream_mode="updates"):
        for _node, update in chunk.items():
            if not isinstance(update, dict):
                continue
            assert "human_summary" not in update
            for key in ("human_summary", "converse_reply", "chat_ack"):
                streamed += str(update.get(key) or "")
            for msg in update.get("messages") or []:
                if isinstance(msg, AIMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    streamed += content
    assert "—" not in streamed
    assert "–" not in streamed
