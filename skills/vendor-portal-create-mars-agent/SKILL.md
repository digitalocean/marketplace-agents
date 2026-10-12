---
name: vendor-portal-create-mars-agent
description: >-
  Creates a new mars-agent listing on DigitalOcean Vendor Portal via POST /apps.
  Use when submitting a new managed agent to the Marketplace, building the JSON
  payload from listings/<slug>.md and specs, with AGENT_CREATE_TOKEN auth.
---

# Vendor Portal create (mars-agent)

Listings are **reviewed before go-live**. Create leaves the app **pending** until Marketplace publishes.

Canonical API notes: [AGENTS.md](../../AGENTS.md#marketplace-listing-api).

## Prerequisites

- Merged (or agreed) **`FRAMEWORK_REPO_SHA`** on `main`
- `AGENT_CREATE_TOKEN` with `vendor_portal:create` / `write` (never print or commit)
- Emergency contact name + email
- `listings/<slug>.md` and `specs/mars-<slug>.yaml` ready
- Agent bootstrapped per **bootstrap-mars-agent**

Verify token is loaded (length only):

```bash
zsh -lic 'echo ${#AGENT_CREATE_TOKEN}'
```

## API

- Base: `https://api.digitalocean.com/api/v1/vendor-portal`
- Auth: `Authorization: Bearer $AGENT_CREATE_TOKEN`
- Type: **`mars-agent`** (not `agent`, not `droplet`)
- Create: `POST /apps`

Important:

- Send `showOnCatalog` as `{"value": true}` (or `false`) — do not omit on create.
- Pin **both** `customData.agent.frameworkRepoSha` and `FRAMEWORK_REPO_SHA` env default to the **same** SHA.
- `sizeSlug` and `HARNESS_INFERENCE_MODEL` env default are **optional** — omit unless you want create UI dropdowns pre-filled.
- Do **not** set `persistentWorkspace`.
- Image check does **not** run for `mars-agent`.

## Build copy fields from markdown

```bash
python3 scripts/listing_fields.py listings/<slug>.md --include-name
```

Maps to `customData.summary`, `description`, optional `gettingStarted`. Display name from `#` heading → top-level `name` in POST body. Catalog logo: upload after create (**marketplace-listing-logo**) → `customData.icon`.

## POST body template

Merge `listing_fields.py` output into `customData`. Set `agent` from your spec (env defaults, secret slots, permissions). Example skeleton:

```json
{
  "name": "<Display Name from listing # heading>",
  "type": "mars-agent",
  "showOnCatalog": { "value": true },
  "emergencyContacts": [
    { "name": "Your Name", "email": "you@digitalocean.com" }
  ],
  "customData": {
    "summary": "<from ## Summary>",
    "description": "<from ## Description through Requirements; excludes Getting Started>",
    "gettingStarted": "<only if ### Getting Started exists>",
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

Add extra `envDefaults` / `secretSlots` from `mars-ghost-writer` or other agents when needed. Extra tools/permissions come from the spec — mirror production behavior.

## Submit

Dry-run: validate JSON locally, then:

```bash
curl -sS -X POST "https://api.digitalocean.com/api/v1/vendor-portal/apps" \
  -H "Authorization: Bearer $AGENT_CREATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

Record returned `appId` and version in your runbook / AGENTS.md table if this is a new DO-owned agent.

## After create

1. If `listings/<slug>.md` has a `logo:` asset, run `python3 scripts/upload_listing_logo.py <appId> listings/<slug>.md --verify` (**marketplace-listing-logo**).
2. Ask Marketplace / Managed Agents to **review and publish**.
3. Sanity-check create-from-Marketplace (or doctl at the same SHA).
4. Future copy/SHA updates: **vendor-portal-update-mars-agent**.

Existing app IDs: [AGENTS.md § Existing listings](../../AGENTS.md#existing-listings-in-this-monorepo).
