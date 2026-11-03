from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.db import get_db
from ..core.errors import AppError
from ..models import AuditEvent, GenerationJob, User
from ..schemas import UserOut
from ..security.auth import require_roles

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
admin = require_roles("admin")


class UserPatch(BaseModel):
    role: Literal["business_owner", "seo_professional", "admin"] | None = None
    is_active: bool | None = None


@router.get("/users", response_model=list[UserOut])
def users(_: User = Depends(admin), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.patch("/users/{uid}", response_model=UserOut)
def patch_user(uid: int, body: UserPatch, me: User = Depends(admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise AppError(404, "not_found", "User not found")
    if u.id == me.id and (body.role not in (None, "admin") or body.is_active is False):
        raise AppError(422, "self_lockout", "Admins cannot demote or deactivate themselves")
    d = body.model_dump(exclude_unset=True)
    for k, v in d.items():
        setattr(u, k, v)
    db.add(AuditEvent(actor_id=me.id, action="user.update", detail={"user_id": uid, **d}))
    db.commit()
    return u


@router.get("/usage")
def usage(_: User = Depends(admin), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = db.execute(select(GenerationJob.kind, GenerationJob.status, func.count()).where(GenerationJob.created_at >= since).group_by(GenerationJob.kind, GenerationJob.status)).all()
    return {"last_7_days": [{"kind": k, "status": s, "count": c} for k, s, c in rows]}


@router.get("/events")
def events(_: User = Depends(admin), db: Session = Depends(get_db)):
    return [{"id": e.id, "actor_id": e.actor_id, "action": e.action, "detail": e.detail, "created_at": e.created_at}
            for e in db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100))]


@router.get("/errors")
def errors(_: User = Depends(admin), db: Session = Depends(get_db)):
    return [{"id": j.id, "kind": j.kind, "provider": j.provider, "error": j.error, "created_at": j.created_at}
            for j in db.scalars(select(GenerationJob).where(GenerationJob.status == "error").order_by(GenerationJob.id.desc()).limit(50))]


@router.get("/health")
def health(_: User = Depends(admin), db: Session = Depends(get_db)):
    s = get_settings()
    db.execute(text("select 1"))
    return {"database": "ok", "ai_provider": s.ai_provider, "ai_model": s.ai_model or None, "ai_key_configured": bool(s.ai_api_key),
            "note": "Provider settings are read from environment variables; they are not editable or stored in the database."}
