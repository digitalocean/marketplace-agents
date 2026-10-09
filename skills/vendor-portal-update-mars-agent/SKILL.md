---
name: vendor-portal-update-mars-agent
description: >-
  Full-updates a mars-agent Vendor Portal listing via PUT /apps/{appId}/versions/{version},
  merging listings/<slug>.md and pinning frameworkRepoSha. Use when refreshing catalog
  copy, gettingStarted, customData.icon (logo upload), or FRAMEWORK_REPO_SHA after merge.
---

# Vendor Portal update (mars-agent)

Canonical flow: [AGENTS.md § Update flow](../../AGENTS.md#update-flow).

## Prerequisites

- `AGENT_CREATE_TOKEN` with `vendor_portal:update` / `write`
- **`appId`** for the agent (see AGENTS.md existing listings table)
- No **pending** / **inReview** version blocking updates
- Listing markdown merged to `main` (or use the branch file intentionally)

## Preferred: repo script

Merges `listings/<slug>.md` into the **current approved** version, pins SHA, sets `reasonForUpdate`:

```bash
export AGENT_CREATE_TOKEN=...   # login shell; never commit

python3 scripts/update_vendor_listing.py <appId> listings/<slug>.md \
  --framework-repo-sha <exact-commit-sha> \
  --reason "Sync catalog copy and framework SHA from main"

# Preview PUT body:
python3 scripts/update_vendor_listing.py <appId> listings/<slug>.md --dry-run
```

Default SHA when `--framework-repo-sha` is omitted: current git `HEAD` at repo root.

Script behavior:

- `GET /apps` → resolve current version; abort if unpublished version is `pending` / `inReview`
- `GET /apps/{appId}/versions/{version}` — do **not** use bare `GET /apps/{appId}` (405)
- Merge parsed listing into `customData`; update `agent.frameworkRepoSha` and `FRAMEWORK_REPO_SHA` default
- `PUT /apps/{appId}/versions/{version}` with `reasonForUpdate`

Preview markdown → customData only:

```bash
python3 scripts/listing_fields.py listings/<slug>.md
python3 -m pytest scripts/test_listing_md.py
```

## Manual PUT (when script is insufficient)

1. `GET /apps` — find `current` and any `unpublished` pending version.
2. If latest is `pending` or `inReview`, **stop** until resolved.
3. `GET /apps/{appId}/versions/{version}` for approved current.
4. Merge from `listings/<slug>.md`: `summary`, `description`, `gettingStarted` (when section exists). Bump SHA on agent block. Preserve fields you are not changing. Keep/adjust `showOnCatalog`.
5. `PUT` with `reasonForUpdate` on `customData`.
6. If logo asset or `logo:` line changed, `python3 scripts/upload_listing_logo.py <appId> listings/<slug>.md` (**marketplace-listing-logo**) — sets `customData.icon`.
7. Hand off to Marketplace for review if the new version is not live.

PUT body must include prior version fields the API expects (`appId`, `developerId`, `name`, `type`, `showOnCatalog`, `emergencyContacts`, full `customData`).

## After update

- Coordinate Marketplace review/publish if status is pending.
- Logo-only workflow details: **marketplace-listing-logo** (same script path).
