# Nightly Repo Security Scan — fix the slice, then you decide

**For** eng leads and maintainers who want a scheduled security pass on a repo slice (application problems, bugs, vulnerable dependency pins) without auto-merge or surprise force-pushes.

**Job-to-be-done:** Trigger → plan one scan area → gather → fix findings → draft one PR (patch included) → **ask before open**.

**Why MARS / LangGraph:** Interrupt-gated LangGraph agent built for DigitalOcean MARS Harness Runtime. Inference model is Grok 4.7. Draft by default: Approve opens a real draft PR when Action Gateway + GitHub Connection are available; Deny discards the open and keeps artifacts.

---

## What you get

- Flow: `intake → plan → gather → analyze → draft → ask → act → report`
- Deterministic fixes for application problems, bugs, and a bundled set of vulnerable dependency pins
- One draft PR per run (title, body, branch, diff stat, unified patch)
- Optional Grok 4.7 review note when `SECURITY_SCAN_LLM_REVIEW=1` and an inference key is set
- HITL gate **Open security fix PR?** — Approve / Discard (`approve` / `deny`)
- **Approve → real draft PR** via Action Gateway when GitHub Connection is configured
- Empty findings → `status: empty`, **no ask**
- Blocked checkout → `status: blocked`, no ask
- Deterministic local path on in-repo `fixtures/sample_repo/` (no API key; no AG required for local proof)

## What you don’t (v1 honesty)

- **No merge and no force-push.** Approve opens a **draft** PR only
- No live vulnerability feed. Patched pins are bundled (same major only)
- No commit push. The gateway action is `github_create_pull_request`; the patch is in the PR body
- No exploit write-ups and no product-feature rewrites
- No Approve when findings are empty or the run is blocked
- Without Action Gateway / GitHub Connection, Approve cannot open on GitHub

---

## Getting started

From this package directory:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python scripts/smoke_invoke.py
```

Optional Grok review note:

```bash
export HARNESS_INFERENCE_BASE_URL=https://inference.do-ai.run/v1
export HARNESS_INFERENCE_MODEL=grok-4.7
export HARNESS_INFERENCE_API_KEY=...
export SECURITY_SCAN_LLM_REVIEW=1
```

**Smoke input (expect ask):** `{ "repo": "owner/name", "ref": "main", "area_hint": "src", "trigger": "manual" }`

**Empty path (no ask):** add `"force_empty": true`.

Shop spec: `specs/mars-nightly-repo-security-scan.yaml`. Package stub: `mars.spec.example.yaml`.

**Honesty for schedules:** unattended triggers reject `permissions.default: ask`. Interactive MARS proof stays on `ask`.
