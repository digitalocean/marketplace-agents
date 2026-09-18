# Nightly Repo Audit

Trigger → sandbox audit slice → one cleanup PR draft → ask before open. LangGraph agent shaped for DigitalOcean MARS (Managed Agents / Harness Runtime).

## What it does

- Plans a nightly audit slice (path/theme) for one repo
- Scans an in-repo fixture sandbox (v1) for hygiene findings (TODO/FIXME, unused legacy)
- Drafts cleanup PR metadata (branch, title, body, diff_stat)
- Stops for human approval before opening a PR

## What it does not

- Auto-merge or force-push
- Multi-repo fleet audits or product feature rewrites
- Presenting Approve when findings are empty or checkout is blocked
- Inventing a PR URL without Action Gateway + GitHub Connection (fail closed; draft stays local)

## Run flow

```
intake → plan → gather → analyze → draft → **ask** → act → report
```

**Ask is skipped** when `findings[]` is empty (`status: empty`) or checkout/tools fail (`status: blocked`).

## Human approval

When the graph reaches **ask**, the run pauses until you **Open draft PR** (`approve`) or **Discard** (`deny`).

| If you… | Resume | The agent will… |
|---------|--------|-----------------|
| **Open draft PR** | `approve` | Open a **real draft PR** on GitHub via Action Gateway when connected (never merge or force-push); otherwise fail closed — draft stays in the run |
| **Discard** | `deny` | Discard the open; artifacts stay in the run (`status: denied`) |

You will see: **Open cleanup PR?** plus branch, title, scope, diff_stat, what-it-does bullets, what-it-will-not-do, and an evidence line.

### Ask body (shape)

```text
Open a draft PR on {owner/repo}?

Branch:  {branch_name}
Title:   {pr_title}
Scope:   {area}
Changes: {diff_stat}

What it does:
{3–5 bullets from patch_summary}

What it will not do:
- Merge
- Touch paths outside {area}
- Change product behavior (cleanup / hygiene only)

Evidence is in this run's artifacts.
Approve opens a real draft PR when Action Gateway + GitHub Connection are available (no merge, no force-push).
```

## Run on DigitalOcean MARS

**Prerequisites**

- DigitalOcean account with Managed Agents / MARS access (Private Preview as applicable)
- This repo public on GitHub (MARS pins a SHA)
- Inference available via harness env (see below)

**Pin**

1. Create or open a MARS agent environment that accepts a LangGraph Agent Server app.
2. Point it at this GitHub repo; pin commit SHA `{sha}`.
3. Ensure root `langgraph.json` is detected (graph export via module-level `.compile(name="NightlyRepoAudit")`).
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

- Fixture scan uses in-repo `fixtures/sample_repo/` (deterministic filesystem scan)
- Spec: `tools: [do.actions]` + `permissions.rules.mcp: allow` (see `mars.spec.example.yaml`)
- Platform injects `HARNESS_MCP_SERVERS` (base64 JSON) with the `do_actions` VPC MCP URL; graph binds MCP at runtime and calls **`github_create_pull_request`** (`draft: true`) after HITL approve
- Credentials stay in Action Gateway Connections — not in agent `env`
- Approve opens a real **draft** PR when GitHub Connection is available; Deny never opens; no fake `pr_url` without AG
- Optional live LLM planning when harness key present (offline path needs no key)

## Smoke

Minimal input JSON (fixture audit; expect ask):

```json
{
  "repo": "owner/name",
  "ref": "main",
  "area_hint": "src",
  "trigger": "manual"
}
```

Empty path (no ask):

```json
{
  "repo": "owner/name",
  "ref": "main",
  "force_empty": true
}
```

Expect:

1. Stages through `draft` without side effects.
2. An **ask** interrupt when findings exist; or a clean `empty` / `blocked` report with no ask.
3. After Approve (with mocked or live Action Gateway): `status: opened`, real `pr_url` / `pr_number`.
4. After Deny: `status: denied` and no PR metadata.
5. After Approve without Action Gateway: `status: error`, fail-closed prose.

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

MARS path stays primary; local is for graph tests. Without an API key, the fixture scan path is fully deterministic.

## License

MIT
