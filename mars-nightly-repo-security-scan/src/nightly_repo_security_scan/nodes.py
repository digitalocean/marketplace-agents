"""Stage nodes: intake → plan → gather → analyze → draft → ask → act → report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from nightly_repo_security_scan.action_gateway import open_draft_pr
from nightly_repo_security_scan.converse import conversational_reply
from nightly_repo_security_scan.hygiene import hygiene_text
from nightly_repo_security_scan.intent import classify_intent, parse_scan_target
from nightly_repo_security_scan.llm import draft_review_note
from nightly_repo_security_scan.persona import (
    approve_open_message,
    ask_body,
    ask_title,
    blocked_checkout_message,
    deny_open_message,
    empty_message,
    open_pr_failed_message,
    plan_confirm_body,
    plan_confirm_title,
    plan_confirmed_message,
    plan_declined_message,
)
from nightly_repo_security_scan.security_scan import default_fixture_path, scan_and_fix
from nightly_repo_security_scan.state import ScanState

ASSISTANT_DISPLAY_NAME = "Nightly Repo Security Scan"


def _append_summary(state: ScanState, line: str) -> list[str]:
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


def _mars_node(fn):
    def wrapped(state):
        out = fn(state)
        if not out:
            return out
        return _mars_stream_safe_update(out)

    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped


def _programmatic_scan(state: ScanState) -> bool:
    return bool(
        state.get("force_blocked")
        or state.get("force_empty")
        or (state.get("repo") or "").strip()
        or (state.get("fixture_path") or "").strip()
        or (state.get("area_hint") or "").strip()
        or (state.get("ref") or "").strip()
    )


def _normalize_decision(raw: Any) -> str:
    """approve|deny. MARS harness may send bool, {approved: true}, or strings."""
    if isinstance(raw, dict):
        if "approved" in raw:
            return "approve" if raw.get("approved") else "deny"
        raw = raw.get("decision") or raw.get("value") or raw.get("choice") or "deny"
    if isinstance(raw, bool):
        return "approve" if raw else "deny"
    decision_s = str(raw).strip().lower()
    if decision_s in {"approve", "approved", "yes", "y", "ok", "okay", "true"}:
        return "approve"
    if decision_s in {"deny", "denied", "no", "n", "false"}:
        return "deny"
    return "deny"


def _diff_stat(fixes: list[dict[str, Any]]) -> str:
    plus = 0
    minus = 0
    for fix in fixes:
        for line in str(fix.get("diff") or "").splitlines():
            if line.startswith(("+++", "---")):
                continue
            if line.startswith("+"):
                plus += 1
            elif line.startswith("-"):
                minus += 1
    files_n = len({str(fix.get("path") or "") for fix in fixes if fix.get("path")})
    return f"+{plus} / −{minus} across {files_n} files"


def intake(state: ScanState) -> dict[str, Any]:
    human_text = _human_message_text(state.get("messages"))
    programmatic = _programmatic_scan(state) and not human_text.strip()
    pending = state.get("pending_scan")
    skip_plan_confirm = not bool(human_text.strip())

    if human_text.strip() or state.get("messages"):
        intent = classify_intent(
            human_text,
            programmatic_scan=programmatic,
            pending_scan=pending if isinstance(pending, dict) else None,
        )
        if intent in {"chat", "help", "other", "plan_denied"}:
            reply = conversational_reply(intent, human_text)
            status = "plan_denied" if intent == "plan_denied" else intent
            return {
                "intent": intent,
                "status": status,
                "skipped": False,
                "findings": [],
                "fixes": [],
                **_assistant_reply(reply),
            }
        if intent == "scan" and isinstance(pending, dict):
            skip_plan_confirm = True
            scan_intent = "scan"
        else:
            scan_intent = "scan_plan" if human_text.strip() else "scan"
    else:
        scan_intent = "scan"

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
                state, "intake: blocked, checkout/tools unavailable"
            ),
            "findings": [],
            "fixes": [],
            "skipped": False,
            **_assistant_reply(blocked),
        }

    parsed = parse_scan_target(human_text) if human_text.strip() else {}
    repo = (state.get("repo") or "").strip() or parsed.get("repo") or "local/sample"
    ref = (state.get("ref") or "").strip() or parsed.get("ref") or "main"
    trigger = (state.get("trigger") or "manual").strip().lower()
    if trigger not in {"cron", "manual"}:
        trigger = "manual"
    area_hint = (state.get("area_hint") or "").strip() or parsed.get("area") or ""
    fixture_path = (state.get("fixture_path") or "").strip()
    if not fixture_path:
        fixture_path = str(default_fixture_path())

    summary = f"Scanning `{repo}` @ `{ref}`."
    return {
        "intent": scan_intent,
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
        "fixes": [],
        "skip_plan_confirm": skip_plan_confirm,
        "plan_confirmed": bool(skip_plan_confirm),
    }


def intake_node(state: ScanState) -> dict[str, Any]:
    return _mars_stream_safe_update(intake(state))


def route_after_intake(state: ScanState) -> str:
    if state.get("status") in {"blocked", "plan_denied"}:
        return "end"
    intent = (state.get("intent") or "scan").strip().lower()
    if intent in {"chat", "help", "other", "plan_denied"}:
        return "end"
    return "plan"


def plan(state: ScanState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}
    hint = (state.get("area_hint") or "").strip()
    if hint:
        area = hint
        rationale = f"Operator hint: focus on `{hint}`."
    else:
        area = "src"
        rationale = "Default nightly slice: application source plus root dependency manifests."
    scope_limits = [
        "No product feature rewrites",
        "No merge and no force-push",
        f"Stay inside `{area}` plus root dependency manifests",
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
        "pending_scan": pending,
        "stage_summaries": _append_summary(state, f"plan: area={area}"),
    }
    if state.get("skip_plan_confirm") or state.get("plan_confirmed"):
        out["human_summary"] = summary
    else:
        out.update(_assistant_reply(summary))
    return out


def should_confirm_plan(state: ScanState) -> str:
    if state.get("skip_plan_confirm") or state.get("plan_confirmed"):
        return "gather"
    return "confirm_plan"


def confirm_plan(state: ScanState) -> dict[str, Any]:
    """Interrupt before gather."""
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
        "pending_action": "start_scan",
        "choices": ["approve", "deny"],
    }
    decision = interrupt(payload)
    decision_s = _normalize_decision(decision)
    if decision_s == "approve":
        confirmed = plan_confirmed_message(area=area, repo=repo)
        return {
            "plan_confirmed": True,
            "stage_summaries": _append_summary(state, "confirm_plan: approve"),
            **_assistant_reply(confirmed),
        }
    return {
        "plan_confirmed": False,
        "status": "plan_denied",
        "stage_summaries": _append_summary(state, "confirm_plan: deny"),
    }


def route_after_confirm_plan(state: ScanState) -> str:
    if state.get("plan_confirmed"):
        return "gather"
    return "report"


def gather(state: ScanState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    checkout = Path(state.get("fixture_path") or default_fixture_path())
    if not checkout.is_dir():
        return {
            "status": "blocked",
            "checkout_path": str(checkout),
            "files_touched_count": 0,
            "commands_run": ["security_scan (failed: missing path)"],
            "human_summary": blocked_checkout_message(state.get("repo") or "local/sample"),
            "stage_summaries": _append_summary(state, "gather: blocked, missing checkout"),
            "findings": [],
            "fixes": [],
        }

    area = state.get("area") or "src"
    commands = [f"security_scan {checkout}", f"area={area}"]
    n_files = sum(1 for p in checkout.rglob("*") if p.is_file())
    summary = f"Checked out; scanning {n_files} paths."
    return {
        "checkout_path": str(checkout.resolve()),
        "files_touched_count": n_files,
        "commands_run": commands,
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"gather: {summary}"),
    }


def analyze(state: ScanState) -> dict[str, Any]:
    if state.get("status") == "blocked":
        return {}

    if state.get("force_empty"):
        summary = "Bullet findings: none (forced empty)."
        return {
            "findings": [],
            "fixes": [],
            "self_check_pass": True,
            "status": "empty",
            "human_summary": summary,
            "stage_summaries": _append_summary(state, "analyze: empty findings"),
        }

    checkout = Path(state.get("checkout_path") or state.get("fixture_path") or ".")
    area = state.get("area") or "src"
    scoped_area = None if area == "." else area
    findings, fixes = scan_and_fix(checkout, area=scoped_area)

    if findings and not fixes:
        return {
            "findings": findings,
            "fixes": [],
            "self_check_pass": False,
            "status": "blocked",
            "human_summary": hygiene_text(
                "Self-check failed, findings without a fix; no ask."
            ),
            "stage_summaries": _append_summary(state, "analyze: self-check fail"),
        }

    for finding in findings:
        if not finding.get("path") or not finding.get("evidence") or not finding.get("fix"):
            return {
                "findings": findings,
                "fixes": fixes,
                "self_check_pass": False,
                "status": "blocked",
                "human_summary": hygiene_text(
                    "Self-check failed, incomplete findings; no ask."
                ),
                "stage_summaries": _append_summary(state, "analyze: self-check fail"),
            }

    if not findings:
        summary = "No findings."
        return {
            "findings": [],
            "fixes": [],
            "self_check_pass": True,
            "status": "empty",
            "human_summary": summary,
            "stage_summaries": _append_summary(state, "analyze: empty findings"),
        }

    bullets = "\n".join(
        f"- [{f.get('severity')}] {f.get('path')}: {f.get('fix')}"
        for f in findings[:8]
    )
    summary = f"Findings: {len(findings)}\n{bullets}"
    return {
        "findings": findings,
        "fixes": fixes,
        "self_check_pass": True,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"analyze: {len(findings)} findings"),
    }


def draft(state: ScanState) -> dict[str, Any]:
    if state.get("status") in {"blocked", "empty"}:
        return {}

    findings = list(state.get("findings") or [])
    fixes = list(state.get("fixes") or [])
    if not findings or not fixes:
        return {
            "status": "empty",
            "human_summary": "No security fixes worth a PR tonight.",
            "stage_summaries": _append_summary(state, "draft: empty"),
        }

    area = state.get("area") or "src"
    repo = state.get("repo") or "local/sample"
    n = len(findings)
    patch_summary = [str(fix.get("summary") or fix.get("path") or "") for fix in fixes]
    patch_diff = "\n".join(str(fix.get("diff") or "") for fix in fixes if fix.get("diff"))
    diff_stat = _diff_stat(fixes)
    branch_name = f"nightly/security-{area.replace('/', '-')}"
    pr_title = f"fix: nightly security scan ({area}), {n} finding(s)"
    body_lines = [
        f"## Nightly security scan for `{repo}`",
        "",
        f"Slice: **{area}**",
        "",
        "### Fixes",
        "",
    ]
    for finding in findings:
        body_lines.append(
            f"- [{finding.get('kind')}] {finding.get('path')}: {finding.get('fix')}"
        )
    review = hygiene_text(draft_review_note(findings))
    if review:
        body_lines.extend(["", "### Review", "", review])
    body_lines.extend(
        [
            "",
            "### Patch",
            "",
            patch_diff.rstrip(),
            "",
            "### Notes",
            "",
            "- Security fixes only. No product feature rewrites.",
            "- Draft PR. Does not merge.",
            "- Dependency bumps stay on the same major as the patched pin.",
            "",
        ]
    )
    pr_body_md = hygiene_text("\n".join(body_lines))
    commit_message = f"fix: nightly security scan in {area} ({n} findings)"
    preview = "\n".join(f"- {b}" for b in patch_summary[:5])
    summary = f"PR draft ready: {pr_title}\n{preview}"
    return {
        "patch_summary": patch_summary,
        "patch_diff": patch_diff,
        "diff_stat": diff_stat,
        "commit_message": commit_message,
        "pr_title": pr_title,
        "pr_body_md": pr_body_md,
        "branch_name": branch_name,
        "status": "ok",
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"draft: {pr_title}"),
    }


def should_ask(state: ScanState) -> str:
    """Route after draft: ask | report."""
    if state.get("status") in {"blocked", "empty", "error"}:
        return "report"
    if not state.get("findings"):
        return "report"
    if not state.get("pr_title"):
        return "report"
    return "ask"


def ask(state: ScanState) -> dict[str, Any]:
    """Interrupt for human approval before open_pr via Action Gateway."""
    from langgraph.types import interrupt

    repo = state.get("repo") or "local/sample"
    branch = state.get("branch_name") or "nightly/security"
    pr_title = state.get("pr_title") or "fix: nightly security scan"
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


def act(state: ScanState) -> dict[str, Any]:
    decision = _normalize_decision(state.get("decision") or "deny")
    if decision != "approve":
        return {
            "skipped": True,
            "status": "denied",
            "pr_url": "",
            "human_summary": deny_open_message(),
            "stage_summaries": _append_summary(state, "act: denied, no PR"),
            "pr_number": 0,
        }

    pr_title = state.get("pr_title") or ""
    result = open_draft_pr(
        repo=state.get("repo") or "",
        ref=state.get("ref") or "main",
        branch=state.get("branch_name") or "",
        title=pr_title,
        body=state.get("pr_body_md") or "",
    )
    if not result.ok:
        msg = open_pr_failed_message(result.error_message)
        return {
            "skipped": True,
            "status": "error",
            "pr_url": "",
            "pr_number": 0,
            "human_summary": msg,
            "stage_summaries": _append_summary(state, "act: open failed"),
            **_assistant_reply(msg),
        }

    return {
        "skipped": False,
        "status": "opened",
        "pr_number": result.pr_number,
        "pr_url": result.pr_url,
        "pr_title": pr_title,
        "pr_body_md": state.get("pr_body_md") or "",
        "human_summary": approve_open_message(pr_title, result.pr_url),
        "stage_summaries": _append_summary(
            state,
            f"act: opened PR #{result.pr_number or '?'} via {result.tool_name}",
        ),
    }


def report(state: ScanState) -> dict[str, Any]:
    status = state.get("status") or "ok"
    repo = state.get("repo") or "local/sample"
    findings_n = len(state.get("findings") or [])

    if status == "plan_denied":
        summary = plan_declined_message()
        next_hint = "Say Scan owner/repo when you want to run."
    elif status == "empty":
        summary = empty_message()
        next_hint = "Re-run when the slice has something to fix."
    elif status == "blocked":
        summary = blocked_checkout_message(repo)
        next_hint = "Fix checkout path or tools and retry."
    elif status == "denied":
        summary = deny_open_message()
        next_hint = "Artifacts kept; re-run and approve to open a draft PR."
    elif status == "error":
        summary = state.get("human_summary") or open_pr_failed_message(
            "Could not open the PR."
        )
        next_hint = "Fix Action Gateway / GitHub Connection and retry."
    elif status == "opened":
        summary = approve_open_message(
            state.get("pr_title") or "security fix PR",
            state.get("pr_url") or "",
        )
        next_hint = "Review the draft PR on GitHub."
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


plan_node = _mars_node(plan)
confirm_plan_node = _mars_node(confirm_plan)
gather_node = _mars_node(gather)
analyze_node = _mars_node(analyze)
draft_node = _mars_node(draft)
ask_node = _mars_node(ask)
act_node = _mars_node(act)
report_node = _mars_node(report)
