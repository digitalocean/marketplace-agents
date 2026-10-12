# Marketplace agents — Cursor skills

Repeatable workflows for bootstrapping MARS agents and managing Vendor Portal (`mars-agent`) listings. Canonical reference: [AGENTS.md](../AGENTS.md).

## Install

From the repo root:

```bash
./scripts/install-cursor-skills.sh              # ~/.cursor/skills/ (personal)
./scripts/install-cursor-skills.sh --project    # .cursor/skills/ (relative symlinks; team-local unless you commit them)
./scripts/install-cursor-skills.sh --uninstall  # remove symlinks (same mode: default or --project)
./scripts/install-cursor-skills.sh --force      # replace conflicting targets
```

Then invoke in Cursor by name (for example: “use the **bootstrap-mars-agent** skill”) or `@` mention the skill when your client supports it.

## Skills

| Directory | Skill | When to use |
|-----------|--------|-------------|
| [bootstrap-mars-agent](./bootstrap-mars-agent/) | Bootstrap a new `mars-<slug>/` package, spec, and listing markdown | New agent in this monorepo |
| [vendor-portal-create-mars-agent](./vendor-portal-create-mars-agent/) | `POST /apps` for a new Marketplace listing | First-time Vendor Portal submit |
| [vendor-portal-update-mars-agent](./vendor-portal-update-mars-agent/) | `PUT` full update from `listings/<slug>.md` | Copy/SHA changes after listing exists |
| [marketplace-listing-logo](./marketplace-listing-logo/) | Asset + `logo:` line + PUT logo → `customData.icon` | Catalog logo for an existing listing |

## Repo helpers

| Script | Purpose |
|--------|---------|
| `python3 scripts/listing_fields.py listings/<slug>.md` | Preview `customData` strings from markdown |
| `python3 scripts/update_vendor_listing.py <appId> listings/<slug>.md` | Merge listing markdown into current version (PUT) |
| `python3 scripts/upload_listing_logo.py <appId> listings/<slug>.md` | Upload SVG/PNG; sets `customData.icon` |
| `python3 -m pytest scripts/test_listing_md.py` | Listing parser tests |
