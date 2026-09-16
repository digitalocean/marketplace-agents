"""Stage nodes: intake → plan → gather → analyze → draft → ask → act → report."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from competitor_pulse.chat import format_watch_ack, looks_like_watchlist_json, parse_track_message
from competitor_pulse.pulse_diff import (
    allow_network,
    counterposition_line,
    default_baseline_path,
    default_fixture_dir,
    default_snapshot_dir,
    default_watchlist,
    diff_snapshots,
    load_baseline,
    load_fixture_snapshot,
    modules_from_watchlist,
    split_deltas,
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


def _delta_bullet(d: dict[str, Any]) -> str:
    comp = d.get("competitor") or "?"
    module = d.get("module") or "?"
    summary = d.get("summary") or ""
    url = d.get("evidence_url") or ""
    line = f"- **{comp}** ({module}): {summary}"
    if url:
        line += f" — {url}"
    return line


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

    user_message = (state.get("user_message") or "").strip()
    from_chat = bool(user_message)
    watchlist = list(state.get("watchlist") or [])

    # Chat path: parse natural language; never echo raw planner JSON.
    if from_chat and looks_like_watchlist_json(user_message):
        user_message = ""
        from_chat = False
    if from_chat:
        parsed = parse_track_message(user_message)
        if parsed:
            watchlist = parsed
    if not watchlist:
        watchlist = default_watchlist()

    # Default notify off unless explicitly requested.
    notify = bool(state.get("notify")) if "notify" in state else False
    channel = (state.get("channel") or "slack").strip() or "slack"
    fixture_dir = (state.get("fixture_dir") or "").strip() or str(
        default_fixture_dir()
    )
    baseline_path = (state.get("baseline_path") or "").strip() or str(
        default_baseline_path()
    )
    snapshot_dir = (state.get("snapshot_dir") or "").strip() or str(
        default_snapshot_dir()
    )
    allow_net = (
        bool(state.get("allow_net"))
        if "allow_net" in state
        else allow_network()
    )

    chat_ack = format_watch_ack(
        watchlist, allow_net=allow_net, from_chat=from_chat or bool(user_message)
    )
    return {
        "watchlist": watchlist,
        "notify": notify,
        "channel": channel,
        "fixture_dir": fixture_dir,
        "baseline_path": baseline_path,
        "snapshot_dir": snapshot_dir,
        "allow_net": allow_net,
        "status": "ok",
        "chat_ack": chat_ack,
        "human_summary": chat_ack,
        "first_run": False,
        "stage_summaries": _append_summary(state, "intake: watchlist ready"),
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
    return {
        "modules": modules,
        "run_id": run_id,
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
    out: dict[str, Any] = {
        "snapshots": snapshots,
        "stage_summaries": _append_summary(
            state, f"gather: fetched {ok_n} ok, {fail_n} failed"
        ),
    }
    if not snapshots:
        out["status"] = "blocked"
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
            "baseline_captures": [],
            "material": False,
            "first_run": False,
            "status": "empty",
            "stage_summaries": _append_summary(
                state, "analyze: empty (forced)"
            ),
        }

    baseline_path = Path(state.get("baseline_path") or default_baseline_path())
    baseline_index = load_baseline(baseline_path)
    snapshots = list(state.get("snapshots") or [])
    all_deltas = diff_snapshots(snapshots, baseline_index)
    captures, changes = split_deltas(all_deltas)

    if state.get("force_material") and not changes:
        changes = [
            {
                "competitor": "Acme",
                "module": "pricing",
                "change_type": "pricing_change",
                "summary": "Pricing page updated — test fixture.",
                "evidence_url": "https://example.com/acme/pricing",
                "old_hash": "old",
                "new_hash": "forced",
                "is_baseline_capture": False,
            }
        ]

    first_run = bool(captures) and not changes
    material = bool(changes)
    deltas = changes if material else captures

    if not all_deltas:
        return {
            "deltas": [],
            "baseline_captures": [],
            "material": False,
            "first_run": False,
            "status": "empty",
            "stage_summaries": _append_summary(state, "analyze: no changes"),
        }

    if first_run:
        return {
            "deltas": captures,
            "baseline_captures": captures,
            "material": False,
            "first_run": True,
            "status": "baseline",
            "stage_summaries": _append_summary(
                state, f"analyze: baseline established ({len(captures)} pages)"
            ),
        }

    return {
        "deltas": changes,
        "baseline_captures": captures,
        "material": material,
        "first_run": False,
        "status": "ok" if material else "empty",
        "stage_summaries": _append_summary(
            state, f"analyze: {len(changes)} material change(s)"
        ),
    }


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------


def draft(state: PulseState) -> dict[str, Any]:
    if state.get("status") in {"blocked", "empty"} and not state.get("first_run"):
        return {}

    deltas = list(state.get("deltas") or [])
    first_run = bool(state.get("first_run"))

    if not deltas and not first_run:
        return {
            "status": "empty",
            "material": False,
            "delta_count": 0,
            "stage_summaries": _append_summary(state, "draft: empty"),
        }

    delta_count = len(deltas)
    names = sorted({d.get("competitor") or "?" for d in deltas})

    if first_run:
        brief_lines = [
            "# Competitor Pulse — first look",
            "",
            f"Baseline captured for **{', '.join(names)}**.",
            "",
            "## What we saw",
            "",
        ]
        for d in deltas:
            brief_lines.append(_delta_bullet(d))
        brief_lines.extend(
            [
                "",
                "_Next pulse will flag real changes against this baseline._",
            ]
        )
        brief_md = "\n".join(brief_lines)
        return {
            "brief_md": brief_md,
            "counterpositions": [],
            "delta_count": 0,
            "notify_draft": "",
            "status": "baseline",
            "stage_summaries": _append_summary(
                state, f"draft: first-look brief ({delta_count} pages)"
            ),
        }

    counterpositions = [
        line
        for d in deltas[:7]
        for line in [counterposition_line(d)]
        if line
    ]
    brief_lines = [
        "# Competitor Pulse brief",
        "",
        f"**{delta_count}** material change(s) across {', '.join(names)}.",
        "",
        "## What moved",
        "",
    ]
    for d in deltas:
        brief_lines.append(_delta_bullet(d))
    if counterpositions:
        brief_lines.extend(["", "## Counterpositions", ""])
        for c in counterpositions:
            brief_lines.append(f"- {c}")
    brief_md = "\n".join(brief_lines)

    highlights = "\n".join(
        f"- {d.get('competitor')} ({d.get('module')}): {d.get('summary')}"
        for d in deltas[:5]
    )
    notify_draft = (
        f"Pulse: {delta_count} material change(s) — {', '.join(names)}.\n"
        f"{highlights}"
    )
    return {
        "brief_md": brief_md,
        "counterpositions": counterpositions,
        "delta_count": delta_count,
        "notify_draft": notify_draft,
        "status": "ok",
        "stage_summaries": _append_summary(
            state, f"draft: brief with {delta_count} deltas"
        ),
    }


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


def should_ask(state: PulseState) -> str:
    """Ask only if notify requested AND material == true."""
    if state.get("status") in {"blocked", "empty", "error", "baseline"}:
        return "report"
    if state.get("first_run"):
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
        f"- {d.get('competitor')} ({d.get('module')}): {d.get('summary')}"
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
        "stage_summaries": _append_summary(
            state, f"act: stub notified {notify_id}"
        ),
    }


def _format_first_run_report(state: PulseState) -> str:
    ack = state.get("chat_ack") or ""
    deltas = list(state.get("deltas") or [])
    names = sorted({d.get("competitor") or "?" for d in deltas})
    allow_net = bool(state.get("allow_net"))
    fetch_note = (
        "Live fetch was on for this run."
        if allow_net
        else "Live fetch is off — offline fixtures were used."
    )
    lines = []
    if ack:
        lines.append(ack)
        lines.append("")
    lines.append(
        f"**First look — baseline established** for {', '.join(names)}."
    )
    lines.append(fetch_note)
    lines.append("")
    lines.append("What the pages look like right now:")
    for d in deltas[:8]:
        lines.append(_delta_bullet(d))
    lines.append("")
    lines.append(
        "Alerts are off unless you ask. Re-run later to see real diffs against this baseline."
    )
    return "\n".join(lines)


def _format_quiet_report(state: PulseState) -> str:
    watchlist = list(state.get("watchlist") or [])
    names = [w.get("name") or "?" for w in watchlist]
    modules = state.get("modules") or []
    return (
        f"**No changes** since the last pulse for {', '.join(names) or 'your watchlist'}.\n\n"
        f"Modules checked: {', '.join(modules) or '—'}.\n"
        "Baseline unchanged — nothing worth a notify."
    )


def _format_material_report(state: PulseState, *, notified: bool = False) -> str:
    deltas = list(state.get("deltas") or [])
    delta_count = state.get("delta_count") or len(deltas)
    names = sorted({d.get("competitor") or "?" for d in deltas})
    lines = [
        f"**{delta_count} material change(s)** across {', '.join(names)}.",
        "",
        "What moved:",
    ]
    for d in deltas[:8]:
        lines.append(_delta_bullet(d))
    counterpositions = list(state.get("counterpositions") or [])
    if counterpositions:
        lines.extend(["", "Counterpositions:"])
        for c in counterpositions[:5]:
            lines.append(f"- {c}")
    if notified:
        lines.append(f"\nNotify sent (stub): `{state.get('notify_id') or '—'}`")
    elif state.get("notify"):
        lines.append("\nNotify was requested — you can approve on the next material run.")
    else:
        lines.append("\nAlerts are off. Say if you want notify on the next pulse.")
    return "\n".join(lines)


def report(state: PulseState) -> dict[str, Any]:
    status = state.get("status") or "ok"
    first_run = bool(state.get("first_run"))
    material = bool(state.get("material"))
    watch_n = len(state.get("watchlist") or [])

    if status == "blocked":
        summary = (
            "Could not complete the pulse — fetch/tools were unavailable.\n"
            f"Watchlist had {watch_n} competitor(s). Fix network/fixtures and retry."
        )
        next_hint = "Fix fixtures / network and retry."
        out_status = "blocked"
    elif first_run or status == "baseline":
        summary = _format_first_run_report(state)
        next_hint = "Re-run after competitors may have updated their pages."
        out_status = "baseline"
    elif status == "denied":
        summary = _format_material_report(state, notified=False)
        summary = (
            "**Brief kept — no notify sent.**\n\n" + summary
        )
        next_hint = "Artifacts kept; re-run and approve to stub-notify."
        out_status = "denied"
    elif status == "notified":
        summary = _format_material_report(state, notified=True)
        next_hint = "Review stub notify id in run state."
        out_status = "notified"
    elif material:
        summary = _format_material_report(state, notified=False)
        next_hint = "Set notify=true to gate a notify ask on the next material pulse."
        out_status = "ok"
    else:
        summary = _format_quiet_report(state)
        next_hint = "Re-run when the watchlist may have moved."
        out_status = "empty"

    artifacts = [
        a
        for a in [
            state.get("brief_md") and "brief_md",
            f"deltas:{state.get('delta_count') or len(state.get('deltas') or [])}",
            state.get("notify_id") or "",
            state.get("run_id") or "",
        ]
        if a
    ]

    return {
        "human_summary": summary,
        "status": out_status,
        "artifacts": artifacts,
        "next_hint": next_hint,
        "stage_summaries": _append_summary(state, "report: complete"),
    }
