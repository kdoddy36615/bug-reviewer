# Bug Reviewer — Claude Playbook

The bug-fix workflow lives in **skills**, not in this file. This file is a thin pointer — see `.claude/skills/` for everything else.

---

## Entry point

When the user asks to fix bugs, triage new bugs, run a bug session, or ship bug fixes — **invoke the `bug-triage-session` skill**. It orchestrates the full flow and pulls in the domain skills as needed.

---

## Available skills (in `.claude/skills/`)

| Skill | When it loads |
|-------|---------------|
| `bug-triage-session` | Top-level orchestrator for an end-to-end bug session |
| `ado-bug-query` | Listing new bugs from the configured ADO board |
| `ado-bug-lifecycle` | Picking up / abandoning bugs (state + assignee) |
| `ado-pr-create` | Creating a draft PR with reviewers + work items |
| `storyblok-bugfix-story` | Creating, finding, or publishing a bugfix story |
| `storyblok-component-push` | Pushing a new `bugfix_*` component schema |
| `bug-capture` | Running `capture.js` for before/after screenshots |
| `bug-reviewer-run` | Launching the local reviewer UI |

One-time human setup (Node, pnpm, Azure CLI, Playwright, Python, Figma MCP) lives in `README.md`.

---

## Adding a design-reference skill

If your codebase has design-system conventions (color tokens, spacing variants, common component patterns, gradient names, max-width policies), add a domain-reference skill at `.claude/skills/<your-design>-reference/SKILL.md`. The skill should load on triggers like "backdrop", "gradient", "max-width", "spacing token" — whatever the agent is likely to encounter when fixing visual bugs in your codebase — and supply reference data the agent would otherwise have to grep for. Keep it scoped to reference data; commands and rules belong in domain skills.

---

## Cross-domain hard rules

These apply across all skills — keep them in mind whenever working in this repo:

1. **No AI references** in committed files, commit messages, or PR descriptions.
2. **The dev server must be running** at `$PREVIEW_BASE_URL` (default `https://localhost:3000`) before any screenshot capture.
3. **Never touch CMS stories or components outside the bug-fix scope** (e.g. the `pages/dev/bugs/` folder and `bugfix_*` components for Storyblok). Treat the rest of the CMS as read-only.
4. **Source `.env` before starting**: `set -a && source .env && set +a`. The skills assume `$AZURE_ASSIGNEE_EMAIL`, `$STORYBLOK_MANAGEMENT_TOKEN`, `$DRAFT_SECRET_TOKEN`, and `$TARGET_REPO_PATH` are available.
