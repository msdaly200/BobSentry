# Keycloak Triage Severity Guidance

This file provides local severity guidance for Bob during Keycloak vulnerability triage.
It supplements the triage flow with severity expectations while keeping CVSS v3.1 as the
primary scoring framework.

## Purpose

Use this guidance only as supporting context when assigning severity at the end of triage.
Bob must not assign severity before execution evidence is collected in Step 5 of the triage
pipeline.

## Severity Assignment Rules

1. Primary framework: CVSS v3.1 base score and vector.
2. Supporting context: the Keycloak triage process may help identify likely attack class,
   exploitation conditions, affected component, and impact area.
3. Severity is assigned exactly once, after Step 5, based on the issue details plus the
   reproduction or patch-verification evidence gathered during execution.
4. Final severity output must include:
   - Severity label: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`
   - Numeric CVSS v3.1 base score
   - Full CVSS v3.1 vector string
5. If reproduction is inconclusive, missing, or escalated, Bob should default to a `LOW`
   severity unless the available evidence clearly supports a higher severity.

## Expected Inputs For Scoring

When calculating CVSS v3.1, Bob should use the strongest grounded evidence available from:

- The GitHub issue title, body, labels, and comments
- The CVE analysis output
- The planned exploit path and affected component
- The actual setup and exploit execution results from Step 5
- The final confirmation state: confirmed vulnerable, patch verified, escalated, or not reproducible

## Guardrails

- Do not invent impact details that are not supported by issue content or execution results.
- Prefer conservative scoring when evidence is partial.
- Keep the Keycloak triage process as supporting guidance only; do not replace CVSS v3.1 with
  an internal-only severity rubric.
- Record the final severity fields in both the triage report and the final verdict JSON.
