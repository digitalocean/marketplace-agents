#!/usr/bin/env python3
"""Upload listings/assets logo for a mars-agent (Vendor Portal customData.icon)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from vendor_portal_logo import _request, upload_from_listing_md


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_id", help="Vendor Portal appId")
    parser.add_argument("listing_md", type=Path, help="Path to listings/<slug>.md")
    parser.add_argument(
        "--version",
        type=int,
        help="App version (default: current from GET /apps)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After upload, print customData.icon from GET version",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    asset = upload_from_listing_md(
        args.app_id,
        args.listing_md,
        repo_root,
        version=args.version,
    )
    print(json.dumps({"uploaded": str(asset)}, indent=2))

    if args.verify:
        import os

        token = os.environ["AGENT_CREATE_TOKEN"]
        version = args.version
        if version is None:
            apps = _request("GET", "/apps", token)
            items = apps if isinstance(apps, list) else apps.get("apps") or []
            for entry in items:
                cur = entry.get("current") or {}
                if cur.get("appId") == args.app_id:
                    version = cur.get("version")
                    break
        doc = _request("GET", f"/apps/{args.app_id}/versions/{version}", token)
        icon = (doc.get("customData") or {}).get("icon")
        print(json.dumps({"version": version, "icon": icon}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
