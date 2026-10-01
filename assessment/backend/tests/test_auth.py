"""Auth: JWT issuance, refresh, password hashing and RBAC."""
import jwt
import pytest

from app.config import settings
from app.security import decode_token, hash_password, verify_password
from tests.conftest import SEED_CREDENTIALS, auth_headers, login_as


def test_password_hashing_roundtrip():
    hashed = hash_password("S3cret!")
    assert hashed != "S3cret!"
    assert verify_password("S3cret!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_login_issues_jwt_with_role_and_scopes(client):
    token = login_as(client, "ADMIN")
    payload = decode_token(token)
    assert payload["sub"] == "1"
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"
    assert "admin" in payload["scopes"]
    assert "read" in payload["scopes"]


def test_login_response_shape(client):
    email, password = SEED_CREDENTIALS["CUSTOMER"]
    response = client.post("/api/auth/token", data={"username": email, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["role"] == "CUSTOMER"
    assert body["expires_in"] > 0


def test_login_with_wrong_password_rejected(client):
    response = client.post(
        "/api/auth/token",
        data={"username": "admin@thebharatresort.com", "password": "nope"},
    )
    assert response.status_code == 401


def test_login_with_unknown_user_rejected(client):
    response = client.post(
        "/api/auth/token",
        data={"username": "ghost@nowhere.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, admin_token):
    response = client.get("/api/auth/me", headers=auth_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["email"] == "admin@thebharatresort.com"


def test_refresh_token_rotates_access_token(client):
    email, password = SEED_CREDENTIALS["STAFF"]
    login = client.post("/api/auth/token", data={"username": email, "password": password})
    refresh = login.json()["refresh_token"]

    response = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    new_payload = decode_token(response.json()["access_token"])
    assert new_payload["type"] == "access"
    assert new_payload["role"] == "STAFF"


def test_access_token_cannot_be_used_as_refresh(client, admin_token):
    response = client.post("/api/auth/refresh", json={"refresh_token": admin_token})
    assert response.status_code == 401


def test_expired_token_is_rejected(client):
    expired = jwt.encode(
        {"sub": "1", "role": "ADMIN", "type": "access", "exp": 1},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = client.get("/api/auth/me", headers=auth_headers(expired))
    assert response.status_code == 401


def test_register_new_customer(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "New Guest",
            "email": "newguest@example.com",
            "password": "Passw0rd!",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "CUSTOMER"


def test_register_duplicate_email_conflicts(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Dup",
            "email": "admin@thebharatresort.com",
            "password": "Passw0rd!",
        },
    )
    assert response.status_code == 409
