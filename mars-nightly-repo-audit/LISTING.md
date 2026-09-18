# Nightly Repo Audit — one cleanup PR draft, then you decide

**For** eng leads and maintainers who want a scheduled hygiene pass on a repo slice — TODOs, dead legacy, CI fluff — without auto-merge or surprise force-pushes.

**Job-to-be-done:** Trigger → plan one audit area → gather/scan → analyze findings → draft cleanup PR metadata → **ask before open**.

**Why MARS / LangGraph:** Interrupt-gated LangGraph agent built for DigitalOcean MARS Harness Runtime. **Approve** opens a **real draft PR** via Action Gateway when GitHub Connection is available. **Deny** discards the open; artifacts stay in the run. Same contract as the other top-3 agents — root `langgraph.json`, module-level `.compile()`, harness inference env.

---

## What you get

- Flow: `intake → plan → gather → analyze → draft → ask → act → report`
- One cleanup PR **draft** per run (title, body, branch, diff_stat, patch summary)
- HITL gate **Open cleanup PR?** — Approve / Discard (`approve` / `deny`)
- **Approve** → real draft PR on GitHub via Action Gateway (`github_create_pull_request`, `draft: true`) when connected
- **Deny** → no open; draft metadata stays in the run
- Empty findings → `status: empty`, **no ask** (“No cleanup worth a PR tonight”)
- Blocked checkout/tools → `status: blocked`, no ask
- Deterministic local path on in-repo `fixtures/sample_repo/` (no API key)
- Harness-native LLM env with optional live planning when a key is present

## What you don’t (honesty)

- No merge, no force-push, hygiene-only scope — ever
- No product-feature rewrites
- No Approve when findings are empty or the run is blocked
- **Without Action Gateway / GitHub Connection:** no real PR open, no fake `pr_url` — fail closed; draft stays local
- Local fixture proof does not need live git checkout; real PR open needs MARS + AG + GitHub Connection
- Public GitHub pin URL and live MARS session evidence still TBD (PLATFORM blockers)

---

## Getting Started

```bash
cd mars-nightly-repo-audit
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

1. **PLATFORM.md** — Harness LangGraph pin, YAML spec shape, `doctl agent` start/show/attach/logs/remove, secrets hygiene.
2. **README → Run on DigitalOcean MARS** in `mars-nightly-repo-audit/README.md` (prereqs, pin SHA, harness env, Action Gateway tools/permissions).
3. **Spec stubs:** `mars-nightly-repo-audit/mars.spec.example.yaml` and `specs/mars-nightly-repo-audit.yaml` (`tools: [do.actions]`, `permissions.rules.mcp: allow`).

**Honesty for schedules:** Partner Guide unattended triggers **reject** `permissions.default: ask`. Interactive MARS proof stays on `ask`; nightly cron needs a separate deny/allow trigger spec later — not part of first pin proof.

**Known gaps:** public `FRAMEWORK_REPO` HTTPS URL TBD; Managed Agents enablement 403 on current team; live MARS smoke pending Reed.
