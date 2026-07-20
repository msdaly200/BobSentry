#!/usr/bin/env python3
"""
setup_realm.py — Issue #50983
Admin UI authentication-flow usage leaks hidden client IDs

Creates a triage environment that reproduces the exact privilege boundary:
  - A "hidden" confidential client (triage-secret-client) intentionally
    NOT grantable to view-realm-only admins via /clients/{id}.
  - A CUSTOM authentication flow (copy of browser) bound SPECIFICALLY to
    triage-secret-client (this is what populates usedBy.type=SPECIFIC_CLIENTS).
  - A help-desk delegated admin (triage-viewer) granted ONLY view-realm
    from realm-management (NO view-clients, NO manage-clients).

The exploit script then verifies:
  1. triage-viewer CANNOT read the hidden client via GET /clients/{id} — 403.
  2. triage-viewer CAN call /ui-ext/authentication-management/flows and
     receives triage-secret-client in usedBy.values (the vulnerability).

NOTE: The vulnerability only triggers with CUSTOM flows (builtIn=false).
Built-in flows use usedBy.type=DEFAULT and do not expose client IDs.
Custom flows bound to specific clients use usedBy.type=SPECIFIC_CLIENTS
and list client IDs — without applying auth.clients().canView(client).
"""

import sys
import time
import json
import urllib.request
import urllib.parse
import urllib.error

BASE       = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
REALM      = "triage-realm"
PUB_CLIENT = "triage-client"
SECRET_CLIENT = "triage-secret-client"
CUSTOM_FLOW   = "triage-custom-flow"
VIEWER_USER = "triage-viewer"
VIEWER_PASS = "triage-pass"


def req(method, url, data=None, token=None, ct="application/json"):
    body = None
    if data is not None:
        body = (urllib.parse.urlencode(data).encode()
                if ct == "application/x-www-form-urlencoded"
                else json.dumps(data).encode())
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", ct)
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")


def admin_token():
    s, b = req("POST", f"{BASE}/realms/master/protocol/openid-connect/token",
               data={"grant_type": "password", "client_id": "admin-cli",
                     "username": ADMIN_USER, "password": ADMIN_PASS},
               ct="application/x-www-form-urlencoded")
    assert s == 200, f"Admin token failed: {s} {b}"
    print("[SETUP] Admin token obtained.")
    return b["access_token"]


def user_token(realm, client, username, password):
    s, b = req("POST", f"{BASE}/realms/{realm}/protocol/openid-connect/token",
               data={"grant_type": "password", "client_id": client,
                     "username": username, "password": password},
               ct="application/x-www-form-urlencoded")
    return s, b


def main():
    print("[SETUP] Waiting for Keycloak to be ready...")
    for i in range(36):
        try:
            urllib.request.urlopen(f"{BASE}/realms/master", timeout=3)
            print("[SETUP] Keycloak is ready.")
            break
        except Exception:
            if i == 35:
                print("[SETUP] ERROR: Keycloak not ready after 3 minutes.")
                sys.exit(1)
            time.sleep(5)

    tok = admin_token()

    s, _ = req("POST", f"{BASE}/admin/realms",
               data={"realm": REALM, "enabled": True}, token=tok)
    assert s in (201, 409), f"Create realm: {s}"
    print(f"[SETUP] Realm '{REALM}': {'created' if s == 201 else 'already exists'}.")

    s, _ = req("POST", f"{BASE}/admin/realms/{REALM}/clients",
               data={"clientId": PUB_CLIENT, "enabled": True, "publicClient": True,
                     "directAccessGrantsEnabled": True,
                     "redirectUris": ["http://localhost:9999/*"]}, token=tok)
    assert s in (201, 409), f"Create pub client: {s}"
    print(f"[SETUP] Client '{PUB_CLIENT}': {'created' if s == 201 else 'already exists'}.")

    s, _ = req("POST", f"{BASE}/admin/realms/{REALM}/clients",
               data={"clientId": SECRET_CLIENT, "enabled": True,
                     "publicClient": False, "directAccessGrantsEnabled": False,
                     "redirectUris": ["http://localhost:9999/secret"],
                     "description": "Confidential client intentionally hidden from help-desk"},
               token=tok)
    assert s in (201, 409), f"Create secret client: {s}"
    print(f"[SETUP] Hidden client '{SECRET_CLIENT}': {'created' if s == 201 else 'already exists'}.")

    s, clients = req("GET", f"{BASE}/admin/realms/{REALM}/clients?clientId={SECRET_CLIENT}", token=tok)
    assert s == 200 and clients, f"Secret client UUID lookup: {s}"
    secret_uuid = clients[0]["id"]
    print(f"[SETUP] '{SECRET_CLIENT}' UUID: {secret_uuid}")

    # Create a CUSTOM (non-built-in) auth flow — only custom flows populate
    # usedBy.type=SPECIFIC_CLIENTS which exposes client IDs in the leak
    s, _ = req("POST", f"{BASE}/admin/realms/{REALM}/authentication/flows/browser/copy",
               data={"newName": CUSTOM_FLOW}, token=tok)
    assert s in (201, 409), f"Copy browser flow: {s}"
    print(f"[SETUP] Custom flow '{CUSTOM_FLOW}': {'created' if s == 201 else 'already exists'}.")

    s, flows = req("GET", f"{BASE}/admin/realms/{REALM}/authentication/flows", token=tok)
    assert s == 200
    custom_flow = next((f for f in flows if f.get("alias") == CUSTOM_FLOW), None)
    assert custom_flow, f"Custom flow not found"
    custom_flow_id = custom_flow["id"]
    print(f"[SETUP] Custom flow ID: {custom_flow_id}")

    s, existing = req("GET", f"{BASE}/admin/realms/{REALM}/clients/{secret_uuid}", token=tok)
    assert s == 200
    existing["authenticationFlowBindingOverrides"] = {"browser": custom_flow_id}
    s, _ = req("PUT", f"{BASE}/admin/realms/{REALM}/clients/{secret_uuid}",
               data=existing, token=tok)
    if s == 204:
        print(f"[SETUP] Custom flow bound to '{SECRET_CLIENT}'.")
    else:
        print(f"[SETUP] WARNING: Flow bind returned {s}.")

    s, verify_flows = req("GET", f"{BASE}/admin/realms/{REALM}/ui-ext/authentication-management/flows", token=tok)
    raw = json.dumps(verify_flows)
    binding_confirmed = SECRET_CLIENT in raw
    print(f"[SETUP] Binding verification: '{SECRET_CLIENT}' in /ui-ext/flows: {binding_confirmed}")

    s, _ = req("POST", f"{BASE}/admin/realms/{REALM}/users",
               data={"username": VIEWER_USER, "enabled": True,
                     "firstName": "Triage", "lastName": "Viewer",
                     "email": "triage-viewer@test.local",
                     "emailVerified": True, "requiredActions": [],
                     "credentials": [{"type": "password",
                                      "value": VIEWER_PASS, "temporary": False}]},
               token=tok)
    assert s in (201, 409)
    print(f"[SETUP] Delegated admin '{VIEWER_USER}': {'created' if s == 201 else 'already exists'}.")

    s, users = req("GET", f"{BASE}/admin/realms/{REALM}/users?username={VIEWER_USER}", token=tok)
    viewer_uuid = users[0]["id"]

    s, rm_clients = req("GET", f"{BASE}/admin/realms/{REALM}/clients?clientId=realm-management", token=tok)
    rm_uuid = rm_clients[0]["id"]

    s, vr_role = req("GET", f"{BASE}/admin/realms/{REALM}/clients/{rm_uuid}/roles/view-realm", token=tok)
    assert s == 200

    s, _ = req("POST",
               f"{BASE}/admin/realms/{REALM}/users/{viewer_uuid}/role-mappings/clients/{rm_uuid}",
               data=[vr_role], token=tok)
    assert s in (204, 409)
    print(f"[SETUP] Granted ONLY 'view-realm' to '{VIEWER_USER}' (view-clients withheld).")

    v_status, v_body = user_token(REALM, PUB_CLIENT, VIEWER_USER, VIEWER_PASS)
    assert v_status == 200
    v_tok = v_body["access_token"]

    baseline_s, _ = req("GET", f"{BASE}/admin/realms/{REALM}/clients/{secret_uuid}", token=v_tok)
    if baseline_s == 403:
        print(f"[SETUP] BASELINE OK: viewer cannot read hidden client via /clients/{{id}} (403).")
    else:
        print(f"[SETUP] WARNING: baseline returned {baseline_s} (expected 403).")

    state = {
        "secret_uuid": secret_uuid,
        "custom_flow_id": custom_flow_id,
        "rm_uuid": rm_uuid,
        "viewer_uuid": viewer_uuid,
        "baseline_direct_status": baseline_s,
        "binding_confirmed": binding_confirmed,
    }
    with open("/tmp/keycloak-triage/state.json", "w") as f:
        json.dump(state, f)

    print()
    print("[SETUP] Setup complete.")
    print(f"[SETUP]   Viewer: {VIEWER_USER}/{VIEWER_PASS} (view-realm ONLY)")
    print(f"[SETUP]   Hidden client: {SECRET_CLIENT} (uuid={secret_uuid})")
    print(f"[SETUP]   Custom flow: {CUSTOM_FLOW} (id={custom_flow_id})")
    print(f"[SETUP]   Binding confirmed: {binding_confirmed}")
    print(f"[SETUP]   Direct client GET: {baseline_s}")


if __name__ == "__main__":
    main()
