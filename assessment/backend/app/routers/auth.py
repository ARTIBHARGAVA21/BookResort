from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User, RoleEnum
from app.schemas import Token, RefreshRequest, UserCreate, UserOut
from app.security import verify_password, issue_tokens, decode_token

router = APIRouter(prefix=f"{settings.API_PREFIX}/auth", tags=["auth"])


@router.post("/token", response_model=Token, summary="Issue JWT access & refresh tokens")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 password grant.

    Returns signed access + refresh tokens carrying the user's role and the
    RBAC scopes attached to that role.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return issue_tokens(user.id, user.role)


@router.post("/refresh", response_model=Token, summary="Rotate access token")
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")

    return issue_tokens(user.id, user.role)


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: UserCreate, db: Session = Depends(get_db)):
    """Register a new account. Only staff/admins may create privileged roles."""
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    role = RoleEnum(body.role or "CUSTOMER")
    user = User(
        full_name=body.full_name,
        email=body.email,
        role=role,
    )
    from app.security import hash_password

    user.password_hash = hash_password(body.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut, summary="Current authenticated user")
def me(current_user: User = Depends(get_current_user)):
    return current_user
