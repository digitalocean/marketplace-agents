"""Chat UX: no raw JSON/HTML in operator copy; first-run baseline tone."""

from __future__ import annotations

import json
from pathlib import Path

from competitor_pulse.graph import compile_graph
from competitor_pulse.pulse_diff import (
    default_watchlist,
    diff_snapshots,
    load_baseline,
    material_baseline_path,
    quiet_baseline_path,
    strip_html,
    summarize_change,
)


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def test_strip_html_removes_doctype():
    raw = "<!DOCTYPE HTML><html><title>FedEx | System Downtime</title><body>Down</body></html>"
    plain = strip_html(raw)
    assert "<!DOCTYPE" not in plain
    assert "<html" not in plain
    assert "FedEx" in plain
    assert "System Downtime" in plain


def test_summarize_change_never_includes_doctype():
    raw = "<!DOCTYPE HTML><html><head><title>FedEx | System Downtime</title></head><body>offline</body></html>"
    summary = summarize_change("site", "", raw, is_baseline_capture=True)
    assert "<!DOCTYPE" not in summary
    assert "error" in summary.lower() or "downtime" in summary.lower()


def test_first_run_empty_baseline_not_material_crisis(monkeypatch, tmp_path):
    """No prior baseline → first look, not 'material changes'."""
    _offline(monkeypatch)
    empty_bl = tmp_path / "empty.json"
    empty_bl.write_text(json.dumps({"version": 1, "entries": []}), encoding="utf-8")

    g = compile_graph()
    result = g.invoke(
        {
            "watchlist": default_watchlist(),
            "notify": False,
            "baseline_path": str(empty_bl),
            "allow_net": False,
        }
    )
    summary = (result.get("human_summary") or "").lower()
    assert result.get("first_run") is True
    assert result.get("material") is False
    assert "first look" in summary or "baseline" in summary
    assert "material change" not in summary
    assert '<!doctype' not in summary
    assert '{"watchlist"' not in summary


def test_track_fedex_chat_no_json_echo(monkeypatch, tmp_path):
    """Natural-language track should ack in plain English, never raw watchlist JSON."""
    _offline(monkeypatch)
    empty_bl = tmp_path / "empty.json"
    empty_bl.write_text(json.dumps({"version": 1, "entries": []}), encoding="utf-8")

    g = compile_graph()
    result = g.invoke(
        {
            "user_message": "track fedex",
            "notify": False,
            "baseline_path": str(empty_bl),
            "allow_net": False,
        }
    )
    summary = result.get("human_summary") or ""
    assert "Fedex" in summary or "fedex" in summary.lower()
    assert '{"watchlist"' not in summary
    assert "<!DOCTYPE" not in summary
    assert "review site_copy_change" not in summary


def test_material_diff_summaries_are_plain_language(monkeypatch):
    _offline(monkeypatch)
    g = compile_graph()
    result = g.invoke(
        {
            "watchlist": default_watchlist(),
            "notify": False,
            "baseline_path": str(material_baseline_path()),
            "allow_net": False,
        }
    )
    summary = result.get("human_summary") or ""
    brief = result.get("brief_md") or ""
    combined = summary + brief
    assert "<!DOCTYPE" not in combined
    assert "<html" not in combined.lower()
    assert "review site_copy_change" not in combined
    assert result.get("material") is True
    counterpositions = result.get("counterpositions") or []
    for c in counterpositions:
        assert "review site_copy_change" not in c


def test_diff_split_baseline_capture_vs_change():
    baseline = load_baseline(quiet_baseline_path())
    snapshots = [
        {
            "competitor": "Acme",
            "module": "site",
            "ok": True,
            "text": "<html><title>NewCo</title><body>Hello</body></html>",
            "content_hash": "abc123",
            "url": "https://example.com/acme/",
        }
    ]
    deltas = diff_snapshots(snapshots, {})
    assert len(deltas) == 1
    assert deltas[0].get("is_baseline_capture") is True
    assert "<!DOCTYPE" not in deltas[0].get("summary", "")

    deltas2 = diff_snapshots(snapshots, baseline)
    if deltas2:
        assert deltas2[0].get("is_baseline_capture") is False
