"""Stage nodes: intake → plan → gather → analyze → draft → ask → act → report."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from competitor_pulse.intake_parse import parse_notify_from_message, parse_watchlist_from_message
from competitor_pulse.pulse_diff import (
    allow_network,
    default_baseline_path,
    default_fixture_dir,
    default_snapshot_dir,
    default_watchlist,
    diff_snapshots,
    load_baseline,
    load_fixture_snapshot,
    modules_from_watchlist,
    spacexai_watchlist,
)
from competitor_pulse.state import PulseState

_MODULE_KEYS = ("site", "pricing", "changelog", "careers")


def _append_summary(state: PulseState, line: str) -> list[str]:
    prev = list(state.get("stage_summaries") or [])
    prev.append(line)
    return prev


def _normalize_decision(raw: Any) -> str:
    """Primary: approve|deny strings. Optional legacy dict compat (undocumented)."""
    if isinstance(raw, dict):
        if "approved" in raw:
            return "approve" if raw.get("approved") else "deny"
        raw = raw.get("decision") or raw.get("value") or "deny"
    decision_s = str(raw).strip().lower()
    if decision_s not in {"approve", "deny"}:
        return "deny"
    return decision_s


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _assistant_reply(summary: str, brief_md: str | None = None) -> dict[str, Any]:
    """Build the final assistant-visible chat message for Agent Server / MARS UI."""
    content = summary
    if brief_md:
        content = f"{summary}\n\n---\n\n{brief_md}"
    return {"messages": [AIMessage(content=content)]}


def _human_message_text(messages: list[Any] | None) -> str:
    for msg in reversed(messages or []):
        if isinstance(msg, HumanMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
        if isinstance(msg, dict):
            role = (msg.get("type") or msg.get("role") or "").lower()
            if role in {"human", "user"}:
                return str(msg.get("content") or "")
    return ""


def _parse_intake_json(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None

    fence = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```",
        stripped,
        re.DOTALL | re.IGNORECASE,
    )
    if fence:
        try:
            parsed = json.loads(fence.group(1).strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    brace = re.search(r"\{.*\}", stripped, re.DOTALL)
    if brace:
        try:
            parsed = json.loads(brace.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def _apply_intake_overlay(state: PulseState, payload: dict[str, Any]) -> dict[str, Any]:
    """Overlay JSON keys onto intake fields when state lacks them."""
    out: dict[str, Any] = {}

    state_watchlist = list(state.get("watchlist") or [])
    payload_watchlist = payload.get("watchlist")
    if not state_watchlist and isinstance(payload_watchlist, list) and payload_watchlist:
        out["watchlist"] = payload_watchlist

    if "notify" not in state and "notify" in payload:
        out["notify"] = bool(payload.get("notify"))

    if "allow_net" not in state and "allow_net" in payload:
        out["allow_net"] = bool(payload.get("allow_net"))

    state_channel = (state.get("channel") or "").strip()
    payload_channel = payload.get("channel")
    if not state_channel and isinstance(payload_channel, str) and payload_channel.strip():
        out["channel"] = payload_channel.strip()

    if "preset" in payload:
        out["preset"] = str(payload.get("preset") or "").strip()

    return out


def _resolve_watchlist(
    state: PulseState,
    overlay: dict[str, Any],
    human_text: str,
) -> dict[str, Any]:
    """Resolve watchlist with source metadata for intake defaults."""
    watchlist = list(overlay.get("watchlist") or state.get("watchlist") or [])
    if watchlist:
        return {"watchlist": watchlist, "from_nl": False, "blocked": False}

    preset = (overlay.get("preset") or "").strip().lower()
    if preset == "spacexai" or "SPACEXAI_PRESET" in human_text:
        return {
            "watchlist": spacexai_watchlist(),
            "from_nl": False,
            "blocked": False,
        }

    parsed = parse_watchlist_from_message(human_text)
    nl_watchlist = list(parsed.get("watchlist") or [])
    if nl_watchlist:
        return {
            "watchlist": nl_watchlist,
            "from_nl": True,
            "blocked": False,
            "notify": parsed.get("notify"),
            "source": parsed.get("source"),
        }

    if parsed.get("is_tracking_request") and not parsed.get("is_generic"):
        return {
            "watchlist": [],
            "from_nl": True,
            "blocked": True,
            "notify": parsed.get("notify"),
            "blocked_summary": (
                "Could not resolve companies to track. "
                "Please name specific competitors (e.g. OpenAI, Anthropic, Cursor)."
            ),
        }

    if parsed.get("is_generic") or not human_text.strip():
        return {
            "watchlist": default_watchlist(),
            "from_nl": False,
            "blocked": False,
        }

    return {
        "watchlist": default_watchlist(),
        "from_nl": False,
        "blocked": False,
    }


# ---------------------------------------------------------------------------
# intake
# ---------------------------------------------------------------------------


def intake(state: PulseState) -> dict[str, Any]:
    if state.get("force_blocked"):
        return {
            "status": "blocked",
            "watchlist": list(state.get("watchlist") or []),
            "notify": bool(state.get("notify")),
            "human_summary": "Blocked: fetch/tools unavailable.",
            "stage_summaries": _append_summary(
                state, "intake: blocked — fetch/tools unavailable"
            ),
            "deltas": [],
            "material": False,
            "skipped": False,
        }

    human_text = _human_message_text(state.get("messages"))
    intake_json = _parse_intake_json(human_text)
    overlay = _apply_intake_overlay(state, intake_json or {})

    resolved = _resolve_watchlist(state, overlay, human_text)
    watchlist = list(resolved.get("watchlist") or [])
    from_nl = bool(resolved.get("from_nl"))

    if resolved.get("blocked"):
        blocked_summary = resolved.get("blocked_summary") or (
            "Could not resolve companies to track."
        )
        return {
            "status": "blocked",
            "watchlist": [],
            "notify": False,
            "human_summary": blocked_summary,
            "stage_summaries": _append_summary(
                state, f"intake: blocked — {blocked_summary}"
            ),
            "deltas": [],
            "material": False,
            "skipped": False,
        }

    if "notify" in overlay:
        notify = bool(overlay.get("notify"))
    elif "notify" in state:
        notify = bool(state.get("notify"))
    elif resolved.get("notify") is not None:
        notify = bool(resolved.get("notify"))
    elif human_text.strip():
        notify = bool(parse_notify_from_message(human_text) or False)
    else:
        notify = False

    channel = (
        overlay.get("channel")
        or (state.get("channel") or "slack").strip()
        or "slack"
    )
    fixture_dir = (state.get("fixture_dir") or "").strip() or str(
        default_fixture_dir()
    )
    baseline_path = (state.get("baseline_path") or "").strip() or str(
        default_baseline_path()
    )
    snapshot_dir = (state.get("snapshot_dir") or "").strip() or str(
        default_snapshot_dir()
    )
    if "allow_net" in overlay:
        allow_net = bool(overlay.get("allow_net"))
    elif "allow_net" in state:
        allow_net = bool(state.get("allow_net"))
    elif from_nl:
        allow_net = True
    else:
        allow_net = allow_network()

    n = len(watchlist)
    names = ", ".join((item.get("name") or "?") for item in watchlist[:5])
    if n > 5:
        names += f", +{n - 5} more"
    summary = f"Pulse for {n} competitor{'s' if n != 1 else ''}."
    if from_nl and names:
        summary = f"{summary} Tracking: {names}."
    return {
        "watchlist": watchlist,
        "notify": notify,
        "channel": channel,
        "fixture_dir": fixture_dir,
        "baseline_path": baseline_path,
        "snapshot_dir": snapshot_dir,
        "allow_net": allow_net,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"intake: {summary}"),
        "skipped": False,
        "notified": False,
        "deltas": [],
        "material": False,
    }


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def plan(state: PulseState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    watchlist = list(state.get("watchlist") or [])
    modules = modules_from_watchlist(watchlist)
    run_id = f"pulse-{uuid.uuid4().hex[:10]}"
    summary = f"Modules this run: {', '.join(modules)} (run_id={run_id})."
    return {
        "modules": modules,
        "run_id": run_id,
        "human_summary": summary,
        "stage_summaries": _append_summary(
            state, f"plan: modules={','.join(modules)}"
        ),
    }


# ---------------------------------------------------------------------------
# gather
# ---------------------------------------------------------------------------


def _fetch_http(url: str) -> dict[str, Any] | None:
    try:
        import httpx

        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url)
            text = resp.text or ""
            ok = 200 <= resp.status_code < 400
            from competitor_pulse.pulse_diff import content_hash

            return {
                "text": text,
                "content_hash": content_hash(text),
                "ok": ok,
                "source": "http",
                "status_code": resp.status_code,
            }
    except Exception as exc:  # noqa: BLE001 — gather continues on per-URL fail
        return {
            "text": "",
            "content_hash": "",
            "ok": False,
            "source": "http",
            "error": str(exc)[:200],
        }


def gather(state: PulseState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    watchlist = list(state.get("watchlist") or [])
    snapshot_dir = Path(state.get("snapshot_dir") or default_snapshot_dir())
    allow_net = bool(state.get("allow_net"))
    fetched_at = _now_iso()
    snapshots: list[dict[str, Any]] = []

    for item in watchlist:
        name = (item.get("name") or "").strip() or "Unknown"
        urls = item.get("urls") or {}
        for module in _MODULE_KEYS:
            url = urls.get(module)
            if not url:
                continue
            snap: dict[str, Any] | None = None
            if not allow_net:
                snap = load_fixture_snapshot(snapshot_dir, name, module)
                if snap:
                    snap = {
                        **snap,
                        "url": url,
                        "fetched_at": fetched_at,
                    }
            else:
                http_result = _fetch_http(url)
                if http_result and http_result.get("ok"):
                    snap = {
                        "competitor": name,
                        "module": module,
                        "url": url,
                        "fetched_at": fetched_at,
                        **http_result,
                    }
                else:
                    # Fall back to fixture if network fails
                    snap = load_fixture_snapshot(snapshot_dir, name, module)
                    if snap:
                        snap = {
                            **snap,
                            "url": url,
                            "fetched_at": fetched_at,
                            "source": "fixture_fallback",
                        }
                    else:
                        snap = {
                            "competitor": name,
                            "module": module,
                            "url": url,
                            "fetched_at": fetched_at,
                            "ok": False,
                            "text": "",
                            "content_hash": "",
                            "source": "http",
                            "error": (http_result or {}).get("error")
                            or "fetch failed",
                        }
            if snap is None:
                snapshots.append(
                    {
                        "competitor": name,
                        "module": module,
                        "url": url,
                        "fetched_at": fetched_at,
                        "ok": False,
                        "text": "",
                        "content_hash": "",
                        "source": "missing",
                    }
                )
            else:
                snapshots.append(snap)

    ok_n = sum(1 for s in snapshots if s.get("ok"))
    fail_n = len(snapshots) - ok_n
    summary = f"Fetched {ok_n} snapshots ({fail_n} failed)."
    out: dict[str, Any] = {
        "snapshots": snapshots,
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"gather: {summary}"),
    }
    if not snapshots:
        out["status"] = "blocked"
        out["human_summary"] = "Blocked: no snapshots gathered."
        out["stage_summaries"] = _append_summary(
            state, "gather: blocked — no snapshots"
        )
    return out


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


def analyze(state: PulseState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    if state.get("force_empty"):
        return {
            "deltas": [],
            "material": False,
            "status": "empty",
            "human_summary": "No material change (forced empty).",
            "stage_summaries": _append_summary(
                state, "analyze: empty (forced)"
            ),
        }

    baseline_path = Path(state.get("baseline_path") or default_baseline_path())
    baseline_index = load_baseline(baseline_path)
    snapshots = list(state.get("snapshots") or [])
    deltas = diff_snapshots(snapshots, baseline_index)

    if state.get("force_material") and not deltas:
        # Synthetic material delta for tests when baseline already matches
        deltas = [
            {
                "competitor": "Acme",
                "module": "pricing",
                "change_type": "pricing_change",
                "summary": "Forced material pricing delta (test).",
                "evidence_url": "https://example.com/acme/pricing",
                "old_hash": "",
                "new_hash": "forced",
            }
        ]

    material = bool(deltas)
    if not material:
        summary = "No material change."
        return {
            "deltas": [],
            "material": False,
            "status": "empty",
            "human_summary": summary,
            "stage_summaries": _append_summary(state, "analyze: no material change"),
        }

    bullets = "\n".join(
        f"- {d.get('competitor')}/{d.get('module')}: {d.get('summary')}"
        for d in deltas[:8]
    )
    summary = f"Material deltas: {len(deltas)}\n{bullets}"
    return {
        "deltas": deltas,
        "material": True,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(
            state, f"analyze: {len(deltas)} material deltas"
        ),
    }


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------


def draft(state: PulseState) -> dict[str, Any]:
    if state.get("status") in {"blocked", "empty"}:
        return {}

    deltas = list(state.get("deltas") or [])
    if not deltas:
        return {
            "status": "empty",
            "material": False,
            "delta_count": 0,
            "human_summary": "No material changes.",
            "stage_summaries": _append_summary(state, "draft: empty"),
        }

    delta_count = len(deltas)
    names = sorted({d.get("competitor") or "?" for d in deltas})
    counterpositions = [
        f"Counter {d.get('competitor')}/{d.get('module')}: "
        f"review {d.get('change_type')} — {d.get('summary')}"
        for d in deltas[:7]
    ]
    brief_lines = [
        "# Competitor Pulse brief",
        "",
        f"Material changes: **{delta_count}** across {', '.join(names)}.",
        "",
        "## Deltas",
        "",
    ]
    for d in deltas:
        brief_lines.append(
            f"- **{d.get('competitor')}** `{d.get('module')}` "
            f"({d.get('change_type')}): {d.get('summary')}"
        )
        if d.get("evidence_url"):
            brief_lines.append(f"  - Evidence: {d.get('evidence_url')}")
    brief_lines.extend(["", "## Counterpositions", ""])
    for c in counterpositions:
        brief_lines.append(f"- {c}")
    brief_md = "\n".join(brief_lines)

    highlights = "\n".join(
        f"- {d.get('competitor')}/{d.get('module')}: {d.get('summary')}"
        for d in deltas[:5]
    )
    notify_draft = (
        f"Pulse: {delta_count} material change(s) — {', '.join(names)}.\n"
        f"{highlights}"
    )
    preview = "\n".join(brief_lines[:12])
    summary = f"Counterposition brief ready ({delta_count} deltas).\n{preview}"
    return {
        "brief_md": brief_md,
        "counterpositions": counterpositions,
        "delta_count": delta_count,
        "notify_draft": notify_draft,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(
            state, f"draft: brief with {delta_count} deltas"
        ),
    }


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


def should_ask(state: PulseState) -> str:
    """Ask only if notify requested AND material == true."""
    if state.get("status") in {"blocked", "empty", "error"}:
        return "report"
    if not state.get("notify"):
        return "report"
    if not state.get("material"):
        return "report"
    if not state.get("deltas"):
        return "report"
    return "ask"


# ---------------------------------------------------------------------------
# ask / act / report
# ---------------------------------------------------------------------------


def ask(state: PulseState) -> dict[str, Any]:
    """Interrupt for human approval before notify stub."""
    from langgraph.types import interrupt

    channel = state.get("channel") or "slack"
    deltas = list(state.get("deltas") or [])
    delta_count = state.get("delta_count") or len(deltas)
    names = sorted({d.get("competitor") or "?" for d in deltas})
    highlights = "\n".join(
        f"- {d.get('competitor')}/{d.get('module')}: {d.get('summary')}"
        for d in deltas[:7]
    ) or "- (none)"
    notify_draft = state.get("notify_draft") or "(empty draft)"

    body = (
        f"Send a pulse notify via {channel}?\n\n"
        f"Material changes: {delta_count}\n"
        f"Competitors: {', '.join(names)}\n\n"
        f"Highlights:\n{highlights}\n\n"
        "Counterposition brief: attached in this run "
        "(not posted in full unless included below).\n\n"
        f"Notify draft:\n{notify_draft}\n\n"
        "Will not: contact competitors, create accounts, or scrape behind login."
    )
    payload = {
        "title": "Notify about competitor changes?",
        "body": body,
        "pending_action": "notify",
        "channel": channel,
        "choices": ["approve", "deny"],
    }
    decision = interrupt(payload)
    decision_s = _normalize_decision(decision)
    return {
        "pending_action": "notify",
        "ask_payload": payload,
        "decision": decision_s,
        "human_summary": f"Ask answered: {decision_s}",
        "stage_summaries": _append_summary(state, f"ask: {decision_s}"),
    }


def act(state: PulseState) -> dict[str, Any]:
    decision = _normalize_decision(state.get("decision") or "deny")
    if decision != "approve":
        return {
            "skipped": True,
            "notified": False,
            "notify_id": "",
            "status": "denied",
            "baseline_updated": False,
            "human_summary": "Denied — no notify sent; brief kept local.",
            "stage_summaries": _append_summary(
                state, "act: denied — no notify"
            ),
        }

    notify_id = f"stub-notify-{uuid.uuid4().hex[:8]}"
    return {
        "skipped": False,
        "notified": True,
        "notify_id": notify_id,
        "status": "notified",
        "baseline_updated": False,
        "human_summary": f"Notified (stub) id={notify_id}.",
        "stage_summaries": _append_summary(
            state, f"act: stub notified {notify_id}"
        ),
    }


def report(state: PulseState) -> dict[str, Any]:
    status = state.get("status") or "ok"
    watch_n = len(state.get("watchlist") or [])
    modules = state.get("modules") or []
    delta_count = state.get("delta_count") or len(state.get("deltas") or [])
    baseline_updated = bool(state.get("baseline_updated"))

    # Quiet / empty: notify disabled with material still reports ok path
    if status == "empty" or (
        not state.get("material") and status not in {"blocked", "denied", "notified", "error"}
    ):
        status = "empty"
        summary = (
            "Competitor Pulse — no material changes\n\n"
            f"Watchlist: {watch_n} · Modules: {', '.join(modules) or '—'}\n"
            f"Baselines: {'updated with same content hash' if baseline_updated else 'unchanged'}"
        )
        next_hint = "Re-run when the watchlist may have moved."
    elif status == "blocked":
        summary = (
            "Competitor Pulse — done\n\n"
            "Status: blocked\n"
            f"Watchlist: {watch_n}\n\n"
            "Fetch/tools failed; no ask."
        )
        next_hint = "Fix fixtures / network and retry."
    elif status == "denied":
        summary = (
            "Competitor Pulse — done\n\n"
            "Status: denied\n"
            f"Watchlist: {watch_n}\n"
            f"Deltas:  {delta_count}\n"
            "Notify:  —\n\n"
            "Quiet — brief kept; no notify."
        )
        next_hint = "Artifacts kept; re-run and approve to stub-notify."
    elif status == "notified":
        summary = (
            "Competitor Pulse — done\n\n"
            "Status: notified\n"
            f"Watchlist: {watch_n}\n"
            f"Deltas:  {delta_count}\n"
            f"Notify:  {state.get('notify_id') or '—'}\n"
        )
        next_hint = "Review stub notify id in run state."
    elif state.get("material") and not state.get("notify"):
        # Material brief, notify off — no ask
        status = "ok"
        summary = (
            "Competitor Pulse — done\n\n"
            "Status: ok (notify off)\n"
            f"Watchlist: {watch_n}\n"
            f"Deltas:  {delta_count}\n"
            "Notify:  skipped (notify=false)\n\n"
            "Brief ready in run artifacts."
        )
        next_hint = "Set notify=true to gate a notify ask."
    else:
        summary = (
            "Competitor Pulse — done\n\n"
            f"Status: {status}\n"
            f"Watchlist: {watch_n}\n"
            f"Deltas:  {delta_count}\n"
        )
        next_hint = "Inspect stage_summaries for details."

    artifacts = [
        a
        for a in [
            state.get("brief_md") and "brief_md",
            f"deltas:{delta_count}",
            state.get("notify_id") or "",
            state.get("run_id") or "",
        ]
        if a
    ]

    return {
        "human_summary": summary,
        "status": status,
        "artifacts": artifacts,
        "next_hint": next_hint,
        "baseline_updated": baseline_updated,
        "stage_summaries": _append_summary(state, "report: complete"),
        **_assistant_reply(summary, state.get("brief_md") or None),
    }
