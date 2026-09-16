"""Research-only path: fixtures → brief, no interrupt; claims have url+date."""

from __future__ import annotations

from sourced_research_desk.graph import compile_graph


FIXTURE_SOURCES = [
    {
        "url": "https://example.com/docs/alpha",
        "title": "Alpha docs",
        "ok": True,
        "claim": "Alpha service supports dated citations in research briefs.",
        "quote": "supports dated citations",
        "published_date": "2026-09-01",
        "text": "Alpha service supports dated citations in research briefs.",
        "confidence": "high",
    },
    {
        "url": "https://example.com/blog/beta",
        "title": "Beta blog",
        "ok": True,
        "claim": "Beta published a September update on public-web research workflows.",
        "quote": "September update on public-web research",
        "published_date": "2026-09-10",
        "text": "Beta published a September update on public-web research workflows.",
        "confidence": "medium",
    },
]


def test_research_only_produces_brief_without_interrupt(monkeypatch):
    # Ensure deterministic / offline path
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    g = compile_graph()
    result = g.invoke(
        {
            "question": "What changed in public-web research tooling?",
            "outbound": "none",
            "freshness_days": 30,
            "fixture_sources": FIXTURE_SOURCES,
        }
    )

    assert "__interrupt__" not in result
    assert result.get("brief_md")
    assert "Research brief" in result["brief_md"]
    assert result.get("claim_count", 0) >= 2
    claims = result.get("claims") or []
    assert len(claims) >= 2
    for c in claims:
        assert c.get("url"), "claim missing url"
        assert c.get("date"), "claim missing date"
    assert result.get("status") in {"ok", "empty"}
    assert result.get("sent") is not True
    assert "not sent" in (result.get("human_summary") or "").lower() or result.get(
        "outbound"
    ) == "none"


def test_claims_map_into_brief_citations(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    g = compile_graph()
    result = g.invoke(
        {
            "question": "Citation quality check",
            "outbound": "none",
            "fixture_sources": FIXTURE_SOURCES,
        }
    )
    brief = result["brief_md"]
    assert "https://example.com/docs/alpha" in brief
    assert "https://example.com/blog/beta" in brief
    assert "2026-09-01" in brief or "2026-09-10" in brief
