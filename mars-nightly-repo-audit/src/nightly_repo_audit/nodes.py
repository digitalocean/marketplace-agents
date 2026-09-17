"""Stage nodes: intake → plan → gather → analyze → draft → ask → act → report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from nightly_repo_audit.converse import conversational_reply
from nightly_repo_audit.hygiene import hygiene_text
from nightly_repo_audit.intent import classify_intent
from nightly_repo_audit.persona import (
    approve_open_message,
    ask_body,
    ask_title,
    blocked_checkout_message,
    deny_open_message,
    empty_message,
    plan_confirm_body,
    plan_confirm_title,
    plan_declined_message,
)
from nightly_repo_audit.repo_scan import default_fixture_path, scan_repo
from nightly_repo_audit.state import AuditState

ASSISTANT_DISPLAY_NAME = "Nightly Repo Audit"


def _append_summary(state: AuditState, line: str) -> list[str]:
    prev = list(state.get("stage_summaries") or [])
    prev.append(line)
    return prev


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


def _assistant_reply(summary: str) -> dict[str, Any]:
    return {
        "messages": [
            AIMessage(content=hygiene_text(summary or ""), name=ASSISTANT_DISPLAY_NAME),
        ]
    }


def _mars_stream_safe_update(full: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in full.items() if key != "human_summary"}


def _programmatic_audit(state: AuditState) -> bool:
    return bool(
        state.get("force_blocked")
        or state.get("force_empty")
        or (state.get("repo") or "").strip()
        or (state.get("fixture_path") or "").strip()
        or (state.get("area_hint") or "").strip()
        or (state.get("ref") or "").strip()
    )


def _normalize_decision(raw: Any) -> str:
    """approve|deny — MARS harness may send bool, {approved: true}, or strings."""
    if isinstance(raw, dict):
        if "approved" in raw:
            return "approve" if raw.get("approved") else "deny"
        raw = (
            raw.get("decision")
            or raw.get("value")
            or raw.get("choice")
            or "deny"
        )
    if isinstance(raw, bool):
        return "approve" if raw else "deny"
    decision_s = str(raw).strip().lower()
    if decision_s in {"approve", "approved", "yes", "y", "ok", "okay", "true"}:
        return "approve"
    if decision_s in {"deny", "denied", "no", "n", "false"}:
        return "deny"
    return "deny"


# ---------------------------------------------------------------------------
# intake
# ---------------------------------------------------------------------------


def intake(state: AuditState) -> dict[str, Any]:
    human_text = _human_message_text(state.get("messages"))
    programmatic = _programmatic_audit(state) and not human_text.strip()
    pending = state.get("pending_audit")
    skip_plan_confirm = not bool(human_text.strip())

    if human_text.strip() or state.get("messages"):
        intent = classify_intent(
            human_text,
            programmatic_audit=programmatic,
            pending_audit=pending if isinstance(pending, dict) else None,
        )
        if intent in {"chat", "help", "other"}:
            reply = conversational_reply(intent, human_text)
            return {
                "intent": intent,
                "status": intent,
                "skipped": False,
                "findings": [],
                **_assistant_reply(reply),
            }
        if intent == "audit" and isinstance(pending, dict):
            skip_plan_confirm = True
            audit_intent = "audit"
        else:
            audit_intent = "audit_plan" if human_text.strip() else "audit"
    else:
        audit_intent = "audit"

    if state.get("force_blocked"):
        repo = state.get("repo") or "local/sample"
        blocked = blocked_checkout_message(repo)
        return {
            "status": "blocked",
            "repo": repo,
            "ref": state.get("ref") or "main",
            "trigger": state.get("trigger") or "manual",
            "human_summary": blocked,
            "stage_summaries": _append_summary(
                state, "intake: blocked — checkout/tools unavailable"
            ),
            "findings": [],
            "skipped": False,
            **_assistant_reply(blocked),
        }

    repo = (state.get("repo") or "local/sample").strip()
    ref = (state.get("ref") or "main").strip()
    trigger = (state.get("trigger") or "manual").strip().lower()
    if trigger not in {"cron", "manual"}:
        trigger = "manual"
    area_hint = (state.get("area_hint") or "").strip()
    fixture_path = (state.get("fixture_path") or "").strip()
    if not fixture_path:
        fixture_path = str(default_fixture_path())

    summary = f"Auditing `{repo}` @ `{ref}`."
    return {
        "intent": audit_intent,
        "repo": repo,
        "ref": ref,
        "trigger": trigger,
        "area_hint": area_hint,
        "fixture_path": fixture_path,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"intake: {summary}"),
        "skipped": False,
        "findings": [],
        "skip_plan_confirm": skip_plan_confirm,
        "plan_confirmed": bool(skip_plan_confirm),
    }


def intake_node(state: AuditState) -> dict[str, Any]:
    return _mars_stream_safe_update(intake(state))


def route_after_intake(state: AuditState) -> str:
    if state.get("status") == "blocked":
        return "end"
    intent = (state.get("intent") or "audit").strip().lower()
    if intent in {"chat", "help", "other"}:
        return "end"
    return "plan"


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def plan(state: AuditState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}
    hint = (state.get("area_hint") or "").strip()
    if hint:
        area = hint
        rationale = f"Operator hint: focus on `{hint}`."
    else:
        area = "src"
        rationale = "Default nightly slice: source tree hygiene."
    scope_limits = [
        "No product behavior changes",
        "No merge",
        f"Stay inside `{area}` (plus known legacy bait paths)",
    ]
    scope_text = ", ".join(scope_limits)
    repo = state.get("repo") or "local/sample"
    ref = state.get("ref") or "main"
    trigger = state.get("trigger") or "manual"
    summary = hygiene_text(
        plan_confirm_body(
            repo=repo,
            ref=ref,
            area=area,
            scope_limits=scope_text,
            trigger=trigger,
        )
    )
    pending = {
        "repo": repo,
        "ref": ref,
        "trigger": trigger,
        "area": area,
        "area_hint": state.get("area_hint") or "",
        "fixture_path": state.get("fixture_path") or "",
    }
    out: dict[str, Any] = {
        "area": area,
        "rationale": rationale,
        "scope_limits": scope_limits,
        "pending_audit": pending,
        "stage_summaries": _append_summary(state, f"plan: area={area}"),
    }
    if state.get("skip_plan_confirm") or state.get("plan_confirmed"):
        out["human_summary"] = summary
    else:
        out.update(_assistant_reply(summary))
    return out


def should_confirm_plan(state: AuditState) -> str:
    if state.get("skip_plan_confirm") or state.get("plan_confirmed"):
        return "gather"
    return "confirm_plan"


def confirm_plan(state: AuditState) -> dict[str, Any]:
    """B4 — interrupt before gather."""
    from langgraph.types import interrupt

    repo = state.get("repo") or "local/sample"
    ref = state.get("ref") or "main"
    area = state.get("area") or "src"
    scope_text = ", ".join(list(state.get("scope_limits") or []))
    trigger = state.get("trigger") or "manual"
    body = hygiene_text(
        plan_confirm_body(
            repo=repo,
            ref=ref,
            area=area,
            scope_limits=scope_text,
            trigger=trigger,
        )
    )
    payload = {
        "title": plan_confirm_title(),
        "body": body,
        "pending_action": "start_audit",
        "choices": ["approve", "deny"],
    }
    decision = interrupt(payload)
    decision_s = _normalize_decision(decision)
    if decision_s == "approve":
        return {
            "plan_confirmed": True,
            "stage_summaries": _append_summary(state, "confirm_plan: approve"),
        }
    return {
        "plan_confirmed": False,
        "status": "plan_denied",
        "stage_summaries": _append_summary(state, "confirm_plan: deny"),
    }


def route_after_confirm_plan(state: AuditState) -> str:
    if state.get("plan_confirmed"):
        return "gather"
    return "report"


# ---------------------------------------------------------------------------
# gather
# ---------------------------------------------------------------------------


def gather(state: AuditState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    checkout = Path(state.get("fixture_path") or default_fixture_path())
    if not checkout.is_dir():
        return {
            "status": "blocked",
            "checkout_path": str(checkout),
            "files_touched_count": 0,
            "commands_run": ["scan_repo (failed: missing path)"],
            "human_summary": blocked_checkout_message(state.get("repo") or "local/sample"),
            "stage_summaries": _append_summary(
                state, "gather: blocked — missing checkout"
            ),
            "findings": [],
        }

    # Count files under area (and legacy bait)
    area = state.get("area") or "src"
    commands = [f"scan_repo {checkout}", f"area={area}"]
    n_files = sum(1 for p in checkout.rglob("*") if p.is_file())
    summary = f"Checked out; scanned {n_files} paths."
    return {
        "checkout_path": str(checkout.resolve()),
        "files_touched_count": n_files,
        "commands_run": commands,
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"gather: {summary}"),
    }


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


def analyze(state: AuditState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    if state.get("force_empty"):
        findings: list[dict[str, Any]] = []
        summary = "Bullet findings: none (forced empty)."
        return {
            "findings": findings,
            "self_check_pass": True,
            "status": "empty",
            "human_summary": summary,
            "stage_summaries": _append_summary(state, "analyze: empty findings"),
        }

    checkout = Path(state.get("checkout_path") or state.get("fixture_path") or ".")
    area = state.get("area") or "src"
    # Scan whole fixture so legacy/ bait is visible even when area=src
    findings = scan_repo(checkout, area=None)
    # Prefer area-scoped findings when area_hint was set; still include legacy
    if area and area != ".":
        scoped = scan_repo(checkout, area=area)
        legacy = [f for f in findings if "legacy" in f.get("path", "")]
        # merge unique by id path+evidence
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for f in scoped + legacy:
            key = f"{f.get('path')}|{f.get('evidence')}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(f)
        findings = merged

    self_ok = True
    for f in findings:
        if not f.get("path") or not f.get("evidence"):
            self_ok = False
            break

    if not findings:
        summary = "No findings."
        return {
            "findings": [],
            "self_check_pass": True,
            "status": "empty",
            "human_summary": summary,
            "stage_summaries": _append_summary(state, "analyze: empty findings"),
        }

    if not self_ok:
        return {
            "findings": findings,
            "self_check_pass": False,
            "status": "blocked",
            "human_summary": "Self-check failed — incomplete findings; no ask.",
            "stage_summaries": _append_summary(state, "analyze: self-check fail"),
        }

    bullets = "\n".join(
        f"- [{f.get('severity')}] {f.get('path')}: {f.get('evidence')[:80]}"
        for f in findings[:8]
    )
    summary = f"Findings: {len(findings)}\n{bullets}"
    return {
        "findings": findings,
        "self_check_pass": True,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(
            state, f"analyze: {len(findings)} findings"
        ),
    }


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------


def draft(state: AuditState) -> dict[str, Any]:
    if state.get("status") in {"blocked", "empty"}:
        return {}

    findings = list(state.get("findings") or [])
    if not findings:
        return {
            "status": "empty",
            "human_summary": "No cleanup worth a PR tonight.",
            "stage_summaries": _append_summary(state, "draft: empty"),
        }

    area = state.get("area") or "src"
    repo = state.get("repo") or "local/sample"
    n = len(findings)
    # Synthetic diff_stat for stub PR
    plus = 10 + n * 2
    minus = 5 + n * 3
    files_n = min(n, 5)
    diff_stat = f"+{plus} / −{minus} across {files_n} files"
    patch_summary = [
        f"Address {f.get('id')}: {f.get('path')} — {f.get('evidence')[:60]}"
        for f in findings[:5]
    ]
    if n > 5:
        patch_summary.append(f"…and {n - 5} more hygiene items")

    branch_name = f"nightly/cleanup-{area.replace('/', '-')}"
    pr_title = f"chore: nightly cleanup ({area}) — {n} finding(s)"
    body_lines = [
        f"## Nightly cleanup for `{repo}`",
        "",
        f"Slice: **{area}**",
        "",
        "### Changes",
        "",
    ]
    for b in patch_summary:
        body_lines.append(f"- {b}")
    body_lines.extend(
        [
            "",
            "### Notes",
            "",
            "- Cleanup / hygiene only — no product behavior changes",
            "- Draft PR; does not merge",
            "",
        ]
    )
    pr_body_md = hygiene_text("\n".join(body_lines))
    commit_message = f"chore: nightly cleanup in {area} ({n} findings)"

    preview = "\n".join(f"- {b}" for b in patch_summary[:5])
    summary = f"PR draft ready: {pr_title}\n{preview}"
    return {
        "patch_summary": patch_summary,
        "diff_stat": diff_stat,
        "commit_message": commit_message,
        "pr_title": pr_title,
        "pr_body_md": pr_body_md,
        "branch_name": branch_name,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"draft: {pr_title}"),
    }


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


def should_ask(state: AuditState) -> str:
    """Route after draft: ask | report."""
    if state.get("status") in {"blocked", "empty", "error"}:
        return "report"
    if not state.get("findings"):
        return "report"
    if not state.get("pr_title"):
        return "report"
    return "ask"


# ---------------------------------------------------------------------------
# ask / act / report
# ---------------------------------------------------------------------------


def ask(state: AuditState) -> dict[str, Any]:
    """Interrupt for human approval before open_pr stub."""
    from langgraph.types import interrupt

    repo = state.get("repo") or "local/sample"
    branch = state.get("branch_name") or "nightly/cleanup"
    pr_title = state.get("pr_title") or "chore: nightly cleanup"
    area = state.get("area") or "src"
    diff_stat = state.get("diff_stat") or "+0 / −0"
    patch_summary = list(state.get("patch_summary") or [])
    bullets = "\n".join(f"- {b}" for b in patch_summary[:5]) or "- (none)"

    body = hygiene_text(
        ask_body(
            repo=repo,
            branch=branch,
            pr_title=pr_title,
            area=area,
            diff_stat=diff_stat,
            bullets=bullets,
        )
    )
    payload = {
        "title": ask_title(),
        "body": body,
        "pending_action": "open_pr",
        "choices": ["approve", "deny"],
    }
    decision = interrupt(payload)
    decision_s = _normalize_decision(decision)
    return {
        "pending_action": "open_pr",
        "ask_payload": payload,
        "decision": decision_s,
        "human_summary": f"Ask answered: {decision_s}",
        "stage_summaries": _append_summary(state, f"ask: {decision_s}"),
    }


def act(state: AuditState) -> dict[str, Any]:
    decision = _normalize_decision(state.get("decision") or "deny")
    if decision != "approve":
        return {
            "skipped": True,
            "status": "denied",
            "pr_url": "",
            "human_summary": deny_open_message(),
            "stage_summaries": _append_summary(state, "act: denied — no PR"),
            # Clear any accidental PR metadata
            "pr_number": 0,
        }

    # Stub open_pr — record metadata in state only (no real GitHub)
    pr_number = 9001
    pr_url = f"https://example.com/{state.get('repo') or 'local/sample'}/pull/{pr_number}"
    pr_title = state.get("pr_title") or ""
    return {
        "skipped": False,
        "status": "opened",
        "pr_number": pr_number,
        "pr_url": pr_url,
        "pr_title": pr_title,
        "pr_body_md": state.get("pr_body_md") or "",
        "human_summary": approve_open_message(pr_title),
        "stage_summaries": _append_summary(
            state, f"act: stub opened PR #{pr_number}"
        ),
    }


def report(state: AuditState) -> dict[str, Any]:
    status = state.get("status") or "ok"
    repo = state.get("repo") or "local/sample"
    findings_n = len(state.get("findings") or [])

    if status == "plan_denied":
        summary = plan_declined_message()
        next_hint = "Say Audit owner/repo when you want to run."
    elif status == "empty":
        summary = empty_message()
        next_hint = "Re-run when the slice has hygiene debt."
    elif status == "blocked":
        summary = blocked_checkout_message(repo)
        next_hint = "Fix checkout path / tools and retry."
    elif status == "denied":
        summary = deny_open_message()
        next_hint = "Artifacts kept; re-run and approve to open stub PR."
    elif status == "opened":
        summary = approve_open_message(state.get("pr_title") or "cleanup PR")
        next_hint = "Review the stub PR metadata in run state."
    else:
        summary = empty_message()
        next_hint = "Inspect stage_summaries for details."

    artifacts = [
        a
        for a in [
            state.get("checkout_path") or "",
            state.get("pr_title") or "",
            f"findings:{findings_n}",
        ]
        if a
    ]

    cleaned = hygiene_text(summary)
    return {
        "human_summary": cleaned,
        "status": status,
        "artifacts": artifacts,
        "next_hint": next_hint,
        "stage_summaries": _append_summary(state, "report: complete"),
        **_assistant_reply(cleaned),
    }
