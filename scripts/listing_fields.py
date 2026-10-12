#!/usr/bin/env python3
"""Print Vendor Portal customData fields parsed from a listings/*.md file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from listing_md import listing_fields_to_custom_data, parse_listing_md


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help="Path to listings/<slug>.md",
    )
    parser.add_argument(
        "--include-name",
        action="store_true",
        help="Include top-level display name from the # heading",
    )
    args = parser.parse_args(argv)

    text = args.path.read_text(encoding="utf-8")
    fields = parse_listing_md(text)
    payload: dict[str, object] = listing_fields_to_custom_data(fields)
    if args.include_name and fields.name:
        payload["name"] = fields.name

    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
