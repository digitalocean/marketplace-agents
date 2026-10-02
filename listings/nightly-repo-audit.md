# Nightly Repo Audit

## Summary

A hygiene pass that drafts one cleanup PR, then waits for your yes.
TODOs, dead legacy, and CI fluff get reviewed; nothing merges without you.

## Description

Nightly Repo Audit is a repo-hygiene agent for eng leads and maintainers who want scheduled cleanup without surprise merges or force-pushes. Name a repo in chat (`https://github.com/owner/name` or `owner/name`); it clones that ref, plans one audit area, and scans for TODOs, dead legacy, and CI fluff. When it finds safe cleanup, it commits the changes and pushes one branch (`nightly/cleanup-<area>`) before asking you to open a pull request.

Use it when your backlog of “we should clean that up” keeps growing and you want a consistent pass that proposes a draft PR and stops. Approve opens a real draft PR when GitHub is connected; deny does not open a PR. The cleanup branch may already be on the remote. Empty nights stay quiet: no ask, no noise.

Ideal for weekly or nightly hygiene on a service you own, pre-release cleanup of a hot path, or giving maintainers a reviewable PR instead of another unchecked bot commit.

### Why use it

- One focused cleanup PR draft per run, not a flood of drive-by commits
- Cleanup branch is pushed before the ask; Approve opens a **draft** PR only and never merges or force-pushes
- Deny does not open a PR; the cleanup branch may already be on the remote
- Quiet when clean: empty findings mean no interrupt and no noise
- Scoped to hygiene (TODOs, legacy, CI fluff), not product-feature rewrites
- Action Gateway + GitHub Connection open real draft PRs when configured
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime

### Getting Started

1. Create a GitHub token with contents write on the repository you want audited (fine-grained: Contents read and write). Set it as the required secret `GITHUB_TOKEN` when you create the agent. The token clones a private repo and pushes the cleanup branch. It does not open the pull request.
2. In the control panel, open **Managed Agents**, **Action Gateway**, **Connections**, and add a GitHub connection with DigitalOcean's OAuth app. Wait until it is active. Approve uses that connection to open the draft pull request. The agent also needs the `do.actions` tool.
3. Start a session and send `Audit https://github.com/owner/name on main, area src`. Approve **Start repo audit?** so it clones and scans. If it finds safe cleanup, it pushes `nightly/cleanup-<area>`, then asks **Open cleanup PR?**. Approve that to open the draft. Deny leaves the branch on the remote and does not open a pull request.
4. Add a daily trigger. A cron trigger cannot use a spec whose permission default is `ask`, so point it at a copy of the agent spec with `permissions.default: allow`. Each firing starts a fresh session, sends the prompt below, and emails you the result. The run still pauses at the two questions above; open the session and approve them.

```shell
doctl harness-runtime triggers create \
  --kind cron \
  --name nightly-repo-audit \
  --session-mode fresh \
  --spec specs/mars-nightly-repo-audit-trigger.yaml \
  --secret HARNESS_INFERENCE_API_KEY=@~/.secrets/do-inference.key \
  --secret GITHUB_TOKEN=@~/.secrets/github.token \
  --prompt "Audit https://github.com/owner/name on main, area src" \
  --cron-expr "0 2 * * *" \
  --timezone America/New_York \
  --output-mode email \
  --output-email you@example.com
```

`0 2 * * *` is 02:00 every day in the timezone you set. Change the prompt to your repository. Pause or resume the trigger later with `doctl harness-runtime triggers pause` and `resume`.

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- Strong coding / reasoning models work best (e.g. `deepseek-v4-pro` or comparable)
- Required secret `GITHUB_TOKEN` with contents write, so the cleanup branch can be pushed
- GitHub Connection + Action Gateway (`do.actions`) to open draft PRs on Approve
- A daily cron trigger whose spec uses `permissions.default: allow`
- Repo access for the target `owner/name` and ref you want audited
