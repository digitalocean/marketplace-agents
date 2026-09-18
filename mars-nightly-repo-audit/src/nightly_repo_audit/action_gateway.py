"""Action Gateway (do_actions MCP) helpers for opening draft GitHub PRs."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

DO_ACTIONS_SERVER_NAME = "do_actions"

# Nix AG catalog id (Wave 1 handoff). Invoked via MCP meta tool action_invoke.
GITHUB_CREATE_PR_TOOL_ID = "github_create_pull_request"
ACTION_INVOKE_TOOL = "action_invoke"
ACTION_SEARCH_TOOL = "action_search"

_CREATE_PR_RE = re.compile(r"(create[_-]?pull[_-]?request|open[_-]?pull[_-]?request)", re.I)


@dataclass(frozen=True)
class McpServerConfig:
    name: str
    transport: str
    url: str
    headers: dict[str, str]


@dataclass(frozen=True)
class OpenPrResult:
    ok: bool
    pr_url: str = ""
    pr_number: int = 0
    error_message: str = ""
    tool_name: str = ""


class McpClientError(Exception):
    """Raised when MCP HTTP transport fails."""


class McpHttpClient:
    """Minimal MCP HTTP JSON-RPC client (initialize + tools/list + tools/call)."""

    def __init__(self, config: McpServerConfig) -> None:
        self._config = config
        self._request_id = 0
        self._initialized = False

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", **self._config.headers}
        req = urllib.request.Request(
            self._config.url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise McpClientError(
                f"MCP HTTP {exc.code} from {self._config.name}: {detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise McpClientError(
                f"Could not reach Action Gateway MCP ({self._config.name}): {exc.reason}"
            ) from exc

        return _parse_mcp_response(raw)

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        data = self._post(payload)
        if "error" in data:
            err = data["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise McpClientError(f"MCP {method} failed: {msg}")
        result = data.get("result")
        return result if isinstance(result, dict) else {}

    def initialize(self) -> None:
        if self._initialized:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "nightly-repo-audit", "version": "0.1.0"},
            },
        )
        # MCP lifecycle: acknowledge initialize before tools/list or tools/call.
        self._post(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
        self._initialized = True

    def list_tools(self) -> list[dict[str, Any]]:
        self.initialize()
        result = self._rpc("tools/list")
        tools = result.get("tools")
        return list(tools) if isinstance(tools, list) else []

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        return self._rpc("tools/call", {"name": name, "arguments": arguments})


# Injectable factory for offline tests.
_mcp_client_factory: Callable[[McpServerConfig], McpHttpClient] | None = None


def set_mcp_client_factory(
    factory: Callable[[McpServerConfig], McpHttpClient] | None,
) -> None:
    global _mcp_client_factory
    _mcp_client_factory = factory


def _make_client(config: McpServerConfig) -> McpHttpClient:
    if _mcp_client_factory is not None:
        return _mcp_client_factory(config)
    return McpHttpClient(config)


def decode_harness_mcp_servers_raw(raw: str) -> str:
    """Return JSON text from HARNESS_MCP_SERVERS (plain JSON or base64-encoded JSON)."""
    trimmed = (raw or "").strip()
    if not trimmed:
        return ""
    if trimmed.startswith("["):
        return trimmed
    try:
        decoded = base64.b64decode(trimmed, validate=True).decode("utf-8").strip()
    except (ValueError, UnicodeDecodeError):
        return trimmed
    return decoded


def parse_harness_mcp_servers(raw: str | None = None) -> list[McpServerConfig]:
    """Parse HARNESS_MCP_SERVERS JSON array into validated server configs.

    Platform injects a JSON array (sometimes base64) of objects like::

        [{"name": "do_actions", "transport": "http", "url": "https://..."}]

    Invalid entries are skipped (same spirit as harness runtime).
    """
    env_raw = raw if raw is not None else os.environ.get("HARNESS_MCP_SERVERS", "")
    json_text = decode_harness_mcp_servers_raw(env_raw)
    if not json_text:
        return []

    try:
        items = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"HARNESS_MCP_SERVERS is not valid JSON: {exc}") from exc
    if not isinstance(items, list):
        raise ValueError("HARNESS_MCP_SERVERS must be a JSON array")

    seen: set[str] = set()
    configs: list[McpServerConfig] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        url = str(item.get("url") or "").strip()
        command = str(item.get("command") or "").strip()
        transport = str(item.get("transport") or "").strip().lower()
        if not transport:
            if url and not command:
                transport = "http"
            elif command and not url:
                transport = "stdio"
        if transport != "http" or not url:
            continue
        headers = item.get("headers")
        hdrs = dict(headers) if isinstance(headers, dict) else {}
        configs.append(
            McpServerConfig(
                name=name,
                transport=transport,
                url=url,
                headers={str(k): str(v) for k, v in hdrs.items()},
            )
        )
        seen.add(name)
    return configs


def get_do_actions_config(
    raw: str | None = None,
) -> McpServerConfig | None:
    for cfg in parse_harness_mcp_servers(raw):
        if cfg.name == DO_ACTIONS_SERVER_NAME:
            return cfg
    return None


def _tool_names(tools: list[dict[str, Any]]) -> set[str]:
    return {str(t.get("name") or "") for t in tools if t.get("name")}


def has_action_invoke(tools: list[dict[str, Any]]) -> bool:
    return ACTION_INVOKE_TOOL in _tool_names(tools)


def build_create_pr_arguments(
    *,
    owner: str,
    repo_name: str,
    title: str,
    body: str,
    branch: str,
    ref: str,
) -> dict[str, Any]:
    return {
        "owner": owner,
        "repo": repo_name,
        "title": title,
        "body": body,
        "head": branch,
        "base": ref or "main",
        "draft": True,
    }


def build_action_invoke_payload(
    *,
    owner: str,
    repo_name: str,
    title: str,
    body: str,
    branch: str,
    ref: str,
) -> dict[str, Any]:
    """Action Gateway meta invoke payload (ACTION-GATEWAY-CONNECTIONS.md)."""
    return {
        "rationale": "Open draft PR after human approve",
        "tools": [
            {
                "tool": GITHUB_CREATE_PR_TOOL_ID,
                "arguments": build_create_pr_arguments(
                    owner=owner,
                    repo_name=repo_name,
                    title=title,
                    body=body,
                    branch=branch,
                    ref=ref,
                ),
            }
        ],
    }


def split_repo_slug(repo: str) -> tuple[str, str]:
    slug = (repo or "").strip().strip("/")
    if "/" not in slug:
        raise ValueError(f"repo must be owner/name, got {repo!r}")
    owner, name = slug.split("/", 1)
    owner = owner.strip()
    name = name.strip()
    if not owner or not name:
        raise ValueError(f"repo must be owner/name, got {repo!r}")
    return owner, name


def _extract_pr_fields(result: dict[str, Any]) -> tuple[str, int]:
    """Best-effort parse PR number/url from MCP tool result."""
    pr_url = ""
    pr_number = 0

    def _walk(obj: Any) -> None:
        nonlocal pr_url, pr_number
        if isinstance(obj, dict):
            for key, val in obj.items():
                key_l = str(key).lower()
                if key_l in {"html_url", "pr_url", "url"} and isinstance(val, str):
                    if "github.com" in val and "/pull/" in val:
                        pr_url = val
                if key_l in {"number", "pr_number"} and isinstance(val, int):
                    pr_number = val
                _walk(val)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                    _walk(parsed)
                except json.JSONDecodeError:
                    if "github.com" in text and "/pull/" in text:
                        pr_url = text.strip()
    _walk(result)
    if pr_url and not pr_number:
        m = re.search(r"/pull/(\d+)", pr_url)
        if m:
            pr_number = int(m.group(1))
    return pr_url, pr_number


def open_draft_pr(
    *,
    repo: str,
    ref: str,
    branch: str,
    title: str,
    body: str,
    harness_mcp_servers: str | None = None,
) -> OpenPrResult:
    """Open a draft PR via do_actions MCP. Fail closed on missing gateway or errors."""
    cfg = get_do_actions_config(harness_mcp_servers)
    if cfg is None:
        return OpenPrResult(
            ok=False,
            error_message=(
                "Could not open the PR: Action Gateway (do_actions) is not wired on "
                "this agent. Your admin needs do.actions in the spec plus a GitHub "
                "Connection."
            ),
        )

    try:
        owner, repo_name = split_repo_slug(repo)
    except ValueError as exc:
        return OpenPrResult(ok=False, error_message=str(exc))

    try:
        client = _make_client(cfg)
        tools = client.list_tools()
        if not has_action_invoke(tools):
            return OpenPrResult(
                ok=False,
                error_message=(
                    "Could not open the PR: Action Gateway is connected but action_invoke "
                    "is not available. Check do.actions in the spec and permissions.rules "
                    "mcp allow."
                ),
            )

        invoke_payload = build_action_invoke_payload(
            owner=owner,
            repo_name=repo_name,
            title=title,
            body=body,
            branch=branch,
            ref=ref,
        )
        raw_result = client.call_tool(ACTION_INVOKE_TOOL, invoke_payload)
        pr_url, pr_number = _extract_pr_fields(raw_result)
        if not pr_url and not pr_number:
            return OpenPrResult(
                ok=False,
                error_message=(
                    "GitHub accepted the call but I could not read a PR URL back. "
                    "Check Action Gateway logs and the GitHub Connection."
                ),
                tool_name=GITHUB_CREATE_PR_TOOL_ID,
            )
        if not pr_url and pr_number:
            pr_url = f"https://github.com/{owner}/{repo_name}/pull/{pr_number}"
        return OpenPrResult(
            ok=True,
            pr_url=pr_url,
            pr_number=pr_number,
            tool_name=GITHUB_CREATE_PR_TOOL_ID,
        )
    except McpClientError as exc:
        return OpenPrResult(ok=False, error_message=str(exc))
    except Exception as exc:  # noqa: BLE001 — fail closed with prose
        return OpenPrResult(
            ok=False,
            error_message=f"Could not open the PR: {exc}",
        )


def _parse_mcp_response(raw: str) -> dict[str, Any]:
    """Parse MCP HTTP body (JSON or SSE data lines)."""
    trimmed = raw.strip()
    if not trimmed:
        return {}
    if trimmed.startswith("{"):
        data = json.loads(trimmed)
        return data if isinstance(data, dict) else {}
    # SSE: take the last data: line with JSON
    for line in reversed(trimmed.splitlines()):
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                data = json.loads(payload)
                return data if isinstance(data, dict) else {}
    raise McpClientError("MCP response was not valid JSON")
