logo: https://github.com/digitalocean/marketplace-agents/raw/main/listings/assets/box-doc-summarizer.svg

# Box Doc Summarizer

## Summary

Point it at a Box folder and get one executive summary with a link to every file.
It saves the summary back to Box only after you say yes. Optional Box Mount support is private preview.

## Description

Box Doc Summarizer is a chief-of-staff agent for anyone who inherits a shared Box folder full of documents and needs the gist fast. Name a folder in chat (`Summarize folder 123456789` or a Box folder link). It reads every PDF, Word, PowerPoint, Excel, Markdown, text, and CSV file, including subfolders, briefs each one, and writes a single executive summary: TL;DR, cross-document themes, a section per document, and a link back to each source file in Box.

Before anything touches Box it asks **Write executive summary to Box?** Approve saves `EXECUTIVE-SUMMARY.md` into the folder (a new version if one already exists, so Box keeps history). Deny keeps the summary in chat only. It never edits or deletes your documents.

It connects through the Box API with a JWT service account. If you have access to Box Mount (private preview, Linux only, no SLA), it can mount the folder instead and write through the mount.

### Why use it

- One readable summary for a whole folder, with a link to every source document
- Human approval before anything is written back to Box
- Versioned write-back: Box keeps the previous summary as an older version
- Reads PDF, DOCX, PPTX, XLSX, Markdown, text, and CSV; other files are listed, not guessed at
- Scoped access: a JWT service account invited only to the folders you choose
- Optional Box Mount (private preview) mode for a mounted, synced folder
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime

### Getting Started

1. In the Box Developer Console create a **Custom App** with **Server Authentication (with JWT)**, App Access Only, scope **Read and write all files and folders**. Generate a keypair and download the JWT config JSON.
2. Have a Box admin authorize the app (Admin Console, Platform Apps). Invite the app's service account (`AutomationUser_…@boxdevedition.com`) to your folder as an **Editor**.
3. Create the agent with secret `BOX_JWT_CONFIG_JSON` set to the whole JSON file and `HARNESS_INFERENCE_API_KEY` set to your inference key. Optionally set env `BOX_FOLDER_ID` so `Refresh` works without an id, and `BOX_SHARED_LINK_ACCESS=open` if you want public links.
4. Optional, Box Mount private preview: request access from Box, then set secret `BOX_MOUNT_BINARY_URL` to a direct download of the Linux build.
5. Start a session and send `Summarize folder 123456789`. Read the preview, then approve or deny **Write executive summary to Box?**

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
- Optional: Box Mount private preview access and a direct binary URL (`BOX_MOUNT_BINARY_URL`); Linux only, no SLA, 5 GB / 10,000 files per mount
