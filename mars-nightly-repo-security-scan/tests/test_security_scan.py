"""Scanner and remediator: fixture bait is found, fixed, and stays fixed."""

from __future__ import annotations

from pathlib import Path

from nightly_repo_security_scan.security_scan import (
    default_fixture_path,
    fix_text,
    scan_and_fix,
)


def test_fixture_finds_app_bugs_and_dependencies():
    findings, fixes = scan_and_fix(default_fixture_path(), area="src")
    kinds = {item.get("kind") for item in findings}
    assert {"app", "bug", "dependency"} <= kinds
    blob = " ".join(
        f"{item.get('path')} {item.get('evidence')} {item.get('fix')}" for item in findings
    )
    assert "sk-live-demo-key-0001" not in blob
    assert "super-secret-db-pass" not in blob
    assert "API_KEY" in blob
    assert "yaml.safe_load" in blob or "yaml.load" in blob
    assert "requests" in blob
    assert "lodash" in blob
    assert "literal_eval" in blob or "eval" in blob
    assert fixes
    assert all(fix.get("diff") for fix in fixes)


def test_fixes_are_idempotent_and_cover_each_rule():
    root = default_fixture_path()
    expected = {
        "src/app.py": (
            'API_KEY = os.environ["API_KEY"]',
            "yaml.safe_load(blob)",
            "verify=True",
            'query = "SELECT id, email FROM users WHERE id = ?"',
            "return query, (user_id,)",
            "debug=False",
            "import os",
        ),
        "src/bugs.py": (
            "import ast",
            "ast.literal_eval(raw)",
            "items[len(items) - 1]",
        ),
        "requirements.txt": (
            "requests==2.32.3",
            "PyYAML==5.4.1",
            "urllib3==1.26.19",
        ),
        "package.json": ('"lodash": "4.17.21"',),
    }
    for rel, needles in expected.items():
        original = (root / rel).read_text(encoding="utf-8")
        updated, findings = fix_text(rel, original)
        assert findings, rel
        for needle in needles:
            assert needle in updated, (rel, needle)
        again, more = fix_text(rel, updated)
        assert more == []
        assert again == updated

    ok_text = (root / "src/ok.py").read_text(encoding="utf-8")
    unchanged, none = fix_text("src/ok.py", ok_text)
    assert none == []
    assert unchanged == ok_text


def test_area_src_still_includes_root_manifests():
    findings, _fixes = scan_and_fix(default_fixture_path(), area="src")
    paths = " ".join(item.get("path", "") for item in findings)
    assert "requirements.txt" in paths
    assert "package.json" in paths
    assert "src/ok.py" not in paths
    assert Path(default_fixture_path()).is_dir()
