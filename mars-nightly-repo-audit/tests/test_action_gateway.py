"""Action Gateway MCP parsing and open-draft-PR (offline mocks)."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from nightly_repo_audit.action_gateway import (
    McpHttpClient,
    McpServerConfig,
    decode_harness_mcp_servers_raw,
    get_do_actions_config,
    open_draft_pr,
    parse_harness_mcp_servers,
    resolve_create_pr_tool,
    set_mcp_client_factory,
    split_repo_slug,
)


class _FakeMcpClient:
    def __init__(self, config: McpServerConfig) -> None:
        self.config = config
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "do.actions.github.create_pull_request"}]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "html_url": (
                                "https://github.com/acme/widgets/pull/42"
                            ),
                            "number": 42,
                        }
                    ),
                }
            ]
        }


@pytest.fixture(autouse=True)
def _reset_mcp_factory():
    set_mcp_client_factory(None)
    yield
    set_mcp_client_factory(None)


def test_decode_plain_and_base64_harness_mcp_servers():
    plain = '[{"name":"do_actions","url":"https://ag.internal/mcp"}]'
    assert decode_harness_mcp_servers_raw(plain) == plain
    encoded = base64.b64encode(plain.encode()).decode()
    assert decode_harness_mcp_servers_raw(encoded) == plain


def test_parse_harness_mcp_servers_do_actions():
    raw = json.dumps(
        [
            {
                "name": "do_actions",
                "transport": "http",
                "url": "https://ag.vpc.internal/mcp",
            },
            {"name": "other", "command": "echo", "transport": "stdio"},
        ]
    )
    configs = parse_harness_mcp_servers(raw)
    assert len(configs) == 1
    assert configs[0].name == "do_actions"
    assert configs[0].url == "https://ag.vpc.internal/mcp"


def test_get_do_actions_config_from_env(monkeypatch):
    payload = json.dumps(
        [{"name": "do_actions", "url": "https://ag.example/mcp"}]
    )
    monkeypatch.setenv("HARNESS_MCP_SERVERS", payload)
    cfg = get_do_actions_config()
    assert cfg is not None
    assert cfg.name == "do_actions"


def test_resolve_create_pr_tool_prefers_narrow_id():
    tools = [
        {"name": "do.actions.github.list_repos"},
        {"name": "do.actions.github.create_pull_request"},
        {"name": "create_pull_request"},
    ]
    assert (
        resolve_create_pr_tool(tools) == "do.actions.github.create_pull_request"
    )


def test_resolve_create_pr_tool_falls_back_to_pattern():
    tools = [{"name": "github_open_pull_request"}]
    assert resolve_create_pr_tool(tools) == "github_open_pull_request"


def test_split_repo_slug():
    assert split_repo_slug("acme/widgets") == ("acme", "widgets")
    with pytest.raises(ValueError):
        split_repo_slug("not-a-slug")


def test_open_draft_pr_missing_gateway():
    result = open_draft_pr(
        repo="acme/widgets",
        ref="main",
        branch="nightly/cleanup",
        title="chore: cleanup",
        body="body",
        harness_mcp_servers="[]",
    )
    assert not result.ok
    assert "do_actions" in result.error_message


def test_open_draft_pr_success_mocked(monkeypatch):
    fake = _FakeMcpClient(
        McpServerConfig("do_actions", "http", "https://ag.example/mcp", {})
    )
    set_mcp_client_factory(lambda _cfg: fake)  # noqa: ARG005
    monkeypatch.setenv("ALLOW_NET", "0")

    result = open_draft_pr(
        repo="acme/widgets",
        ref="main",
        branch="nightly/cleanup-src",
        title="chore: nightly cleanup",
        body="## cleanup",
        harness_mcp_servers=json.dumps(
            [{"name": "do_actions", "url": "https://ag.example/mcp"}]
        ),
    )
    assert result.ok
    assert result.pr_number == 42
    assert "github.com/acme/widgets/pull/42" in result.pr_url
    assert result.tool_name == "do.actions.github.create_pull_request"
    assert fake.calls[0][1]["draft"] is True
    assert fake.calls[0][1]["head"] == "nightly/cleanup-src"


def test_open_draft_pr_no_matching_tool(monkeypatch):
    class _NoPrToolClient:
        def list_tools(self) -> list[dict[str, Any]]:
            return [{"name": "do.actions.github.list_repos"}]

        def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            raise AssertionError("should not call")

    set_mcp_client_factory(lambda _cfg: _NoPrToolClient())  # noqa: ARG005
    result = open_draft_pr(
        repo="acme/widgets",
        ref="main",
        branch="nightly/cleanup",
        title="chore: cleanup",
        body="body",
        harness_mcp_servers=json.dumps(
            [{"name": "do_actions", "url": "https://ag.example/mcp"}]
        ),
    )
    assert not result.ok
    assert "no github" in result.error_message.lower()
