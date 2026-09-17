"""Stage nodes: intake → plan → gather → analyze → draft → ask → act → report."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from sourced_research_desk.hygiene import hygiene_text
from sourced_research_desk.llm import harness_env_available
from sourced_research_desk.llm_http import plan_from_llm, suggest_urls_from_llm
from sourced_research_desk.persona import ask_body, ask_title, research_plan_summary
from sourced_research_desk.state import ResearchState

_HTTP_ALLOW = {"http", "https"}
_FETCH_TIMEOUT = 15.0
_MAX_TEXT = 8000


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return date.today().isoformat()


def _append_summary(state: ResearchState, line: str) -> list[str]:
    prev = list(state.get("stage_summaries") or [])
    prev.append(line)
    return prev


def _deterministic_mode(state: ResearchState) -> bool:
    """Offline/tests: fixtures present and no inference key."""
    fixtures = state.get("fixture_sources") or []
    return bool(fixtures) and not harness_env_available()


# ---------------------------------------------------------------------------
# intake
# ---------------------------------------------------------------------------


def intake(state: ResearchState) -> dict[str, Any]:
    question = (state.get("question") or "").strip()
    if not question:
        return {
            "status": "blocked",
            "human_summary": "Blocked: missing question.",
            "stage_summaries": _append_summary(state, "intake: missing question"),
            "outbound": "none",
        }
    outbound = (state.get("outbound") or "none").strip().lower()
    if outbound not in {"none", "slack", "email"}:
        outbound = "none"
    freshness = int(state.get("freshness_days") or 30)
    audience = (state.get("audience") or "operators").strip()
    summary = f"Researching: {question}"
    return {
        "question": question,
        "audience": audience,
        "outbound": outbound,
        "freshness_days": freshness,
        "destination": state.get("destination") or "",
        "subject": state.get("subject") or f"Research brief: {question[:80]}",
        "seed_urls": list(state.get("seed_urls") or []),
        "fixture_sources": list(state.get("fixture_sources") or []),
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"intake: {summary}"),
        "sent": False,
        "skipped": False,
        "unsourced": False,
    }


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def _plan_deterministic(question: str) -> tuple[list[str], list[str]]:
    q = question.strip()
    subquestions = [
        f"What is the current status of: {q}?",
        f"What recent evidence exists for: {q}?",
        f"What conflicting views exist on: {q}?",
    ]
    # Lightweight query strings (no paid search required)
    words = re.findall(r"[A-Za-z0-9\-]+", q.lower())
    stem = " ".join(words[:8]) or "research"
    search_queries = [
        f"{stem} overview",
        f"{stem} recent developments",
        f"{stem} sources",
    ]
    return subquestions, search_queries


def plan(state: ResearchState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}
    question = state["question"]
    if _deterministic_mode(state) or not harness_env_available():
        subquestions, search_queries = _plan_deterministic(question)
    else:
        text = plan_from_llm(question)
        if text:
            subquestions, search_queries = _parse_plan_llm(text, question)
        else:
            subquestions, search_queries = _plan_deterministic(question)

    outbound = (state.get("outbound") or "none").strip().lower()
    summary = hygiene_text(
        research_plan_summary(
            question=question,
            subquestions=subquestions,
            search_queries=search_queries,
            outbound=outbound,
            destination=(state.get("destination") or "").strip(),
            allow_net=not _deterministic_mode(state),
        )
    )
    return {
        "subquestions": subquestions,
        "search_queries": search_queries,
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"plan: {summary}"),
    }


def _parse_plan_llm(text: str, question: str) -> tuple[list[str], list[str]]:
    subs: list[str] = []
    queries: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        upper = line.upper()
        if upper.startswith("SUBQUESTIONS:"):
            subs = [p.strip() for p in line.split(":", 1)[1].split("|") if p.strip()]
        elif upper.startswith("QUERIES:"):
            queries = [p.strip() for p in line.split(":", 1)[1].split("|") if p.strip()]
    if not subs or not queries:
        return _plan_deterministic(question)
    return subs[:3], queries[:3]


# ---------------------------------------------------------------------------
# gather
# ---------------------------------------------------------------------------


def _allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in _HTTP_ALLOW and bool(parsed.netloc)


def _fetch_url(url: str) -> dict[str, Any]:
    if not _allowed_url(url):
        return {
            "url": url,
            "title": "",
            "fetched_at": _now_iso(),
            "ok": False,
            "error": "url not allowlisted (http/https only)",
            "text": "",
        }
    try:
        with httpx.Client(follow_redirects=True, timeout=_FETCH_TIMEOUT) as client:
            resp = client.get(url, headers={"User-Agent": "sourced-research-desk/0.1"})
            text = resp.text[:_MAX_TEXT] if resp.is_success else ""
            title = _guess_title(text, url)
            return {
                "url": str(resp.url),
                "title": title,
                "fetched_at": _now_iso(),
                "ok": resp.is_success,
                "text": text,
                "published_date": _today(),
                "error": "" if resp.is_success else f"HTTP {resp.status_code}",
            }
    except Exception as exc:
        return {
            "url": url,
            "title": "",
            "fetched_at": _now_iso(),
            "ok": False,
            "error": str(exc),
            "text": "",
        }


def _guess_title(html_or_text: str, url: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html_or_text, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    return urlparse(url).netloc or url


def gather(state: ResearchState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    fixtures = list(state.get("fixture_sources") or [])
    if fixtures:
        sources: list[dict[str, Any]] = []
        for fx in fixtures:
            sources.append(
                {
                    "url": fx.get("url", "https://example.com/fixture"),
                    "title": fx.get("title", "Fixture source"),
                    "fetched_at": fx.get("fetched_at", _now_iso()),
                    "ok": fx.get("ok", True),
                    "text": fx.get("text", fx.get("quote", "")),
                    "published_date": fx.get("published_date")
                    or fx.get("date")
                    or _today(),
                    "error": fx.get("error", ""),
                }
            )
        ok_n = sum(1 for s in sources if s.get("ok"))
        fail_n = len(sources) - ok_n
        summary = f"Fetched {ok_n} sources ({fail_n} failed) [fixtures]."
        return {
            "sources": sources,
            "human_summary": summary,
            "stage_summaries": _append_summary(state, f"gather: {summary}"),
        }

    urls: list[str] = []
    for u in state.get("seed_urls") or []:
        if u and u not in urls:
            urls.append(u)

    # Optional LLM-suggested public URLs when live key present
    if harness_env_available() and not urls:
        text = suggest_urls_from_llm(state.get("question") or "")
        if text:
            for line in text.splitlines():
                cand = line.strip().strip("`").strip()
                if cand.startswith("http") and _allowed_url(cand) and cand not in urls:
                    urls.append(cand)
                if len(urls) >= 3:
                    break

    sources = [_fetch_url(u) for u in urls]
    ok_n = sum(1 for s in sources if s.get("ok"))
    fail_n = len(sources) - ok_n
    summary = f"Fetched {ok_n} sources ({fail_n} failed)."
    if not sources:
        summary = "Fetched 0 sources (provide seed_urls or fixture_sources)."
    return {
        "sources": sources,
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"gather: {summary}"),
    }


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


def _claims_from_sources(
    question: str, sources: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims: list[dict[str, Any]] = []
    for src in sources:
        if not src.get("ok"):
            continue
        url = src.get("url") or ""
        pub = src.get("published_date") or (src.get("fetched_at") or _today())[:10]
        title = src.get("title") or url
        text = (src.get("text") or "").strip()
        # Prefer explicit fixture claim field
        if src.get("claim"):
            claim_text = str(src["claim"])
        elif text:
            # First non-empty sentence-ish chunk
            snippet = re.split(r"(?<=[.!?])\s+", text)[0].strip()
            snippet = re.sub(r"<[^>]+>", "", snippet)
            claim_text = snippet[:280] if snippet else f"Source discusses: {title}"
        else:
            claim_text = f"Source available on topic related to: {question}"
        quote = (src.get("quote") or text[:160] or claim_text)[:200]
        claims.append(
            {
                "claim": claim_text,
                "url": url,
                "date": pub,
                "quote": quote,
                "confidence": src.get("confidence", "medium"),
            }
        )

    conflicts: list[dict[str, Any]] = []
    # Simple conflict: duplicate topics with very different claim text lengths / polarity words
    neg = re.compile(r"\b(not|no|never|false|deny|refut)", re.I)
    pos = re.compile(r"\b(yes|confirmed|supports|true|agre)", re.I)
    if len(claims) >= 2:
        a, b = claims[0], claims[1]
        if (neg.search(a["claim"]) and pos.search(b["claim"])) or (
            pos.search(a["claim"]) and neg.search(b["claim"])
        ):
            conflicts.append(
                {
                    "topic": question[:80],
                    "summary": "Sources appear to disagree on polarity.",
                    "urls": [a["url"], b["url"]],
                }
            )
    return claims, conflicts


def analyze(state: ResearchState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}
    sources = list(state.get("sources") or [])
    question = state.get("question") or ""

    if _deterministic_mode(state) or not harness_env_available():
        claims, conflicts = _claims_from_sources(question, sources)
    else:
        try:
            claims, conflicts = _claims_from_sources(question, sources)
            # Live path still builds deterministic claims from fetched text;
            # LLM could refine later — keep v1 grounded in source text.
        except Exception:
            claims, conflicts = [], []

    ok_sources = [s for s in sources if s.get("ok")]
    if not claims and ok_sources:
        claims, conflicts = _claims_from_sources(question, sources)

    summary = f"Claims: {len(claims)}; conflicts: {len(conflicts)}."
    return {
        "claims": claims,
        "conflicts": conflicts,
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"analyze: {summary}"),
    }


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------


def _draft_brief(
    question: str,
    audience: str,
    claims: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Research brief",
        "",
        f"**Question:** {question}",
        f"**Audience:** {audience}",
        "",
        "## Findings",
        "",
    ]
    if not claims:
        lines.append("- No sourced claims available.")
    else:
        for i, c in enumerate(claims, 1):
            lines.append(
                f"{i}. {c.get('claim', '').strip()} "
                f"([{_domain(c.get('url', ''))}]({c.get('url', '')}), "
                f"{c.get('date', 'n/a')})"
            )
    lines.extend(["", "## Conflicts", ""])
    if not conflicts:
        lines.append("- None flagged.")
    else:
        for conf in conflicts:
            lines.append(f"- {conf.get('summary', '')} ({', '.join(conf.get('urls') or [])})")
    lines.extend(
        [
            "",
            "## Citations",
            "",
        ]
    )
    for i, c in enumerate(claims, 1):
        lines.append(f"{i}. {c.get('url', '')} — {c.get('date', 'n/a')}")
    lines.append("")
    return "\n".join(lines)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc or "source"
    except Exception:
        return "source"


def _brief_has_unsourced_bullets(brief_md: str, claims: list[dict[str, Any]]) -> bool:
    """Quality bar: every factual bullet should map to a claim with url+date."""
    if not claims:
        # Brief with only "No sourced claims" is empty, not unsourced invention
        return False
    for c in claims:
        if not (c.get("url") and c.get("date")):
            return True
    # Bullets under Findings that look factual without a markdown link
    in_findings = False
    for line in brief_md.splitlines():
        if line.strip().startswith("## Findings"):
            in_findings = True
            continue
        if line.strip().startswith("## ") and in_findings:
            break
        if not in_findings:
            continue
        stripped = line.strip()
        if not stripped.startswith(("-", "*")) and not re.match(r"^\d+\.", stripped):
            continue
        if "No sourced claims" in stripped:
            continue
        if "](" not in stripped and "http" not in stripped:
            return True
    return False


def draft(state: ResearchState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}
    claims = list(state.get("claims") or [])
    conflicts = list(state.get("conflicts") or [])
    question = state.get("question") or ""
    audience = state.get("audience") or "operators"

    if not claims:
        brief = hygiene_text(_draft_brief(question, audience, claims, conflicts))
        return {
            "brief_md": brief,
            "claim_count": 0,
            "oldest_source_date": "",
            "newest_source_date": "",
            "unsourced": False,
            "status": "empty",
            "draft_message": brief,
            "human_summary": "Brief empty — no claims.",
            "stage_summaries": _append_summary(
                state, "draft: empty — no claims"
            ),
        }

    brief = hygiene_text(_draft_brief(question, audience, claims, conflicts))
    dates = sorted(c.get("date", "") for c in claims if c.get("date"))
    oldest = dates[0] if dates else ""
    newest = dates[-1] if dates else ""
    unsourced = _brief_has_unsourced_bullets(brief, claims)

    status = "blocked" if unsourced else (state.get("status") or "ok")
    if unsourced:
        summary = (
            "Unsourced claims — revise question or allow more fetches; "
            "no outbound ask."
        )
    else:
        preview = "\n".join(brief.splitlines()[:12])
        summary = f"Brief ready ({len(claims)} claims).\n{preview}"

    draft_message = brief
    if state.get("outbound") and state.get("outbound") != "none":
        draft_message = (
            f"{state.get('subject') or 'Research brief'}\n\n{brief}"
        )

    return {
        "brief_md": brief,
        "claim_count": len(claims),
        "oldest_source_date": oldest,
        "newest_source_date": newest,
        "unsourced": unsourced,
        "status": status if unsourced else "ok",
        "draft_message": draft_message,
        "human_summary": summary,
        "stage_summaries": _append_summary(
            state,
            f"draft: {'blocked unsourced' if unsourced else f'{len(claims)} claims'}",
        ),
    }


# ---------------------------------------------------------------------------
# routing helpers
# ---------------------------------------------------------------------------


def should_ask(state: ResearchState) -> str:
    """Route after draft: ask | report."""
    if state.get("status") in {"blocked", "empty", "error"}:
        return "report"
    outbound = (state.get("outbound") or "none").lower()
    if outbound == "none":
        return "report"
    if state.get("unsourced"):
        return "report"
    if not state.get("claims"):
        return "report"
    return "ask"


# ---------------------------------------------------------------------------
# ask / act / report
# ---------------------------------------------------------------------------


def ask(state: ResearchState) -> dict[str, Any]:
    """Interrupt for human approval before outbound send."""
    from langgraph.types import interrupt

    channel = state.get("outbound") or state.get("channel") or "slack"
    destination = state.get("destination") or "(not set)"
    subject = state.get("subject") or "Research brief"
    draft_message = state.get("draft_message") or state.get("brief_md") or ""
    preview_lines = "\n".join(draft_message.splitlines()[:8])
    claim_count = state.get("claim_count") or len(state.get("claims") or [])
    oldest = state.get("oldest_source_date") or "n/a"
    newest = state.get("newest_source_date") or "n/a"
    conflicts = state.get("conflicts") or []

    body = hygiene_text(
        ask_body(
            channel=channel,
            destination=destination,
            subject=subject,
            preview_lines=preview_lines,
            claim_count=int(claim_count),
            oldest=oldest,
            newest=newest,
            conflicts_n=len(conflicts),
        )
    )
    payload = {
        "title": ask_title(channel=channel),
        "body": body,
        "pending_action": "send_outbound",
        "channel": channel,
        "choices": ["approve", "deny"],
    }
    decision = interrupt(payload)
    # Normalize resume value
    if isinstance(decision, dict):
        decision = decision.get("decision") or decision.get("value") or "deny"
    decision_s = str(decision).strip().lower()
    if decision_s not in {"approve", "deny"}:
        decision_s = "deny"
    return {
        "pending_action": "send_outbound",
        "channel": channel,
        "ask_payload": payload,
        "decision": decision_s,
        "human_summary": f"Ask answered: {decision_s}",
        "stage_summaries": _append_summary(state, f"ask: {decision_s}"),
    }


def act(state: ResearchState) -> dict[str, Any]:
    decision = (state.get("decision") or "deny").lower()
    if decision != "approve":
        return {
            "sent": False,
            "skipped": True,
            "status": "denied",
            "message_id": "",
            "human_summary": "Denied — no send; brief remains in run artifacts.",
            "stage_summaries": _append_summary(state, "act: denied — no send"),
        }
    # Stub send only — never real Slack/email
    message_id = f"stub-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    return {
        "sent": True,
        "skipped": False,
        "status": "ok",
        "message_id": message_id,
        "human_summary": f"Stub send recorded (message_id={message_id}).",
        "stage_summaries": _append_summary(state, f"act: stub sent {message_id}"),
    }


def report(state: ResearchState) -> dict[str, Any]:
    outbound = (state.get("outbound") or "none").lower()
    status = state.get("status") or "ok"
    claim_count = state.get("claim_count") or len(state.get("claims") or [])
    conflicts_n = len(state.get("conflicts") or [])
    question = state.get("question") or ""

    if status == "blocked":
        summary = (
            "Sourced Research Desk — blocked\n\n"
            f"Question: {question}\n"
            "Reason: unsourced claims or intake failure. No outbound ask."
        )
    elif status == "empty":
        summary = (
            "Sourced Research Desk — empty\n\n"
            f"Question: {question}\n"
            "No sourced claims to brief."
        )
    elif status == "denied":
        summary = (
            "Sourced Research Desk — denied\n\n"
            f"Question: {question}\n"
            f"Claims:   {claim_count} with urls + dates\n"
            "Outbound: not sent; brief kept in artifacts."
        )
    elif outbound == "none" or not state.get("sent"):
        if outbound != "none" and state.get("sent"):
            summary = ""  # fall through
        else:
            summary = (
                "Research brief ready (not sent).\n\n"
                f"Question: {question}\n"
                f"Claims:   {claim_count} with urls + dates\n"
                f"Conflicts: {conflicts_n}\n\n"
                "Open the brief artifact in this run to copy or share yourself."
            )
    else:
        summary = (
            "Sourced Research Desk — done\n\n"
            f"Status: sent (stub)\n"
            f"Question: {question}\n"
            f"Claims: {claim_count}\n"
            f"Message id: {state.get('message_id') or '—'}"
        )

    if state.get("sent"):
        summary = (
            "Sourced Research Desk — done\n\n"
            f"Status: sent (stub)\n"
            f"Question: {question}\n"
            f"Claims: {claim_count}\n"
            f"Message id: {state.get('message_id') or '—'}"
        )

    return {
        "human_summary": hygiene_text(summary),
        "status": status,
        "stage_summaries": _append_summary(state, "report: complete"),
    }
