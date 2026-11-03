import re
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..core.db import get_db
from ..core.errors import AppError
from ..models import Article, CalendarEntry, Cluster, ExportRecord, User
from ..schemas import CalendarIn, CalendarOut, CalendarPatch, ExportIn
from ..security.auth import current_user
from ..services import exports as ex
from .deps import get_article, get_business

calendar = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])
exports = APIRouter(prefix="/api/v1/exports", tags=["exports"])
dash = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _validate_refs(db, u, b, data):
    if data.get("article_id"):
        a = db.get(Article, data["article_id"])
        if not a or a.business_id != b.id:
            raise AppError(404, "not_found", "Article not found")
    if data.get("cluster_id"):
        c = db.get(Cluster, data["cluster_id"])
        if not c or c.business_id != b.id:
            raise AppError(404, "not_found", "Cluster not found")
    if data.get("assignee_id") not in (None, u.id):
        raise AppError(422, "invalid_assignee", "Assignee must be the project owner (multi-user sharing is not implemented)")


@calendar.get("", response_model=list[CalendarOut])
def list_(business_id: int, status: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, business_id)
    st = select(CalendarEntry).where(CalendarEntry.business_id == business_id)
    if status:
        st = st.where(CalendarEntry.status == status)
    return db.scalars(st.order_by(CalendarEntry.planned_date)).all()


@calendar.post("", response_model=CalendarOut, status_code=201)
def create(body: CalendarIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    _validate_refs(db, u, b, body.model_dump())
    e = CalendarEntry(**body.model_dump())
    db.add(e)
    db.commit()
    return e


def _entry(db, u, eid):
    e = db.get(CalendarEntry, eid)
    if not e:
        raise AppError(404, "not_found", "Entry not found")
    get_business(db, u, e.business_id)
    return e


@calendar.patch("/{eid}", response_model=CalendarOut)
def patch(eid: int, body: CalendarPatch, u: User = Depends(current_user), db: Session = Depends(get_db)):
    e = _entry(db, u, eid)
    d = body.model_dump(exclude_unset=True)
    _validate_refs(db, u, get_business(db, u, e.business_id), d)
    for k, v in d.items():
        setattr(e, k, v)
    db.commit()
    return e


@calendar.delete("/{eid}", status_code=204)
def delete(eid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_entry(db, u, eid))
    db.commit()


MEDIA = {"md": "text/markdown", "txt": "text/plain", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "pdf": "application/pdf", "csv_keywords": "text/csv", "csv_calendar": "text/csv"}


@exports.post("", status_code=201)
def create_export(body: ExportIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    art = None
    if body.article_id:
        art, ab = get_article(db, u, body.article_id)
        if ab.id != b.id:
            raise AppError(404, "not_found", "Article not found")
    f = body.format
    if f == "csv_keywords":
        data, ext = ex.csv_keywords(db, b), "csv"
    elif f == "csv_calendar":
        data, ext = ex.csv_calendar(db, b), "csv"
    else:
        md = ex.build_pack(db, b, art)
        data, ext = {"md": lambda: md.encode(), "txt": lambda: ex.md_to_text(md).encode(), "docx": lambda: ex.render_docx(md),
                     "pdf": lambda: ex.render_pdf(md)}[f](), f
    name = re.sub(r"[^a-z0-9]+", "-", f"{b.name}-{'seo-pack' if f in ('md','txt','docx','pdf') else f}".lower()).strip("-") + f".{ext}"
    rec = ExportRecord(business_id=b.id, article_id=art.id if art else None, fmt=f, filename=name, content=data)
    db.add(rec)
    db.commit()
    return {"id": rec.id, "filename": name, "format": f, "size": len(data), "created_at": rec.created_at}


@exports.get("")
def list_exports(business_id: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, business_id)
    return [{"id": r.id, "filename": r.filename, "format": r.fmt, "created_at": r.created_at, "size": len(r.content)}
            for r in db.scalars(select(ExportRecord).where(ExportRecord.business_id == business_id).order_by(ExportRecord.id.desc()).limit(100))]


@exports.get("/{xid}")
def download(xid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(ExportRecord, xid)
    if not r:
        raise AppError(404, "not_found", "Export not found")
    get_business(db, u, r.business_id)
    return Response(r.content, media_type=MEDIA[r.fmt], headers={"Content-Disposition": f'attachment; filename="{r.filename}"'})


@dash.get("")
def dashboard(u: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import Business, SeoAudit
    bids = [i for (i,) in db.execute(select(Business.id).where(Business.owner_id == u.id))]
    if not bids:
        return {"businesses": 0, "articles_total": 0, "by_status": {}, "clusters": 0, "needs_attention": 0}
    by = dict(db.execute(select(Article.status, func.count()).where(Article.business_id.in_(bids)).group_by(Article.status)).all())
    latest = {}
    for a in db.execute(select(SeoAudit.article_id, SeoAudit.id, SeoAudit.results).join(Article).where(Article.business_id.in_(bids)).order_by(SeoAudit.id)):
        latest[a[0]] = a[2]
    attn = sum(1 for r in latest.values() if r["summary"].get("needs_improvement", 0) > 0)
    return {"businesses": len(bids), "articles_total": sum(by.values()), "by_status": by,
            "clusters": db.scalar(select(func.count()).select_from(Cluster).where(Cluster.business_id.in_(bids))),
            "needs_attention": attn}
