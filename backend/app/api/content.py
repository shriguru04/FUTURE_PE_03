import re
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from ..ai import workflow
from ..core.db import get_db
from ..core.errors import AppError
from ..models import Article, CalendarEntry, Cluster, Keyword, Revision, User
from ..schemas import (ArticleGenIn, ArticleOut, ArticlePatch, BriefIn, ClusterGenIn, ClusterOut, OutlineGenIn)
from ..security.auth import current_user
from ..security.ratelimit import limiter
from ..seo import audit as seo_audit
from ..seo import clustering as cl
from ..seo.intent import FORMATS, classify
from ..seo.text import slugify
from .deps import art_dict, biz_dict, get_article, get_business, run_ai

clusters = APIRouter(prefix="/api/v1/clusters", tags=["clusters"])
content = APIRouter(prefix="/api/v1/content", tags=["content"])


# ------------------------------------------------------------------ clusters
@clusters.post("/generate")
def generate(body: ClusterGenIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    st = select(Keyword).where(Keyword.business_id == b.id)
    if body.keyword_ids:
        st = st.where(Keyword.id.in_(body.keyword_ids))
    kws = db.scalars(st).all()
    if len(kws) < 2:
        raise AppError(422, "too_few_keywords", "At least 2 keywords are required to build clusters")
    ids = [k.id for k in kws]
    # regenerate: drop untouched idea-stage articles for these keywords, then empty clusters
    db.execute(delete(Article).where(Article.business_id == b.id, Article.status == "idea", Article.keyword_id.in_(ids)))
    for k in kws:
        k.cluster_id = None
    db.flush()
    for c in db.scalars(select(Cluster).where(Cluster.business_id == b.id)).all():
        if not db.scalar(select(Article.id).where(Article.cluster_id == c.id).limit(1)):
            db.delete(c)
    db.flush()
    by_phrase = {k.phrase: k for k in kws}
    used = {s for (s,) in db.execute(select(Article.slug).where(Article.business_id == b.id))}
    existing = {a.keyword_id: a for a in db.scalars(select(Article).where(Article.business_id == b.id, Article.keyword_id.in_(ids)))}
    out = []
    for c in cl.cluster_keywords([{"phrase": k.phrase, "intent": k.intent, "priority": k.priority} for k in kws]):
        plan = cl.build_plan(c)
        row = Cluster(business_id=b.id, name=c["name"], pillar_keyword=c["pillar"]["phrase"], cannibalization=plan["cannibalization"])
        db.add(row)
        db.flush()
        for m in c["members"]:
            by_phrase[m["phrase"]].cluster_id = row.id
        arts = []
        for it in plan["items"]:
            k = by_phrase[it["keyword"]["phrase"]]
            others = [m["phrase"] for m in c["members"] if m["phrase"] != k.phrase][:4]
            a = existing.get(k.id)
            if a:
                a.cluster_id, a.is_pillar = row.id, it["is_pillar"]
            else:
                a = Article(business_id=b.id, cluster_id=row.id, keyword_id=k.id, title=cl.title_for(k.phrase, k.content_type),
                            primary_keyword=k.phrase, secondary_keywords=list(dict.fromkeys(it["secondary"] + others))[:6], intent=k.intent,
                            funnel_stage=k.funnel_stage, content_type=k.content_type, is_pillar=it["is_pillar"], priority=k.priority,
                            status="idea", slug=cl.slug_unique(k.phrase, used))
                db.add(a)
            arts.append(a)
        db.flush()
        out.append({"cluster": ClusterOut.model_validate(row).model_dump(), "articles": [ArticleOut.model_validate(a).model_dump(mode="json") for a in arts]})
    db.commit()
    return {"clusters": out, "note": "Clusters use token-overlap similarity (heuristic), not embeddings. Review before publishing."}


@clusters.get("")
def list_clusters(business_id: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, business_id)
    res = []
    for c in db.scalars(select(Cluster).where(Cluster.business_id == business_id)):
        arts = db.scalars(select(Article).where(Article.cluster_id == c.id).order_by(Article.is_pillar.desc(), Article.priority.desc())).all()
        res.append({**ClusterOut.model_validate(c).model_dump(), "articles": [{"id": a.id, "title": a.title, "primary_keyword": a.primary_keyword,
                    "is_pillar": a.is_pillar, "status": a.status, "intent": a.intent, "slug": a.slug} for a in arts]})
    return res


@clusters.get("/{cid}")
def get_cluster(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Cluster, cid)
    if not c:
        raise AppError(404, "not_found", "Cluster not found")
    get_business(db, u, c.business_id)
    arts = db.scalars(select(Article).where(Article.cluster_id == cid)).all()
    kws = db.scalars(select(Keyword).where(Keyword.cluster_id == cid)).all()
    return {**ClusterOut.model_validate(c).model_dump(), "articles": [ArticleOut.model_validate(a).model_dump(mode="json") for a in arts],
            "keywords": [{"id": k.id, "phrase": k.phrase, "intent": k.intent} for k in kws]}


# ------------------------------------------------------------------ content
@content.post("/briefs", response_model=ArticleOut, status_code=201)
def create_brief(body: BriefIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    k = None
    if body.keyword_id:
        k = db.get(Keyword, body.keyword_id)
        if not k or k.business_id != b.id:
            raise AppError(404, "not_found", "Keyword not found")
    pk = (k.phrase if k else (body.primary_keyword or "")).strip().lower()
    if not pk:
        raise AppError(422, "no_keyword", "Provide keyword_id or primary_keyword")
    if body.cluster_id:
        c = db.get(Cluster, body.cluster_id)
        if not c or c.business_id != b.id:
            raise AppError(404, "not_found", "Cluster not found")
    c_ = classify(pk, b.name, b.city)
    sec = [x.phrase for x in db.scalars(select(Keyword).where(Keyword.business_id == b.id, Keyword.cluster_id == (k.cluster_id if k else None),
           Keyword.phrase != pk).limit(5))] if k and k.cluster_id else []
    used = {s for (s,) in db.execute(select(Article.slug).where(Article.business_id == b.id))}
    brief = {"intent": c_["intent"], "intent_explanation": c_["explanation"], "user_goal": c_["user_goal"], "recommended_format": c_["content_format"],
             "recommended_cta": c_["cta"], "audience": b.audience, "location": b.city, "context_source": b.context_source,
             "inputs_used": ["business profile", *( ["fetched homepage metadata"] if b.context_source == "crawled" else []), "keyword record" if k else "manual keyword"]}
    a = Article(business_id=b.id, cluster_id=body.cluster_id or (k.cluster_id if k else None), keyword_id=k.id if k else None,
                title=body.title or cl.title_for(pk, k.content_type if k else "educational_guide"), primary_keyword=pk, secondary_keywords=sec,
                intent=k.intent if k else c_["intent"], funnel_stage=k.funnel_stage if k else c_["funnel_stage"],
                content_type=k.content_type if k else "educational_guide", priority=k.priority if k else 0, status="planned",
                slug=cl.slug_unique(pk, used), brief=brief, cta_text=body.cta_text)
    db.add(a)
    db.commit()
    return a


@content.post("/outlines/generate", response_model=ArticleOut, dependencies=[limiter("ai", "ai_rate_per_min")])
def gen_outline(body: OutlineGenIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    a, b = get_article(db, u, body.article_id)
    res, p = run_ai(db, u, "outline", lambda pr: workflow.generate_outline(pr, art_dict(a), biz_dict(b)))
    a.outline = res.model_dump()
    a.seo_title = a.seo_title or res.seo_title
    if a.status in ("idea", "planned"):
        a.status = "outline"
    a.generation_meta = {**a.generation_meta, "outline_provider": p.name, "outline_model": p.model, "mock": p.is_mock}
    db.commit()
    return a


@content.post("/articles/generate", dependencies=[limiter("ai", "ai_rate_per_min")])
def gen_article(body: ArticleGenIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    a, b = get_article(db, u, body.article_id)
    if not a.outline:
        raise AppError(422, "outline_required", "Generate and review an outline first")
    opts = body.model_dump(exclude={"article_id"})
    opts["language"] = opts["language"] or b.language
    res, p = run_ai(db, u, "article", lambda pr: workflow.generate_article(pr, art_dict(a), biz_dict(b), a.outline, opts))
    if a.body_markdown:
        db.add(Revision(article_id=a.id, title=a.title, body_markdown=a.body_markdown, created_by=u.id))
    a.body_markdown, a.seo_title, a.meta_description = res.body_markdown, res.seo_title, res.meta_description
    a.slug = slugify(res.slug) or a.slug
    a.sources_to_verify, a.editorial_notes = res.sources_to_verify, res.editorial_notes
    a.generation_meta = {**a.generation_meta, "provider": p.name, "model": p.model, "mock": p.is_mock, "options": opts,
                         "inputs_used": ["business profile", "outline", *(["fetched homepage metadata"] if b.context_source == "crawled" else [])]}
    a.status = "draft"
    db.add(Revision(article_id=a.id, title=a.title, body_markdown=a.body_markdown, created_by=u.id))
    db.flush()
    from urllib.parse import urlparse
    result = seo_audit.audit({**art_dict(a)}, None, urlparse(b.website_url or "").netloc)
    from ..models import SeoAudit
    sa = SeoAudit(article_id=a.id, score=result["score"], results=result)
    db.add(sa)
    db.commit()
    return {"article": ArticleOut.model_validate(a).model_dump(mode="json"), "audit": {"id": sa.id, **result}}


@content.get("/articles", response_model=list[ArticleOut])
def list_articles(business_id: int, status: str | None = None, cluster_id: int | None = None, q: str | None = None,
                  u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, business_id)
    st = select(Article).where(Article.business_id == business_id)
    if status:
        st = st.where(Article.status == status)
    if cluster_id:
        st = st.where(Article.cluster_id == cluster_id)
    if q:
        st = st.where(Article.title.ilike(f"%{q}%") | Article.primary_keyword.ilike(f"%{q}%"))
    return db.scalars(st.order_by(Article.updated_at.desc()).limit(500)).all()


@content.get("/articles/{aid}", response_model=ArticleOut)
def get_one(aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_article(db, u, aid)[0]


@content.patch("/articles/{aid}", response_model=ArticleOut)
def patch_article(aid: int, body: ArticlePatch, u: User = Depends(current_user), db: Session = Depends(get_db)):
    a, b = get_article(db, u, aid)
    d = body.model_dump(exclude_unset=True)
    if "slug" in d and d["slug"] is not None and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", d["slug"]):
        raise AppError(422, "invalid_slug", "Slug must be lowercase letters, numbers and hyphens")
    if d.get("cluster_id"):
        c = db.get(Cluster, d["cluster_id"])
        if not c or c.business_id != b.id:
            raise AppError(404, "not_found", "Cluster not found")
    if "body_markdown" in d and d["body_markdown"] is not None and d["body_markdown"] != a.body_markdown:
        if a.body_markdown:
            db.add(Revision(article_id=a.id, title=a.title, body_markdown=a.body_markdown, created_by=u.id))
    for f, v in d.items():
        if v is not None or f in ("target_url", "cluster_id"):
            setattr(a, f, v)
    if d.get("status") == "published":
        from datetime import datetime, timezone
        for e in db.scalars(select(CalendarEntry).where(CalendarEntry.article_id == a.id)):
            e.status, e.published_date = "published", e.published_date or datetime.now(timezone.utc)
    db.commit()
    return a


@content.delete("/articles/{aid}", status_code=204)
def delete_article(aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(get_article(db, u, aid)[0])
    db.commit()


@content.post("/articles/{aid}/duplicate", response_model=ArticleOut, status_code=201)
def duplicate(aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    a, b = get_article(db, u, aid)
    used = {s for (s,) in db.execute(select(Article.slug).where(Article.business_id == b.id))}
    n = Article(business_id=a.business_id, cluster_id=a.cluster_id, keyword_id=None, title=f"Copy of {a.title}"[:300], primary_keyword=a.primary_keyword,
                secondary_keywords=a.secondary_keywords, intent=a.intent, funnel_stage=a.funnel_stage, content_type=a.content_type, priority=a.priority,
                status="planned", slug=cl.slug_unique(a.slug or a.primary_keyword, used), seo_title=a.seo_title, meta_description=a.meta_description,
                brief=a.brief, outline=a.outline, body_markdown=a.body_markdown, cta_text=a.cta_text)
    db.add(n)
    db.commit()
    return n


@content.get("/articles/{aid}/revisions")
def revisions(aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_article(db, u, aid)
    return [{"id": r.id, "title": r.title, "created_at": r.created_at, "body_markdown": r.body_markdown}
            for r in db.scalars(select(Revision).where(Revision.article_id == aid).order_by(Revision.id.desc()).limit(50))]
