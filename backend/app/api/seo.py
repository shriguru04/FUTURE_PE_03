from urllib.parse import urlparse
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from ..ai import workflow
from ..core.db import get_db
from ..core.errors import AppError
from ..models import Article, InternalLink, SeoAudit, User, WebsitePage
from ..schemas import AuditIn, LinkRecIn, LocalIn
from ..security.auth import current_user
from ..security.ratelimit import limiter
from ..seo import audit as engine
from ..seo import links as link_engine
from .deps import art_dict, biz_dict, get_article, get_business, run_ai

seo = APIRouter(prefix="/api/v1/seo", tags=["seo"])
links = APIRouter(prefix="/api/v1/internal-links", tags=["internal-links"])
local = APIRouter(prefix="/api/v1/local-seo", tags=["local-seo"])


@seo.post("/audit", status_code=201)
def run_audit(body: AuditIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    a, b = get_article(db, u, body.article_id)
    res = engine.audit(art_dict(a), body.config, urlparse(b.website_url or "").netloc)
    row = SeoAudit(article_id=a.id, score=res["score"], results=res)
    db.add(row)
    db.commit()
    return {"id": row.id, "article_id": a.id, "created_at": row.created_at, **res}


@seo.get("/audits/{audit_id}")
def get_audit(audit_id: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(SeoAudit, audit_id)
    if not row:
        raise AppError(404, "not_found", "Audit not found")
    get_article(db, u, row.article_id)
    return {"id": row.id, "article_id": row.article_id, "created_at": row.created_at, **row.results}


@seo.get("/audits")
def list_audits(article_id: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_article(db, u, article_id)
    return [{"id": r.id, "score": r.score, "created_at": r.created_at} for r in
            db.scalars(select(SeoAudit).where(SeoAudit.article_id == article_id).order_by(SeoAudit.id.desc()).limit(30))]


@links.post("/recommend")
def recommend(body: LinkRecIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    arts = db.scalars(select(Article).where(Article.business_id == b.id, Article.status != "archived")).all()
    pages = db.scalars(select(WebsitePage).where(WebsitePage.business_id == b.id)).all()
    res = link_engine.recommend([art_dict(a) for a in arts], [{"id": p.id, "url": p.url, "title": p.title} for p in pages], body.sitemap_complete)
    db.execute(delete(InternalLink).where(InternalLink.business_id == b.id))
    for r in res["recommendations"]:
        db.add(InternalLink(business_id=b.id, source_article_id=r["source_article_id"], target_article_id=r["target_article_id"],
                            target_page_id=r["target_page_id"], target_url=r["target_url"], anchor_text=r["anchor_text"][:300],
                            section=r["section"][:300], relation=r["relation"], status=r["status"], reason=r["reason"]))
    db.commit()
    return res


@links.get("")
def list_links(business_id: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, business_id)
    return [{c: getattr(l, c) for c in ("id", "source_article_id", "target_article_id", "target_page_id", "target_url", "anchor_text", "section", "relation", "status", "reason")}
            for l in db.scalars(select(InternalLink).where(InternalLink.business_id == business_id))]


@local.post("/generate", dependencies=[limiter("ai", "ai_rate_per_min")])
def local_generate(body: LocalIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    if len({f.strip().lower() for f in body.local_facts}) < 2 or any(len(f.strip()) < 10 for f in body.local_facts):
        raise AppError(422, "insufficient_local_context", "Provide at least 2 distinct, specific local facts (10+ characters each)")
    res, p = run_ai(db, u, "local", lambda pr: workflow.generate_local(pr, biz_dict(b), body.model_dump(exclude={"business_id"})))
    return {**res.model_dump(), "provider": p.name, "mock": p.is_mock,
            "warnings": ["Verify service availability, addresses and hours yourself; none were generated.",
                         "Each city page needs its own genuine local facts; do not reuse this output with only the city name changed."]}
