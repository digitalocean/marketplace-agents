# marketplace-agents

LangGraph agents shaped for DigitalOcean MARS (Managed Agents / Harness Runtime).

Each agent lives in its own subdirectory. Pin with the same `FRAMEWORK_REPO` + `FRAMEWORK_REPO_SHA` and set `FRAMEWORK_SUBDIR` to the agent folder.

| Subdir | Agent |
|--------|--------|
| `mars-sourced-research-desk` | Sourced Research Desk |
| `mars-nightly-repo-audit` | Nightly Repo Audit |
| `mars-competitor-pulse` | Competitor Pulse |

## MARS pin (per agent)

```yaml
agent: langgraph
template: langgraph
env:
  FRAMEWORK_REPO: "https://github.com/digitalocean/marketplace-agents.git"
  FRAMEWORK_REPO_SHA: "<exact-commit-sha>"
  FRAMEWORK_SUBDIR: "mars-competitor-pulse"  # or mars-sourced-research-desk / mars-nightly-repo-audit
  HARNESS_INFERENCE_BASE_URL: "https://inference.do-ai.run/v1"
  HARNESS_INFERENCE_MODEL: deepseek-v4-pro
secrets:
  HARNESS_INFERENCE_API_KEY: "<set via doctl --secret>"
permissions:
  default: ask
```

Each subdirectory `langgraph.json` registers the graph as **`agent`** (required by the harness invoke path). Install deps via that subdir’s `requirements.txt` (includes `-e .`).
