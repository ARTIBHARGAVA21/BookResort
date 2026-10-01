"""Booking business logic: rate calculation, conflict detection, ownership."""
import pytest

from tests.conftest import auth_headers, login_as


def _register_and_login(client, email):
    client.post(
        "/api/auth/register",
        json={"full_name": email.split("@")[0], "email": email, "password": "Passw0rd!"},
    )
    return login_as_custom(client, email)


def login_as_custom(client, email, password="Passw0rd!"):
    response = client.post("/api/auth/token", data={"username": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_booking_calculates_price(client, customer_token):
    response = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 1, "check_in": "2026-11-01", "check_out": "2026-11-03"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    # 2 nights x 5000.00 daily rate
    assert body["total_price"] == pytest.approx(10000.0)
    assert body["status"] == "CONFIRMED"
    assert body["resource_name"] == "Test Room A"


def test_price_matches_three_nights(client, customer_token):
    response = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 3, "check_in": "2026-12-01", "check_out": "2026-12-04"},
    )
    assert response.status_code == 201
    # 3 nights x 12000.00
    assert response.json()["total_price"] == pytest.approx(36000.0)


def test_overlapping_booking_is_rejected(client, customer_token):
    first = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 2, "check_in": "2027-01-10", "check_out": "2027-01-14"},
    )
    assert first.status_code == 201

    conflict = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 2, "check_in": "2027-01-12", "check_out": "2027-01-16"},
    )
    assert conflict.status_code == 409
    assert "already booked" in conflict.json()["detail"]


def test_adjacent_dates_do_not_conflict(client, customer_token):
    first = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 2, "check_in": "2027-02-01", "check_out": "2027-02-05"},
    )
    assert first.status_code == 201

    # Check-in exactly on the previous check-out must be allowed.
    second = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 2, "check_in": "2027-02-05", "check_out": "2027-02-07"},
    )
    assert second.status_code == 201


def test_checkout_must_be_after_checkin(client, customer_token):
    response = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 1, "check_in": "2026-11-10", "check_out": "2026-11-10"},
    )
    assert response.status_code == 422


def test_unknown_resource_rejected(client, customer_token):
    response = client.post(
        "/api/bookings/",
        headers=auth_headers(customer_token),
        json={"resource_id": 999, "check_in": "2026-11-10", "check_out": "2026-11-12"},
    )
    assert response.status_code == 404


def test_booking_requires_authentication(client):
    response = client.post(
        "/api/bookings/",
        json={"resource_id": 1, "check_in": "2026-11-10", "check_out": "2026-11-12"},
    )
    assert response.status_code == 401


def test_my_reservations_returns_only_own_bookings(client):
    token_a = login_as_custom(client, "usera@example.com")
    token_b = login_as_custom(client, "userb@example.com")

    client.post(
        "/api/bookings/",
        headers=auth_headers(token_a),
        json={"resource_id": 4, "check_in": "2026-09-01", "check_out": "2026-09-03"},
    )

    mine_a = client.get("/api/bookings/my-reservations", headers=auth_headers(token_a))
    mine_b = client.get("/api/bookings/my-reservations", headers=auth_headers(token_b))

    assert mine_a.status_code == 200
    assert len(mine_a.json()) >= 1
    assert all(b["user_id"] is not None for b in mine_a.json())
    assert mine_b.status_code == 200
    assert all(b["user_id"] != 1 for b in mine_b.json())


def test_my_reservations_status_filter(client):
    token = login_as_custom(client, "filteruser@example.com")
    created = client.post(
        "/api/bookings/",
        headers=auth_headers(token),
        json={"resource_id": 1, "check_in": "2028-03-01", "check_out": "2028-03-03"},
    )
    booking_id = created.json()["id"]

    cancelled = client.patch(
        f"/api/bookings/{booking_id}/cancel", headers=auth_headers(token)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    confirmed_only = client.get(
        "/api/bookings/my-reservations?status=CONFIRMED", headers=auth_headers(token)
    )
    assert all(b["status"] == "CONFIRMED" for b in confirmed_only.json())


def test_customer_cannot_cancel_others_booking(client, admin_token, customer_token):
    booking = client.post(
        "/api/bookings/",
        headers=auth_headers(admin_token),
        json={"resource_id": 3, "check_in": "2028-06-01", "check_out": "2028-06-03"},
    )
    booking_id = booking.json()["id"]

    attempt = client.patch(
        f"/api/bookings/{booking_id}/cancel", headers=auth_headers(customer_token)
    )
    assert attempt.status_code == 403


def test_cancelled_booking_cannot_be_cancelled_twice(client):
    token = login_as_custom(client, "twice@example.com")
    booking = client.post(
        "/api/bookings/",
        headers=auth_headers(token),
        json={"resource_id": 2, "check_in": "2028-07-01", "check_out": "2028-07-03"},
    )
    booking_id = booking.json()["id"]

    first = client.patch(f"/api/bookings/{booking_id}/cancel", headers=auth_headers(token))
    assert first.status_code == 200
    second = client.patch(f"/api/bookings/{booking_id}/cancel", headers=auth_headers(token))
    assert second.status_code == 409
