# Submitting Managed Agents to the Marketplace

Guide for DigitalOcean engineers adding LangGraph agents to this monorepo and listing them on the Agent Marketplace (Vendor Portal type `mars-agent`).

Marketplace listings are **reviewed before they go live**. Creating or updating a listing does not by itself publish it for customers. Coordinate with Marketplace / Managed Agents for review and publish after your PR and listing payload are ready.

For running agents on MARS **without** Marketplace, see [DOCTL.md](./DOCTL.md).

---

## Prerequisites

1. Access to this repo: `https://github.com/digitalocean/marketplace-agents`
2. Ability to open a PR against `main`
3. The agent must be **open source under the MIT License** (same as this monorepo’s [LICENSE](./LICENSE)). Do not add proprietary or differently licensed agent packages here.
4. A Vendor Portal token with `vendor_portal:create` / `vendor_portal:update` and `write` scope (team must already be a marketplace vendor). In practice the token is often available only in a login shell:

   ```bash
   # Example — do not print or commit the token
   zsh -lic 'echo ${#AGENT_CREATE_TOKEN}'   # length only
   ```

5. Emergency contact (name + email) for the listing — required on create and full update

---

## Bootstrap a new agent

Copy an existing agent and rename. Preferred templates:

| Start from | When |
|------------|------|
| [`mars-sourced-research-desk/`](./mars-sourced-research-desk/) | Chat + HITL research-style agent |
| [`mars-nightly-repo-audit/`](./mars-nightly-repo-audit/) | Tools / Action Gateway + ask-before-side-effect |
| [`mars-ghost-writer/`](./mars-ghost-writer/) | Extra env defaults and CMS secret slots |

### 1. Package directory

Create `mars-<slug>/` (kebab-case, prefixed with `mars-`):

```text
mars-<slug>/
  langgraph.json
  requirements.txt
  pyproject.toml
  README.md
  LISTING.md                 # package-level operator notes (optional but match peers)
  src/<package_name>/
    __init__.py
    graph.py                 # exports compiled `graph`
  tests/
  scripts/smoke_invoke.py    # recommended
```

**LangGraph / MARS contract (required):**

| Rule | Detail |
|------|--------|
| Graph key | `langgraph.json` → `graphs.agent` (key **must** be `agent`) |
| Export | Module-level compiled graph named `graph` (see existing `graph.py`) |
| Install path | `requirements.txt` ends with `-e ./mars-<slug>/` (repo **root** is pip cwd on MARS) |
| Inference | Prefer `HARNESS_INFERENCE_BASE_URL` / `_MODEL` / `_API_KEY` |
| Permissions | Specs usually use `permissions.default: ask` for interactive HITL |

Example `langgraph.json` shape (from Sourced Research Desk):

```json
{
  "dependencies": [".", "langchain_openai", "httpx"],
  "graphs": {
    "agent": "./src/sourced_research_desk/graph.py:graph"
  }
}
```

### 2. doctl / Shop spec

Add [`specs/mars-<slug>.yaml`](./specs/) by copying an existing spec. Set at least:

- `name`, `agent: langgraph`, `template: langgraph`
- `FRAMEWORK_REPO` → `https://github.com/digitalocean/marketplace-agents.git`
- `FRAMEWORK_REPO_SHA` → exact commit after merge (placeholder `<exact-commit-sha>` until then)
- `FRAMEWORK_SUBDIR` → `mars-<slug>`
- Inference env + `HARNESS_INFERENCE_API_KEY` secret
- Any agent-specific env, secrets, `tools`, or `permissions.rules` (see Nightly Repo Audit / Ghost Writer)

Prove the agent locally or with doctl before filing a Marketplace listing:

```bash
# After merge, pin SHA in the spec, then:
doctl agent create --spec specs/mars-<slug>.yaml --name <slug> \
  --secret HARNESS_INFERENCE_API_KEY=@~/.secrets/do-inference.key
doctl agent launch <slug>
```

Full doctl notes: [DOCTL.md](./DOCTL.md).

### 3. Marketplace listing markdown

Add catalog copy at [`listings/<slug>.md`](./listings/). This is the source for Vendor Portal `summary` and `description`. Follow the existing four files:

```markdown
# Display Name

## Summary

One or two short sentences for the catalog card.

## Description

Customer-facing paragraphs…

### Why use it

- …

### Requirements

- …
```

Do **not** put local install paths, fixture smoke recipes, or “PLATFORM blockers” in this file — keep those in the package `README.md`.

Wire the new row into the root [README.md](./README.md) agent table when you open the PR.

### Checklist before Marketplace submit

- [ ] `mars-<slug>/` mirrors an existing agent’s layout
- [ ] Package is MIT-licensed (compatible with this repo)
- [ ] `langgraph.json` registers **`agent`**
- [ ] `requirements.txt` uses `-e ./mars-<slug>/`
- [ ] `specs/mars-<slug>.yaml` present and doctl-createable
- [ ] `listings/<slug>.md` has `## Summary` and `## Description`
- [ ] Tests / smoke pass; PR merged (or SHA agreed) for the pin you will publish

---

## Marketplace listing API

Base URL: `https://api.digitalocean.com/api/v1/vendor-portal`  
Auth header: `Authorization: Bearer $AGENT_CREATE_TOKEN`  
Listing type: **`mars-agent`** (not `agent`, not `droplet`)

| Action | Method | Path |
|--------|--------|------|
| List | `GET` | `/apps` |
| Get by version | `GET` | `/apps/{appId}/versions/{version}` |
| Create | `POST` | `/apps` |
| Full update | `PUT` | `/apps/{appId}/versions/{version}` |

Notes from production use:

- Bare `GET /apps/{appId}` may return **405**; use the **versioned** GET.
- `showOnCatalog` must be sent as `{"value": true}` or `{"value": false}`. Omitting it on create can leave catalog visibility ambiguous — send **`{"value": true}`** so the listing is catalog-eligible once Marketplace review publishes it.
- Image check does **not** run for `mars-agent`; a successful create stays **`pending`** / not live until review publishes it.
- **`sizeSlug` and `HARNESS_INFERENCE_MODEL` are optional.** Leave them empty / without a default so the create UI shows size and model dropdowns for the customer. If the agent runs better with a specific size or model, set `sizeSlug` and/or the `HARNESS_INFERENCE_MODEL` env default explicitly.
- Do **not** set `persistentWorkspace` (deprecated / ignored by harness).
- Pin **both** `customData.agent.frameworkRepoSha` and the `FRAMEWORK_REPO_SHA` env default to the same exact commit SHA.

### Create payload shape

```json
{
  "name": "Display Name",
  "type": "mars-agent",
  "showOnCatalog": { "value": true },
  "emergencyContacts": [
    { "name": "Your Name", "email": "you@digitalocean.com" }
  ],
  "customData": {
    "summary": "<from listings/<slug>.md ## Summary>",
    "description": "<from listings/<slug>.md ## Description through Requirements>",
    "agent": {
      "adapter": "langgraph",
      "template": "langgraph",
      "frameworkRepo": "https://github.com/digitalocean/marketplace-agents.git",
      "frameworkRepoSha": "<exact-commit-sha>",
      "permissions": { "defaultAction": "ask" },
      "envDefaults": [
        {
          "name": "FRAMEWORK_REPO",
          "label": "Framework repo",
          "type": "string",
          "required": true,
          "default": "https://github.com/digitalocean/marketplace-agents.git"
        },
        {
          "name": "FRAMEWORK_REPO_SHA",
          "label": "Framework repo SHA",
          "type": "string",
          "required": true,
          "default": "<exact-commit-sha>"
        },
        {
          "name": "FRAMEWORK_SUBDIR",
          "label": "Framework subdir",
          "type": "string",
          "required": true,
          "default": "mars-<slug>"
        },
        {
          "name": "HARNESS_INFERENCE_BASE_URL",
          "label": "Inference base URL",
          "type": "string",
          "required": true,
          "default": "https://inference.do-ai.run/v1"
        },
        {
          "name": "HARNESS_INFERENCE_MODEL",
          "label": "Inference model",
          "type": "string",
          "required": true
        }
      ],
      "secretSlots": [
        {
          "name": "HARNESS_INFERENCE_API_KEY",
          "label": "Inference API key",
          "required": true
        }
      ]
    }
  }
}
```

Optional: add more `envDefaults` / `secretSlots` when the agent needs them (see Ghost Writer’s blog vars).

### Update flow

1. `GET /apps` — find `current` (and any `unpublished` pending version).
2. If latest is `pending` or `inReview`, **stop** until that version is resolved.
3. `GET /apps/{appId}/versions/{version}` for the approved current version.
4. Merge: refresh `summary` / `description` from `listings/<slug>.md`, bump SHA, keep/adjust `showOnCatalog`, preserve agent fields you are not changing.
5. `PUT` with `reasonForUpdate` set.
6. Hand off to Marketplace for review if the new version is not yet live.

### Existing listings in this monorepo

| Agent | App ID | Safe name | Subdir |
|-------|--------|-----------|--------|
| Sourced Research Desk | `d8dfb7023b864e4eacc460f7` | `sourced-research-desk` | `mars-sourced-research-desk` |
| Nightly Repo Audit | `814d8a64ff9c8bc30d8ca0af` | `nightly-repo-audit` | `mars-nightly-repo-audit` |
| Competitor Pulse | `9557dfbccd5bafca7811aec2` | `competitor-pulse` | `mars-competitor-pulse` |
| Ghost Writer | `4e4673e65050028cb571650a` | `ghost-writer` | `mars-ghost-writer` |

---

## Review and go-live

1. Merge agent code to `main`; note the exact SHA.
2. Create or update the Vendor Portal listing with `showOnCatalog: {"value": true}`.
3. Ask Marketplace / Managed Agents to **review and publish**. Expect `pending` / not live until that happens — catalog visibility only takes effect after publish.
4. Sanity-check create-from-Marketplace (or doctl pin at the same SHA).

Emergency contact for the current DigitalOcean-owned listings: Scott Miller, `scottmiller@digitalocean.com`.
