#!/usr/bin/env python3
"""
setup_realm.py — CVE-2026-4629 triage setup
Creates:
  - realm: triage-realm
  - client: triage-client (public, direct access grants enabled)
  - user: triage-user / triage-pass
  - delegated admin: triage-delegated-admin / triage-pass
    with ONLY manage-clients from realm-management
    (NOT realm-admin, NOT manage-realm, NOT manage-users)

Baseline check: confirms delegated admin CANNOT directly assign
realm-admin via RoleMapperResource (expected 403).
"""

import sys
import time
import json
import urllib.request
import urllib.parse
import urllib.error

BASE = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
REALM = "triage-realm"
CLIENT_ID = "triage-client"
TEST_USER = "triage-user"
TEST_PASS = "triage-pass"
DELEGATED_ADMIN = "triage-delegated-admin"
DELEGATED_PASS = "triage-pass"


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
            body = json.loads(raw)
        except Exception:
            body = raw.decode(errors="replace")
        return e.code, body


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

    # --- Create client ---
    status, _ = request("POST", f"{BASE}/admin/realms/{REALM}/clients",
        data={
            "clientId": CLIENT_ID,
            "enabled": True,
            "publicClient": True,
            "directAccessGrantsEnabled": True,
            "redirectUris": ["http://localhost:9999/*"]
        }, token=token)
    assert status in (201, 409), f"Create client: {status}"
    print(f"[SETUP] Client '{CLIENT_ID}': {'created' if status == 201 else 'already exists'}.")

    # Resolve client UUID
    status, clients = request("GET",
        f"{BASE}/admin/realms/{REALM}/clients?clientId={CLIENT_ID}", token=token)
    assert status == 200 and clients, f"Client lookup failed: {status}"
    client_uuid = clients[0]["id"]
    print(f"[SETUP] Client UUID: {client_uuid}")

    # --- Create triage-user ---
    status, _ = request("POST", f"{BASE}/admin/realms/{REALM}/users",
        data={"username": TEST_USER, "enabled": True,
              "credentials": [{"type": "password", "value": TEST_PASS, "temporary": False}]},
        token=token)
    assert status in (201, 409), f"Create test user: {status}"
    print(f"[SETUP] User '{TEST_USER}': {'created' if status == 201 else 'already exists'}.")

    # --- Create delegated admin ---
    status, _ = request("POST", f"{BASE}/admin/realms/{REALM}/users",
        data={"username": DELEGATED_ADMIN, "enabled": True,
              "credentials": [{"type": "password", "value": DELEGATED_PASS, "temporary": False}]},
        token=token)
    assert status in (201, 409), f"Create delegated admin: {status}"
    print(f"[SETUP] User '{DELEGATED_ADMIN}': {'created' if status == 201 else 'already exists'}.")

    # Resolve delegated admin UUID
    status, users = request("GET",
        f"{BASE}/admin/realms/{REALM}/users?username={DELEGATED_ADMIN}", token=token)
    assert status == 200 and users, f"Delegated admin lookup failed: {status}"
    delegated_uuid = users[0]["id"]

    # Resolve realm-management client UUID
    status, rm_clients = request("GET",
        f"{BASE}/admin/realms/{REALM}/clients?clientId=realm-management", token=token)
    assert status == 200 and rm_clients, f"realm-management client lookup failed: {status}"
    rm_uuid = rm_clients[0]["id"]

    # Resolve manage-clients role in realm-management
    status, roles = request("GET",
        f"{BASE}/admin/realms/{REALM}/clients/{rm_uuid}/roles/manage-clients", token=token)
    assert status == 200, f"manage-clients role lookup failed: {status}"
    manage_clients_role = roles
    print(f"[SETUP] 'manage-clients' role ID: {manage_clients_role['id']}")

    # Assign manage-clients role to delegated admin (client role assignment)
    status, _ = request("POST",
        f"{BASE}/admin/realms/{REALM}/users/{delegated_uuid}/role-mappings/clients/{rm_uuid}",
        data=[manage_clients_role], token=token)
    assert status in (204, 409), f"Assign manage-clients: {status}"
    print(f"[SETUP] Granted 'manage-clients' to '{DELEGATED_ADMIN}'.")

    # --- Baseline check: delegated admin cannot directly assign realm-admin to triage-user ---
    # Get delegated admin token from triage-realm (need admin-cli in realm or use master)
    # Use master realm admin-cli to get delegated admin token via master realm impersonation
    # Actually: delegated admin is a user in triage-realm; use triage-client for token
    d_status, d_body = get_token(REALM, CLIENT_ID, DELEGATED_ADMIN, DELEGATED_PASS)
    assert d_status == 200, f"Delegated admin token failed: {d_status} {d_body}"
    d_token = d_body["access_token"]
    print(f"[SETUP] Delegated admin token obtained.")

    # Resolve triage-user UUID
    status, tusers = request("GET",
        f"{BASE}/admin/realms/{REALM}/users?username={TEST_USER}", token=token)
    assert status == 200 and tusers, f"triage-user lookup failed: {status}"
    tuser_uuid = tusers[0]["id"]

    # Resolve realm-admin role in realm-management
    status, ra_role = request("GET",
        f"{BASE}/admin/realms/{REALM}/clients/{rm_uuid}/roles/realm-admin", token=token)
    assert status in (200, 404), f"realm-admin role lookup: {status}"

    if status == 200:
        # Baseline: attempt direct assignment of realm-admin to triage-user using delegated token
        b_status, b_body = request("POST",
            f"{BASE}/admin/realms/{REALM}/users/{tuser_uuid}/role-mappings/clients/{rm_uuid}",
            data=[ra_role], token=d_token)
        if b_status == 403:
            print(f"[SETUP] BASELINE OK: Direct realm-admin assignment via RoleMapperResource "
                  f"returned 403 (as expected — guard works for direct assignment).")
        else:
            print(f"[SETUP] WARNING: Baseline direct assignment returned {b_status} (expected 403).")
    else:
        print(f"[SETUP] NOTE: realm-admin role not found in realm-management (status {status}); "
              f"skipping baseline direct-assignment check.")

    print()
    print("[SETUP] Setup complete. Environment ready for exploit_test.py")
    print(f"[SETUP] Client UUID for exploit: {client_uuid}")
    print(f"[SETUP] Delegated admin: {DELEGATED_ADMIN} / {DELEGATED_PASS}")
    print(f"[SETUP] Test user:       {TEST_USER} / {TEST_PASS}")

    # Write state file for exploit script
    with open("/tmp/keycloak-triage/state.json", "w") as f:
        json.dump({"client_uuid": client_uuid, "tuser_uuid": tuser_uuid,
                   "rm_uuid": rm_uuid}, f)


if __name__ == "__main__":
    main()
