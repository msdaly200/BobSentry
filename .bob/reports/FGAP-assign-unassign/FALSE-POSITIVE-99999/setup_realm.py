#!/usr/bin/env python3
"""
setup_realm.py — FALSE POSITIVE triage test (#99999)
Issue claim: "view-clients delegated admin can read the full client list —
             possible information disclosure."

Reality: view-clients is a Keycloak-standard read-only delegated role
         intentionally designed to allow listing clients. This is NOT a
         vulnerability — it is documented, expected behaviour.

Setup creates:
  - realm: triage-realm
  - client: triage-client  (public, direct grants enabled — used for token acquisition)
  - confidential client: triage-secret-client  (the "sensitive" client in the claim)
  - user: triage-user / triage-pass
  - delegated reader: triage-reader / triage-pass
    with ONLY view-clients from realm-management
    (NOT manage-clients, NOT realm-admin)

Baseline check: confirms that triage-reader CANNOT modify a client
(expected 403 on PUT /clients/{id}) — proving the role is correctly
scoped to read-only and not a privilege escalation path.
"""

import sys
import time
import json
import urllib.request
import urllib.parse
import urllib.error

BASE          = "http://localhost:8080"
ADMIN_USER    = "admin"
ADMIN_PASS    = "admin"
REALM         = "triage-realm"
CLIENT_ID     = "triage-client"
SECRET_CLIENT = "triage-secret-client"
TEST_USER     = "triage-user"
TEST_PASS     = "triage-pass"
READER_USER   = "triage-reader"
READER_PASS   = "triage-pass"


def request(method, url, data=None, token=None, content_type="application/json"):
    body = None
    if data is not None:
        if content_type == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode()
        else:
            body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            b = json.loads(raw)
        except Exception:
            b = raw.decode(errors="replace")
        return e.code, b


def get_admin_token():
    url = f"{BASE}/realms/master/protocol/openid-connect/token"
    status, body = request("POST", url,
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": ADMIN_USER, "password": ADMIN_PASS},
        content_type="application/x-www-form-urlencoded")
    assert status == 200, f"Admin token failed: {status} {body}"
    print("[SETUP] Admin token obtained.")
    return body["access_token"]


def get_token(realm, client, username, password):
    url = f"{BASE}/realms/{realm}/protocol/openid-connect/token"
    status, body = request("POST", url,
        data={"grant_type": "password", "client_id": client,
              "username": username, "password": password},
        content_type="application/x-www-form-urlencoded")
    return status, body


def main():
    print("[SETUP] Waiting for Keycloak to be ready...")
    for i in range(30):
        try:
            urllib.request.urlopen(f"{BASE}/realms/master", timeout=3)
            print("[SETUP] Keycloak is ready.")
            break
        except Exception:
            if i == 29:
                print("[SETUP] ERROR: Keycloak did not become ready in time.")
                sys.exit(1)
            time.sleep(5)

    token = get_admin_token()

    # --- Create realm ---
    status, _ = request("POST", f"{BASE}/admin/realms",
        data={"realm": REALM, "enabled": True}, token=token)
    assert status in (201, 409), f"Create realm: {status}"
    print(f"[SETUP] Realm '{REALM}': {'created' if status == 201 else 'already exists'}.")

    # --- Create public client for token acquisition ---
    status, _ = request("POST", f"{BASE}/admin/realms/{REALM}/clients",
        data={"clientId": CLIENT_ID, "enabled": True, "publicClient": True,
              "directAccessGrantsEnabled": True,
              "redirectUris": ["http://localhost:9999/*"]},
        token=token)
    assert status in (201, 409), f"Create client: {status}"
    print(f"[SETUP] Client '{CLIENT_ID}': {'created' if status == 201 else 'already exists'}.")

    # --- Create the "sensitive" confidential client being reported as exposed ---
    status, _ = request("POST", f"{BASE}/admin/realms/{REALM}/clients",
        data={"clientId": SECRET_CLIENT, "enabled": True, "publicClient": False,
              "directAccessGrantsEnabled": False,
              "redirectUris": ["http://localhost:9999/secret"]},
        token=token)
    assert status in (201, 409), f"Create secret client: {status}"
    print(f"[SETUP] Client '{SECRET_CLIENT}': {'created' if status == 201 else 'already exists'}.")

    # --- Create triage-user ---
    status, _ = request("POST", f"{BASE}/admin/realms/{REALM}/users",
        data={"username": TEST_USER, "enabled": True,
              "firstName": "Triage", "lastName": "User", "email": "triage-user@test.local", "emailVerified": True, "requiredActions": [], "credentials": [{"type": "password", "value": TEST_PASS, "temporary": False}]},
        token=token)
    assert status in (201, 409), f"Create test user: {status}"
    print(f"[SETUP] User '{TEST_USER}': {'created' if status == 201 else 'already exists'}.")

    # --- Create triage-reader with view-clients only ---
    status, _ = request("POST", f"{BASE}/admin/realms/{REALM}/users",
        data={"username": READER_USER, "enabled": True,
              "firstName": "Triage", "lastName": "Reader", "email": "triage-reader@test.local", "emailVerified": True, "requiredActions": [], "credentials": [{"type": "password", "value": READER_PASS, "temporary": False}]},
        token=token)
    assert status in (201, 409), f"Create reader user: {status}"
    print(f"[SETUP] User '{READER_USER}': {'created' if status == 201 else 'already exists'}.")

    # Resolve reader UUID
    status, users = request("GET",
        f"{BASE}/admin/realms/{REALM}/users?username={READER_USER}", token=token)
    assert status == 200 and users, f"Reader lookup failed: {status}"
    reader_uuid = users[0]["id"]

    # Resolve realm-management client UUID
    status, rm_clients = request("GET",
        f"{BASE}/admin/realms/{REALM}/clients?clientId=realm-management", token=token)
    assert status == 200 and rm_clients, f"realm-management lookup failed: {status}"
    rm_uuid = rm_clients[0]["id"]

    # Resolve view-clients role
    status, vc_role = request("GET",
        f"{BASE}/admin/realms/{REALM}/clients/{rm_uuid}/roles/view-clients", token=token)
    assert status == 200, f"view-clients role lookup failed: {status}"
    print(f"[SETUP] 'view-clients' role ID: {vc_role['id']}")

    # Assign view-clients to reader
    status, _ = request("POST",
        f"{BASE}/admin/realms/{REALM}/users/{reader_uuid}/role-mappings/clients/{rm_uuid}",
        data=[vc_role], token=token)
    assert status in (204, 409), f"Assign view-clients: {status}"
    print(f"[SETUP] Granted 'view-clients' to '{READER_USER}'.")

    # --- Baseline check: reader CANNOT modify a client (must return 403) ---
    r_status, r_body = get_token(REALM, CLIENT_ID, READER_USER, READER_PASS)
    assert r_status == 200, f"Reader token failed: {r_status} {r_body}"
    r_token = r_body["access_token"]

    # Resolve triage-client UUID
    status, clients = request("GET",
        f"{BASE}/admin/realms/{REALM}/clients?clientId={CLIENT_ID}", token=token)
    assert status == 200 and clients, f"Client UUID lookup failed: {status}"
    client_uuid = clients[0]["id"]

    # Attempt a write with the reader token (must be 403)
    mod_status, _ = request("PUT",
        f"{BASE}/admin/realms/{REALM}/clients/{client_uuid}",
        data={"id": client_uuid, "clientId": CLIENT_ID, "enabled": True,
              "publicClient": True, "directAccessGrantsEnabled": True,
              "description": "baseline_write_attempt"},
        token=r_token)
    if mod_status == 403:
        print(f"[SETUP] BASELINE OK: view-clients reader cannot modify clients (403 as expected).")
    else:
        print(f"[SETUP] WARNING: Modify attempt returned {mod_status} (expected 403).")

    # Save state for exploit script
    with open("/tmp/keycloak-triage/state.json", "w") as f:
        json.dump({"client_uuid": client_uuid, "rm_uuid": rm_uuid,
                   "reader_uuid": reader_uuid}, f)

    print()
    print("[SETUP] Setup complete. Environment ready for exploit_test.py")
    print(f"[SETUP] Reader user:    {READER_USER} / {READER_PASS}  (view-clients only)")
    print(f"[SETUP] Test client:    {CLIENT_ID} (uuid={client_uuid})")
    print(f"[SETUP] 'Secret' client: {SECRET_CLIENT}")


if __name__ == "__main__":
    main()
