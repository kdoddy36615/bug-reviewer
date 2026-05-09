---
name: ado-bug-lifecycle
description: Pick up or abandon an ADO bug — store the previous assignee, transition state to Active or back to New, and write/restore the session state file used for resume. Use when the user says "pick up bug X", "take bug X", "abandon bug X", "rollback bug X", or when the orchestrator transitions a bug at the start or end of work.
allowed-tools: Bash, Read, Write
---

# Azure DevOps — Bug Lifecycle

Owns state transitions on ADO work items. Every bug set to `Active` must end in either a merged PR or an explicit rollback to `New` — no orphans.

---

## Hard rule — store PREV_ASSIGNEE first

Before changing state, capture the existing assignee. You need it to roll back cleanly.

```bash
PREV_ASSIGNEE=$(az boards work-item show --id <WORK_ITEM_ID> --output json \
  | jq -r '.fields."System.AssignedTo".uniqueName // ""')
```

If `PREV_ASSIGNEE` is empty (bug was Unassigned), the rollback should leave it unassigned — pass an empty string to `--assigned-to`.

---

## Pick up — set Active and assign to self

```bash
az boards work-item update --id <WORK_ITEM_ID> \
  --state "Active" \
  --assigned-to "$AZURE_ASSIGNEE_EMAIL"
```

`--assigned-to` accepts email or display name. Email is more reliable. **Do not pass a GUID.**

---

## Write session state — immediately after pickup

This protects against session token limits or crashes mid-session.

```bash
cat > /tmp/bug-session-state.json <<EOF
{
  "activeBugs": [
    { "id": <WORK_ITEM_ID>, "prevAssignee": "$PREV_ASSIGNEE" }
  ]
}
EOF
```

If multiple bugs are being picked up in a triage session, append to `activeBugs` rather than overwriting.

**On session resume:** the orchestrator (`bug-triage-session`) reads this file first and either finishes or rolls back any in-progress bug before starting new work.

---

## Abandon / rollback — restore state and assignee

If a bug cannot be finished:

```bash
az boards work-item update --id <WORK_ITEM_ID> \
  --state "New" \
  --assigned-to "$PREV_ASSIGNEE"
```

After rollback, remove the bug from `/tmp/bug-session-state.json`.

---

## Valid states

`New`, `Active`, `Resolved`, `Closed`. The triage flow only ever transitions between `New` and `Active` — `Resolved`/`Closed` are set by the team after PR merge.

Custom fields (rare) use `--fields "FieldName=value"` — space-separated key=value pairs.

---

## Hard rules

- **Never change state without storing `PREV_ASSIGNEE` first.**
- **Every Active pickup ends in a PR or a rollback.** If you set a bug to `Active` and the work doesn't ship, roll it back before ending the session.
- Use email, not GUID, for `--assigned-to`.
