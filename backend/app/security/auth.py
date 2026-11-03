import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.db import get_db
from ..core.errors import AppError
from ..models import User

N, R, P = 2 ** 14, 8, 1


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return "scrypt$%d$%d$%d$%s$%s" % (N, R, P, base64.b64encode(salt).decode(), base64.b64encode(h).decode())


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        calc = hashlib.scrypt(pw.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(h))
    except Exception:
        return False


def make_token(user_id: int, kind: str) -> str:
    s = get_settings()
    exp = timedelta(minutes=s.access_minutes) if kind == "access" else timedelta(days=s.refresh_days)
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "typ": kind, "iss": s.jwt_issuer, "aud": s.jwt_audience,
                       "iat": now, "exp": now + exp, "jti": secrets.token_hex(8)}, s.secret_key, algorithm="HS256")


def decode_token(tok: str, kind: str) -> int:
    s = get_settings()
    try:
        d = jwt.decode(tok, s.secret_key, algorithms=["HS256"], audience=s.jwt_audience, issuer=s.jwt_issuer,
                       options={"require": ["exp", "iss", "aud", "sub"]})
    except jwt.PyJWTError:
        raise AppError(401, "invalid_token", "Authentication required")
    if d.get("typ") != kind:
        raise AppError(401, "invalid_token", "Authentication required")
    return int(d["sub"])


def set_auth_cookies(resp, user_id: int):
    s = get_settings()
    common = dict(httponly=True, samesite="lax", secure=s.cookie_secure, path="/")
    resp.set_cookie("access_token", make_token(user_id, "access"), max_age=s.access_minutes * 60, **common)
    resp.set_cookie("refresh_token", make_token(user_id, "refresh"), max_age=s.refresh_days * 86400,
                    **{**common, "path": "/api/v1/auth"})
    # readable by JS on purpose: double-submit CSRF token, echoed in X-CSRF-Token
    resp.set_cookie("csrf_token", secrets.token_urlsafe(24), max_age=s.refresh_days * 86400, httponly=False,
                    samesite="lax", secure=s.cookie_secure, path="/")


def clear_auth_cookies(resp):
    for name, path in (("access_token", "/"), ("refresh_token", "/api/v1/auth"), ("csrf_token", "/")):
        resp.delete_cookie(name, path=path)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    tok = request.cookies.get("access_token")
    if not tok:
        raise AppError(401, "not_authenticated", "Authentication required")
    u = db.get(User, decode_token(tok, "access"))
    if not u or not u.is_active:
        raise AppError(401, "not_authenticated", "Authentication required")
    return u


def require_roles(*roles):
    def dep(u: User = Depends(current_user)):
        if u.role not in roles:
            raise AppError(403, "forbidden", "You do not have permission for this action")
        return u
    return dep


SAFE = {"GET", "HEAD", "OPTIONS"}
CSRF_EXEMPT = {"/api/v1/auth/login", "/api/v1/auth/register"}


async def csrf_middleware(request: Request, call_next):
    from fastapi.responses import JSONResponse
    if request.method not in SAFE and request.url.path not in CSRF_EXEMPT and request.cookies.get("access_token"):
        c, h = request.cookies.get("csrf_token", ""), request.headers.get("x-csrf-token", "")
        if not c or not hmac.compare_digest(c, h):
            return JSONResponse({"error": {"code": "csrf_failed", "message": "Missing or invalid CSRF token"}}, status_code=403)
    return await call_next(request)
