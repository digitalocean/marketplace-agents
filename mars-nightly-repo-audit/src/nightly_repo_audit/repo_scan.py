"""Deterministic filesystem audit of an in-repo fixture slice (v1)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX)\b", re.I)
_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache"}


def scan_repo(root: Path, area: str | None = None) -> list[dict[str, Any]]:
    """Walk root (optionally under area) and emit hygiene findings."""
    root = root.resolve()
    if not root.is_dir():
        return []

    scan_root = root
    if area:
        candidate = root / area
        if candidate.is_dir():
            scan_root = candidate

    findings: list[dict[str, Any]] = []
    fid = 0

    for path in sorted(scan_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()

        # Legacy path bait
        if "legacy" in path.parts or path.name.startswith("legacy_"):
            fid += 1
            findings.append(
                {
                    "id": f"F{fid:03d}",
                    "severity": "medium",
                    "path": rel,
                    "evidence": "Unused legacy path — candidate for removal.",
                }
            )

        # Text scan for TODO/FIXME
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if _TODO_RE.search(line):
                fid += 1
                findings.append(
                    {
                        "id": f"F{fid:03d}",
                        "severity": "low",
                        "path": f"{rel}:{i}",
                        "evidence": line.strip()[:200],
                    }
                )
            if re.search(r"\bunused[_-]legacy\b", line, re.I):
                fid += 1
                findings.append(
                    {
                        "id": f"F{fid:03d}",
                        "severity": "medium",
                        "path": f"{rel}:{i}",
                        "evidence": line.strip()[:200],
                    }
                )

    return findings


_COMMENT_ONLY_RE = re.compile(
    r"^\s*(?:#|//|/\*|\*|<!--)",
)


def _inside_root(root: Path, rel: str) -> Path | None:
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def apply_hygiene(root: Path, findings: list[dict[str, Any]]) -> list[str]:
    """Apply safe cleanup on a checkout.

    Deletes unused legacy files and comment-only TODO/FIXME lines. Leaves
    inline TODOs and product code alone. Returns relative paths that changed.
    """
    root = root.resolve()
    deletions: dict[str, set[int]] = {}
    removals: list[str] = []
    for finding in findings:
        raw = str(finding.get("path") or "")
        if ":" in raw and raw.rsplit(":", 1)[-1].isdigit():
            rel, line_s = raw.rsplit(":", 1)
            deletions.setdefault(rel, set()).add(int(line_s))
            continue
        name = Path(raw).name
        if "legacy" in Path(raw).parts or name.startswith("legacy_"):
            removals.append(raw)

    changed: list[str] = []
    for rel in removals:
        path = _inside_root(root, rel)
        if path is None or not path.is_file():
            continue
        path.unlink()
        changed.append(rel)

    for rel, lines in deletions.items():
        path = _inside_root(root, rel)
        if path is None or not path.is_file():
            continue
        original = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        kept: list[str] = []
        mutated = False
        for index, line in enumerate(original, 1):
            if index in lines and _COMMENT_ONLY_RE.match(line):
                mutated = True
                continue
            kept.append(line)
        if mutated:
            path.write_text("".join(kept), encoding="utf-8")
            changed.append(rel)
    return changed


def default_fixture_path() -> Path:
    """Package-adjacent fixtures/sample_repo."""
    # src/nightly_repo_audit/repo_scan.py → repo root
    return Path(__file__).resolve().parents[2] / "fixtures" / "sample_repo"
