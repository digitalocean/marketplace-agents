"""doctl agent prompt ``text`` shape: no watchlist JSON, greeting once."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage

from competitor_pulse.chat import contains_watchlist_json
from competitor_pulse.graph import compile_graph
from competitor_pulse.mars_text import assemble_doctl_prompt_text, hi_chat_payload

_GREETING_RE = re.compile(
    r"(Hey there|Hey — I'm|Hey, welcome).{0,40}Competitor Pulse",
    re.IGNORECASE,
)


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def _greeting_count(text: str) -> int:
    return len(_GREETING_RE.findall(text))


def test_doctl_text_hi_without_watchlist_input(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    payload = hi_chat_payload()
    text = assemble_doctl_prompt_text(g, payload)
    assert not contains_watchlist_json(text)
    assert _greeting_count(text) == 1
    assert "Competitor Pulse" in text


def test_doctl_text_hi_rejects_legacy_empty_watchlist_input(monkeypatch):
    """Input schema no longer accepts watchlist; legacy [] cannot prefix ``text``."""
    _offline(monkeypatch)
    g = compile_graph()
    payload = hi_chat_payload(include_empty_watchlist=True)
    text = assemble_doctl_prompt_text(g, payload)
    assert not contains_watchlist_json(text)
    assert _greeting_count(text) == 1


def test_doctl_text_track_fedex_first_run_clean(monkeypatch, tmp_path):
    _offline(monkeypatch)
    empty_bl = tmp_path / "empty.json"
    empty_bl.write_text(json.dumps({"version": 1, "entries": []}), encoding="utf-8")
    g = compile_graph()
    payload = {
        "messages": [HumanMessage(content="track fedex")],
        "allow_net": False,
        "baseline_path": str(empty_bl),
    }
    text = assemble_doctl_prompt_text(g, payload)
    assert not contains_watchlist_json(text)
    assert text.lower().count("fedex") >= 1


def test_doctl_text_hi_stream_updates_never_emit_human_summary(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    payload = hi_chat_payload()
    for chunk in g.stream(payload, stream_mode="updates"):
        for _node, update in chunk.items():
            u = update or {}
            assert "human_summary" not in u
            assert "watchlist" not in u
            assert "internal" not in u
            assert "converse_reply" not in u


def test_input_schema_excludes_watchlist(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    schema = g.get_input_jsonschema()
    props = schema.get("properties") or {}
    assert "watchlist" not in props
    assert "internal" not in props
    assert "messages" in props


def test_output_schema_messages_only_for_chat_text(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    schema = g.get_output_jsonschema()
    props = schema.get("properties") or {}
    assert "messages" in props
    assert "human_summary" not in props
    assert "watchlist" not in props
    assert "internal" not in props


def test_input_schema_printable_proof(monkeypatch, capsys):
    """Regression guard: exported input JSON schema must not expose watchlist."""
    _offline(monkeypatch)
    g = compile_graph()
    schema = g.get_input_jsonschema()
    print(json.dumps(schema, indent=2, sort_keys=True))
    captured = capsys.readouterr().out
    assert '"watchlist"' not in captured
    assert '"internal"' not in captured
