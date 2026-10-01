from datetime import datetime, timezone

from app.database import Base, SessionLocal, engine
from app.models import Resource, ResourceCategoryEnum, RoleEnum, User
from app.security import hash_password

SEED_USERS = [
    ("Arti Bhargava", "admin@thebharatresort.com", "Admin@12345", RoleEnum.ADMIN),
    ("Resort Staff", "staff@thebharatresort.com", "Staff@12345", RoleEnum.STAFF),
    ("Guest User", "customer@thebharatresort.com", "Guest@12345", RoleEnum.CUSTOMER),
]

SEED_RESOURCES = [
    ("Deluxe Garden Room 101", ResourceCategoryEnum.ROOM, 4500.00),
    ("Deluxe Garden Room 102", ResourceCategoryEnum.ROOM, 4500.00),
    ("Premium Pool Suite 201", ResourceCategoryEnum.SUITE, 9200.00),
    ("Premium Pool Suite 202", ResourceCategoryEnum.SUITE, 9200.00),
    ("Royal Banquet Hall", ResourceCategoryEnum.HALL, 25000.00),
    ("Conference Hall A", ResourceCategoryEnum.HALL, 18000.00),
]


def init_db() -> None:
    """Create schema and seed demo data when the database is empty."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            for full_name, email, password, role in SEED_USERS:
                db.add(
                    User(
                        full_name=full_name,
                        email=email,
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
            print(f"[seed] created {len(SEED_USERS)} demo users")

        if db.query(Resource).count() == 0:
            for name, category, rate in SEED_RESOURCES:
                db.add(Resource(name=name, category=category, daily_rate=rate, is_available=True))
            print(f"[seed] created {len(SEED_RESOURCES)} demo resources")

        db.commit()
    finally:
        db.close()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
