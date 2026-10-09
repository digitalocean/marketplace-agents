---
name: bootstrap-mars-agent
description: >-
  Bootstraps a new LangGraph MARS agent in digitalocean/marketplace-agents:
  mars-<slug>/ package, specs/mars-<slug>.yaml, listings/<slug>.md, and README
  table row. Use when adding a new managed agent to the monorepo, copying from
  mars-sourced-research-desk, mars-nightly-repo-audit, or mars-ghost-writer.
---

# Bootstrap a new MARS agent (marketplace-agents)

Read [AGENTS.md](../../AGENTS.md) for prerequisites (MIT license, PR access, Vendor Portal token later).

## Inputs to confirm

- **slug** — kebab-case, no `mars-` prefix in the slug itself (directory is `mars-<slug>/`)
- **template agent** — pick one:
  - `mars-sourced-research-desk` — chat + HITL research
  - `mars-nightly-repo-audit` — Action Gateway tools + ask-before-side-effect
  - `mars-ghost-writer` — extra env defaults / CMS secret slots
- **display name** — for listing `#` heading and Vendor Portal `name`

## Steps

### 1. Copy and rename package

```text
mars-<slug>/
  langgraph.json          # graphs.agent key MUST be "agent"
  requirements.txt        # ends with -e ./mars-<slug>/  (repo root is pip cwd on MARS)
  pyproject.toml
  README.md               # operator notes, smoke recipes — not catalog copy
  LISTING.md              # optional; match peers
  src/<package_name>/
    __init__.py
    graph.py              # module-level compiled `graph`
  tests/
  scripts/smoke_invoke.py # recommended
```

After copy: rename Python package imports, `pyproject.toml` name, and `langgraph.json` graph path to `./src/<package_name>/graph.py:graph`.

### 2. LangGraph / MARS contract (verify)

| Rule | Detail |
|------|--------|
| Graph key | `langgraph.json` → `graphs.agent` |
| Export | `graph` at module level in `graph.py` |
| Inference | `HARNESS_INFERENCE_BASE_URL` / `_MODEL` / `_API_KEY` |
| Permissions | Spec usually `permissions.default: ask` for interactive HITL |

### 3. Shop / doctl spec

Copy `specs/mars-<similar>.yaml` → `specs/mars-<slug>.yaml`. Set:

- `FRAMEWORK_REPO`: `https://github.com/digitalocean/marketplace-agents.git`
- `FRAMEWORK_REPO_SHA`: `<exact-commit-sha>` after merge (placeholder until then)
- `FRAMEWORK_SUBDIR`: `mars-<slug>`
- Inference env + `HARNESS_INFERENCE_API_KEY` secret
- Agent-specific env, secrets, `tools`, `permissions.rules` as needed

Prove before Marketplace submit ([DOCTL.md](../../DOCTL.md)):

```bash
doctl agent create --spec specs/mars-<slug>.yaml --name <slug> \
  --secret HARNESS_INFERENCE_API_KEY=@~/.secrets/do-inference.key
doctl agent launch <slug>
```

### 4. Listing markdown

Create `listings/<slug>.md` with at least `## Summary` and `## Description`. Optional top `logo:` line (see **marketplace-listing-logo** skill). Optional `### Getting Started` → Vendor Portal `gettingStarted`, excluded from `description`.

Preview parsed fields:

```bash
python3 scripts/listing_fields.py listings/<slug>.md
```

Do **not** put local install paths or PLATFORM blockers in the listing file — keep those in package `README.md`.

### 5. Wire README and checklist

Add a row to the agent table in [README.md](../../README.md).

Before Marketplace submit:

- [ ] Layout mirrors an existing agent
- [ ] MIT-compatible license
- [ ] `langgraph.json` registers `agent`
- [ ] `requirements.txt` uses `-e ./mars-<slug>/`
- [ ] Spec is doctl-createable
- [ ] Listing has Summary + Description; logo/gettingStarted rules per AGENTS.md
- [ ] Tests / smoke pass; merge SHA agreed for publish pin

## Next skills

- First Vendor Portal row: **vendor-portal-create-mars-agent**
- After `appId` exists: **vendor-portal-update-mars-agent** or **marketplace-listing-logo**
