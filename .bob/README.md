# Bob-Sentry — Security Triage System

Bob-Sentry is a semi-autonomous security triage pipeline for Keycloak. It converts a raw GitHub issue number into a structured vulnerability verdict (confirmed / patch verified / escalated) with reproducible scripts, a sandbox execution log, a final severity assessment, and a Markdown report — all without touching GitHub.

---

## 1. How to Start a Triage

**Activate the mode first:** Switch to the **Security Sentry** custom mode (defined in [`custom_modes.yaml`](custom_modes.yaml)). This loads the guardrails, CVE knowledge base, and multi-model routing strategy automatically.

**Then run the slash command:**

```
/triage <github-issue-number>
/triage <github-issue-number> searchDup
```

**`searchDup` (optional):** Before any analysis begins, Bob searches `keycloak/keycloak` for existing open and closed issues that match the same vulnerability. If candidate duplicates (score ≥ 3) are found, the pipeline **halts and reports them** — it will not consume triage resources on a known issue. Re-run without `searchDup` to proceed once you've confirmed it is not a duplicate.

---

## 2. What Happens Behind the Scenes

The command triggers a 6-step pipeline. Steps 3 and 4 are iterative — scripts are revised until they run cleanly.

| Step | Mode | What it does |
|------|------|--------------|
| 1 | — | Fetches the GitHub issue (read-only `gh issue view`) |
| 2 | Security Sentry | Runs the CVE Analyzer skill; produces a threat-assessment JSON matched against 5 trained CVE patterns |
| 3 | Plan | Produces a 4-stage triage plan (component, sandbox config, execution strategy, verification signals); **waits for your approval** |
| 4 | Code | Generates `setup_realm.py` and `exploit_test.py` tailored to the threat profile; **presents both scripts for review** before execution |
| 5 | Agent | Spins up a Docker sandbox, runs the scripts, captures logs, assigns the final CVSS v3.1 severity, tears everything down, writes the Markdown report |
| 6 | Agent | Runs a retrospective, proposes targeted updates to the knowledge-base files; **waits for your approval** before touching anything |

**Sandbox lifecycle:** A Docker Compose file is written to `/tmp/keycloak-triage/`, Keycloak boots (60-second timeout), both scripts run, and `docker compose down -v` plus `rm -rf /tmp/keycloak-triage/` execute unconditionally — even on failure. No container state persists between sessions.

---

## 3. Output Files

All artefacts land under `.bob/reports/`, organised by attack class and issue number:

```
.bob/reports/
  <attack-class>/
    <issue-number>/
      setup_realm.py            ← Script A: provisions the sandbox realm
      exploit_test.py           ← Script B: executes the exploit and asserts the result
      triage-<number>-<date>.md ← the full triage report
  metrics-summary.md            ← running productivity totals across all sessions
```

**Attack-class folder names** (set by the CVE Analyzer):

| Folder | Vulnerability class |
|--------|---------------------|
| `SSRF-backchannel/` | SSRF via backchannel / CIBA notification endpoint |
| `TOCTOU-role-rename/` | Time-of-check/time-of-use via role rename |
| `FGAP-assign-unassign/` | Fine-Grained Admin Permission bypass |
| `param-pollution-redirect/` | Redirect URI parameter pollution |
| `policy-bypass-ROPC/` | Client policy bypass via ROPC grant |
| `novel-pattern/` | Vulnerabilities that don't match a known class |

The triage report includes: executive summary, threat profile, sandbox config, full execution logs, HTTP evidence, final severity label, CVSS v3.1 base score, CVSS v3.1 vector, verdict JSON, a suggested investigation area in the Keycloak source tree, and a session-metrics table.

---

## 4. Reusing Artefacts for Future Triages

The folder structure is deliberately cumulative. When a new issue arrives in the same attack class, Code mode reads the **most recent working scripts** from that folder before writing new ones. This means:

- Correct API attribute keys, endpoint paths, and mock-server contracts are reused from confirmed working implementations.
- The CVE history file ([`references/keycloak-cve-history.md`](references/keycloak-cve-history.md)) grows with each approved retrospective, adding new patterns for the next triage to score against.
- The API schema reference ([`references/admin-api-schemas.md`](references/admin-api-schemas.md)) is updated when API surprises are found during execution — so subsequent scripts don't repeat the same wrong key names.
- [`reports/metrics-summary.md`](reports/metrics-summary.md) accumulates timing data across all sessions.

To re-triage a known issue (e.g. after a patch is applied), run `/triage <same-issue-number>` again. Bob will read the prior scripts as reference, assign severity during Step 5, and produce a new dated Markdown report in the same subfolder.

---

## 5. Key Files at a Glance

| File | Purpose |
|------|---------|
| [`commands/init-triage.md`](commands/init-triage.md) | Full `/triage` command specification and pipeline steps |
| [`custom_modes.yaml`](custom_modes.yaml) | Security Sentry mode definition (role, permissions, when to use) |
| [`rules/security-guardrails.md`](rules/security-guardrails.md) | Non-negotiable constraints (network isolation, no real credentials, read-only GitHub) |
| [`skills/cve-analyzer/SKILL.md`](skills/cve-analyzer/SKILL.md) | CVE Analyzer skill — 6-step pattern-matching engine |
| [`references/keycloak-cve-history.md`](references/keycloak-cve-history.md) | 5 deep CVE training profiles + 20-class vulnerability matrix |
| [`references/admin-api-schemas.md`](references/admin-api-schemas.md) | Authoritative Keycloak Admin REST API payloads used by generated scripts |
| [`references/docker-compose.yml`](references/docker-compose.yml) | Sandbox Compose template (Keycloak + optional WireMock) |
| [`agent/AGENTS.md`](agent/AGENTS.md) | Consolidated instructions for Plan mode, Code mode, and Agent mode |
| [`agent/DUPLICATE_SEARCH.md`](agent/DUPLICATE_SEARCH.md) | Duplicate detection procedure used by `searchDup` flag |
| [`reports/`](reports/) | All triage output (reports, scripts, metrics) — the only workspace path Bob writes to |
| [`skills/cve-analyzer/ui/`](skills/cve-analyzer/ui/) | HTML report generator, Jinja2 templates, and CSS assets — run `generate_html_reports.py --all` to produce HTML from markdown |
