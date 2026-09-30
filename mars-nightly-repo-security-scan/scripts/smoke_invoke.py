#!/usr/bin/env python3
"""Smoke invoke for Nightly Repo Security Scan.

Runs the fixture path offline (no API key). Exercises empty skip and
ask→deny, then ask→approve with a mocked Action Gateway.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from nightly_repo_security_scan.action_gateway import set_mcp_client_factory  # noqa: E402
from nightly_repo_security_scan.graph import compile_graph  # noqa: E402
from nightly_repo_security_scan.llm import harness_env_available, resolve_llm_env  # noqa: E402
from nightly_repo_security_scan.security_scan import default_fixture_path  # noqa: E402


class _SmokeApproveMcpClient:
    def list_tools(self):
        return [{"name": "action_invoke"}, {"name": "action_search"}]

    def call_tool(self, name, arguments):
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "html_url": "https://github.com/local/sample/pull/1",
                            "number": 1,
                        }
                    ),
                }
            ]
        }


def main() -> int:
    print("=== Nightly Repo Security Scan smoke ===")
    os.environ.setdefault("ALLOW_NET", "0")
    os.environ.setdefault("HARNESS_INFERENCE_MODEL", "grok-4.7")
    resolved = resolve_llm_env()
    print(
        json.dumps(
            {
                "base_url": resolved["base_url"],
                "model": resolved["model"],
                "api_key_set": bool(resolved["api_key"]),
                "prefer": "HARNESS_INFERENCE_* then OPENAI_*; default grok-4.7",
            },
            indent=2,
        )
    )
    if not harness_env_available():
        print(
            "\nNo HARNESS_INFERENCE_API_KEY / OPENAI_API_KEY — "
            "using fixtures/sample_repo (deterministic offline)."
        )

    fixture = str(default_fixture_path())
    if not Path(fixture).is_dir():
        print(f"SMOKE FAIL: missing fixture {fixture}", file=sys.stderr)
        return 1

    g_empty = compile_graph()
    empty = g_empty.invoke(
        {
            "repo": "local/sample",
            "ref": "main",
            "fixture_path": fixture,
            "force_empty": True,
        }
    )
    print("\n--- empty path ---")
    print("status:", empty.get("status"))
    if empty.get("status") != "empty" or "__interrupt__" in empty:
        print("SMOKE FAIL: empty path should skip ask", file=sys.stderr)
        return 1

    g = compile_graph(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "smoke-security"}}
    mid = g.invoke(
        {
            "repo": "local/sample",
            "ref": "main",
            "trigger": "manual",
            "area_hint": "src",
            "fixture_path": fixture,
        },
        cfg,
    )
    print("\n--- ask interrupt ---")
    if "__interrupt__" not in mid:
        print("SMOKE FAIL: expected ask interrupt on fixture bait", file=sys.stderr)
        return 1
    payload = mid["__interrupt__"][0].value
    print("title:", payload.get("title"))
    print("choices:", payload.get("choices"))
    if payload.get("title") != "Open security fix PR?":
        print("SMOKE FAIL: bad ask title", file=sys.stderr)
        return 1
    snap = g.get_state(cfg).values
    body = snap.get("pr_body_md") or ""
    if "yaml.safe_load" not in body or "requests==2.32.3" not in body:
        print("SMOKE FAIL: draft patch missing fixes", file=sys.stderr)
        return 1

    final = g.invoke(Command(resume="deny"), cfg)
    print("\n--- after deny ---")
    print("status:", final.get("status"))
    if final.get("status") != "denied" or final.get("pr_url"):
        print("SMOKE FAIL: deny should yield denied + no pr_url", file=sys.stderr)
        return 1

    os.environ["HARNESS_MCP_SERVERS"] = json.dumps(
        [{"name": "do_actions", "url": "https://ag.smoke.example/mcp"}]
    )
    set_mcp_client_factory(lambda _cfg: _SmokeApproveMcpClient())  # noqa: ARG005
    g2 = compile_graph(checkpointer=MemorySaver())
    cfg2 = {"configurable": {"thread_id": "smoke-security-approve"}}
    mid2 = g2.invoke(
        {
            "repo": "local/sample",
            "ref": "main",
            "trigger": "manual",
            "area_hint": "src",
            "fixture_path": fixture,
        },
        cfg2,
    )
    if "__interrupt__" not in mid2:
        print("SMOKE FAIL: expected ask before approve", file=sys.stderr)
        return 1
    approved = g2.invoke(Command(resume="approve"), cfg2)
    print("\n--- approve path (mock AG) ---")
    print("status:", approved.get("status"))
    print("pr_url:", approved.get("pr_url"))
    if approved.get("status") != "opened" or not approved.get("pr_url"):
        print("SMOKE FAIL: approve should open draft PR via mocked AG", file=sys.stderr)
        return 1
    set_mcp_client_factory(None)

    print("\nSMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
