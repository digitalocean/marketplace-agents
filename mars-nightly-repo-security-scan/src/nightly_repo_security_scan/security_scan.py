"""Deterministic security scan and in-memory fixes for one repo slice.

Looks for application problems, logic bugs, and dependency pins below a
bundled patched release. Rewrites are local text transforms. The checkout
on disk is not modified.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

_SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".pytest_cache",
    "dist",
    "build",
}

# Same-major patched pins. Evidence names the floor only; no exploit detail.
_PYPI_PATCHED: dict[str, str] = {
    "pyyaml": "5.4.1",
    "requests": "2.32.3",
    "urllib3": "1.26.19",
}
_NPM_PATCHED: dict[str, str] = {
    "lodash": "4.17.21",
}

_SECRET_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<name>[A-Z][A-Z0-9_]*(?:KEY|SECRET|PASSWORD|TOKEN))"
    r"\s*=\s*(?P<quote>['\"])(?P<value>[^'\"]{8,})(?P=quote)[ \t]*$",
    re.M,
)
_YAML_LOAD_RE = re.compile(
    r"\byaml\.load\((?P<arg>[^),\n]+)"
    r"(?:\s*,\s*Loader\s*=\s*yaml\.\w+\s*)?\)"
)
_VERIFY_RE = re.compile(r"\bverify\s*=\s*False\b")
_DEBUG_RE = re.compile(r"\bdebug\s*=\s*True\b")
_EVAL_RE = re.compile(r"(?<![\w.])eval\(")
_INDEX_RE = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\[len\((?P=name)\)\]")
_SQL_ASSIGN_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<lhs>\w+)\s*=\s*f(?P<q>[\"'])"
    r"(?P<sql>(?:SELECT|INSERT|UPDATE|DELETE)\b.*?)(?P=q)[ \t]*$",
    re.M | re.I,
)
_REQ_LINE_RE = re.compile(
    r"^(?P<prefix>[ \t]*)(?P<name>[A-Za-z0-9_.-]+)"
    r"(?P<eq>\s*==\s*)(?P<ver>[A-Za-z0-9.*+!]+)(?P<rest>.*)$",
    re.M,
)


def default_fixture_path() -> Path:
    """Package-adjacent fixtures/sample_repo."""
    return Path(__file__).resolve().parents[2] / "fixtures" / "sample_repo"


def _parse_version(raw: str) -> tuple[int, ...]:
    nums: list[int] = []
    for part in (raw or "").split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        nums.append(int(digits))
    return tuple(nums) if nums else (0,)


def _version_less(left: str, right: str) -> bool:
    aa = _parse_version(left)
    bb = _parse_version(right)
    width = max(len(aa), len(bb))
    aa = aa + (0,) * (width - len(aa))
    bb = bb + (0,) * (width - len(bb))
    return aa < bb


def _same_major(left: str, right: str) -> bool:
    return _parse_version(left)[:1] == _parse_version(right)[:1]


def _line_no(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _finding(
    *,
    kind: str,
    severity: str,
    path: str,
    evidence: str,
    fix: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "severity": severity,
        "path": path,
        "evidence": evidence,
        "fix": fix,
    }


def _ensure_import(text: str, statement: str) -> str:
    if re.search(rf"(?m)^(?:import {re.escape(statement[7:])}|{re.escape(statement)})\b", text):
        return text
    # `import os` / `import ast` — statement is the full line.
    if statement in text.splitlines():
        return text
    lines = text.splitlines(keepends=True)
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    if insert_at < len(lines):
        stripped = lines[insert_at].lstrip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            quote = '"""' if stripped.startswith('"""') else "'''"
            if stripped.count(quote) >= 2 and stripped.strip() != quote:
                insert_at += 1
            else:
                insert_at += 1
                while insert_at < len(lines) and quote not in lines[insert_at]:
                    insert_at += 1
                if insert_at < len(lines):
                    insert_at += 1
    lines.insert(insert_at, statement + "\n")
    return "".join(lines)


def _fix_secrets(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        name = match.group("name")
        findings.append(
            _finding(
                kind="app",
                severity="high",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence=f"Hardcoded credential assigned to {name}.",
                fix=f"Read {name} from the environment instead of source.",
            )
        )
        indent = match.group("indent")
        return f'{indent}{name} = os.environ["{name}"]'

    updated = _SECRET_RE.sub(repl, text)
    if findings:
        updated = _ensure_import(updated, "import os")
    return updated, findings


def _fix_yaml_load(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        findings.append(
            _finding(
                kind="app",
                severity="high",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence="yaml.load is not the safe loader.",
                fix="Use yaml.safe_load instead of yaml.load.",
            )
        )
        return f"yaml.safe_load({match.group('arg').strip()})"

    return _YAML_LOAD_RE.sub(repl, text), findings


def _fix_verify(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        findings.append(
            _finding(
                kind="app",
                severity="high",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence="TLS certificate verification is disabled.",
                fix="Enable TLS certificate verification.",
            )
        )
        return "verify=True"

    return _VERIFY_RE.sub(repl, text), findings


def _fix_debug(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        findings.append(
            _finding(
                kind="app",
                severity="medium",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence="Debug mode is left on.",
                fix="Turn off debug mode.",
            )
        )
        return "debug=False"

    return _DEBUG_RE.sub(repl, text), findings


def _fix_eval(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        findings.append(
            _finding(
                kind="bug",
                severity="high",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence="eval is used where a literal parse is enough.",
                fix="Parse with ast.literal_eval instead of eval.",
            )
        )
        return "ast.literal_eval("

    updated = _EVAL_RE.sub(repl, text)
    if findings:
        updated = _ensure_import(updated, "import ast")
    return updated, findings


def _fix_index(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        name = match.group("name")
        findings.append(
            _finding(
                kind="bug",
                severity="medium",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence=f"Index len({name}) is past the last item.",
                fix=f"Read the last {name} item with len({name}) - 1.",
            )
        )
        return f"{name}[len({name}) - 1]"

    return _INDEX_RE.sub(repl, text), findings


def _fix_sql(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    replacements: list[tuple[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        sql = match.group("sql")
        names = re.findall(r"\{(\w+)\}", sql)
        if not names:
            return match.group(0)
        new_sql = re.sub(r"""['\"]\{(\w+)\}['\"]""", "?", sql)
        new_sql = re.sub(r"\{(\w+)\}", "?", new_sql)
        lhs = match.group("lhs")
        replacements.append((lhs, ", ".join(names)))
        findings.append(
            _finding(
                kind="app",
                severity="high",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence="SQL query interpolates values into the statement.",
                fix="Parameterize the SQL query instead of interpolating values.",
            )
        )
        quote = match.group("q")
        return f"{match.group('indent')}{lhs} = {quote}{new_sql}{quote}"

    updated = _SQL_ASSIGN_RE.sub(repl, text)
    for lhs, names in replacements:
        updated = re.sub(
            rf"^([ \t]*)return {re.escape(lhs)}, \(\)[ \t]*$",
            rf"\1return {lhs}, ({names},)",
            updated,
            count=1,
            flags=re.M,
        )
    return updated, findings


def _fix_source(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    updated = text
    for fixer in (
        _fix_secrets,
        _fix_yaml_load,
        _fix_verify,
        _fix_sql,
        _fix_debug,
        _fix_eval,
        _fix_index,
    ):
        updated, found = fixer(updated, rel)
        findings.extend(found)
    return updated, findings


def _fix_requirements(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        name = match.group("name")
        patched = _PYPI_PATCHED.get(name.lower())
        ver = match.group("ver")
        if not patched or not _same_major(ver, patched) or not _version_less(ver, patched):
            return match.group(0)
        findings.append(
            _finding(
                kind="dependency",
                severity="high",
                path=f"{rel}:{_line_no(text, match.start())}",
                evidence=f"{name} {ver} is below the patched pin {patched}.",
                fix=f"Bump {name} to {patched}.",
            )
        )
        return f"{match.group('prefix')}{name}{match.group('eq')}{patched}{match.group('rest')}"

    return _REQ_LINE_RE.sub(repl, text), findings


def _fix_package_json(text: str, rel: str) -> tuple[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    updated = text
    for name, patched in _NPM_PATCHED.items():
        pattern = re.compile(
            rf'(?P<prefix>"{re.escape(name)}"\s*:\s*")(?P<ver>[^"]+)(?P<suffix>")'
        )
        match = pattern.search(updated)
        if not match:
            continue
        raw = match.group("ver").strip()
        if raw[:1] in "^~><" or " " in raw:
            continue
        if not _same_major(raw, patched) or not _version_less(raw, patched):
            continue
        findings.append(
            _finding(
                kind="dependency",
                severity="high",
                path=rel,
                evidence=f"{name} {raw} is below the patched pin {patched}.",
                fix=f"Bump {name} to {patched}.",
            )
        )
        updated = pattern.sub(rf"\g<prefix>{patched}\g<suffix>", updated, count=1)
    return updated, findings


def fix_text(rel: str, text: str) -> tuple[str, list[dict[str, Any]]]:
    """Return patched text and findings for one file. No change means no findings."""
    name = Path(rel).name
    if name in {"requirements.txt", "requirements-dev.txt"}:
        return _fix_requirements(text, rel)
    if name == "package.json":
        return _fix_package_json(text, rel)
    if rel.endswith(".py"):
        return _fix_source(text, rel)
    return text, []


def _unified(rel: str, before: str, after: str) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{rel}",
        tofile=f"b/{rel}",
    )
    return "".join(diff)


def _assign_ids(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    numbered: list[dict[str, Any]] = []
    for index, finding in enumerate(findings, 1):
        row = dict(finding)
        row["id"] = f"F{index:03d}"
        numbered.append(row)
    return numbered


def _iter_files(root: Path, area: str | None) -> list[Path]:
    scan_root = root
    if area:
        candidate = root / area
        if candidate.is_dir():
            scan_root = candidate
    found: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            return
        if any(part in _SKIP_DIRS for part in path.parts):
            return
        seen.add(resolved)
        found.append(path)

    if scan_root.is_dir():
        for path in sorted(scan_root.rglob("*")):
            add(path)
    for name in ("requirements.txt", "requirements-dev.txt", "package.json"):
        add(root / name)
    return found


def scan_and_fix(
    root: Path,
    area: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Scan root and return (findings, file fixes). Fixes are in-memory diffs."""
    root = root.resolve()
    if not root.is_dir():
        return [], []

    findings: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []
    for path in _iter_files(root, area):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "\x00" in text or len(text) > 200_000:
            continue
        updated, file_findings = fix_text(rel, text)
        if not file_findings or updated == text:
            continue
        findings.extend(file_findings)
        summaries = [str(item.get("fix") or "") for item in file_findings]
        fixes.append(
            {
                "path": rel,
                "summary": "; ".join(s for s in summaries if s),
                "diff": _unified(rel, text, updated),
            }
        )
    return _assign_ids(findings), fixes


def scan_repo(root: Path, area: str | None = None) -> list[dict[str, Any]]:
    """Findings only. Same pass as ``scan_and_fix``."""
    findings, _fixes = scan_and_fix(root, area)
    return findings
