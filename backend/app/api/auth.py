from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.db import get_db
from ..core.errors import AppError
from ..models import User
from ..schemas import LoginIn, RegisterIn, UserOut
from ..security.auth import (clear_auth_cookies, current_user, decode_token, hash_password, set_auth_cookies, verify_password)
from ..security.ratelimit import limiter
from fastapi import Request

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
_DUMMY = hash_password("dummy-password-for-timing")


@router.post("/register", response_model=UserOut, status_code=201, dependencies=[limiter("auth", "auth_rate_per_min")])
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise AppError(409, "email_taken", "An account with this email already exists")
    u = User(email=body.email, password_hash=hash_password(body.password), role=body.role)
    db.add(u)
    db.commit()
    set_auth_cookies(response, u.id)
    return u


@router.post("/login", response_model=UserOut, dependencies=[limiter("auth", "auth_rate_per_min")])
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    ok = verify_password(body.password, u.password_hash if u else _DUMMY)
    if not u or not ok or not u.is_active:
        raise AppError(401, "invalid_credentials", "Invalid email or password")
    set_auth_cookies(response, u.id)
    return u


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    tok = request.cookies.get("refresh_token")
    if not tok:
        raise AppError(401, "not_authenticated", "Authentication required")
    u = db.get(User, decode_token(tok, "refresh"))
    if not u or not u.is_active:
        raise AppError(401, "not_authenticated", "Authentication required")
    set_auth_cookies(response, u.id)
    return u


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_auth_cookies(response)


@router.get("/me", response_model=UserOut)
def me(u: User = Depends(current_user)):
    return u
