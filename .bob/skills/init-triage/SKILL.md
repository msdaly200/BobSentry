---
name: init-triage
description: '# Command: `/triage`'
metadata:
  user-invocable: true
  disable-model-invocation: true
---

# Command: `/triage`

**Usage:** `/triage <github-issue-number> [searchDup]`
**Examples:**
- `/triage 49427` — fetch issue and begin triage immediately
- `/triage 49427 searchDup` — check for duplicate issues first; halt if duplicates found

**Target repository:** `keycloak/keycloak` (hardcoded)

Kicks off the full Bob-Sentry **5-phase** triage pipeline against a Keycloak GitHub issue.
The pipeline runs from raw issue ingestion through to a local HTML triage report,
and closes with a mandatory retrospective that feeds learnings back into the agent files.

For severity assignment, load `@.bob/references/keycloak-triage-severity-guidance.md`.
Use `CVSS v3.1` as the primary scoring framework and treat the Keycloak triage process as
supporting guidance only.

The optional `searchDup` flag inserts a **pre-triage duplicate search** before any CVE
analysis, sandbox provisioning, or script generation. If candidate duplicates are found,
the pipeline halts and reports them — it does not proceed until the engineer re-issues
the command without `searchDup`.

---

## ⚠️ Read-Only Mode — GitHub Access Policy

**GitHub access during this pipeline is STRICTLY READ-ONLY.**

The following operations are ABSOLUTELY PROHIBITED at every step:

- Posting comments to any GitHub issue (`gh issue comment`)
- Creating pull requests (`gh pr create`)
- Pushing branches or tags (`git push`)
- Editing issue fields (`gh issue edit`)
- Any GitHub API call using an HTTP verb other than `GET`

The only permitted GitHub operation is reading issue content (Step 1 below).
**All triage output is written to local files under `.bob/reports/` ONLY.**

---

## Pipeline Steps

### Step 0 — Duplicate Search *(only when `searchDup` is present)*

Load `@.bob/agent/DUPLICATE_SEARCH.md` and execute the full procedure defined there.

- **`searchDup` present:** Run the duplicate search. If candidate duplicates (score ≥ 3)
  are found, output the duplicate report and **stop here**. Do not proceed to Step 1.
  If no duplicates are found, output the "NO DUPLICATES FOUND" banner and continue
  automatically to Step 1.
- **`searchDup` absent:** Skip Step 0 entirely and proceed directly to Step 1.

---

### Step 1 — Fetch the GitHub Issue (READ ONLY)

Read the issue content using the GitHub CLI:

```bash
gh issue view <issue-number> --repo keycloak/keycloak
```

Capture and display:
- Issue title
- Issue body (full text)
- All comments (use `--comments` flag)
- Issue labels and metadata (severity, component area, fix version)

If `gh` is not authenticated or unavailable, output:
```
ERROR: GitHub CLI (gh) is not available or not authenticated.
To proceed without gh, paste the full issue body directly into this chat.
```

Do NOT attempt to use the GitHub REST API directly. Do NOT attempt any workaround
that involves writing to GitHub.

---

### Step 2 — Activate Security-Sentry Mode & Run CVE Analysis

Switch to the `security-sentry` mode.

Invoke `@.bob/skills/cve-analyzer/SKILL.md` (all 6 steps).

Produce the threat assessment JSON:

```json
{
  "issue_number": <number>,
  "matched_cve_pattern": "CVE-XXXX",
  "attack_type": "...",
  "affected_component": "...",
  "confidence": "HIGH|MEDIUM|LOW",
  "recommended_keycloak_version_for_sandbox": "...",
  "novel_pattern": false,
  "triage_checklist_flags": ["..."]
}
```

If `novel_pattern: true` AND `confidence: LOW` → halt pipeline, output `ESCALATE`,
save a partial report to `.bob/reports/<report_folder>/<issue-number>/triage-<issue-number>-<date>-ESCALATED.md`.

---

### Step 3 — Plan Mode: 4-Stage Pipeline

Switch to Plan mode. Load `@.bob/agent/AGENTS.md` and use the **Part 1 — Plan Mode** section.

Using the threat assessment JSON from Step 2, produce the full triage plan:

- Stage 1: Semantic Parsing (component, version, sandbox image tag)
- Stage 2: Sandbox Provisioning (realm, client, user, CVE-specific config)
  - Reference the exact sections of `@.bob/references/admin-api-schemas.md` to use
- Stage 3: Execution Strategy (control test + exploit test with expected HTTP codes)
- Stage 4: Verification (confirmation signal + denial signal)

Present the plan to the engineer. **Wait for confirmation before proceeding to Step 4.**

---

### Step 4 — Code Mode: Generate Python Scripts

Switch to Code mode. Load `@.bob/agent/AGENTS.md` and use the **Part 2 — Code Mode** section.

Using the triage plan from Step 3:

1. **Resolve the Keycloak image version** from the plan's Stage 1 output
2. **Determine the script destination** from the CVE Analyzer JSON `report_folder` and
   `report_path` fields:
   ```
   .bob/reports/<report_folder>/<issue-number>/
   ```
3. **Check for prior triage artefacts** in that folder — read any existing
   `setup_realm.py` and `exploit_test.py` as reference before writing new scripts
   (see **Part 2 — Code Mode / Prior Triage Reference Pass** in `@.bob/agent/AGENTS.md`).
4. **Generate `setup_realm.py` (Script A)** — save to the destination folder:
   - Uses only payloads from `@.bob/references/admin-api-schemas.md` Section A
     (and Section C if FGAP is required)
   - Must include the standard header from code/AGENTS.md (with `Attack Class Folder:` line)
   - Must produce structured `[SETUP]` console output
   - Must exit `0` on success, `2` on failure
5. **Generate `exploit_test.py` (Script B)** — save to the destination folder:
   - Uses only payloads from `@.bob/references/admin-api-schemas.md` Section B
   - Must include the standard header from code/AGENTS.md
   - Must produce structured `[EXPLOIT]` and `[ASSERT]` console output
   - Must exit `0` (patched), `1` (vulnerable), or `2` (error)
   - Must end with a `RESULT: {...}` JSON line

Present both scripts to the engineer for review before proceeding to Step 5.

---

### Step 5 — Agent Mode: Execute Sandbox, Assign Severity & Produce Report

Switch to Agent mode. Load `@.bob/agent/AGENTS.md` and `@.bob/references/keycloak-triage-severity-guidance.md`.

Execute the full agent pipeline:

1. Prepare `/tmp/keycloak-triage/` working directory
2. Substitute `{{KEYCLOAK_VERSION}}` in the compose template and deploy
3. Poll for Keycloak readiness (60-second timeout)
4. Run Script A — halt and escalate if exit code is `2`
5. Secret scan Script B — halt and escalate if credential pattern found
6. Run Script B — capture stdout/stderr to `result.log`
7. Parse the `RESULT:` JSON line from `result.log`
8. Assign severity exactly once using `CVSS v3.1`, based on the issue details and Step 5 execution evidence
   - Output a severity label: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`
   - Output the numeric CVSS v3.1 base score
   - Output the full CVSS v3.1 vector string
   - Use the Keycloak triage severity guidance as supporting context only
   - If evidence is inconclusive, default to `LOW` unless the grounded evidence supports a higher severity
9. **Always run cleanup:** `docker compose down -v && rm -rf /tmp/keycloak-triage/`

Produce the final triage report as a Markdown file.
Save it at:
```
.bob/reports/<report_folder>/<issue-number>/triage-<issue-number>-<YYYY-MM-DD>.md
```

The report must include the final severity label, CVSS v3.1 base score, and CVSS v3.1 vector.

Once the file is written:

1. Output the absolute file path to the console.
2. **Read the file back and display its full contents inline** so the engineer can review the complete report without opening a separate file.
3. Output the verdict JSON separately after the report for easy parsing.

**Do not post, comment, push, or write to GitHub. The report is the final deliverable.**

---

### Step 6 — Retrospective & Knowledge Base Update

> **This step requires human approval before any files are modified.**

After the triage report is written and the verdict is confirmed by the engineer, Bob must
conduct a retrospective on the triage session and propose updates to the agent files.

**6a — Generate the retrospective.**

Analyse the completed triage session and identify:

1. **Script iterations** — how many times were setup or exploit scripts revised, and why?
2. **Attribute/API surprises** — any API key names, response codes, or endpoint paths that
   differed from what was in `@.bob/references/admin-api-schemas.md`?
3. **SPI/configuration surprises** — any server-level config requirements discovered
   during execution that are not documented in `@.bob/references/docker-compose.yml`?
4. **Networking or timing issues** — any container networking, mock server timing, or
   callback ordering problems encountered?
5. **Novel CVE pattern** — if the vulnerability did not match any existing training
   pattern, describe the new pattern in the format used in
   `@.bob/references/keycloak-cve-history.md`.
6. **Proposed file changes** — for each finding above, specify the exact file and section
   to update.

Present the retrospective to the engineer in this format:

```
## Retrospective — Issue #<number>

### Findings
1. [Finding description] → proposed change to [file/section]
2. ...

### Proposed File Updates
| File | Section | Change |
|------|---------|--------|
| .bob/references/admin-api-schemas.md | Section X | Add payload / fix key name |
| .bob/references/docker-compose.yml   | SPI flags  | Add commented example |
| .bob/references/keycloak-cve-history.md | New pattern | Add CVE entry |
| .bob/code/AGENTS.md | Rules | Add new behavioural rule |
| .bob/agent/AGENTS.md | Notes | Add new discovery |

### No Changes Proposed
[List any areas where the session produced no new learnings]
```

**6b — Wait for engineer approval.**

After presenting the retrospective, ask:

> "Do you approve these updates to the agent files? You can approve all, approve
> individual items by number, or skip the update entirely."

**Do not modify any file until explicit approval is given.**

**6c — Apply approved changes.**

For each approved item, apply the minimal targeted edit to the relevant file. After all
edits are complete, confirm which files were updated.

---

## Output Summary

At the end of a successful pipeline run, display the following **in order**:

**1. The complete triage report (read from file and rendered inline):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TRIAGE REPORT — keycloak/keycloak#<number>
 .bob/reports/<report_folder>/<issue-number>/triage-<issue-number>-<date>.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<full report contents rendered here>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**2. The verdict JSON:**

```json
{
  "confirmed": true/false,
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "cvss_base_score": 0.0,
  "cvss_vector": "CVSS:3.1/...",
  "affected_component": "...",
  ...
}
```

**3. The pipeline summary box:**

```
╔══════════════════════════════════════════════════════════╗
║  Bob-Sentry Triage Complete                              ║
╠══════════════════════════════════════════════════════════╣
║  Issue:    keycloak/keycloak#<number>                    ║
║  Dup check: PASSED (none found) | SKIPPED                ║
║  Status:   CONFIRMED VULNERABLE | PATCH VERIFIED |       ║
║            ESCALATED | NOT REPRODUCIBLE                  ║
║  Report:   .bob/reports/<report_folder>/<issue-number>/  ║
║            triage-<number>-<date>.md                   ║
║  Retro:    Retrospective presented in chat; updates      ║
║            require explicit engineer approval            ║
║  GitHub:   READ ONLY — no writes performed               ║
╚══════════════════════════════════════════════════════════╝
```

**4. The Step 6 retrospective prompt** (see above).
