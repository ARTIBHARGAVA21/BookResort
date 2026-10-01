"""RBAC enforcement on protected routes."""
import pytest

from tests.conftest import auth_headers


def test_customer_cannot_list_all_bookings(client, customer_token):
    response = client.get("/api/bookings/", headers=auth_headers(customer_token))
    assert response.status_code == 403


def test_staff_can_list_all_bookings(client, staff_token):
    response = client.get("/api/bookings/", headers=auth_headers(staff_token))
    assert response.status_code == 200


def test_admin_can_list_all_bookings(client, admin_token):
    response = client.get("/api/bookings/", headers=auth_headers(admin_token))
    assert response.status_code == 200


def test_customer_cannot_read_audit_trail(client, customer_token):
    response = client.get("/api/security/audit-log", headers=auth_headers(customer_token))
    assert response.status_code == 403


def test_staff_cannot_read_audit_trail(client, staff_token):
    response = client.get("/api/security/audit-log", headers=auth_headers(staff_token))
    assert response.status_code == 403


def test_admin_can_read_audit_trail(client, admin_token):
    response = client.get("/api/security/audit-log", headers=auth_headers(admin_token))
    assert response.status_code == 200


def test_customer_can_access_own_reservations(client, customer_token):
    response = client.get(
        "/api/bookings/my-reservations", headers=auth_headers(customer_token)
    )
    assert response.status_code == 200


def test_invalid_token_rejected(client):
    response = client.get("/api/bookings/my-reservations", headers=auth_headers("bogus.token.value"))
    assert response.status_code == 401
