import io
import os
import stat
import tarfile

import pytest

from box_doc_summarizer import box_mount

FAKE = """#!/bin/sh
STATE="$FAKE_BM_STATE"
case "$1" in
  status)
    if [ -f "$STATE" ]; then echo "$(cat "$STATE") synced"; else echo "No mount found."; fi ;;
  mount)
    [ -n "$FAKE_BM_FAIL" ] && { echo "auth error" >&2; exit 3; }
    echo "$2" > "$STATE"; echo "mounted $2 $3" ;;
  unmount) rm -f "$STATE" ;;
esac
"""


@pytest.fixture
def fake_bin(tmp_path, monkeypatch):
    b = tmp_path / "bin" / "box-mount"
    b.parent.mkdir()
    b.write_text(FAKE)
    b.chmod(0o755)
    monkeypatch.setenv("FAKE_BM_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("BOX_MOUNT_PATH", str(tmp_path / "box"))
    monkeypatch.setenv("BOX_MOUNT_BINARY_URL", "https://example.invalid/box-mount.tar.gz")
    return b


def test_mount_writes_private_config(fake_bin, tmp_path, monkeypatch):
    monkeypatch.setenv("BOX_JWT_CONFIG_JSON", '{"x": 1}')
    res = box_mount.ensure_mount("123", binary=str(fake_bin), home=str(tmp_path / "home"))
    assert res.ok and res.state == "mounted"
    jwt_file = tmp_path / "home" / ".box-mount" / "jwt-config.json"
    assert stat.S_IMODE(os.stat(jwt_file).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(jwt_file.parent / "box-config.json").st_mode) == 0o600
    again = box_mount.ensure_mount("123", binary=str(fake_bin), home=str(tmp_path / "home"))
    assert again.state == "reused"


def test_mount_blocked_without_jwt(fake_bin, tmp_path):
    res = box_mount.ensure_mount("123", binary=str(fake_bin), home=str(tmp_path / "home"))
    assert not res.ok and res.state == "blocked" and "BOX_JWT_CONFIG_JSON" in res.message


def test_mount_failure_blocked(fake_bin, tmp_path, monkeypatch):
    monkeypatch.setenv("BOX_JWT_CONFIG_JSON", "{}")
    monkeypatch.setenv("FAKE_BM_FAIL", "1")
    res = box_mount.ensure_mount("123", binary=str(fake_bin), home=str(tmp_path / "home"))
    assert res.state == "blocked" and "auth error" in res.message


def test_skipped_when_not_configured():
    assert box_mount.ensure_mount("1").state == "skipped"


def _tgz(payload: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("box-mount")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def test_download_extracts_tarball_and_checks_sha(tmp_path, monkeypatch):
    import hashlib

    import requests

    elf = b"\x7fELF" + b"\0" * 32
    blob = _tgz(elf)

    class R:
        content = blob

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    dest = tmp_path / "bin" / "box-mount"
    monkeypatch.setenv("BOX_MOUNT_SHA256", hashlib.sha256(blob).hexdigest())
    box_mount._download_binary("https://x", dest)
    assert dest.read_bytes() == elf and stat.S_IMODE(os.stat(dest).st_mode) == 0o700
    monkeypatch.setenv("BOX_MOUNT_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="SHA256"):
        box_mount._download_binary("https://x", dest)


def test_download_rejects_html(tmp_path, monkeypatch):
    import requests

    class R:
        content = b"<html>login</html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    with pytest.raises(RuntimeError, match="not a Linux binary"):
        box_mount._download_binary("https://x", tmp_path / "bm")
