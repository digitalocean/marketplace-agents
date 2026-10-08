"""Tests for listings/*.md parsing."""

from __future__ import annotations

import unittest
from pathlib import Path

from listing_md import parse_listing_md

REPO_ROOT = Path(__file__).resolve().parents[1]
LISTINGS = REPO_ROOT / "listings"


class ParseListingMdTests(unittest.TestCase):
    def test_nightly_repo_audit_listing(self) -> None:
        path = LISTINGS / "nightly-repo-audit.md"
        fields = parse_listing_md(path.read_text(encoding="utf-8"))
        self.assertEqual(fields.name, "Nightly Repo Audit")
        self.assertIn("nightly-repo-audit.svg", fields.logo_url or "")
        self.assertIn("hygiene pass", fields.summary)
        self.assertIn("Nightly Repo Audit is a repo-hygiene agent", fields.description)
        self.assertNotIn("Getting Started", fields.description.split("###")[0])
        self.assertIn("GITHUB_TOKEN", fields.getting_started or "")
        self.assertNotIn("doctl harness-runtime triggers create", fields.description)

    def test_logo_line_stripped_from_body(self) -> None:
        text = """logo: https://example.com/icon.png

# Demo Agent

## Summary

Short.

## Description

Intro paragraph.

### Why use it

- One

### Getting Started

Step 1.

### Requirements

- Req
"""
        fields = parse_listing_md(text)
        self.assertEqual(fields.logo_url, "https://example.com/icon.png")
        self.assertEqual(fields.name, "Demo Agent")
        self.assertEqual(fields.getting_started, "Step 1.")
        self.assertIn("Intro paragraph", fields.description)
        self.assertIn("### Requirements", fields.description)
        self.assertNotIn("Step 1", fields.description)

    def test_all_catalog_listings_parse(self) -> None:
        for path in sorted(LISTINGS.glob("*.md")):
            with self.subTest(path=path.name):
                fields = parse_listing_md(path.read_text(encoding="utf-8"))
                self.assertTrue(fields.name)
                self.assertTrue(fields.summary)
                self.assertTrue(fields.description)


if __name__ == "__main__":
    unittest.main()
