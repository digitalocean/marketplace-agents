# Sourced Research Desk

## Summary

Turn a research question into a citation-backed brief you can trust.
Every claim carries a URL and date, and nothing leaves the room until you say so.

## Description

Sourced Research Desk is a research agent for PMs, analysts, and operators who need answers they can defend. Ask a question in plain language; the agent plans queries, gathers public sources, builds a claim table with URL and date on every factual claim, and drafts a markdown brief with citations and conflict callouts when sources disagree.

Use it when you need a decision-ready brief without babysitting browser tabs or risking an auto-post to Slack or email. Research-only runs keep the brief in artifacts by default; if you opt into outbound, a human approval gate fires before any send so you stay in control of what leaves the room.

Ideal for competitive diligence, market sizing, policy research, and any brief that has to survive a skeptical review, when “the model said so” is not enough.

### Why use it

- Citation-backed briefs with URL and date on every factual claim
- Conflict callouts when sources disagree, so you see the tension, not a smoothed narrative
- Human approval before any Slack or email send; deny keeps the brief local
- Research-only mode by default: no outbound noise, no surprise posts
- End-to-end flow from clarifying the question to a finished markdown brief
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime
- Works from a clear question; no custom RAG stack or paid search API required

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- Strong reasoning models work best (e.g. `deepseek-v4-pro` or comparable)
- Optional: Slack or email targets only if you enable outbound (approval still required)
