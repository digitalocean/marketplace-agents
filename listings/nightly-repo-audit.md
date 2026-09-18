# Nightly Repo Audit — one cleanup PR draft, then you decide

**For** eng leads and maintainers who want a scheduled hygiene pass on a repo slice — TODOs, dead legacy, CI fluff — without auto-merge or surprise force-pushes.

**Job-to-be-done:** Trigger → plan one audit area → gather/scan → analyze findings → draft cleanup PR metadata → **ask before open**.

**Why MARS / LangGraph:** Interrupt-gated LangGraph agent built for DigitalOcean MARS Harness Runtime. Draft by default: Approve opens a real draft PR when Action Gateway and GitHub are wired; Deny discards the side effect and keeps artifacts. Same contract as the other top-3 agents — root `langgraph.json`, module-level `.compile()`, harness inference env.

---

## What you get

- Flow: `intake → plan → gather → analyze → draft → ask → act → report`
- One cleanup PR **draft** per run (title, body, branch, diff_stat, patch summary)
- HITL gate **Open cleanup PR?** — Approve / Discard (`approve` / `deny`)
- Empty findings → `status: empty`, **no ask** (“No cleanup worth a PR tonight”)
- Blocked checkout/tools → `status: blocked`, no ask
- Deterministic local path on in-repo `fixtures/sample_repo/` (no API key)
- Harness-native LLM env with optional live planning when a key is present

## What you don’t (honesty)

- No auto-merge, force-push, or multi-repo fleet audits
- No product-feature rewrites — hygiene / cleanup scope only
- No Approve when findings are empty or the run is blocked
- No PR open without Action Gateway (`do.actions`) and a GitHub Connection — Approve fails closed with clear prose
- Local fixture proof does not need live git checkout; real PR open needs MARS + AG + Connection
- Public GitHub pin URL and live MARS session evidence still TBD (PLATFORM blockers)

---

## Getting Started

Repo path on this machine:

```bash
cd /home/box/Shop/mars-top3-agents/mars-nightly-repo-audit
```

Install, test, smoke (fixtures; no API key):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
python scripts/smoke_invoke.py
```

Optional live LLM planning:

```bash
export HARNESS_INFERENCE_BASE_URL=...
export HARNESS_INFERENCE_MODEL=...
export HARNESS_INFERENCE_API_KEY=...
```

**Smoke input (expect ask):** `{ "repo": "owner/name", "ref": "main", "area_hint": "src", "trigger": "manual" }`

**Empty path (no ask):** add `"force_empty": true`.

Expect: stages through `draft` with no side effects; ask when findings exist; Approve → real draft PR when AG wired (mocked offline); Deny → `status: denied`.

Full ask templates and MARS section: `mars-nightly-repo-audit/README.md`.

---

## Pin on MARS when available

Point at existing docs — no invented console UI:

1. **PLATFORM.md** — Harness LangGraph pin, YAML spec shape, `doctl agent` start/show/attach/logs/remove, secrets hygiene, evidence path.
2. **README → Run on DigitalOcean MARS** in `mars-nightly-repo-audit/README.md` (prereqs, pin SHA steps, harness env, Action Gateway tools/permissions).
3. **Spec stubs:** `mars-nightly-repo-audit/mars.spec.example.yaml` and Shop `specs/mars-nightly-repo-audit.yaml`.

**Honesty for schedules:** Partner Guide unattended triggers **reject** `permissions.default: ask`. Interactive MARS proof stays on `ask`; nightly cron needs a separate deny/allow trigger spec later (PLATFORM.md §4 Triggers) — not part of first pin proof.

**Known gaps:** public `FRAMEWORK_REPO` HTTPS URL TBD; Managed Agents enablement 403 on current team; no live path-smoke yet.
