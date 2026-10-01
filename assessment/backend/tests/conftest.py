"""Shared pytest fixtures.

Every test runs against an isolated in-memory SQLite database; the env var is
set *before* the app modules are imported so the module-level engine binds to
the test database.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app.main import app
from app.models import Resource, ResourceCategoryEnum, RoleEnum, User
from app.security import hash_password

SEED_CREDENTIALS = {
    "ADMIN": ("admin@thebharatresort.com", "Admin@12345"),
    "STAFF": ("staff@thebharatresort.com", "Staff@12345"),
    "CUSTOMER": ("customer@thebharatresort.com", "Guest@12345"),
}


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create schema once and seed users + resources for the whole session."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            for role, (email, password) in SEED_CREDENTIALS.items():
                db.add(
                    User(
                        full_name=f"{role.title()} User",
                        email=email,
                        password_hash=hash_password(password),
                        role=RoleEnum(role),
                    )
                )
        if db.query(Resource).count() == 0:
            for i, (name, cat, rate) in enumerate(
                [
                    ("Test Room A", ResourceCategoryEnum.ROOM, 5000.0),
                    ("Test Room B", ResourceCategoryEnum.ROOM, 6000.0),
                    ("Test Suite S", ResourceCategoryEnum.SUITE, 12000.0),
                    ("Test Hall H", ResourceCategoryEnum.HALL, 30000.0),
                ]
            ):
                db.add(Resource(id=i + 1, name=name, category=cat, daily_rate=rate))
        db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def login_as(client, role: str) -> str:
    """Return an access token for the seeded user of the given role."""
    email, password = SEED_CREDENTIALS[role]
    response = client.post(
        "/api/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client):
    return login_as(client, "ADMIN")


@pytest.fixture
def staff_token(client):
    return login_as(client, "STAFF")


@pytest.fixture
def customer_token(client):
    return login_as(client, "CUSTOMER")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
