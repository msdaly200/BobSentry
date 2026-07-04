"""
Triage Setup — Issue #49570 (CVE-2026-45292)
Creates triage-realm and triage-client for DoS surface validation.
All credentials are test defaults (Rule 4 compliant).
"""

import sys
import requests

BASE = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
REALM = "triage-realm"
CLIENT_ID = "triage-client"


def get_admin_token():
    r = requests.post(
        f"{BASE}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
            "grant_type": "password",
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def create_realm(token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "realm": REALM,
        "enabled": True,
        "accessTokenLifespan": 300,
    }
    r = requests.post(f"{BASE}/admin/realms", json=payload, headers=headers)
    if r.status_code == 409:
        print(f"[SETUP] Realm '{REALM}' already exists — skipping.")
    else:
        r.raise_for_status()
        print(f"[SETUP] Realm '{REALM}' created.")


def create_client(token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "clientId": CLIENT_ID,
        "enabled": True,
        "publicClient": True,
        "directAccessGrantsEnabled": True,
        "redirectUris": ["http://localhost:8888/*"],
    }
    r = requests.post(
        f"{BASE}/admin/realms/{REALM}/clients", json=payload, headers=headers
    )
    if r.status_code == 409:
        print(f"[SETUP] Client '{CLIENT_ID}' already exists — skipping.")
    else:
        r.raise_for_status()
        print(f"[SETUP] Client '{CLIENT_ID}' created.")


def main():
    print("[SETUP] Obtaining admin token...")
    token = get_admin_token()
    create_realm(token)
    create_client(token)
    print("[SETUP] Setup complete. Ready for exploit_test.py.")


if __name__ == "__main__":
    main()
