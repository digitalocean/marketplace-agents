"""OPTIONAL Box Mount (private preview) mode.

Only used when secret ``BOX_MOUNT_BINARY_URL`` is set. The default Box path is
the REST API (:mod:`box_doc_summarizer.box_api`). When enabled, this module
downloads the binary, writes the JWT config as 600-mode files, mounts the
folder at ``BOX_MOUNT_PATH`` and polls ``box-mount status`` until synced.
"""

from __future__ import annotations

import os
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MountResult:
    ok: bool
    state: str  # mounted | reused | blocked | skipped
    path: str = ""
    message: str = ""


def mount_enabled() -> bool:
    return bool(os.environ.get("BOX_MOUNT_BINARY_URL", "").strip())


def default_binary_path() -> Path:
    return Path(os.path.expanduser("~/.local/bin/box-mount"))


def mount_path() -> str:
    return os.environ.get("BOX_MOUNT_PATH", "/workspace/box")


def _run(binary: str, *args: str, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run([binary, *args], capture_output=True, text=True, timeout=timeout)


def _status_synced(out: str, path: str) -> bool:
    low = out.lower()
    if "no mount found" in low:
        return False
    return path.lower() in low and any(w in low for w in ("synced", "idle", "ready", "up to date", "mounted"))


def _download_binary(url: str, dest: Path) -> None:
    """Download the preview build. Accepts a raw ELF or a ``.tar.gz`` holding ``box-mount``
    (Box ships ``box-mount-<ver>-linux-<arch>.tar.gz``). Optional ``BOX_MOUNT_SHA256``
    verifies the downloaded artifact."""
    import hashlib
    import io
    import tarfile

    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=600, allow_redirects=True)
    resp.raise_for_status()
    data = resp.content
    want = os.environ.get("BOX_MOUNT_SHA256", "").strip().lower()
    if want and hashlib.sha256(data).hexdigest() != want:
        raise RuntimeError("Box Mount download failed SHA256 check.")
    if data[:2] == b"\x1f\x8b":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            member = next(
                (m for m in tar.getmembers() if m.isfile() and Path(m.name).name == "box-mount"),
                None,
            )
            if member is None:
                raise RuntimeError("Box Mount archive has no box-mount binary.")
            data = tar.extractfile(member).read()
    if data[:4] != b"\x7fELF":
        raise RuntimeError("Box Mount download is not a Linux binary (check the direct-download URL).")
    dest.write_bytes(data)
    os.chmod(dest, stat.S_IRWXU)


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o600)


def ensure_mount(folder_id: str, *, binary: str | None = None, home: str | None = None) -> MountResult:
    if not mount_enabled() and binary is None:
        return MountResult(ok=False, state="skipped", message="Box Mount not configured.")
    target = mount_path()
    bin_path = Path(binary) if binary else default_binary_path()
    try:
        if not bin_path.exists():
            _download_binary(os.environ["BOX_MOUNT_BINARY_URL"], bin_path)
        status = _run(str(bin_path), "status")
        if status.returncode == 0 and _status_synced(status.stdout, target):
            return MountResult(ok=True, state="reused", path=target)

        jwt_json = os.environ.get("BOX_JWT_CONFIG_JSON", "").strip()
        if not jwt_json:
            return MountResult(ok=False, state="blocked", message="BOX_JWT_CONFIG_JSON is not set.")
        base = Path(home or os.path.expanduser("~")) / ".box-mount"
        jwt_path = base / "jwt-config.json"
        _write_private(jwt_path, jwt_json)
        _write_private(
            base / "box-config.json",
            '{"auth_type": "jwt", "jwt_config_path": "%s"}' % jwt_path,
        )
        Path(target).mkdir(parents=True, exist_ok=True)
        res = _run(str(bin_path), "mount", target, str(folder_id))
        if res.returncode != 0:
            return MountResult(ok=False, state="blocked", message=(res.stderr or res.stdout or "mount failed").strip()[:300])
        deadline = time.time() + float(os.environ.get("BOX_MOUNT_SYNC_TIMEOUT_S", "300"))
        while time.time() < deadline:
            st = _run(str(bin_path), "status")
            if st.returncode == 0 and _status_synced(st.stdout, target):
                return MountResult(ok=True, state="mounted", path=target)
            time.sleep(2)
        return MountResult(ok=False, state="blocked", message="Box Mount initial sync timed out.")
    except Exception as exc:  # noqa: BLE001
        return MountResult(ok=False, state="blocked", message=f"{type(exc).__name__}: {exc}"[:300])
