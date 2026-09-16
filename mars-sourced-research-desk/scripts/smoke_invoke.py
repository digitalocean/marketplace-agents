#!/usr/bin/env python3
"""Smoke invoke for Sourced Research Desk.

Documents harness env and runs the research-only path with fixtures when no
API key is set (no network, no spend).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running without editable install
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sourced_research_desk.graph import compile_graph  # noqa: E402
from sourced_research_desk.llm import harness_env_available, resolve_llm_env  # noqa: E402


FIXTURES = [
    {
        "url": "https://example.com/docs/citations",
        "title": "Citation guide",
        "ok": True,
        "claim": "Every factual claim in a research brief should include a url and a date.",
        "quote": "url and a date",
        "published_date": "2026-09-01",
        "text": "Every factual claim in a research brief should include a url and a date.",
        "confidence": "high",
    },
    {
        "url": "https://example.com/blog/mars-langgraph",
        "title": "LangGraph on MARS",
        "ok": True,
        "claim": "MARS pins a public GitHub SHA and injects HARNESS_INFERENCE_* for models.",
        "quote": "HARNESS_INFERENCE_* for models",
        "published_date": "2026-09-10",
        "text": "MARS pins a public GitHub SHA and injects HARNESS_INFERENCE_* for models.",
        "confidence": "high",
    },
]


def main() -> int:
    print("=== Sourced Research Desk smoke ===")
    print("Harness / OpenAI env resolution:")
    resolved = resolve_llm_env()
    print(
        json.dumps(
            {
                "base_url": resolved["base_url"],
                "model": resolved["model"],
                "api_key_set": bool(resolved["api_key"]),
                "prefer": "HARNESS_INFERENCE_* then OPENAI_*",
            },
            indent=2,
        )
    )
    if not harness_env_available():
        print(
            "\nNo HARNESS_INFERENCE_API_KEY / OPENAI_API_KEY — "
            "using fixture_sources (deterministic research-only)."
        )

    graph = compile_graph()
    result = graph.invoke(
        {
            "question": "How should sourced research briefs cite evidence on MARS?",
            "audience": "operators",
            "outbound": "none",
            "freshness_days": 30,
            "fixture_sources": FIXTURES,
        }
    )

    brief = result.get("brief_md") or ""
    claims = result.get("claims") or []
    print("\n--- status ---")
    print(result.get("status"))
    print("\n--- human_summary ---")
    print(result.get("human_summary"))
    print("\n--- claim_count ---")
    print(result.get("claim_count"), f"({len(claims)} claims)")
    for c in claims:
        print(f"  - {c.get('claim', '')[:80]}… url={c.get('url')} date={c.get('date')}")
    print("\n--- brief_md (excerpt) ---")
    print("\n".join(brief.splitlines()[:24]))
    if not brief or not claims:
        print("SMOKE FAIL: expected brief_md and sourced claims", file=sys.stderr)
        return 1
    for c in claims:
        if not c.get("url") or not c.get("date"):
            print("SMOKE FAIL: claim missing url/date", file=sys.stderr)
            return 1
    print("\nSMOKE OK")
    return 0


if __name__ == "__main__":
    # Optional: document expected exports without requiring them
    _ = os.environ.get("HARNESS_INFERENCE_BASE_URL")
    raise SystemExit(main())
