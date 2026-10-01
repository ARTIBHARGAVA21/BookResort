import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Application configuration.

    All values are overridable via environment variables so the same image
    runs against SQLite locally and PostgreSQL/MySQL in the cloud.
    """

    PROJECT_NAME: str = "Bharat Resort Booking API"
    API_PREFIX: str = "/api"

    # Database ---------------------------------------------------------------
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}"
    )

    # JWT / OAuth2 -----------------------------------------------------------
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET",
        "9f2b1a7e4c8d40f6a1e5c3b7d9a2f8e4c1b6d3a7f9e2c5b8a1d4f7e0c3b6a9d2",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # Role -> OAuth2 scopes granted on token issue (RBAC scope validation)
    ROLE_SCOPES: dict = {
        "ADMIN": ["read", "write", "admin"],
        "STAFF": ["read", "write"],
        "CUSTOMER": ["read", "write"],
    }

    # CORS (frontend dev origin) --------------------------------------------
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
