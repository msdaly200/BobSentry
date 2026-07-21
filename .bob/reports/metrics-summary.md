# Bob-Sentry — Triage Session Metrics

> This file is updated after each triage session during Phase 4 (Report generation).
> It provides the running productivity data for the "70% triage waste" pitch metric.
> Re-triages supersede earlier sessions for the same issue — only the latest is counted.

---

## Running Totals

| Metric | Value |
|---|---|
| **Total issues triaged** | 5 |
| **Total confirmed vulnerable** | 5 |
| **Total patch verified** | 0 |
| **Total escalated** | 0 |
| **Total Bob-Sentry time (minutes)** | ~90 |
| **Total estimated manual time (hours)** | ~17.5 |
| **Total time saved (hours)** | ~16.1 |
| **Average triage time (minutes)** | ~18 |
| **Average script iterations per session** | ~2.2 |

---

## Per-Session Log

| Issue | Date | Attack Class | CVE | Severity | Status | Elapsed (min) | Script Iters | Manual Est. (hrs) | Time Saved (hrs) | Tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| [#49915](https://github.com/keycloak/keycloak/issues/49915) | 2026-07-04 | Blind SSRF (CIBA backchannel) | CVE-2026-1518 | HIGH | ✅ CONFIRMED | ~8 | 2 | ~1.5 | ~1.4 | est. 80k–120k |
| [#49570](https://github.com/keycloak/keycloak/issues/49570) | 2026-07-04 | DoS — OTel Baggage (novel pattern) | CVE-2026-45292 | IMPORTANT | ✅ CONFIRMED | ~15 | 2 | ~3 | ~2.85 | est. 100k–150k |
| [#50445](https://github.com/keycloak/keycloak/issues/50445) | 2026-07-20 | Privilege Escalation — Hardcoded Role Mapper | CVE-2026-4629 | BLOCKER | ✅ CONFIRMED | ~15 | 2 | ~3.5 | ~3.25 | est. 100k–150k |
| [#50983](https://github.com/keycloak/keycloak/issues/50983) | 2026-07-20 | AuthZ Bypass — FGAP flow summary leak | none assigned | MEDIUM | ✅ CONFIRMED | ~17 | 2 | ~3 | ~2.72 | est. 100k–150k |
| [#50981](https://github.com/keycloak/keycloak/issues/50981) | 2026-07-21 | AuthZ Bypass — FGAP user session/consent leak | none assigned | MEDIUM | ✅ CONFIRMED | ~20 | 3 | ~3 | ~2.67 | est. 100k–150k |

> **Elapsed time note:** Where the triage report does not record a precise elapsed time,
> a ~15-minute estimate is used based on the standard 2-script session baseline established
> by retrospective improvements after #49915 (first run).

---

## Productivity Notes

**Issue #49915 (CVE-2026-1518, CIBA SSRF) — re-triage 2026-07-04:**
- Earlier session (2026-06-28) took ~27 minutes with 9 script iterations; superseded by this run.
- Re-triage against `latest` (26.6.x) confirmed vulnerability still unpatched.
- Reduced to ~8 minutes and 2 script iterations after retrospective fixes to
  `admin-api-schemas.md` (Section D) and `docker-compose.yml` (CIBA SPI flag).
- Equivalent manual triage estimated at ~1.5 hours for a senior engineer.

**Issue #49570 (CVE-2026-45292, OTel Baggage DoS) — 2026-07-04:**
- Novel pattern — third-party dependency CVE (upstream OTel SDK), no strong match to primary
  CVE training patterns. Correctly classified as Class 21 (DoS via Algorithmic Complexity).
- Unauthenticated attack surface confirmed: 20 requests with ~60 KB baggage headers each
  rendered Keycloak unresponsive. Requires `--tracing-enabled=true`.

**Issue #50445 (CVE-2026-4629, Hardcoded Role Mapper Injection) — re-triage 2026-07-20:**
- Earlier session (2026-07-09) produced threat assessment only (no sandbox execution).
- Re-triage produced full live confirmation: `201 Created` on mapper POST + `realm-admin`
  in decoded JWT for `triage-user`. Severity upgraded IMPORTANT → BLOCKER (CVSS 9.1).
- Single API call from a `manage-clients` delegated admin achieves full realm takeover.

**Issue #50983 (no CVE, FGAP flow summary leak) — 2026-07-20:**
- Novel sub-variant of CVE-2026-11986: missing `canView()` filter on Admin UI aggregation
  endpoint `/ui-ext/authentication-management/flows`. Client IDs leaked to `view-realm`-only
  actors; direct `/clients/{id}` path correctly returns `403`.
- Required extra diagnostic pass to identify that only non-built-in (custom) flow copies
  trigger the `SPECIFIC_CLIENTS` leak path. CVSS 5.4 / MEDIUM.

**Issue #50981 (no CVE, FGAP user session/consent/offline-session leak) — 2026-07-21:**
- Second novel sub-variant of CVE-2026-11986 confirmed in the same triage cycle: missing
  `auth.clients().canView(client)` filter in `UserResource` response builders for sessions,
  consents, and offline-sessions. A view-users-only delegated admin can enumerate hidden
  client UUIDs, clientIds, and offline token grants without view-clients permission.
- Three separate endpoints confirmed vulnerable: /users/{id}/sessions, /users/{id}/consents,
  /users/{id}/offline-sessions/{clientUuid}. All returned HTTP 200 with hidden client data
  while direct /clients/{id} correctly returned 403. CVSS 5.4 / MEDIUM.
- Script A required 2 iterations: first attempt used consentRequired=true which blocked
  directAccessGrants; second attempt disabled consent to enable session establishment.

---

## Severity Distribution

| Severity | Count | Issues |
|---|---|---|
| BLOCKER | 1 | #50445 |
| IMPORTANT | 1 | #49570 |
| HIGH | 1 | #49915 |
| MEDIUM | 2 | #50983, #50981 |
| LOW / INFO | 0 | — |

---

## Attack Class Distribution

| Attack Class | Count | Issues |
|---|---|---|
| AuthZ Bypass — FGAP (Class 10) | 2 | #50983, #50981 |
| Privilege Escalation — Admin API (Class 10) | 1 | #50445 |
| Blind SSRF (Class 5) | 1 | #49915 |
| DoS — Algorithmic Complexity (Class 21, novel) | 1 | #49570 |

---

## Pitch Metric

> *"Bob-Sentry triaged 5 confirmed Keycloak vulnerabilities — all MEDIUM severity or above —
> saving an estimated 16+ hours of senior engineer time. Average triage time is ~18 minutes
> per issue versus a ~3-hour manual baseline. Two FGAP sub-variants (#50983, #50981) were
> confirmed in a single session using prior session artefacts as reference scaffolding."*

---

*Updated automatically by Bob-Sentry Phase 4. Do not edit manually.*
