"""Security audit pipeline: middleware threat tagging + audit-log endpoints."""
import pytest

from tests.conftest import auth_headers


def test_middleware_flags_sql_injection_as_high(client, admin_token, customer_token):
    # Malicious payload -> schema validation rejects it (422), but the
    # middleware must still record a HIGH audit entry.
    client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 1, "check_in": "2026-10-20", "check_out": "2026-10-22' OR 1=1 --"},
    )

    response = client.get(
        "/api/security/audit-log?threat_level=HIGH",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
    high_entries = [e for e in response.json() if e["endpoint"] == "/api/bookings/"]
    assert any("SQL injection" in (e["details"] or "") for e in high_entries)


def test_middleware_flags_xss_payload(client, admin_token, customer_token):
    client.post(
        "/api/security/audit-log",
        headers=auth_headers(customer_token),
        json={"endpoint": "/guestbook", "event": "<script>alert(1)</script>"},
    )

    response = client.get(
        "/api/security/audit-log?threat_level=HIGH",
        headers=auth_headers(admin_token),
    )
    assert any((e["details"] or "").find("XSS") >= 0 for e in response.json())


def test_audit_event_threat_level_is_elevated_by_assessment(client, admin_token, customer_token):
    """A payload declared LOW but matching attack signatures is stored as HIGH."""
    response = client.post(
        "/api/security/audit-log",
        headers=auth_headers(customer_token),
        json={
            "endpoint": "/payments",
            "event": "CARD_TOKEN",
            "threat_level": "LOW",
            "details": "' UNION SELECT card_number FROM payments --",
        },
    )
    assert response.status_code == 201
    assert response.json()["threat_level"] == "HIGH"
    assert "UNION SELECT" in (response.json()["details"] or "")


def test_benign_audit_event_keeps_declared_level(client, customer_token):
    response = client.post(
        "/api/security/audit-log",
        headers=auth_headers(customer_token),
        json={
            "endpoint": "/profile",
            "event": "PROFILE_VIEW",
            "threat_level": "LOW",
            "details": "viewed own profile",
        },
    )
    assert response.status_code == 201
    assert response.json()["threat_level"] == "LOW"
    assert response.json()["user_email"] == "customer@thebharatresort.com"


def test_audit_query_filters_by_endpoint(client, admin_token, customer_token):
    client.post(
        "/api/security/audit-log",
        headers=auth_headers(customer_token),
        json={"endpoint": "/filter-endpoint-test", "event": "PROBE"},
    )

    response = client.get(
        "/api/security/audit-log?endpoint=/filter-endpoint-test",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert all("/filter-endpoint-test" in e["endpoint"] for e in response.json())


def test_audit_query_threat_level_filter_is_exhaustive(client, admin_token):
    for level in ("LOW", "MEDIUM", "HIGH"):
        response = client.get(
            f"/api/security/audit-log?threat_level={level}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        assert all(e["threat_level"] == level for e in response.json())


def test_audit_query_requires_admin(client, customer_token):
    response = client.get("/api/security/audit-log", headers=auth_headers(customer_token))
    assert response.status_code == 403


def test_audit_event_requires_authentication(client):
    response = client.post(
        "/api/security/audit-log",
        json={"endpoint": "/x", "event": "ANON"},
    )
    assert response.status_code == 401


def test_response_exposes_threat_level_header(client, customer_token):
    response = client.post(
        "/api/security/audit-log",
        headers=auth_headers(customer_token),
        json={"endpoint": "/header-test", "event": "BENIGN"},
    )
    assert response.headers.get("x-threat-level") == "LOW"


def test_audit_query_pagination(client, admin_token):
    first = client.get(
        "/api/security/audit-log?limit=2", headers=auth_headers(admin_token)
    )
    second = client.get(
        "/api/security/audit-log?limit=2&skip=2", headers=auth_headers(admin_token)
    )
    assert len(first.json()) <= 2
    assert len(second.json()) <= 2
    first_ids = {e["id"] for e in first.json()}
    second_ids = {e["id"] for e in second.json()}
    assert not (first_ids & second_ids)
