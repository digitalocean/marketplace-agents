logo: https://github.com/digitalocean/marketplace-agents/raw/dd89dd6bfe71fd00818cb9528a6c756ceea0895e/listings/assets/box-doc-summarizer.svg

# Box Doc Summarizer

## Summary

A Box Mount demo: sync a Box folder into the agent, get one executive summary with a link to every file.
It saves the summary back through the mount only after you say yes. Box Mount is private preview.

## Description

Box Doc Summarizer is a chief-of-staff agent for anyone who inherits a shared Box folder full of documents and needs the gist fast. Ask `list folders` to see what it can reach, then name a folder in chat by name, id, or link (`summarize Hawaii Trip`). It reads every PDF, Word, PowerPoint, Excel, Markdown, text, and CSV file, including subfolders, briefs each one, and writes a single executive summary: TL;DR, cross-document themes, a section per document, and a link back to each source file in Box.

Before anything touches Box it asks **Write executive summary to Box?** Approve saves `EXECUTIVE-SUMMARY.md` into the folder (a new version if one already exists, so Box keeps history). Deny keeps the summary in chat only. It never edits or deletes your documents.

It runs on Box Mount (private preview, Linux only, no SLA): the agent downloads the Box Mount build, verifies its SHA256, syncs your folder into its sandbox, reads the files from the mount, and writes the summary back through it so Box keeps versions. Box Mount syncs files but cannot create links, so the same JWT service account uses the Box API only for file links and optional public shared links.

### Why use it

- One readable summary for a whole folder, with a link to every source document
- Human approval before anything is written back to Box
- Versioned write-back: Box keeps the previous summary as an older version
- Reads PDF, DOCX, PPTX, XLSX, Markdown, text, and CSV; other files are listed, not guessed at
- Scoped access: a JWT service account invited only to the folders you choose
- Box Mount (private preview): reads and writes go through a synced folder, with a verified binary
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime

### Getting Started

1. In the Box Developer Console create a **Custom App** with **Server Authentication (with JWT)**, App Access Only, scope **Read and write all files and folders**. Generate a keypair and download the JWT config JSON.
2. Have a Box admin authorize the app (Admin Console, Platform Apps). Invite the app's service account (`AutomationUser_…@boxdevedition.com`) to your folder as an **Editor**.
3. Create the agent with secret `BOX_JWT_CONFIG_JSON` set to the whole JSON file and `HARNESS_INFERENCE_API_KEY` set to your inference key. You do not need `BOX_FOLDER_ID` for chat: use `list folders`, then `summarize <folder name or id>`. Set `BOX_FOLDER_ID` only for webhook `Refresh` or triggers with no folder in the prompt. Optionally set `BOX_SHARED_LINK_ACCESS=open` for public links.
4. Box Mount (private preview): request access from Box. The Marketplace manifest and doctl spec include env `BOX_MOUNT_BINARY_URL` (direct download) and `BOX_MOUNT_SHA256`; without the checksum the agent won't download the binary.
5. Start a session. Send `list folders` to see what the service account can reach, `list files in <folder>` to check what Box Mount synced, then `summarize <folder name or id>`. Read the preview, then approve or deny **Write executive summary to Box?**

```shell
doctl harness-runtime triggers create \
  --kind webhook \
  --provider custom \
  --name box-doc-summarizer \
  --session-mode reuse \
  --spec specs/mars-box-doc-summarizer-trigger.yaml \
  --secret HARNESS_INFERENCE_API_KEY=@~/.secrets/do-inference.key \
  --secret BOX_JWT_CONFIG_JSON=@~/.secrets/box-jwt.json \
  --prompt "Refresh"
```

Point a Box webhook (FILE.UPLOADED on the folder) at the trigger URL so a new file re-runs the summary.

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- A Box JWT app authorized by a Box admin, with its service account invited to the folder
- Required secret `BOX_JWT_CONFIG_JSON`
- Box Mount private preview access (Linux only, no SLA, 5 GB / 10,000 files per mount); the listing includes `BOX_MOUNT_BINARY_URL` and `BOX_MOUNT_SHA256` defaults
