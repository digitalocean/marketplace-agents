# Nightly Repo Security Scan

## Summary

A security pass that fixes what it finds, then waits for your yes.
Application bugs and vulnerable dependency pins become one draft PR.

## Description

Nightly Repo Security Scan is a repo security agent for eng leads and maintainers who want a scheduled fix pass without surprise merges or force-pushes. Point it at a repo slice; it plans one area, scans for application problems, bugs, and dependency pins that are still below a patched release, applies those fixes, and drafts a single pull request for you to review.

Use it when known-bad patterns and stale dependency pins keep surviving review and you want a consistent pass that proposes a draft PR and stops. Approve opens a real draft PR when GitHub is connected; deny discards the open and keeps the findings and the patch as artifacts. Empty nights stay quiet: no ask, no noise.

The draft includes the patch: hardcoded credentials moved to the environment, unsafe loaders and disabled TLS verification corrected, interpolated SQL parameterized, unsafe eval replaced, off-by-one indexes corrected, debug mode turned off, and bundled vulnerable pins bumped to a same-major patched release. Grok 4.7 writes a short review note when inference is configured. The fixes themselves do not depend on the model.

Ideal for a nightly or weekly pass on a service you own, or a pre-release check that should end in a reviewable draft rather than an unchecked commit.

### Why use it

- One focused security-fix PR draft per run, not a flood of drive-by commits
- Fixes application problems, bugs, and vulnerable dependency pins before the ask
- Human approval before any PR opens; deny keeps work local
- Approve opens a **draft** PR only: never merges or force-pushes
- Quiet when clean: empty findings mean no interrupt and no noise
- Scoped to security fixes, not product-feature rewrites
- Runs on Grok 4.7 for the review note
- Action Gateway + GitHub Connection open real draft PRs when configured
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- Grok 4.7 (`HARNESS_INFERENCE_MODEL=grok-4.7`)
- GitHub Connection + Action Gateway to open draft PRs on Approve
- Repo access for the target `owner/name` and ref you want scanned
