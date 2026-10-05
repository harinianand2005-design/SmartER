def token_for(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_password_hashing_and_login(client, users):
    token = token_for(client, "admin@example.com", "AdminPass123!")
    assert token
    assert token != "AdminPass123!"


def test_invalid_login_is_rejected(client, users):
    response = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong-pass"})
    assert response.status_code == 401


def test_current_user_endpoint(client, users):
    token = token_for(client, "nurse@example.com", "NursePass123!")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "TRIAGE_NURSE"


def test_missing_token_is_rejected(client):
    assert client.get("/api/v1/access/dashboard").status_code == 401


def test_role_authorization(client, users):
    nurse_token = token_for(client, "nurse@example.com", "NursePass123!")
    authority_token = token_for(client, "authority@example.com", "AuthorityPass123!")
    assert client.get("/api/v1/access/admin-settings", headers={"Authorization": f"Bearer {nurse_token}"}).status_code == 403
    assert client.get("/api/v1/access/triage-recommendations", headers={"Authorization": f"Bearer {nurse_token}"}).status_code == 200
    assert client.get("/api/v1/access/health-authority-analytics", headers={"Authorization": f"Bearer {authority_token}"}).status_code == 200
    assert client.get("/api/v1/access/triage-recommendations", headers={"Authorization": f"Bearer {authority_token}"}).status_code == 403