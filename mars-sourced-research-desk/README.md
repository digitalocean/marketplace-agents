# Sourced Research Desk

Plan → search/fetch → claim table with urls/dates → brief → ask before outbound. LangGraph agent shaped for DigitalOcean MARS (Managed Agents / Harness Runtime).

## What it does

- Clarifies a research question and plans subquestions / search queries
- Fetches allowlisted `http`/`https` sources (or uses fixture / seed URLs)
- Builds a claim table with **url + date** on every claim
- Drafts a markdown research brief with citations
- Stops for human approval before any outbound send (Slack/email channel)

## What it does not (v1)

- Auto-send Slack or email (act is a stub that records intent only)
- Login scrapes or paid search API requirements
- Vector DB / GPU research runners
- Inventing Approve flows when claims are unsourced (`status: blocked`)

## Run flow

```
intake → plan → gather → analyze → draft → **ask** → act → report
```

**Ask is skipped** when `outbound` is `none` (default / research-only), when the run is `empty` or `blocked`, or when claims fail the citation quality bar.

## Human approval

When the graph reaches **ask**, the run pauses until you **Send** (`approve`) or **Keep local only** (`deny`).

| If you… | Resume | The agent will… |
|---------|--------|-----------------|
| **Send** | `approve` | Stub-send the draft brief via the configured channel (records `sent: true` + message id; no real Slack/email in v1) |
| **Keep local only** | `deny` | Keep artifacts; skip the side effect; finish with status `denied` |

You will see: **Send research brief?** plus channel, destination, preview, claim counts, and conflict tally.

### Ask body (shape)

```text
Send this brief via {channel}?

To:      {destination}
Subject: {subject}

Preview:
{first ~8 lines of draft_message}

Sources: {claim_count} claims · dated {oldest} → {newest}
Conflicts flagged: {n}

This will post/send the draft above. It will not edit the brief further.
```

## Run on DigitalOcean MARS

**Prerequisites**

- DigitalOcean account with Managed Agents / MARS access (Private Preview as applicable)
- This repo public on GitHub (MARS pins a SHA)
- Inference available via harness env (see below)

**Pin**

1. Create or open a MARS agent environment that accepts a LangGraph Agent Server app.
2. Point it at this GitHub repo; pin commit SHA `{sha}`.
3. Ensure root `langgraph.json` is detected (graph export via module-level `.compile()`).
4. Set harness inference env (names below). Do not hardcode keys in the repo.
5. Deploy / start the agent server; run one smoke invoke (see Smoke).

See `mars.spec.example.yaml` for `FRAMEWORK_REPO` / `FRAMEWORK_REPO_SHA` placeholders.

**Harness inference env (required)**

| Variable | Purpose |
|----------|---------|
| `HARNESS_INFERENCE_BASE_URL` | OpenAI-compatible base URL |
| `HARNESS_INFERENCE_MODEL`    | Model id |
| `HARNESS_INFERENCE_API_KEY`  | API key |

Fallbacks `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` are OK if documented, but prefer harness names first.

**Permissions / tools**

- Public HTTP fetch via `httpx` (allowlisted `http`/`https` only)
- v1 stubs outbound send; no Action Gateway required for the research-only path
- Tests / offline runs accept `fixture_sources` in input (no live network or API key)

## Smoke

Minimal input JSON (research-only):

```json
{
  "question": "What is the status of public-web research citations?",
  "outbound": "none",
  "freshness_days": 30,
  "fixture_sources": [
    {
      "url": "https://example.com/docs",
      "title": "Example docs",
      "ok": true,
      "claim": "Citations require url and date.",
      "published_date": "2026-09-01",
      "text": "Citations require url and date."
    }
  ]
}
```

Outbound example (expect interrupt):

```json
{
  "question": "Same question",
  "outbound": "slack",
  "destination": "#research",
  "fixture_sources": [ { "url": "https://example.com/docs", "ok": true, "claim": "…", "published_date": "2026-09-01", "text": "…" } ]
}
```

Expect:

1. Stages through `draft` without side effects.
2. An **ask** interrupt when `outbound` is `slack` or `email` and claims are sourced; or a clean research-only report when `outbound` is `none`.
3. After Approve: stub send evidence (`sent: true`, `message_id` prefix `stub-`).
4. After Deny: `status: denied` and no external write.

Local smoke (fixtures, no API key):

```bash
python scripts/smoke_invoke.py
```

## Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
export HARNESS_INFERENCE_BASE_URL=...
export HARNESS_INFERENCE_MODEL=...
export HARNESS_INFERENCE_API_KEY=...
pytest -q
python scripts/smoke_invoke.py
```

MARS path stays primary; local is for graph tests. Without an API key, provide `fixture_sources` (or run the smoke script) for a deterministic path.

## License

MIT
