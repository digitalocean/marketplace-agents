"""Chat URL clones a repo, commits cleanup, and pushes before the PR ask."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from nightly_repo_audit.checkout import CheckoutError, set_git_overrides
from nightly_repo_audit.graph import compile_graph
from nightly_repo_audit.repo_scan import default_fixture_path


def _offline(monkeypatch):
    monkeypatch.delenv("HARNESS_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("ALLOW_NET", "0")


def _git_copy(src: Path) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="audit-remote-"))
    shutil.copytree(src, dest, dirs_exist_ok=True)
    subprocess.check_call(["git", "init"], cwd=dest)
    subprocess.check_call(["git", "add", "-A"], cwd=dest)
    subprocess.check_call(
        [
            "git",
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=t",
            "commit",
            "-m",
            "init",
        ],
        cwd=dest,
    )
    return dest


def test_url_commits_and_pushes_before_ask(monkeypatch):
    _offline(monkeypatch)
    checkout = _git_copy(default_fixture_path())
    pushed: list[tuple[str, str]] = []

    def _clone(repo: str, ref: str) -> Path:
        assert repo == "digitalocean/marketplace-agents"
        assert ref == "main"
        return checkout

    def _push(_path: Path, branch: str, repo: str) -> None:
        pushed.append((branch, repo))

    set_git_overrides(clone=_clone, push=_push)
    try:
        g = compile_graph(checkpointer=MemorySaver())
        cfg = {"configurable": {"thread_id": "audit-remote"}}
        planned = g.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="audit https://github.com/digitalocean/marketplace-agents"
                    )
                ]
            },
            cfg,
        )
        assert planned["__interrupt__"][0].value.get("title") == "Start repo audit?"
        asked = g.invoke(Command(resume="approve"), cfg)
        assert "__interrupt__" in asked
        assert asked["__interrupt__"][0].value.get("title") == "Open cleanup PR?"
        assert pushed == [
            ("nightly/cleanup-src", "digitalocean/marketplace-agents")
        ]
        log = subprocess.check_output(
            ["git", "log", "-1", "--format=%s"], cwd=checkout, text=True
        )
        assert "nightly cleanup" in log.lower()
        assert not (checkout / "legacy" / "old_module.py").exists()
    finally:
        set_git_overrides(clone=None, push=None)


def test_push_failure_is_shown_and_skips_ask(monkeypatch):
    _offline(monkeypatch)
    checkout = _git_copy(default_fixture_path())

    def _push(*_args) -> None:
        raise CheckoutError("authentication failed")

    set_git_overrides(clone=lambda _repo, _ref: checkout, push=_push)
    try:
        g = compile_graph(checkpointer=MemorySaver())
        cfg = {"configurable": {"thread_id": "audit-push-fail"}}
        g.invoke(
            {
                "messages": [
                    HumanMessage(content="Audit acme/widgets on main, area src")
                ]
            },
            cfg,
        )
        final = g.invoke(Command(resume="approve"), cfg)
        assert "__interrupt__" not in final
        assert final.get("status") == "error"
        text = " ".join(getattr(m, "content", "") for m in final.get("messages") or [])
        assert "authentication failed" in text.lower()
    finally:
        set_git_overrides(clone=None, push=None)
