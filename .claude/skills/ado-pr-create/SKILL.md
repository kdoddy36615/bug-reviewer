---
name: ado-pr-create
description: Create a draft pull request in Azure DevOps for the bug fixes — sets the required reviewer, optional reviewers, and links work items in a single command. Owns the PR description format and the reviewer table. Use when the user says "open the PR", "create draft PR", "ship the bugs", or when the orchestrator finishes the reviewer step.
allowed-tools: Bash, Read
---

# Azure DevOps — Draft PR Creation

One-shot PR creation. All reviewers and work items are set at creation time — no follow-up commands needed.

---

## Prerequisites

- Branch is pushed to origin: `git push -u origin <branch-name>`
- Reviewer has approved every bug in `results.json` (no `"status": "feedback"` outstanding)
- Type-checking passes (ignore pre-existing errors)
- No AI references in commits

---

## Single command — create the PR

Reviewers come from `.env`:
- `$YOUR_REQUIRED_REVIEWER_EMAIL` — set as required at PR creation
- `$YOUR_REVIEWER_1_EMAIL`, `$YOUR_REVIEWER_2_EMAIL` — added as optional reviewers

```bash
az repos pr create \
  --title "<short title under 70 chars>" \
  --description "$(cat <<'EOF'
<see PR description format below>
EOF
)" \
  --draft \
  --source-branch <branch-name> \
  --target-branch dev \
  --work-items <ID1> <ID2> ... \
  --required-reviewers "$YOUR_REQUIRED_REVIEWER_EMAIL" \
  --reviewers "$YOUR_REVIEWER_1_EMAIL" "$YOUR_REVIEWER_2_EMAIL"
```

`--required-reviewers` and `--work-items` work at creation. **Do not** chain follow-up `az repos pr reviewer add` or `az repos pr work-item add` — the create command handles both.

`az repos pr reviewer add` does not have a `--required` flag.

---

## PR description format

Keep it short — ADO has a 4000-character limit and a batch of 12+ bugs hits it fast.

```markdown
## Bug Fixes

| # | Bug | Fix |
|---|-----|-----|
| [12345](https://dev.azure.com/<YOUR_AZURE_ORG>/<YOUR_AZURE_PROJECT>/_workitems/edit/12345) | Header alignment off on mobile | Constrained container to `max-w-screen-md` |
| [12346](https://dev.azure.com/<YOUR_AZURE_ORG>/<YOUR_AZURE_PROJECT>/_workitems/edit/12346) | Icon weight inconsistent | Updated to `weight="regular"` consistently |

## Remaining Bugs (not in this PR)

**Medium:**
- 12347 — Title — reason it's medium

**Hard:**
- 12348 — Title — reason it's hard
```

ADO work item URL pattern: `$AZURE_ORG/$AZURE_PROJECT/_workitems/edit/<ID>`

---

## Reviewer reference

The reviewers below are an example layout — configure your own in `.env` as `YOUR_REQUIRED_REVIEWER_EMAIL`, `YOUR_REVIEWER_1_EMAIL`, `YOUR_REVIEWER_2_EMAIL`.

| Reviewer | Env var | Role |
|----------|---------|------|
| Tech Lead (**required**) | `$YOUR_REQUIRED_REVIEWER_EMAIL` | Required at PR creation |
| Reviewer 1 | `$YOUR_REVIEWER_1_EMAIL` | Optional |
| Reviewer 2 | `$YOUR_REVIEWER_2_EMAIL` | Optional |

If your team uses GUIDs instead of emails for some flows (e.g. ADO REST API), look up the GUID once with `az devops user show --user <email>` and store it alongside the email in `.env` (e.g. `YOUR_REQUIRED_REVIEWER_ID`). The `az repos pr create` flags accept email — GUIDs are only needed for direct REST calls.

---

## Hard rules

- **Always `--draft`.** Never open a non-draft PR from this flow.
- **Target branch is `dev`** (or whatever your team's integration branch is). Never `main` or `master` directly from this flow.
- **No AI references** in title or description.
- Set required reviewer at creation — there's no clean way to make it required afterwards via CLI.
