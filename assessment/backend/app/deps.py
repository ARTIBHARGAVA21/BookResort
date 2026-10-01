from typing import Optional, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, RoleEnum
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/token")

CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate the access JWT and load the owning user."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise CREDENTIAL_EXCEPTION

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type; an access token is required",
        )

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise CREDENTIAL_EXCEPTION

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise CREDENTIAL_EXCEPTION
    return user


def require_roles(*allowed_roles: RoleEnum) -> Callable:
    """RBAC dependency factory: restrict a route to the given roles.

    Example:
        @router.post("/", dependencies=[Depends(require_roles(RoleEnum.ADMIN))])
    """
    allowed = {r.value for r in allowed_roles}

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions; requires one of {sorted(allowed)}",
            )
        return current_user

    return _checker


require_admin = require_roles(RoleEnum.ADMIN)
require_staff = require_roles(RoleEnum.ADMIN, RoleEnum.STAFF)
