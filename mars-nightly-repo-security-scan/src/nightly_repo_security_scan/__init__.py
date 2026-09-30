"""Nightly Repo Security Scan: scan a repo slice, fix findings, ask before a draft PR."""

from nightly_repo_security_scan.graph import build_graph, graph

__all__ = ["build_graph", "graph"]
