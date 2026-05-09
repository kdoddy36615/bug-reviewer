---
name: ado-bug-query
description: Query Azure DevOps for new bugs in the configured project, fetch full work item details, and download embedded screenshots. Use when the user asks to "find new bugs", "query ADO", "list new bugs", "what bugs are open", or when the bug-triage-session orchestrator needs the current bug list.
allowed-tools: Bash, Read, Write
---

# Azure DevOps — Bug Query

Read-only against ADO: list `New` bugs, fetch details, download screenshots embedded in description HTML.

---

## Saved query (New Bugs)

The team's saved query GUID is stored in `$ADO_BUGS_QUERY_ID` (set in `.env`). Create the query in ADO once and copy the GUID from the URL.

```bash
az boards query --id $ADO_BUGS_QUERY_ID --output json \
  | jq -r '.[] | select(.fields."System.State" == "New") | "\(.id) | \(.fields."System.AssignedTo".displayName // "Unassigned") | \(.fields."System.Title")"'
```

---

## Full work item details

```bash
az boards work-item show --id <WORK_ITEM_ID> --output json
```

Clean field extraction:

```bash
az boards work-item show --id <WORK_ITEM_ID> --output json \
  | jq -r '.fields | {
      title: ."System.Title",
      state: ."System.State",
      assignedTo: ."System.AssignedTo".uniqueName,
      description: ."System.Description",
      repro: ."Microsoft.VSTS.TCM.ReproSteps"
    }'
```

---

## Downloading screenshots

Screenshots are embedded as `<img>` tags inside the HTML `System.Description` and `Microsoft.VSTS.TCM.ReproSteps` fields. They are **not** separate attachments.

Always re-download fresh — never assume `/tmp/bug-<ID>-*.png` from a previous session still exists.

```bash
# Extract image URLs
az boards work-item show --id <WORK_ITEM_ID> --output json \
  | jq -r '[.fields."System.Description" // "", .fields."Microsoft.VSTS.TCM.ReproSteps" // ""] | join(" ")' \
  | grep -oE 'https://dev\.azure\.com[^"]*fileName=[^"]*'

# Download with bearer token (token can expire — regenerate if 401)
TOKEN=$(az account get-access-token --resource "499b84ac-1321-427f-aa17-267ca6975798" --query accessToken -o tsv)
curl -s -o /tmp/bug-<WORK_ITEM_ID>-1.png \
  -H "Authorization: Bearer $TOKEN" \
  "<IMAGE_URL>"
```

If `az` commands fail with auth errors, ask the user to run `az login`.

---

## ADO work item URL pattern

```
$AZURE_ORG/$AZURE_PROJECT/_workitems/edit/<WORK_ITEM_ID>
```

---

## What this skill does NOT do

- Does not change bug state or assignee — that's `ado-bug-lifecycle`.
- Does not rank bugs Easy/Medium/Hard — the orchestrator (`bug-triage-session`) owns ranking criteria.
