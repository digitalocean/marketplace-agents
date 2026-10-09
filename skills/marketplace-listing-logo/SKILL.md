---
name: marketplace-listing-logo
description: >-
  Adds or updates a Marketplace catalog logo for a mars-agent: SVG in listings/assets/,
  logo: line in listings/<slug>.md, then PUT .../logo so Vendor Portal sets customData.icon.
  Use when adding listing logo, catalog icon, or customData.icon for managed agents.
---

# Marketplace listing logo

Logos are **catalog metadata**, not part of `summary`, `description`, or `gettingStarted`.

Vendor Portal stores the live catalog image on **`customData.icon`** (marketplace assets CDN). JSON create/update **does not** persist `logoUrl` — upload the file with the logo endpoint.

Parser: [scripts/listing_md.py](../../scripts/listing_md.py) — top-of-file `logo: <url>` before `#` documents the repo asset under `listings/assets/` (not sent in JSON PUT).

## 1. Add or update the asset

Place SVG (preferred) under [listings/assets/](../../listings/assets/):

```text
listings/assets/<slug>.svg
```

Match peer agents (64×64 viewBox, simple mark). Commit on `main` before publishing.

## 2. Pin the logo URL in listing markdown

First non-empty lines of `listings/<slug>.md`, **before** `#`:

```markdown
logo: https://github.com/digitalocean/marketplace-agents/raw/<commit-or-main>/listings/assets/<slug>.svg

# Display Name
```

Use a **pinned** GitHub raw URL on this monorepo. Example on `main`:

```markdown
logo: https://github.com/digitalocean/marketplace-agents/raw/main/listings/assets/nightly-repo-audit.svg
```

After merge, prefer pinning to the **exact commit SHA** you ship with `FRAMEWORK_REPO_SHA`.

## 3. Verify parsing

```bash
python3 scripts/listing_fields.py listings/<slug>.md
# Must NOT include logoUrl or icon (copy fields only)

python3 -m pytest scripts/test_listing_md.py
```

The `logo:` line must **not** appear inside `summary`, `description`, or `gettingStarted` strings.

## 4. Upload to Vendor Portal

Requires an existing listing (`appId`). **Do not** rely on `update_vendor_listing.py` for the image.

```bash
python3 scripts/upload_listing_logo.py <appId> listings/<slug>.md --verify
```

Equivalent curl (SVG):

```bash
curl -X PUT \
  "https://api.digitalocean.com/api/v1/vendor-portal/apps/<appId>/versions/<version>/logo" \
  -H "Authorization: Bearer $AGENT_CREATE_TOKEN" \
  -F "rawImage=@listings/assets/<slug>.svg;type=image/svg+xml"
```

Use **vendor-portal-update-mars-agent** only for copy/SHA — run logo upload when the asset changes.

On create (no `appId` yet), `POST /apps` first (**vendor-portal-create-mars-agent**), then `upload_listing_logo.py`.

## 5. Review

Image check does **not** run for `mars-agent`; logo changes still follow Marketplace review/publish like other listing updates. Confirm `customData.icon` in GET version and that the catalog renders after publish.

## Checklist

- [ ] SVG committed under `listings/assets/`
- [ ] `logo:` line at top of `listings/<slug>.md`
- [ ] `listing_fields.py` output has no `logoUrl` / `icon`
- [ ] Logo PUT succeeded; GET shows `customData.icon`
- [ ] Pending version handed to Marketplace for publish if required
