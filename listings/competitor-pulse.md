# Competitor Pulse — public-web deltas, counterposition brief, quiet when clean

**For** product and GTM operators who watch a named competitor list and want a material-change brief — not a noisy bot that pings every crawl.

**Job-to-be-done:** Say `track FedEx` (or load a watchlist) → fetch public modules (site / pricing / changelog / careers) → diff baselines → operator-grade chat brief → **ask before notify** only when you opt in and changes are material.

**Chat tone:** Plain English, never raw JSON or HTML — with a sharp, dry GTM-researcher personality. Greetings and how-to questions get a warm conversational reply (no pulse run). First run establishes a baseline (“first look”); later runs surface PM-readable deltas with evidence URLs.

**Why MARS / LangGraph:** Same MARS-shaped LangGraph family as Research Desk and Nightly Audit: structured stages, one approval gate before outbound, draft-by-default. Public HTTP only — never competitor logins.

---

## What you get

- Flow: `intake → plan → gather → analyze → draft → ask → act → report`
- Watchlist of competitors with public URLs per module
- Baseline diff with `material` flag; counterposition brief + notify draft
- HITL gate **Notify about competitor changes?** only when `notify` is on **and** `material == true` (notify defaults **off**)
- First baseline capture → “first look” summary, **no ask**, not fake “material crisis”
- Quiet when clean: empty / non-material diff → `status: empty`, **no ask**
- Offline fixture path (`ALLOW_NET=0`) for tests and smoke — no API key
- Optional live public HTTP when `ALLOW_NET=1`; harness LLM env optional for live planning

## What you don’t (v1 honesty)

- **No real Slack/email notify** — `act` stubs `notify_id` / `status: notified` only
- No competitor logins, signup identity, scrape-behind-login, or outbound contact to competitors
- No churn winback workflows or marketplace / desktop-bot branding
- No Approve when the diff is empty, non-material, or `notify` is false
- Action Gateway not wired for local proof
- Public GitHub pin URL and live MARS invoke evidence still TBD

---

## Getting Started

**In MARS chat, just name the companies** — no JSON paste required.

| Example prompt | Result |
|----------------|--------|
| `Track OpenAI, Anthropic, and Google for SpaceXAI` | Offline alias map → public URLs for each |
| `Pulse on Cursor and Perplexity` | Two-company watchlist |
| `Track Cursor and alert on Slack` | Cursor + notify gate enabled |

Known AI vendor aliases resolve offline. With harness inference configured, the agent can extract less common names via LLM. If you ask to track companies it cannot resolve, it asks you to name specific competitors (no silent Acme fallback). `hi` / `what do you do?` get conversational help — fixture watchlist is for programmatic smoke only.

Optional power-user paths: fenced JSON with `watchlist`, or `{"preset": "spacexai"}`.

**Local install and test** (fixtures offline):

```bash
cd mars-competitor-pulse
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
export ALLOW_NET=0
pytest -q
python scripts/smoke_invoke.py
```

Optional live LLM / HTTP:

```bash
export HARNESS_INFERENCE_BASE_URL=...
export HARNESS_INFERENCE_MODEL=...
export HARNESS_INFERENCE_API_KEY=...
export ALLOW_NET=1
```

**Smoke:** chat prompts above, or `ALLOW_NET=0 python scripts/smoke_invoke.py` for fixture path. **Quiet path (no ask):** `notify: true` + quiet `baseline_path` — see README.

Expect: stages through `draft`; ask only on material + notify; Approve → stub notify; Deny → `status: denied`, brief kept.

Full operator copy: `mars-competitor-pulse/README.md`.

---

## Pin on MARS when available

Follow documented pin path only:

1. **PLATFORM.md** — LangGraph Harness pin (`FRAMEWORK_REPO` + exact SHA), doctl beta agent commands, secrets via `--secret` / `secrets:`, evidence under `evidence/<slug>/mars-session/`.
2. **README → Run on DigitalOcean MARS** in `mars-competitor-pulse/README.md`.
3. **Spec stubs:** `mars-competitor-pulse/mars.spec.example.yaml` and Shop `specs/mars-competitor-pulse.yaml`.

**Known gaps (left open):** public HTTPS GitHub `FRAMEWORK_REPO` not published yet; Managed Agents feature flag / enablement still 403 on the preview team; no invented Agent Server HTTP base URL — use `doctl agent attach` / `prompt` / `logs` until DO documents one (PLATFORM.md §4 Invoke honesty).
