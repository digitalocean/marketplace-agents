"""Clone a GitHub repo and publish a local branch before opening a PR."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

COMMIT_NAME = "Nightly Repo Audit"
COMMIT_EMAIL = "nightly-repo-audit@users.noreply.github.com"

CloneFn = Callable[[str, str], Path]
PushFn = Callable[[Path, str, str], None]

_clone_override: CloneFn | None = None
_push_override: PushFn | None = None


class CheckoutError(Exception):
    """Clone, commit, or push failed. Message is safe to show in chat."""


def set_git_overrides(
    *,
    clone: CloneFn | None = None,
    push: PushFn | None = None,
) -> None:
    """Test hook. Pass None to restore the real git commands."""
    global _clone_override, _push_override
    _clone_override = clone
    _push_override = push


def is_remote_repo(repo: str) -> bool:
    slug = (repo or "").strip().strip("/")
    if slug in {"", "local/sample"} or slug.count("/") != 1:
        return False
    owner, name = slug.split("/", 1)
    if not owner or not name or owner.lower() in {"http:", "https:", "github.com"}:
        return False
    return True


def github_token() -> str:
    return (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()


def _redact(text: str) -> str:
    token = github_token()
    cleaned = (text or "").strip()
    if token:
        cleaned = cleaned.replace(token, "***")
    return cleaned[-500:]


def _run(args: list[str], cwd: Path | None = None, timeout: int = 120) -> str:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "Never"
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CheckoutError(f"git timed out: {' '.join(args[:3])}") from exc
    except OSError as exc:
        raise CheckoutError(f"git is not available: {exc}") from exc
    if proc.returncode != 0:
        detail = _redact(proc.stderr or proc.stdout or "git failed")
        raise CheckoutError(detail or "git failed")
    return proc.stdout


def _authenticated_url(repo: str) -> str:
    slug = repo.strip().strip("/")
    token = github_token()
    if token:
        return f"https://x-access-token:{token}@github.com/{slug}.git"
    return f"https://github.com/{slug}.git"


def clone_github_repo(repo: str, ref: str) -> Path:
    """Shallow-clone ``owner/name`` at ``ref`` into a temp directory."""
    if _clone_override is not None:
        return _clone_override(repo, ref)
    if not is_remote_repo(repo):
        raise CheckoutError(f"repo must be owner/name, got {repo!r}")
    url = _authenticated_url(repo)
    branch = (ref or "main").strip() or "main"
    dest = Path(tempfile.mkdtemp(prefix="nightly-audit-"))
    try:
        _run(["git", "clone", "--depth", "1", "--branch", branch, url, str(dest)])
        return dest
    except CheckoutError as first:
        # --branch fails for SHAs and some refs. Clone the default branch, then fetch.
        shutil.rmtree(dest, ignore_errors=True)
        dest = Path(tempfile.mkdtemp(prefix="nightly-audit-"))
        try:
            _run(["git", "clone", "--depth", "1", url, str(dest)])
            _run(["git", "fetch", "--depth", "1", "origin", branch], cwd=dest)
            _run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=dest)
        except CheckoutError as second:
            raise CheckoutError(
                f"Could not clone {repo} @ {branch}. {second}"
            ) from first
        return dest


def commit_branch(checkout: Path, branch: str, message: str) -> None:
    """Create ``branch`` and commit the working tree. Fails when nothing changed."""
    if not branch.strip():
        raise CheckoutError("Refusing to commit without a branch name.")
    _run(["git", "checkout", "-B", branch], cwd=checkout)
    _run(["git", "add", "-A"], cwd=checkout)
    quiet = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=checkout,
        capture_output=True,
        text=True,
        check=False,
    )
    if quiet.returncode == 0:
        raise CheckoutError("No file changes to commit.")
    _run(
        [
            "git",
            "-c",
            f"user.email={COMMIT_EMAIL}",
            "-c",
            f"user.name={COMMIT_NAME}",
            "commit",
            "-m",
            message,
        ],
        cwd=checkout,
    )


def push_branch(checkout: Path, branch: str, repo: str) -> None:
    """Push ``branch`` to origin. Uses GITHUB_TOKEN or GH_TOKEN when set."""
    if _push_override is not None:
        _push_override(checkout, branch, repo)
        return
    token = github_token()
    try:
        if token:
            remote = _authenticated_url(repo)
            _run(
                ["git", "push", remote, f"HEAD:refs/heads/{branch}"],
                cwd=checkout,
            )
        else:
            _run(["git", "push", "-u", "origin", branch], cwd=checkout)
    except CheckoutError as exc:
        if token:
            raise
        raise CheckoutError(
            f"{exc} Push needs GITHUB_TOKEN or GH_TOKEN with contents write on {repo}."
        ) from exc


def publish_branch(checkout: Path, *, branch: str, message: str, repo: str) -> None:
    commit_branch(checkout, branch, message)
    push_branch(checkout, branch, repo)
