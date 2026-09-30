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

### Requirements

- DigitalOcean Managed Agents / Harness Runtime (sandboxed LangGraph session)
- OpenAI-compatible inference provider (DigitalOcean Gradient / Inference recommended)
- Strong writing / reasoning models work best (e.g. `deepseek-v4-pro` or comparable)
- Network egress for live web research
- Ghost or WordPress credentials (`BLOG_TYPE`, `BLOG_URL`, `BLOG_API_KEY`) to publish
