"""Action Gateway MCP parsing and open-draft-PR (offline mocks)."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from nightly_repo_security_scan.action_gateway import (
    ACTION_INVOKE_TOOL,
    GITHUB_CREATE_PR_TOOL_ID,
    McpServerConfig,
    build_action_invoke_payload,
    decode_harness_mcp_servers_raw,
    get_do_actions_config,
    has_action_invoke,
    open_draft_pr,
    parse_harness_mcp_servers,
    set_mcp_client_factory,
    split_repo_slug,
)


class _FakeMcpClient:
    def __init__(self, config: McpServerConfig) -> None:
        self.config = config
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "action_search"}, {"name": ACTION_INVOKE_TOOL}]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "html_url": "https://github.com/acme/widgets/pull/42",
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
    monkeypatch.setenv(
        "HARNESS_MCP_SERVERS",
        json.dumps([{"name": "do_actions", "url": "https://ag.example/mcp"}]),
    )
    cfg = get_do_actions_config()
    assert cfg is not None
    assert cfg.name == "do_actions"


def test_build_action_invoke_payload_is_draft():
    payload = build_action_invoke_payload(
        owner="acme",
        repo_name="widgets",
        title="fix: nightly security scan",
        body="## body",
        branch="nightly/security-src",
        ref="main",
    )
    assert payload["rationale"] == "Open draft security-fix PR after human approve"
    tool = payload["tools"][0]
    assert tool["tool"] == GITHUB_CREATE_PR_TOOL_ID
    args = tool["arguments"]
    assert args["draft"] is True
    assert args["head"] == "nightly/security-src"
    assert args["base"] == "main"
    assert has_action_invoke([{"name": ACTION_INVOKE_TOOL}])


def test_split_repo_slug():
    assert split_repo_slug("acme/widgets") == ("acme", "widgets")
    with pytest.raises(ValueError):
        split_repo_slug("not-a-slug")


def test_open_draft_pr_missing_gateway():
    result = open_draft_pr(
        repo="acme/widgets",
        ref="main",
        branch="nightly/security-src",
        title="fix: nightly security scan",
        body="body",
        harness_mcp_servers="[]",
    )
    assert not result.ok
    assert "do_actions" in result.error_message


def test_open_draft_pr_success_via_action_invoke(monkeypatch):
    fake = _FakeMcpClient(McpServerConfig("do_actions", "http", "https://ag.example/mcp", {}))
    set_mcp_client_factory(lambda _cfg: fake)  # noqa: ARG005
    monkeypatch.setenv("ALLOW_NET", "0")
    result = open_draft_pr(
        repo="acme/widgets",
        ref="main",
        branch="nightly/security-src",
        title="fix: nightly security scan",
        body="## scan",
        harness_mcp_servers=json.dumps(
            [{"name": "do_actions", "url": "https://ag.example/mcp"}]
        ),
    )
    assert result.ok
    assert result.pr_number == 42
    assert result.tool_name == GITHUB_CREATE_PR_TOOL_ID
    assert fake.calls[0][0] == ACTION_INVOKE_TOOL
    assert fake.calls[0][1]["tools"][0]["arguments"]["draft"] is True


def test_open_draft_pr_no_action_invoke():
    class _NoInvokeClient:
        def list_tools(self) -> list[dict[str, Any]]:
            return [{"name": "action_search"}]

        def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            raise AssertionError("should not call")

    set_mcp_client_factory(lambda _cfg: _NoInvokeClient())  # noqa: ARG005
    result = open_draft_pr(
        repo="acme/widgets",
        ref="main",
        branch="nightly/security-src",
        title="fix: nightly security scan",
        body="body",
        harness_mcp_servers=json.dumps(
            [{"name": "do_actions", "url": "https://ag.example/mcp"}]
        ),
    )
    assert not result.ok
    assert "action_invoke" in result.error_message
