---
name: bug-triage-session
description: Run an end-to-end bug triage session against the configured ADO board — query new bugs, rank, fix Easy ones in a batch, run the local reviewer UI, and open a draft PR. Use when the user says "bug triage session", "fix new bugs", "start a bug session", "process new bugs", or similar. This is the orchestrator skill — it invokes the domain skills in sequence.
---

# Bug Triage Session — Orchestrator

You are running an end-to-end bug fix session against the configured target codebase. This skill owns sequencing. Domain work delegates to other skills.

---

## Critical sequence

**The reviewer is the gate, not an afterthought.** The correct order is:

```
story → current screenshot → fix → fixed screenshot → repeat for all bugs
→ reviewer (BEFORE commit) → commit → draft PR
```

Never commit fixes or open the PR before the reviewer has approved every bug. No exceptions.

---

## Session startup — always do this first

1. **Resume check**: read `/tmp/bug-session-state.json` if it exists. If there are `activeBugs`, finish or roll them back (via `ado-bug-lifecycle`) before starting anything new.
2. **Verify dev server**: `curl -sk $PREVIEW_BASE_URL | head -5`. If it fails, tell the user to run `$DEV_COMMAND` in the target repo and stop.
3. **Source env**: confirm `$AZURE_ASSIGNEE_EMAIL`, `$STORYBLOK_MANAGEMENT_TOKEN`, `$DRAFT_SECRET_TOKEN`, `$TARGET_REPO_PATH` are set. If missing, tell the user to run `set -a && source .env && set +a`.
4. **Cut a clean branch in the target repo**:
   ```bash
   cd $TARGET_REPO_PATH
   git checkout dev && git pull origin dev
   git checkout -b cms/bugfix/<short-descriptive-name>
   pnpm install   # or npm/yarn equivalent for the target repo
   ```
   Branch name should hint at the batch (e.g. `cms/bugfix/triage-2026-05-09`).

---

## Step 1 — Query and rank bugs

Invoke **`ado-bug-query`** to get the list of `New` bugs with full details and screenshots downloaded.

Rank each bug **Easy / Medium / Hard**:

| Difficulty | Criteria |
|------------|----------|
| **Easy** | Pure CSS/Tailwind fix, well-understood component, high confidence, single file |
| **Medium** | Logic change, multiple files, or moderate uncertainty |
| **Hard** | Architecture change, unclear root cause, CMS schema change needed, or cross-package impact |

**Only fix Easy bugs in this session.** List Medium/Hard for the user at the end.

### Stop conditions — ask the user, do not guess

- **Uncertain about the correct fix** (e.g. which gradient is expected, which design variant) — stop and ask before implementing.
- **Bug cannot be reproduced in an isolated CMS story** (e.g. it requires referencing another story, or a page configuration that can't be recreated) — stop and tell the user. Do not proceed without a way to capture before/after screenshots.

---

## Step 2 — Fix each bug, one at a time

For each Easy bug, in sequence:

1. **Pick up** — invoke **`ado-bug-lifecycle`** to store `PREV_ASSIGNEE`, set state to `Active`, assign to self, and write the session state file.
2. **Create the CMS story** (if your stack uses one) — invoke **`storyblok-bugfix-story`** to create and publish an isolated preview story.
3. **Capture the CURRENT (broken) screenshot** — invoke **`bug-capture`** with code still unfixed.
4. **Implement the code fix** in the target repo.
5. **Run** the type-checker for the target repo (e.g. `pnpm type-check`); ignore pre-existing errors.
6. **Capture the FIXED screenshot** — invoke **`bug-capture`** again.
7. **Append the merged payload** to `bugs.json` (see `bug-capture` for schema).

Do not batch all fixes before capturing. The current screenshot must be taken **before** the fix is applied — once the code changes, you can't recover the broken state.

---

## Step 3 — Run the reviewer (BEFORE commit)

Invoke **`bug-reviewer-run`** with the populated `bugs.json`. Wait for the user to finish reviewing.

After the reviewer exits, read `results.json`. For any bug with `"status": "feedback"` — address the feedback before proceeding. Do not move on to commit/PR until every bug is approved.

---

## Step 4 — Pre-PR completion checklist

Before committing, verify:

- [ ] Unit tests updated where applicable (`.test.tsx` or equivalent)
- [ ] Storybook stories updated where applicable (`.stories.tsx` or equivalent)
- [ ] Docs updated where applicable
- [ ] Type-checking passes (ignore pre-existing errors)
- [ ] Build artifacts stashed or `.gitignore`d
- [ ] **No AI tool references** in committed files or commit messages

---

## Step 5 — Commit and open draft PR

```bash
git add <specific files>
git commit -m "Bug fixes: <short description>"
git push -u origin <branch-name>
```

No `git add -A` — stage specific files only. No AI references in commit messages.

Then invoke **`ado-pr-create`** with the list of work item IDs.

---

## Step 6 — Report to user

Give the user:
1. PR link
2. Table of bugs fixed (use the format from `ado-pr-create`)
3. Medium/Hard bugs with one-line difficulty reasoning — ask whether to continue with a Medium/Hard pass

---

## Hard rules

- **Reviewer before commit.** Always.
- **Easy only** in a triage session. Medium/Hard go to the user for explicit approval.
- **Never guess on uncertain fixes.** Ask.
- **Every bug set to `Active` ends in either a PR or a rollback** — see `ado-bug-lifecycle`. No bug stays orphaned.
- **The dev server must be running** at `$PREVIEW_BASE_URL` before any screenshots.
