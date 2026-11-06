---
sidebar_position: 14
---

# 🤖 AI agents

AI coding agents, such as Claude Code, Codex or Cursor, can set up Django Headless and write frontend code against the API. Give them the Django Headless skill or the Markdown version of this documentation, so they use the decorator options and settings instead of writing serializers and viewsets by hand.

## Agent skill

The Django Headless skill is a `SKILL.md` file in the [Agent Skills](https://agentskills.io) format. It covers the setup, the `@expose()` options, permissions and authentication, the query parameters of the API and the TypeScript client. An agent loads it when a task involves Django Headless.

In Claude Code, install it as a plugin:

```text
/plugin install django-headless --marketplace dwarsbit/django-headless
```

For other agents, install it with the [skills](https://www.npmjs.com/package/skills) command, which asks which agents to install it for:

```bash
npx skills add dwarsbit/django-headless
```

To install it by hand, copy the [`skills/django-headless`](https://github.com/dwarsbit/django-headless/tree/main/skills/django-headless) folder of the repository into the skills folder of your agent, such as `.claude/skills/` in your project.

## Documentation for agents

This documentation is also available as Markdown, following the [llms.txt](https://llmstxt.org) convention:

- [`/llms.txt`](https://djangoheadless.org/llms.txt): an index of the pages, with a link to the Markdown of each page.
- [`/llms-full.txt`](https://djangoheadless.org/llms-full.txt): every page in one file.
- `/docs/<page>.md`: the Markdown of one page, such as [`/docs/filtering.md`](https://djangoheadless.org/docs/filtering.md).

Point an agent that has no skills to `https://djangoheadless.org/llms.txt`, for example in the `AGENTS.md` of your project.

## Related pages

- [Installation](./installation.md)
- [TypeScript client](./client.md)
