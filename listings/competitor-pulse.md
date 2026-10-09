logo: https://github.com/digitalocean/marketplace-agents/raw/main/listings/assets/competitor-pulse.svg

# Competitor Pulse

## Summary

Watch named competitors on the public web and get a brief only when something material changes.
Quiet when clean: counterposition notes when it matters, with your OK before notify.

## Description

Competitor Pulse is a competitive-intel agent for product and GTM operators who track a named watchlist and want signal, not crawl noise. Say “track FedEx” (or name a list); the agent fetches public modules (site, pricing, changelog, careers), diffs against your baseline, and returns an operator-grade brief in plain English with evidence URLs.

Use it when you need to stay current on rivals without living in browser tabs or drowning in “something changed” alerts. The first run establishes a baseline (“first look”); later runs surface PM-readable deltas. Notify stays off by default and only asks before outbound when you opt in and the change is marked material, so quiet nights stay quiet.

Ideal for weekly competitive reviews, launch-week monitoring, pricing and positioning watches, and any GTM rhythm where a short counterposition brief beats a raw scrape dump.

### Why use it

- Material-change briefs with evidence URLs, not a ping on every crawl
- Quiet when clean: empty or non-material diffs produce no notify ask
- First run captures a calm baseline instead of inventing a crisis
- Plain-English, operator-grade voice: never raw JSON or HTML dumps
- Human approval before notify when you opt in; deny keeps the brief local
- Public web only: no competitor logins or behind-the-wall scrapes
- Chat-native: name companies in plain language to build a watchlist
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime

### Getting Started

1. Create the agent with your inference API key. No other secrets are needed. The agent reads public pages only, so it needs network access to the sites you track.
2. Start a session and send `Track OpenAI, Anthropic, and Google` (or `track fedex`). Well-known names resolve to their public URLs right away; less common names use the inference model to find a site. The first run reads each competitor's site, pricing, changelog, and careers pages and replies with **First look — baseline established** plus a plain-English summary of each page. If it cannot match a name, it asks you to name specific companies instead of guessing.
3. To get a notify ask, mention it in the request: `Track Cursor and alert on Slack`. When the run finds a material change, it pauses at **Notify about competitor changes?** with the change count, highlights, and a notify draft. Choose **Send notify** or **Quiet — keep brief**. In this version, Send notify records the notify in the run; it does not post to Slack or email yet. First looks and quiet runs never ask.

Send `what do you do?` at any time for a short explanation of tracking, baselines, and notify.

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- Strong reasoning models work best (e.g. `deepseek-v4-pro` or comparable)
- Network egress for live public HTTP fetches (fixture path available offline)
- Optional: notify channel only if you enable outbound (approval still required on material changes)
