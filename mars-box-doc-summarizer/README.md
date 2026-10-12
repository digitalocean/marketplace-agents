# Box Doc Summarizer (MARS LangGraph agent)

Briefs every document in one Box folder and writes one executive summary
(TL;DR, themes, a section per document, a link to every file) back to the
folder after human approval.

Flow: `intake → connect → inventory → extract → brief → links → synthesize → ask → write_back → report`

## Box access modes

| Mode | When | Reads | Write-back |
|------|------|-------|------------|
| **Box API (primary / fallback)** | `BOX_JWT_CONFIG_JSON` set | REST list (recursive, `MAX_DEPTH`) + download | Upload `SUMMARY_FILENAME`, or new version of the existing file |
| **Box Mount (optional, private preview)** | `BOX_MOUNT_BINARY_URL` set | Mounted folder at `BOX_MOUNT_PATH` | In-place write (no temp+rename) so Box keeps versions |
| **Fixture** | input `fixture_path` | Local directory | `write_dir` (or the fixture dir) |

If Box Mount fails and the JWT config is present, the run falls back to the API path and records `mount_state: failed: …`.

Box Mount bootstrap (verified against box-mount 0.6.0): downloads
`BOX_MOUNT_BINARY_URL` (raw ELF or Box's `box-mount-<ver>-linux-<arch>.tar.gz`;
optional `BOX_MOUNT_SHA256`) to `~/.local/bin/box-mount` (0700), writes the JWT
JSON to `~/.box-mount/jwt-config.json` (0600, must stay on disk), pipes
`jwt` + that path into the interactive `box-mount config` (writes
`box-config.json`), runs `box-mount mount <dir> <folder-id>`, and waits for
`box-mount status` to show `<dir> | ... | status=running` plus the first
bootstrap cycle (files appear, ~6s). Box Mount is a two-way sync folder, not
FUSE: write-back is a plain file write into the folder and the daemon uploads
it. The preview binary and its URL are secrets: never commit them.

Inference on MARS: the harness may rewrite `HARNESS_INFERENCE_BASE_URL` to an
internal endpoint that returns HTTP 401 for a tenant key; the agent retries
once on `https://inference.do-ai.run/v1` (`INFERENCE_PUBLIC_BASE_URL`). Any
fallback reason (HTTP status / exception class only) is recorded in
`stage_summaries`, `llm_note`, and a note at the end of the summary.

Links: `shared_link.url` when the file has one, else `https://app.box.com/file/<id>`.
Set `BOX_SHARED_LINK_ACCESS=open` to create public shared links for files that lack one.

## Env / secrets

| Name | Kind | Default | Notes |
|------|------|---------|-------|
| `HARNESS_INFERENCE_API_KEY` | secret | | Briefs + TL;DR via direct HTTP `stream:false`; heuristics offline |
| `BOX_JWT_CONFIG_JSON` | secret | | Developer Console JWT config (whole file) |
| `BOX_MOUNT_BINARY_URL` | secret | | Optional, enables Box Mount |
| `BOX_FOLDER_ID` | env | | Default folder for `Refresh` |
| `BOX_MOUNT_PATH` | env | `/workspace/box` | |
| `SUMMARY_FILENAME` | env | `EXECUTIVE-SUMMARY.md` | Excluded from inventory |
| `MAX_FILES` / `MAX_DEPTH` / `MAX_CHARS_PER_DOC` / `MAX_FILE_BYTES` | env | 50 / 3 / 20000 / 25 MB | |
| `BOX_SHARED_LINK_ACCESS` | env | empty | `open` creates public links |

The LLM only ever sees extracted document text, never env or config.

## Local

```bash
# from the repo root
pip install -r mars-box-doc-summarizer/requirements.txt
cd mars-box-doc-summarizer && pytest -q && python scripts/smoke_invoke.py
```

Offline: no API key, no network, no binary (mocked Box client + fake `box-mount` script).

## MARS

Spec: `specs/mars-box-doc-summarizer.yaml` (`size: mars-2vcpu-4gb`, `permissions.default: ask`).
Webhook trigger: `specs/mars-box-doc-summarizer-trigger.yaml`. Chat: `Summarize folder 123456789`, `Refresh`, `help`.
Programmatic input: `{"folder_id": "...", "auto_approve": false}`.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `Box JWT auth failed` | App authorized by an admin? Correct JSON? |
| `HTTP 404` on folder | Service account invited to the folder as Editor |
| Links point at the folder | File ids unavailable (fixture/mount without JWT) |
| Box Mount `not a Linux binary` | URL must be a direct download, not the shared-link web page |

## License

MIT
