from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import settings
from app.models import RoleEnum


# --------------------------------------------------------------------------- #
# Password hashing (bcrypt)
# --------------------------------------------------------------------------- #
def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# JWT (access + refresh) with RBAC scopes
# --------------------------------------------------------------------------- #
def _create_token(
    subject: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: Optional[dict] = None,
) -> str:
    now = datetime.now(timezone.utc)
    scopes = settings.ROLE_SCOPES.get(role, [])
    payload = {
        "sub": subject,
        "role": role,
        "scopes": scopes,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, role: str, extra_claims: Optional[dict] = None) -> str:
    return _create_token(
        subject,
        role,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(subject: str, role: str) -> str:
    return _create_token(
        subject,
        role,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """Decode + signature/expire validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def issue_tokens(user_id: int, role: str) -> dict:
    role_value = role.value if isinstance(role, RoleEnum) else str(role)
    return {
        "access_token": create_access_token(str(user_id), role_value),
        "refresh_token": create_refresh_token(str(user_id), role_value),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role": role_value,
        "scopes": settings.ROLE_SCOPES.get(role_value, []),
    }
