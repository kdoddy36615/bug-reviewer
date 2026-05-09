---
name: bug-reviewer-run
description: Launch the local bug-reviewer web UI (server.js) so the user can approve or request changes on each bug before a PR is created. Reads bugs.json, writes results.json. Use when the user says "run the reviewer", "open the review UI", "launch the reviewer", or when the orchestrator hits Step 5 of the triage flow.
allowed-tools: Bash, Read
---

# Bug Reviewer — Local UI

Spawns `server.js` with the populated `bugs.json`. The server exits automatically when the user finishes reviewing every bug.

---

## Launch — use Bash with `run_in_background: true`

The Bash tool's `run_in_background: true` parameter triggers an automatic notification when the process exits. Use it. Do not append `&` and do not poll with `curl`.

```bash
node ~/projects/bug-reviewer/server.js bugs.json results.json
```

**Correct invocation:**

- `command`: `node ~/projects/bug-reviewer/server.js bugs.json results.json`
- `run_in_background`: `true`

**Wrong** (will fire the notification too early — when the wrapper shell exits, not when `server.js` exits):

```bash
node ~/projects/bug-reviewer/server.js bugs.json results.json & sleep 1 && echo done
```

---

## Tell the user

After launching, say (verbatim or close):

> Reviewer is up at http://localhost:3737 — open it and review. I'll be notified automatically when you're done.

Do not poll or check status. The notification fires when the server exits.

---

## After the reviewer exits — read results.json

```bash
cat results.json | jq '.[] | {id, status}'
```

For any bug with `"status": "feedback"`, the user has requested changes. Address the feedback before continuing to commit/PR. Do not move to `ado-pr-create` until every bug is `approved`.

---

## Hard rules

- **Use `run_in_background: true`.** Not `&`. Not polling.
- **Reviewer runs before commit and PR.** No exceptions — see the orchestrator's sequencing rule.
- **Address `feedback` status bugs before proceeding.** Re-run the capture if needed and re-launch the reviewer.
