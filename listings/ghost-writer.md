# Ghost Writer

## Summary

Research the web, draft a full HTML post, and publish only when you say go.
An AI blog author for Ghost or WordPress, without surprise posts.

## Description

Ghost Writer is a content agent for operators and marketers who want researched, publish-ready blog posts without giving an AI an unsupervised byline. Describe a topic; the agent brainstorms angles, searches the web for current context, and presents a complete HTML draft in chat so you can edit, reject, or green-light publish.

Use it when you need a steady cadence of posts but still want editorial control. In chat mode, nothing hits Ghost or WordPress until you confirm. For scheduled or headless runs, an explicit publish sentinel lets you automate the pipeline when you are ready to trust the loop.

Ideal for product blogs, developer education, changelog-style explainers, and anyone who wants research-backed drafts that land in their CMS, with a human gate before the public post.

### Why use it

- Full HTML drafts in chat: title, body, and structure ready to review
- Web research for current angles before the draft, not after
- Publish only after you confirm (chat) or an explicit publish sentinel (autonomous)
- Native clients for Ghost and WordPress, including optional feature images
- Keeps editorial control: no surprise posts from a runaway agent
- Works for interactive authoring and scheduled / headless publish runs
- Built for DigitalOcean Managed Agents (MARS) with a sandboxed LangGraph runtime

### Getting Started

1. Get credentials for your blog. For Ghost, open **Settings**, **Integrations**, add a custom integration, and copy its Admin API key (`id:secret`). For WordPress, open **Users**, **Profile**, **Application Passwords**, create one, and use `username:application-password`. When you create the agent, set the secrets `BLOG_TYPE` (`ghost` or `wordpress`), `BLOG_URL` (your site root, such as `https://myblog.com`), and `BLOG_API_KEY`. Set `BLOG_TOPIC` to a comma-separated list of the topics you write about.
2. Start a session and send `Write a post about running LangGraph agents on DigitalOcean`. The agent suggests angles, searches the web, and shows a complete HTML draft, then asks whether to publish or change it. Ask for edits as many times as you like. Reply `publish it` to post it live on your blog with a generated feature image when one is available. Nothing is published until you confirm.
3. To publish on a schedule, add a cron trigger. A cron trigger cannot use a spec whose permission default is `ask`, so point it at a copy of the agent spec with `permissions.default: allow`. Each firing starts a fresh session and sends `__GW_PUBLISH__`, which picks one topic from `BLOG_TOPIC`, researches it, skips angles you published recently, and publishes the post without asking. Use chat mode until you trust the drafts.

```shell
doctl harness-runtime triggers create \
  --kind cron \
  --name ghost-writer-weekly \
  --session-mode fresh \
  --spec specs/mars-ghost-writer-trigger.yaml \
  --secret HARNESS_INFERENCE_API_KEY=@~/.secrets/do-inference.key \
  --secret BLOG_TYPE=ghost \
  --secret BLOG_URL=https://myblog.com \
  --secret BLOG_API_KEY=@~/.secrets/blog-api.key \
  --prompt "__GW_PUBLISH__" \
  --cron-expr "0 9 * * 1" \
  --timezone America/New_York \
  --output-mode email \
  --output-email you@example.com
```

`0 9 * * 1` is 09:00 every Monday in the timezone you set. The result email includes the published post's URL. Pause or resume the trigger later with `doctl harness-runtime triggers pause` and `resume`.

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- Strong writing / reasoning models work best (e.g. `deepseek-v4-pro` or comparable)
- Network egress for live web research
- Ghost or WordPress credentials (`BLOG_TYPE`, `BLOG_URL`, `BLOG_API_KEY`) to publish
