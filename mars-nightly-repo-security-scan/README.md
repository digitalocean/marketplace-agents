# Nightly Repo Security Scan

Trigger → sandbox security slice → fix findings → one draft PR → ask before open. LangGraph agent shaped for DigitalOcean MARS (Managed Agents / Harness Runtime). Inference model is **Grok 4.7**.

## What it does

- Plans one scan slice (path) for one repo
- Scans an in-repo fixture sandbox (v1 local) for:
  - application problems (hardcoded credentials, `yaml.load`, TLS `verify=False`, interpolated SQL, debug mode left on)
  - bugs (`eval`, off-by-one index)
  - dependency pins below a bundled same-major patched release (`requirements.txt`, `package.json`)
- Applies those fixes in memory and puts the unified diff in the draft PR body
- Stops for human approval before opening a PR
- **On Approve:** opens a **real draft PR** on GitHub via Action Gateway when a GitHub Connection is available
- When `SECURITY_SCAN_LLM_REVIEW=1` and an inference key is set, asks **Grok 4.7** for a short review note. The fixes do not depend on the model.

## What it does not (v1)

- Auto-merge or force-push
- Live OSV / advisory feeds (pins are a bundled floor: PyYAML 5.4.1, requests 2.32.3, urllib3 1.26.19, lodash 4.17.21)
- Push a commit. `github_create_pull_request` opens the draft; the patch is in the PR body. If that head branch does not exist, GitHub rejects the open and the run says so.
- Multi-repo fleet scans or product feature rewrites
- Exploit write-ups. Findings name the fix, not an attack procedure.
- Presenting Approve when findings are empty or checkout is blocked
- Opening a GitHub PR when Action Gateway / GitHub Connection is missing

## Run flow

```
intake → plan → gather → analyze → draft → **ask** → act → report
```

**Ask is skipped** when `findings[]` is empty (`status: empty`) or checkout/tools fail (`status: blocked`).

Chat asks before the scan (`Start security scan?`). A programmatic payload with `repo` / `fixture_path` and no chat message skips that confirm and goes straight to the scan, same as Nightly Repo Audit.

## Human approval

When the graph reaches **ask**, the run pauses until you **Open draft PR** (`approve`) or **Discard** (`deny`).

| If you… | Resume | The agent will… |
|---------|--------|-----------------|
| **Open draft PR** | `approve` | Open a **draft** PR via Action Gateway + GitHub Connection when configured (`status: opened`, real `pr_url` / number when AG succeeds). Without AG/GitHub, records metadata only and reports that open was unavailable. |
| **Discard** | `deny` | Keep artifacts; skip the side effect; finish with status `denied` |

You will see: **Open security fix PR?** plus branch, title, scope, diff stat, what-it-does bullets, what-it-will-not-do, and an evidence line.

## Run on DigitalOcean MARS

**Prerequisites**

- DigitalOcean account with Managed Agents / MARS access
- This repo public on GitHub (MARS pins a SHA)
- Inference via harness env. Model id is `grok-4.7`
- For real PR open: Action Gateway enabled and a GitHub Connection on the agent

**Harness inference env**

| Variable | Purpose |
|----------|---------|
| `HARNESS_INFERENCE_BASE_URL` | OpenAI-compatible base URL |
| `HARNESS_INFERENCE_MODEL` | `grok-4.7` |
| `HARNESS_INFERENCE_API_KEY` | API key |
| `SECURITY_SCAN_LLM_REVIEW` | `1` to ask Grok for the PR review note |

**Permissions / tools**

- Local/fixture path uses in-repo `fixtures/sample_repo/` (deterministic scan; no AG required)
- MARS `open_pr` uses Action Gateway (`do.actions`) via MCP `action_invoke` → `github_create_pull_request` (`draft: true`) after HITL approve
- Spec: `tools: [do.actions]` + `permissions.rules` mcp allow (see `mars.spec.example.yaml`)
- Credentials stay in Action Gateway Connections, not in agent `env`

## Smoke

Minimal input JSON (fixture scan; expect ask):

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
3. The draft body contains the unified diff (parameterized SQL, `yaml.safe_load`, bumped pins).
4. After Approve (AG + GitHub connected): real draft PR evidence (`status: opened`, `pr_url`).
5. After Approve without AG: honest unavailable outcome (no fake GitHub URL).
6. After Deny: `status: denied` and no PR opened.

Local smoke (fixtures, no API key, no AG):

```bash
python scripts/smoke_invoke.py
```

## Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
export HARNESS_INFERENCE_BASE_URL=https://inference.do-ai.run/v1
export HARNESS_INFERENCE_MODEL=grok-4.7
export HARNESS_INFERENCE_API_KEY=...
pytest -q
python scripts/smoke_invoke.py
```

From this monorepo, install with the repo root as cwd so `-e ./mars-nightly-repo-security-scan` resolves. `pytest` from this directory uses `pythonpath = src` and does not need the editable install.

MARS path stays primary for real PR open; local is for graph tests. Without an API key, the fixture scan path is fully deterministic.

## License

MIT
