"""Stage nodes: intake → plan → gather → analyze → draft → ask → act → report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nightly_repo_audit.hygiene import hygiene_text
from nightly_repo_audit.persona import ask_body, ask_title
from nightly_repo_audit.repo_scan import default_fixture_path, scan_repo
from nightly_repo_audit.state import AuditState


def _append_summary(state: AuditState, line: str) -> list[str]:
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


# ---------------------------------------------------------------------------
# intake
# ---------------------------------------------------------------------------


def intake(state: AuditState) -> dict[str, Any]:
    if state.get("force_blocked"):
        return {
            "status": "blocked",
            "repo": state.get("repo") or "local/sample",
            "ref": state.get("ref") or "main",
            "trigger": state.get("trigger") or "manual",
            "human_summary": "Blocked: checkout/tools unavailable.",
            "stage_summaries": _append_summary(
                state, "intake: blocked — checkout/tools unavailable"
            ),
            "findings": [],
            "skipped": False,
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
    }


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
    summary = f"Tonight's slice: **{area}**. Out of scope: {', '.join(scope_limits)}."
    return {
        "area": area,
        "rationale": rationale,
        "scope_limits": scope_limits,
        "human_summary": summary,
        "stage_summaries": _append_summary(state, f"plan: area={area}"),
    }


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
            "human_summary": f"Blocked: checkout path missing ({checkout}).",
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
        "title": ask_title(repo=repo),
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
            "human_summary": "Denied — no PR opened.",
            "stage_summaries": _append_summary(state, "act: denied — no PR"),
            # Clear any accidental PR metadata
            "pr_number": 0,
        }

    # Stub open_pr — record metadata in state only (no real GitHub)
    pr_number = 9001
    pr_url = f"https://example.com/{state.get('repo') or 'local/sample'}/pull/{pr_number}"
    return {
        "skipped": False,
        "status": "opened",
        "pr_number": pr_number,
        "pr_url": pr_url,
        "pr_title": state.get("pr_title") or "",
        "pr_body_md": state.get("pr_body_md") or "",
        "human_summary": f"Opened PR #{pr_number} (stub).",
        "stage_summaries": _append_summary(
            state, f"act: stub opened PR #{pr_number}"
        ),
    }


def report(state: AuditState) -> dict[str, Any]:
    status = state.get("status") or "ok"
    repo = state.get("repo") or "local/sample"
    area = state.get("area") or "—"
    findings_n = len(state.get("findings") or [])
    self_check = "pass" if state.get("self_check_pass", True) else "fail"
    pr = state.get("pr_url") or "—"

    if status == "empty":
        summary = (
            "Nightly Repo Audit — done\n\n"
            "Status: empty\n"
            f"Repo:   {repo}\n"
            f"Slice:  {area}\n"
            "PR:     —\n\n"
            "No cleanup worth a PR tonight."
        )
        next_hint = "Re-run when the slice has hygiene debt."
    elif status == "blocked":
        summary = (
            "Nightly Repo Audit — done\n\n"
            "Status: blocked\n"
            f"Repo:   {repo}\n"
            f"Slice:  {area}\n"
            "PR:     —\n\n"
            "Checkout/tools failed or self-check failed; no ask."
        )
        next_hint = "Fix checkout path / tools and retry."
    elif status == "denied":
        summary = (
            "Nightly Repo Audit — done\n\n"
            "Status: denied\n"
            f"Repo:   {repo}\n"
            f"Slice:  {area}\n"
            "PR:     —\n\n"
            f"Findings: {findings_n}  ·  Self-check: {self_check}"
        )
        next_hint = "Artifacts kept; re-run and approve to open stub PR."
    elif status == "opened":
        summary = (
            "Nightly Repo Audit — done\n\n"
            "Status: opened\n"
            f"Repo:   {repo}\n"
            f"Slice:  {area}\n"
            f"PR:     {pr}\n\n"
            f"Findings: {findings_n}  ·  Self-check: {self_check}"
        )
        next_hint = "Review the stub PR metadata in run state."
    else:
        summary = (
            "Nightly Repo Audit — done\n\n"
            f"Status: {status}\n"
            f"Repo:   {repo}\n"
            f"Slice:  {area}\n"
            f"PR:     {pr}\n\n"
            f"Findings: {findings_n}  ·  Self-check: {self_check}"
        )
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

    return {
        "human_summary": hygiene_text(summary),
        "status": status,
        "artifacts": artifacts,
        "next_hint": next_hint,
        "stage_summaries": _append_summary(state, "report: complete"),
    }
