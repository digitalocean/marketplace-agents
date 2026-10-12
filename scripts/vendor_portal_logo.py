"""Upload a listing logo to Vendor Portal (sets customData.icon)."""

from __future__ import annotations

import mimetypes
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "https://api.digitalocean.com/api/v1/vendor-portal"


def _request(method: str, path: str, token: str, body: dict | None = None) -> Any:
    import json

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


def _multipart_image_body(field_name: str, asset_path: Path) -> tuple[bytes, str]:
    content_type = mimetypes.guess_type(asset_path.name)[0]
    if content_type not in {"image/svg+xml", "image/png"}:
        if asset_path.suffix.lower() == ".svg":
            content_type = "image/svg+xml"
        elif asset_path.suffix.lower() == ".png":
            content_type = "image/png"
        else:
            raise SystemExit(f"Unsupported logo type: {asset_path} (use SVG or PNG)")

    boundary = f"----MarketplaceAgents{uuid.uuid4().hex}"
    data = asset_path.read_bytes()
    parts: list[bytes] = [
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{asset_path.name}"\r\n'
        ).encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def upload_app_logo(
    app_id: str,
    asset_path: Path,
    token: str,
    *,
    version: int | None = None,
) -> None:
    """PUT logo file; Vendor Portal sets customData.icon to the assets CDN URL."""
    if not asset_path.is_file():
        raise SystemExit(f"Logo file not found: {asset_path}")

    if version is None:
        import json

        req = urllib.request.Request(
            f"{BASE_URL}/apps",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"HTTP {exc.code} GET /apps: {detail}") from exc

        apps = payload if isinstance(payload, list) else payload.get("apps") or []
        version = None
        for entry in apps:
            current = entry.get("current") or {}
            if current.get("appId") == app_id or entry.get("appId") == app_id:
                version = current.get("version")
                break
        if not isinstance(version, int):
            raise SystemExit(f"Could not resolve current version for app {app_id}")

    path = f"/apps/{app_id}/versions/{version}/logo"
    body, content_type = _multipart_image_body("rawImage", asset_path)
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            if resp.status not in (200, 201):
                raise SystemExit(f"Unexpected HTTP {resp.status} from logo upload")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} PUT {path}: {detail}") from exc


def upload_from_listing_md(
    app_id: str,
    listing_md: Path,
    repo_root: Path,
    token: str | None = None,
    *,
    version: int | None = None,
) -> Path:
    import sys

    _SCRIPT_DIR = Path(__file__).resolve().parent
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))

    from listing_md import logo_asset_path, parse_listing_md

    tok = token or os.environ.get("AGENT_CREATE_TOKEN")
    if not tok:
        raise SystemExit("AGENT_CREATE_TOKEN is not set")

    fields = parse_listing_md(listing_md.read_text(encoding="utf-8"))
    asset = logo_asset_path(fields, repo_root)
    if asset is None:
        raise SystemExit(
            f"No local listings/assets file for logo: line in {listing_md}. "
            "Use a URL ending in listings/assets/<slug>.svg (or .png)."
        )
    upload_app_logo(app_id, asset, tok, version=version)
    return asset
