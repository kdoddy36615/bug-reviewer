---
name: bug-capture
description: Run capture.js to take a before/after screenshot of a bug fix and build the bug-reviewer payload entry — including issue-tracker screenshots, computed styles, and a parsed git diff. Use when the user says "capture the bug", "take before/after screenshots", "build the payload for bug X", or when the orchestrator runs current/fixed captures during the fix loop.
allowed-tools: Bash, Read, Write, Edit
---

# Bug Capture

Wraps `capture.js` to produce one entry in `bugs.json`. Each bug is captured **twice** — once before the fix (current/broken), once after (fixed). The two payloads are merged into a single entry.

The dev server must be running at `$PREVIEW_BASE_URL` before any capture.

---

## Capture config schema

Write a config file (e.g. `/tmp/bug-<ID>-config.json`):

```json
{
  "id": 12345,
  "title": "Bug title from issue tracker",
  "description": "<p>HTML from issue tracker description</p>",
  "adoScreenshots": ["/tmp/bug-12345-issue-1.png"],
  "currentUrl": "https://localhost:3000/dev/bugs/bugfix-component-12345?secret=$DRAFT_SECRET_TOKEN&slug=pages%2Fdev%2Fbugs%2Fbugfix-component-12345",
  "fixedUrl":   "https://localhost:3000/dev/bugs/bugfix-component-12345?secret=$DRAFT_SECRET_TOKEN&slug=pages%2Fdev%2Fbugs%2Fbugfix-component-12345",
  "selector":   "[data-c='my-component']",
  "styles":     ["background-color", "border-color"],
  "repoPath":   "$TARGET_REPO_PATH"
}
```

**Always set `selector`** — target the specific component, not the full page. Full-page screenshots are noisy and hide the diff.

---

## Capture order — strict

The CURRENT screenshot must be captured **before** the fix is applied. Once the code changes, the broken state can't be recovered.

### 1. CURRENT (broken) — code unfixed

Set `currentUrl` only. Omit `fixedUrl`.

```bash
node ~/projects/bug-reviewer/capture.js /tmp/bug-12345-config-current.json /tmp/bug-12345-payload-current.json
```

### 2. Implement the fix in the target repo.

### 3. FIXED — code patched

Set `fixedUrl` only. Omit `currentUrl`.

```bash
node ~/projects/bug-reviewer/capture.js /tmp/bug-12345-config-fixed.json /tmp/bug-12345-payload-fixed.json
```

The fixed pass also runs `git diff --unified=3` in `repoPath` and parses it into the `codeDiff` field of the payload.

### 4. Merge the two payloads into `bugs.json`

Final entry shape (combine fields from both passes):

```json
{
  "id": 12345,
  "title": "Bug title from issue tracker",
  "description": "<p>HTML from issue tracker</p>",
  "problem": "One sentence: what the user was seeing",
  "fix": "One sentence: what changed in the code, with `backtick` references",
  "adoScreenshots": ["/tmp/bug-12345-issue-1.png"],
  "currentScreenshot": "/tmp/bug-12345-current.png",
  "fixedScreenshot": "/tmp/bug-12345-fixed.png",
  "codeDiff": {
    "path": "packages/ui/src/components/Button/Button.tsx",
    "hunk": "@@ -42,7 +42,7 @@",
    "lines": [
      { "type": "ctx", "oldNo": 42, "newNo": 42, "content": "  const base = cva(..." },
      { "type": "del", "oldNo": 43, "newNo": null, "content": "    'bg-blue-600'" },
      { "type": "add", "oldNo": null, "newNo": 43, "content": "    'bg-blue-700'" }
    ]
  }
}
```

`problem` and `fix` are written by Claude (one sentence each) — `capture.js` leaves them empty.

`problem`, `fix`, and `codeDiff` are optional — the reviewer UI has graceful fallbacks. Legacy `currentStyles`/`fixedStyles` still render if present but are deprecated in favor of `codeDiff`.

---

## Output paths

`capture.js` always writes screenshots to `/tmp/bug-<id>-current.png` and `/tmp/bug-<id>-fixed.png`. You can rely on those paths in the merged payload.

---

## Hard rules

- **The dev server must be running** at `$PREVIEW_BASE_URL` before any capture. Verify with `curl -sk $PREVIEW_BASE_URL | head -5`.
- **Capture CURRENT before applying the fix.** Never reverse the order.
- **Always set `selector`.** Full-page captures are too noisy.
- **No `_storyblok=` query param** in capture URLs (see `storyblok-bugfix-story`).
