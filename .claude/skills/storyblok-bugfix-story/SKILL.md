---
name: storyblok-bugfix-story
description: Create, find, or publish a Storyblok story under the configured bug-fix folder for an isolated bug-fix preview, and build the localhost preview URL. Use when the user says "create a bugfix story", "publish to Storyblok", "find the bugfix story for X", or when the orchestrator needs an isolated preview page for screenshot capture.
allowed-tools: Bash, Read
---

# Storyblok — Bug Fix Story

Story management is **curl-only against the management API**. The Storyblok CLI cannot create, read, or find stories — only push component schemas (see `storyblok-component-push`).

---

## Auth — the most common failure point

The personal access token uses **no `Bearer` prefix**:

```bash
# CORRECT
-H "Authorization: $STORYBLOK_MANAGEMENT_TOKEN"

# WRONG — will return 401
-H "Authorization: Bearer $STORYBLOK_MANAGEMENT_TOKEN"
```

**Base URL**: pick the region matching your space.
- US region: `https://api-us.storyblok.com/v1`
- EU region: `https://api.storyblok.com/v1`

This skill assumes US — adjust if your space is in EU.

---

## Folder ID

The bug-fix folder ID is stored in `$STORYBLOK_BUGS_FOLDER_ID` (set in `.env`).

To find it once for your space:

```bash
curl -s \
  "https://api-us.storyblok.com/v1/spaces/$STORYBLOK_SPACE_ID/stories?starts_with=pages/dev/bugs&folder_only=true" \
  -H "Authorization: $STORYBLOK_MANAGEMENT_TOKEN" \
  | jq '.stories[] | select(.full_slug == "pages/dev/bugs") | .id'
```

Adjust `starts_with=` if your team uses a different folder path.

---

## Find existing bug fix stories

```bash
curl -s \
  "https://api-us.storyblok.com/v1/spaces/$STORYBLOK_SPACE_ID/stories?starts_with=pages/dev/bugs/&story_only=true" \
  -H "Authorization: $STORYBLOK_MANAGEMENT_TOKEN" \
  | jq '.stories[] | {id, name, full_slug, parent_id}'
```

---

## Create a bug fix story

The example below uses a `general_page` content type with `title`, `title_short`, `description_short` (richtext), and `meta_tags` (bloks). If your space uses a different content type, adjust the JSON shape accordingly.

```bash
curl -s -X POST \
  "https://api-us.storyblok.com/v1/spaces/$STORYBLOK_SPACE_ID/stories" \
  -H "Authorization: $STORYBLOK_MANAGEMENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "story": {
      "name": "bugfix-<component>-<bug_id>",
      "slug": "bugfix-<component>-<bug_id>",
      "parent_id": '"$STORYBLOK_BUGS_FOLDER_ID"',
      "content": {
        "component": "general_page",
        "_uid": "'$(uuidgen | tr '[:upper:]' '[:lower:]')'",
        "title": "<Bug title from issue tracker>",
        "title_short": "<Bug title from issue tracker>",
        "description_short": {
          "type": "doc",
          "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "<one sentence summary>" }] }]
        },
        "meta_tags": [{
          "component": "meta_tags",
          "_uid": "'$(uuidgen | tr '[:upper:]' '[:lower:]')'",
          "meta_description": "<one sentence summary>"
        }]
      }
    }
  }'
```

Full slug after creation: `pages/dev/bugs/bugfix-<component>-<bug_id>` (or whatever your folder path is).

---

## Publish the story

```bash
curl -s -X GET \
  "https://api-us.storyblok.com/v1/spaces/$STORYBLOK_SPACE_ID/stories/<STORY_ID>/publish" \
  -H "Authorization: $STORYBLOK_MANAGEMENT_TOKEN"
```

---

## Preview URL pattern

```
$PREVIEW_BASE_URL/{full_slug minus "pages/"}?secret=$DRAFT_SECRET_TOKEN&slug={full_slug URL-encoded}
```

Example for `pages/dev/bugs/bugfix-tabs-99001`:

```
https://localhost:3000/dev/bugs/bugfix-tabs-99001?secret=$DRAFT_SECRET_TOKEN&slug=pages%2Fdev%2Fbugs%2Fbugfix-tabs-99001
```

**Do NOT include `_storyblok=<id>` in screenshot URLs** — that activates the visual editor overlay and pollutes the screenshot. Use `secret` + `slug` only.

The dev server must be running at `$PREVIEW_BASE_URL` before any preview is fetched.

**SSL note**: if your dev server runs HTTPS with a self-signed cert, `capture.js` already sets `ignoreHTTPSErrors: true`. For Playwright MCP, navigate then call `page.keyboard.type('thisisunsafe')` to bypass the interstitial (Chromium).

---

## Naming convention

| Thing | Format | Example |
|-------|--------|---------|
| Component | `bugfix_<component_name>_<bug_id>` (underscores) | `bugfix_tabs_99001` |
| Story slug | `bugfix-<component-name>-<bug_id>` (hyphens) | `bugfix-tabs-99001` |
| Story location | configured in `$STORYBLOK_BUGS_FOLDER_ID` | `pages/dev/bugs/bugfix-tabs-99001` |

---

## Hard rules

- **Never delete or modify existing stories** outside the bug-fix folder. Treat the rest of the space as read-only.
- **Auth header has no `Bearer` prefix.** Use `Authorization: $STORYBLOK_MANAGEMENT_TOKEN` directly.
- **Use the API region matching your space** (`api-us` for US, `api` for EU). Not `mapi.storyblok.com`.
- **Do not include `_storyblok=` in preview URLs** for screenshots.
