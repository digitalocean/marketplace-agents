# Sourced Research Desk — citations before the brief leaves the room

**For** PMs, analysts, and operators who need a research brief they can trust — every claim dated and URL’d — without auto-posting to Slack or email.

**Job-to-be-done:** Clarify a question → plan queries → fetch public sources → build a claim table → draft a markdown brief → **ask before any outbound send**.

**Why MARS / LangGraph:** A compiled LangGraph graph with a single HITL interrupt before side effects, shaped for DigitalOcean Managed Agents (Harness Runtime). Same repo runs locally and pins on MARS via public GitHub SHA — no proprietary marketplace bot packaging.

---

## What you get

- End-to-end research path: `intake → plan → gather → analyze → draft → ask → act → report`
- Claim table with **url + date** on every factual claim; conflict callouts when sources disagree
- Markdown research brief with citations
- HITL gate **Send research brief?** when `outbound` is `slack` or `email` — Approve sends, Deny keeps the brief local
- Research-only default (`outbound: none`): brief lands in run artifacts with **no ask**
- Local smoke via fixtures (`fixture_sources`) — no API key required for the deterministic path
- Harness-native LLM env: `HARNESS_INFERENCE_BASE_URL` / `_MODEL` / `_API_KEY` (OpenAI_* fallback OK)

## What you don’t (v1 honesty)

- **No real Slack/email send** — `act` stubs outbound (`sent: true`, `message_id` prefix `stub-`); records intent only
- No login scrapes, paid search API hard-requirement, or vector DB
- No Approve when claims are unsourced (`status: blocked`) or when the run is empty/blocked
- No auto-send, auto-merge, or invented console UI steps
- Public GitHub `FRAMEWORK_REPO` URL and live MARS pin are **not yet available** (see PLATFORM blockers)

---

## Getting Started

Repo path on this machine:

```bash
cd /home/box/Shop/mars-top3-agents/mars-sourced-research-desk
```

Install, test, smoke (fixtures; no API key):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
python scripts/smoke_invoke.py
```

Optional live LLM path — export harness inference env first:

```bash
export HARNESS_INFERENCE_BASE_URL=...
export HARNESS_INFERENCE_MODEL=...
export HARNESS_INFERENCE_API_KEY=...
```

**Smoke input (research-only):** see README — `question` + `outbound: "none"` + `fixture_sources`. Expect stages through `draft`/`report` with no interrupt.

**Outbound path:** set `outbound` to `slack` or `email` with sourced fixtures → expect **ask** interrupt; Approve → stub send; Deny → `status: denied`, no external write.

Full operator copy (ask body, non-goals, smoke JSON): `mars-sourced-research-desk/README.md`.

---

## Pin on MARS when available

Do **not** invent console clicks. Follow the pin recipe already documented:

1. **Platform contract & CLI:** `/home/box/Shop/mars-top3-agents/PLATFORM.md` — `agent: langgraph`, `FRAMEWORK_REPO` + exact `FRAMEWORK_REPO_SHA`, `doctl agent create/start` with secrets, evidence via `attach` / `prompt` / `logs`.
2. **Repo README MARS section:** `mars-sourced-research-desk/README.md` → **Run on DigitalOcean MARS** (prereqs, pin steps, harness env table, tools note).
3. **Spec stub:** `mars-sourced-research-desk/mars.spec.example.yaml` and Shop `specs/mars-sourced-research-desk.yaml` (placeholders only).

**Known gaps (do not invent):** public HTTPS GitHub URL TBD; Managed Agents enablement currently blocked on the preview team (403); LangGraph Agent Server has no documented stable public HTTP invoke URL — use session attach/logs until DO publishes one (PLATFORM.md §4).
