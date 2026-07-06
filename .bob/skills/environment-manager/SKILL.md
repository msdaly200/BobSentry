# Skill Name: Ephemeral Podman Environment Manager
# Description: Rules and automated hooks to guarantee a completely isolated, pristine,
# and uncontaminated Keycloak target environment for each replication cycle.
# Invoked during: Phase 3 (Autonomous Exploit Replication) of every Bob-Sentry triage session.

---

## Core Mandates

1. **Anti-Contamination Protocol**: Explicitly kill and drop any leftover container
   instances or unmapped volume states before spinning up a new sandbox run.
2. **Dynamic Version Selection**: Never pull or target `quay.io/keycloak/keycloak:latest`
   indiscriminately. The container image version MUST match the targeted CVE context using
   the version-resolution priority defined in Phase 3 Step B below.
3. **Volatile Runtime Constraints**: All test environments launched via Podman behave as
   true disposable sandboxes. No state persists across distinct test runs.

---

## Phase 3 Execution Layout

Phase 3 consists of **four ordered steps**. Bob-Shell MUST execute them in sequence.
Skipping or reordering any step is a guardrail violation.

---

### Step A — Aggressive Pre-Launch Purge

Before any container is created, the host namespace MUST be cleared. This is the first
action inside every generated `setup_realm.py` preamble, executed via `subprocess`:

```python
import subprocess, sys

def purge_sandbox() -> None:
    """Kill and remove any prior keycloak-sentry-sandbox container unconditionally."""
    subprocess.run(
        ["podman", "rm", "-f", "keycloak-sentry-sandbox"],
        capture_output=True,  # suppress stdout/stderr — failure is expected if no container exists
    )
    # Non-zero exit from 'rm -f' on a missing container is NOT an error — always proceed.
```

This call must happen **before** the `podman run` invocation, with no conditional guard.
Do not check whether a container is running first — always purge unconditionally.

---

### Step B — Version-Pinned Ephemeral Launch

Resolve the target image version using this priority order (same as `docker-compose.yml`
header):

1. Explicit version named in the CVE/issue report (e.g. `"26.0.5"`)
2. Version current at the issue filing date (June 2026 issues → `"26.1"`)
3. `"latest"` **only** if neither of the above can be determined

The container MUST be launched with:

- `--rm` flag — container filesystem is purged automatically on exit (volatile runtime)
- `--name keycloak-sentry-sandbox` — deterministic name required for Step A purge
- `-p 8080:8080 -p 9000:9000` — port 8080 for the app, port 9000 for the management/health API
- `KC_HEALTH_ENABLED=true` — enables the `/health/ready` management endpoint (Step C depends on this)
- `start-dev` command — dev mode, no TLS, no hostname enforcement

**Never** pass named host volumes (`-v` mounts with persistent paths). This prevents state
leakage across triage sessions.

Generated Python scaffold for Step B:

```python
import subprocess, sys

KEYCLOAK_VERSION = "26.1"            # MUST be replaced with resolved version per priority above
CONTAINER_NAME   = "keycloak-sentry-sandbox"
KC_IMAGE         = f"quay.io/keycloak/keycloak:{KEYCLOAK_VERSION}"

def launch_sandbox() -> None:
    """Launch a version-pinned, ephemeral Keycloak container for exploit replication."""
    result = subprocess.run(
        [
            "podman", "run", "-d", "--rm",
            "--name", CONTAINER_NAME,
            "-p", "8080:8080",
            "-p", "9000:9000",
            "-e", "KC_BOOTSTRAP_ADMIN_USERNAME=admin",
            "-e", "KC_BOOTSTRAP_ADMIN_PASSWORD=admin",
            "-e", "KC_HEALTH_ENABLED=true",
            "-e", "KC_HTTP_PORT=8080",
            "-e", "KC_HOSTNAME_STRICT=false",
            "-e", "KC_HOSTNAME_STRICT_HTTPS=false",
            KC_IMAGE,
            "start-dev",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[ERROR] podman run failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"[INFO] Container {CONTAINER_NAME} started (image: {KC_IMAGE})")
```

---

### Step C — Readiness Evaluation Loop

**No exploit vector may be triggered until Keycloak passes a health check.**
The readiness loop MUST poll `http://localhost:9000/health/ready` — the Keycloak management
port — not the application port (`8080`). A bare `sleep N` is **prohibited**.

Readiness criteria:
- HTTP `200 OK` returned from `GET http://localhost:9000/health/ready`
- Response body contains `"status": "UP"` (Keycloak 26+ JSON format)
- Timeout: **120 seconds** maximum wait; abort with a descriptive error if exceeded

Generated Python scaffold for Step C:

```python
import time, requests, sys

HEALTH_URL        = "http://localhost:9000/health/ready"
READINESS_TIMEOUT = 120   # seconds
POLL_INTERVAL     = 3     # seconds

def wait_for_ready() -> None:
    """Block until Keycloak management API confirms readiness or timeout expires."""
    deadline = time.time() + READINESS_TIMEOUT
    print(f"[INFO] Polling {HEALTH_URL} (timeout: {READINESS_TIMEOUT}s) ...")
    while time.time() < deadline:
        try:
            resp = requests.get(HEALTH_URL, timeout=2)
            if resp.status_code == 200 and resp.json().get("status") == "UP":
                print("[INFO] Keycloak is ready.")
                return
        except (requests.ConnectionError, requests.Timeout, ValueError):
            pass  # server not yet accepting connections — keep polling
        time.sleep(POLL_INTERVAL)
    print(
        f"[ERROR] Keycloak did not become ready within {READINESS_TIMEOUT}s. "
        "Check container logs: podman logs keycloak-sentry-sandbox",
        file=sys.stderr,
    )
    sys.exit(1)
```

---

### Step D — Exploit Vector Activation

Only after `wait_for_ready()` returns successfully may the exploit script proceed to realm
setup and the exploit sequence itself.

The complete call order in every generated `setup_realm.py` MUST be:

```python
if __name__ == "__main__":
    purge_sandbox()    # Step A — unconditional pre-launch purge
    launch_sandbox()   # Step B — version-pinned --rm container
    wait_for_ready()   # Step C — management API readiness gate
    setup_realm()      # Step D — realm provisioning (exploit preconditions)
```

And in `exploit_test.py`:

```python
if __name__ == "__main__":
    wait_for_ready()   # Re-verify readiness if exploit_test.py is run standalone
    run_exploit()      # Exploit vectors fire only after this gate passes
```

---

## Constraint Summary Table

| Constraint | Value | Rationale |
|---|---|---|
| Pre-launch purge command | `podman rm -f keycloak-sentry-sandbox \|\| true` | Eliminates container contamination |
| `--rm` flag | Mandatory on every `podman run` | Volatile filesystem — no state leakage on exit |
| Image tag | Resolved per CVE context, never bare `latest` | Reproducible, CVE-accurate target |
| Health endpoint | `http://localhost:9000/health/ready` | Management port, not app port |
| Health field assertion | `"status": "UP"` in JSON body | Confirms Keycloak internals ready, not just TCP open |
| Readiness timeout | 120 seconds | Accommodates slow dev-mode cold starts |
| Named volumes | Prohibited | Prevents cross-session state persistence |
| `sleep N` readiness | Prohibited | Non-deterministic; replaced by polling loop |

---

## Relationship to Security Guardrails

This skill governs **how** containers are launched. The non-negotiable rules in
`.bob/rules/security-guardrails.md` govern **what** scripts may do once the container is
running. Both documents MUST be loaded and applied together:

- **Rule 1** (Network Isolation): All script requests target `localhost` only.
- **Rule 4** (No Real Credentials): Scripts use only approved test defaults.
- **Rule 5** (Secret Scan): All generated scripts are scanned before execution.
- **Rule 6** (Mandatory Cleanup): `podman rm -f` / `docker compose down -v` runs after
  every session regardless of outcome. The `--rm` flag handles container filesystem cleanup
  during the run; Rule 6 handles post-session teardown of any compose network state.
- **Rule 8** (Working Directory Isolation): All runtime files written to `/tmp/keycloak-triage/`.
