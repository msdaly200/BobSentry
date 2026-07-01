# Mandatory Security Execution Guardrails

> These rules are **non-negotiable**. They apply to ALL Bob modes (Plan, Code, Agent,
> security-sentry) during every stage of a triage session. Bob must load and acknowledge
> these rules before executing any script or container operation.

---

## Rule 1 — Absolute Network Isolation

All HTTP requests generated or executed during a triage session MUST target only:

- `http://localhost:8080` (direct host binding)
- The Docker internal network alias (e.g. `http://keycloak:8080` within a compose network)

**Never** target a remote hostname, a cloud endpoint, an internal corporate network address,
or any URL that resolves outside the local machine. If a generated script contains a
non-localhost URL that is not a WireMock mock (see Rule 2), **abort execution immediately**
and flag the script for manual review before proceeding.

---

## Rule 2 — Mock All External Identity Providers

If the vulnerability under triage involves an external Identity Provider (IdP) — including
but not limited to Google OIDC, Microsoft Azure AD, GitHub OAuth, or any SAML federation
partner — a **local WireMock instance** MUST be used to simulate that IdP.

- WireMock should be added as a second service in the compose file under the name `mock-idp`.
- Its stub mappings must be defined as static JSON files written to
  `/tmp/keycloak-triage/wiremock/mappings/`.
- **Never** use real external IdP credentials, real client secrets, or live external
  network calls during triage.

---

## Rule 3 — Deterministic HTTP Response Classification

Triage verdict is determined by the HTTP response code received from the exploit script:

| Response Code | Classification | Action |
|---|---|---|
| `401 Unauthorized` or `403 Forbidden` | Patch working / Not vulnerable | Mark `confirmed: false` |
| `200 OK` (on an exploit request expecting denial) | **Vulnerability confirmed** | Mark `confirmed: true` |
| `302 Found` to an external/unexpected host | **Vulnerability confirmed** (open redirect) | Mark `confirmed: true` |
| `400 Bad Request` (expected on malformed input) | Secure behavior | Mark `confirmed: false` |
| `500 Internal Server Error` | Indeterminate — requires manual review | Emit `ESCALATE` verdict and halt |

**Never** interpret a `500` error as either confirmation or disproval of a vulnerability.
Always escalate to human review.

---

## Rule 4 — No Real Credentials

All triage scripts MUST use only the following well-known test defaults:

| Parameter | Value |
|---|---|
| Admin username | `admin` |
| Admin password | `admin` |
| Test realm name | `triage-realm` |
| Test client ID | `triage-client` |
| Test client secret | `triage-secret` |
| Test username | `triage-user` |
| Test password | `triage-pass` |

**Never** use:
- Production admin credentials
- Real OAuth client secrets from any environment
- JWT tokens extracted from live systems
- Passwords from environment variables that are not explicitly test defaults

---

## Rule 5 — Secret Scan Before Script Execution

Before executing **any** generated Python script, the script source text MUST be scanned
for the following patterns. If any match is found, **abort execution and flag the script**:

1. **JWT pattern**: three dot-delimited base64url segments matching
   `[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}`
2. **Long base64 string**: any contiguous base64 string longer than 100 characters
3. **AWS/GCP/Azure credential patterns**: strings matching `AKIA`, `AIza`, or
   `-----BEGIN RSA PRIVATE KEY-----`
4. **Hardcoded non-default passwords**: any password-like string that does not match the
   approved test defaults in Rule 4

Flagged scripts must be reviewed by the human engineer before any execution proceeds.

---

## Rule 6 — Mandatory Container Cleanup

`docker compose down -v` MUST always execute after a triage session, regardless of whether:

- The setup script succeeded or failed
- The exploit script confirmed or disproved the vulnerability
- An `ESCALATE` condition was triggered
- Bob was interrupted mid-session

The working directory `/tmp/keycloak-triage/` MUST be removed after cleanup:
```bash
docker compose -f /tmp/keycloak-triage/docker-compose.yml down -v
rm -rf /tmp/keycloak-triage/
```

There must be **no persistent container state** between triage sessions.

---

## Rule 7 — GitHub Is Read-Only

The GitHub CLI (`gh`) and any GitHub MCP server connection are used **exclusively for
reading** issue content. The following operations are **absolutely prohibited** at all
times during a triage session:

- `gh issue comment` — posting comments to any issue
- `gh pr create` — creating pull requests
- `git push` — pushing any branch or tag
- `gh issue edit` — modifying issue fields
- Any REST or GraphQL API call using an HTTP verb other than `GET`

The only permitted GitHub operation is:
```bash
gh issue view <issue-number> --repo keycloak/keycloak
```

Triage output is written **exclusively to local files** under `.bob/reports/`.

---

## Rule 8 — Working Directory Isolation

All triage runtime files (compose files, scripts, logs) MUST be written to
`/tmp/keycloak-triage/`. They MUST NOT be written to:

- The Keycloak source tree (anywhere under the workspace root)
- Any shared or network-mounted path
- The user's home directory

The `.bob/reports/` directory is the **only** location within the workspace where Bob may
write files — and only for the final triage report Markdown.
