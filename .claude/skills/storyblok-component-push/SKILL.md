---
name: storyblok-component-push
description: Push a NEW bugfix_* component schema to Storyblok via the CLI and regenerate TypeScript types. Use only when a bug fix requires a new isolated component schema — never to modify existing components. Triggered by "push bugfix component", "regen storyblok types", or when the orchestrator needs a new component schema in place before creating a story.
allowed-tools: Bash, Read
---

# Storyblok — Component Schema Push

Component schemas are the **only** thing the Storyblok CLI is reliable for. Stories themselves are managed via curl (see `storyblok-bugfix-story`).

---

## Workflow

```bash
cd $TARGET_REPO_PATH/packages/cms   # adjust the subpath to wherever your CMS schema lives

# 1. Pull latest (safe, read-only) — always do this first
pnpm storyblok:pull-components

# 2. Push only the NEW bugfix_<name>_<id> component
storyblok components push bugfix_<name>_<id> \
  --space $STORYBLOK_SPACE_ID \
  --path /tmp/storyblok-push/ \
  --separate-files

# 3. Regenerate TypeScript types after any push
pnpm storyblok:types

cd ../..
```

---

## Naming

`bugfix_<component_name>_<bug_id>` — underscores throughout. Example: `bugfix_tabs_99001`.

This is the component name. The corresponding story slug uses hyphens (see `storyblok-bugfix-story`).

---

## Hard rules

- **NEVER delete or modify existing components or content types.** Only push new `bugfix_*` components.
- **Always pull before push.** Confirms you're working from the current schema and avoids overwriting newer changes.
- **Always regenerate types** after a successful push — `pnpm storyblok:types`. The target repo depends on the generated types.
- **Single-component push only.** Do not run `storyblok components push` with no name argument or with a glob — that pushes everything.
