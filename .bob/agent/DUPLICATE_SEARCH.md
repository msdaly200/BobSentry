# Bob-Sentry — Duplicate Issue Search

> **This file is loaded automatically when the `/triage <issue> searchDup` flag is
> present. Do not skip it — duplicate detection MUST complete before any triage pipeline
> action is taken.**

---

## Purpose

Before committing triage resources to a new issue, determine whether an equivalent or
closely related vulnerability has already been reported, triaged, or fixed in the
`keycloak/keycloak` repository. If one or more duplicates are found, **halt the pipeline
and report them**. Do not proceed to CVE analysis, sandbox provisioning, or script
generation until the engineer confirms how to proceed.

---

## When to Run

Run this search by default — i.e. whenever the user invokes:

```
/triage <issue-number>
```

Skip this search (proceed directly to Step 1 of the triage pipeline) only when the
user explicitly passes the opt-out flag:

```
/triage <issue-number> --skip-dups
```

---

## Duplicate Search Procedure

### Step D1 — Fetch the Target Issue

Read the issue to be triaged:

```bash
gh issue view <issue-number> --repo keycloak/keycloak --comments
```

Extract and record:
- **Title** (full text)
- **Body** — first 500 characters (enough to extract key technical terms)
- **Labels** — especially `kind/cve`, `area/*`, `priority/*`
- **Assignees** and **milestone** (if any)

---

### Step D1.5 — Local Index Search (fast, offline)

Before making any network call, grep `.bob/reports/index.json` for signals that this
issue — or a closely related one — has already been triaged locally.

Run all three checks unconditionally and collect every matching session object:

```bash
# Check 1 — exact issue number re-triage
grep -i '"issue_number".*"<issue-number>"' .bob/reports/index.json

# Check 2 — same report_folder (attack-class cluster)
grep -i '"report_folder".*"<folder-keyword>"' .bob/reports/index.json

# Check 3 — attack_type substring overlap (use the most specific noun phrase
#            extracted in Step D2; run this after D2 if needed, or skip if
#            no specific noun phrase is available yet)
grep -i '"attack_type".*"<attack-noun-phrase>"' .bob/reports/index.json
```

> **How to derive `<folder-keyword>`:** use the generic attack-class term extracted
> from the issue (e.g. `SSRF`, `TOCTOU`, `FGAP`, `novel-pattern`).

For each matching session object, record:
- `issue_number`, `report_folder`, `attack_type`, `verdict`, `severity`, `triage_date`
- `session_path` (links to the existing local report)

**Scoring (feeds into Step D4):**

| Local index signal | Score |
|--------------------|-------|
| `issue_number` exact match | +6 (definitive re-triage of same issue) |
| `report_folder` match **and** `attack_type` substring overlap | +4 |
| `report_folder` match only | +2 |
| `attack_type` substring overlap only | +2 |

A local index hit with score ≥ 3 is a **candidate duplicate** — treat it identically
to a high-scoring GitHub result in Step D5.

If the local index is empty or no check matches, proceed silently to Step D2.

---

### Step D2 — Extract Search Terms

From the issue title and body, extract a ranked list of search terms. Apply this
priority order:

1. **CVE identifier** — if the issue title or body contains a `CVE-YYYY-NNNNN` string,
   use it as the primary search term. CVE IDs are unique; a match is a definitive duplicate.
2. **Technical noun phrases** — e.g. `CIBA notification endpoint`, `backchannel logout`,
   `redirect_uri`, `role rename`, `FGAP unassign`. These are specific enough to reduce
   noise.
3. **Error/endpoint strings** — e.g. `/ext/ciba/auth`, `UriUtils.checkUrl`,
   `client_session_host`. Use these as secondary terms to narrow results.
4. **Generic attack-class keywords** — e.g. `SSRF`, `TOCTOU`, `parameter pollution`.
   Use these only if no more specific terms are available; they will produce broader results.

Assemble up to **3 distinct search queries** from the above terms, from most specific
to least specific.

---

### Step D3 — Search the GitHub Repository

Execute up to 3 searches using the GitHub CLI. Always search both **open** and **closed**
issues. Use READ-ONLY GitHub operations only.

```bash
# Search 1 — most specific (e.g. CVE ID or exact technical term)
gh issue list --repo keycloak/keycloak --search "<term-1>" --state all --limit 10 \
  --json number,title,state,labels,createdAt,url

# Search 2 — secondary technical term
gh issue list --repo keycloak/keycloak --search "<term-2>" --state all --limit 10 \
  --json number,title,state,labels,createdAt,url

# Search 3 — attack-class keyword (if searches 1 and 2 produce no results)
gh issue list --repo keycloak/keycloak --search "<term-3>" --state all --limit 10 \
  --json number,title,state,labels,createdAt,url
```

**Never search more than 3 times.** If all 3 searches return empty results, proceed
to Step D5 (No Duplicates Found).

---

### Step D4 — Score and Filter Results

For each result returned, score it against the target issue using these criteria:

| Signal | Score |
|--------|-------|
| **Local index:** `issue_number` exact match | +6 (definitive re-triage) |
| **Local index:** `report_folder` + `attack_type` substring overlap | +4 |
| **Local index:** `report_folder` match only | +2 |
| **Local index:** `attack_type` substring overlap only | +2 |
| Same CVE identifier in title or body | +5 (definitive duplicate) |
| Same affected component (from `area/*` label match) | +2 |
| Same attack type keyword in title | +2 |
| Same `kind/cve` label | +1 |
| Issue is CLOSED with label `duplicate` or `wontfix` | note this explicitly |
| Issue is a PR (skip) | discard |

**Threshold:** Any result with score ≥ 3 is a **candidate duplicate**.

Discard:
- Pull requests (URLs containing `/pull/`)
- Issues with only generic label matches and no title/body overlap
- The target issue itself (same issue number)

---

### Step D5 — Report the Outcome

#### If candidate duplicates are found (score ≥ 3):

Output the following and **HALT THE PIPELINE**:

```
╔══════════════════════════════════════════════════════════════╗
║  DUPLICATE SEARCH — keycloak/keycloak#<issue-number>         ║
╠══════════════════════════════════════════════════════════════╣
║  Result: POSSIBLE DUPLICATES FOUND — Triage halted           ║
╚══════════════════════════════════════════════════════════════╝

## Local Index Hits

| # | Issue | Report Folder | Attack Type | Verdict | Triage Date | Report Path |
|---|-------|---------------|-------------|---------|-------------|-------------|
| 1 | #NNNNN | <folder> | <attack_type> | confirmed/not-vuln | YYYY-MM-DD | <session_path> |

_(Omit this section if no local index matches were found.)_

## Candidate Duplicates (GitHub)

| # | Issue | Title | State | Score | URL |
|---|-------|-------|-------|-------|-----|
| 1 | #NNNNN | <title> | open/closed | N/5 | <url> |
| 2 | ... | ... | ... | ... | ... |

## Recommendation

Review the issues above before proceeding. If these are confirmed duplicates:
- Link this issue to the existing one and close.

If they are NOT duplicates (different root cause or different component):
- Type `/triage <issue-number>` to proceed with triage (duplicate search will run again).
- Or type `/triage <issue-number> --skip-dups` to bypass the duplicate check entirely.
```

Do **not** proceed to CVE analysis, sandbox provisioning, or script generation.
Do **not** post any comment or link on GitHub.

---

#### If no candidate duplicates are found (all scores < 3 or all searches empty):

Output:

```
╔══════════════════════════════════════════════════════════════╗
║  DUPLICATE SEARCH — keycloak/keycloak#<issue-number>         ║
╠══════════════════════════════════════════════════════════════╣
║  Result: NO DUPLICATES FOUND — Proceeding with triage        ║
╚══════════════════════════════════════════════════════════════╝

Local index checked: yes (0 matches)
Search terms used: ["<term-1>", "<term-2>", "<term-3>"]
GitHub issues examined: <N>
```

Then **automatically continue** to Step 1 of the standard triage pipeline
(fetch the issue, activate CVE Analyzer, etc.) without requiring further input from
the engineer.

---

## Rules

- This search is **READ-ONLY**. No writes, comments, or edits to any GitHub issue.
- The `gh` CLI is the only permitted GitHub access method.
- If `gh` is unavailable or unauthenticated, output:
  ```
  ERROR: GitHub CLI (gh) not available. Cannot perform duplicate search.
  To skip duplicate check and proceed directly, type: /triage <issue-number> --skip-dups
  ```
- Results are displayed inline in the chat only. Nothing is written to `.bob/reports/`
  for the duplicate search phase — reports are only written after a full triage completes.
