# Nightly Repo Audit

## Summary

A hygiene pass that drafts one cleanup PR, then waits for your yes.
TODOs, dead legacy, and CI fluff get reviewed; nothing merges without you.

## Description

Nightly Repo Audit is a repo-hygiene agent for eng leads and maintainers who want scheduled cleanup without surprise merges or force-pushes. Point it at a repo slice; it plans one audit area, scans for TODOs, dead legacy, and CI fluff, then drafts a single cleanup PR (title, body, branch, and patch summary) for you to review.

Use it when your backlog of “we should clean that up” keeps growing and you want a consistent pass that proposes a draft PR and stops. Approve opens a real draft PR when GitHub is connected; deny discards the open and keeps the findings as artifacts. Empty nights stay quiet: no ask, no noise.

Ideal for weekly or nightly hygiene on a service you own, pre-release cleanup of a hot path, or giving maintainers a reviewable PR instead of another unchecked bot commit.

### Why use it

- One focused cleanup PR draft per run, not a flood of drive-by commits
- Human approval before any PR opens; deny keeps work local
- Approve opens a **draft** PR only: never merges or force-pushes
- Quiet when clean: empty findings mean no interrupt and no noise
- Scoped to hygiene (TODOs, legacy, CI fluff), not product-feature rewrites
- Action Gateway + GitHub Connection open real draft PRs when configured
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- Strong coding / reasoning models work best (e.g. `deepseek-v4-pro` or comparable)
- GitHub Connection + Action Gateway to open draft PRs on Approve
- Repo access for the target `owner/name` and ref you want audited
