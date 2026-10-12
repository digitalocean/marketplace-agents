#!/usr/bin/env python3
"""Merge listings/*.md fields into a Vendor Portal app version (PUT)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from listing_md import listing_fields_to_custom_data, parse_listing_md

BASE_URL = "https://api.digitalocean.com/api/v1/vendor-portal"


def _request(method: str, path: str, token: str, body: dict | None = None) -> Any:
    url = f"{BASE_URL}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {method} {path}: {detail}") from exc


def _apps_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    for key in ("apps", "data", "items"):
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def _resolve_app(apps: list[dict[str, Any]], app_id: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return (current version summary, optional unpublished version summary)."""
    for entry in apps:
        current = entry.get("current") or {}
        if current.get("appId") == app_id or entry.get("appId") == app_id:
            unpublished = entry.get("unpublished")
            return current, unpublished if isinstance(unpublished, dict) else None
    raise SystemExit(f"App {app_id} not found in GET /apps")


def _status_value(version_doc: dict[str, Any]) -> str:
    status = version_doc.get("status")
    if isinstance(status, dict):
        return str(status.get("value") or "")
    return str(status or "")


def _pin_sha(agent: dict[str, Any], framework_sha: str) -> None:
    agent["frameworkRepoSha"] = framework_sha
    for item in agent.get("envDefaults") or []:
        if item.get("name") == "FRAMEWORK_REPO_SHA":
            item["default"] = framework_sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_id", help="Vendor Portal appId")
    parser.add_argument("listing_md", type=Path, help="Path to listings/<slug>.md")
    parser.add_argument(
        "--framework-repo-sha",
        help="Pin FRAMEWORK_REPO_SHA / frameworkRepoSha (default: current git HEAD)",
    )
    parser.add_argument(
        "--reason",
        default="Add catalog logo from listings markdown",
        help="reasonForUpdate on customData",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print merged PUT body without sending",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("AGENT_CREATE_TOKEN")
    if not token:
        raise SystemExit("AGENT_CREATE_TOKEN is not set")

    listing_text = args.listing_md.read_text(encoding="utf-8")
    parsed = parse_listing_md(listing_text)
    listing_custom = listing_fields_to_custom_data(parsed)

    repo_root = Path(__file__).resolve().parents[1]
    framework_sha = args.framework_repo_sha
    if not framework_sha:
        import subprocess

        framework_sha = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True)
            .strip()
        )

    apps_payload = _request("GET", "/apps", token)
    app_summary, unpublished = _resolve_app(_apps_list(apps_payload), args.app_id)
    if unpublished:
        pending_status = _status_value(unpublished).lower()
        if pending_status in {"pending", "inreview", "in_review"}:
            raise SystemExit(
                f"Unpublished version {unpublished.get('version')} is {pending_status}; "
                "wait for review before submitting another update."
            )

    version = app_summary.get("version")
    if not isinstance(version, int):
        raise SystemExit(f"Could not determine version from app list: {app_summary.keys()}")

    version_doc = _request("GET", f"/apps/{args.app_id}/versions/{version}", token)
    status = _status_value(version_doc).lower()
    if status in {"pending", "inreview", "in_review"}:
        raise SystemExit(
            f"Version {version} is {status}; wait for review before submitting another update."
        )

    custom_data = dict(version_doc.get("customData") or {})
    custom_data.update(listing_custom)

    agent = dict(custom_data.get("agent") or {})
    _pin_sha(agent, framework_sha)
    custom_data["agent"] = agent

    put_body = {
        "appId": args.app_id,
        "developerId": version_doc.get("developerId") or app_summary.get("developerId"),
        "name": version_doc.get("name") or app_summary.get("name"),
        "type": version_doc.get("type") or app_summary.get("type") or "mars-agent",
        "showOnCatalog": version_doc.get("showOnCatalog") or app_summary.get("showOnCatalog") or {"value": True},
        "emergencyContacts": version_doc.get("emergencyContacts") or app_summary.get("emergencyContacts") or [],
        "reasonForUpdate": args.reason,
        "customData": custom_data,
    }

    if args.dry_run:
        print(json.dumps(put_body, indent=2, ensure_ascii=False))
        return 0

    result = _request("PUT", f"/apps/{args.app_id}/versions/{version}", token, put_body)
    out_status = _status_value(result) or _status_value(version_doc)
    print(
        json.dumps(
            {
                "appId": args.app_id,
                "version": version,
                "status": out_status,
                "icon": custom_data.get("icon"),
                "frameworkRepoSha": agent.get("frameworkRepoSha"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
