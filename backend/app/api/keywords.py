from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..ai import workflow
from ..core.db import get_db
from ..core.errors import AppError
from ..models import Keyword, User
from ..schemas import KeywordImportIn, KeywordOut, KeywordPatch, KeywordResearchIn
from ..security.auth import current_user
from ..security.ratelimit import limiter
from ..seo import keywords as kw
from ..seo.intent import FUNNEL
from .deps import biz_dict, get_business, run_ai

router = APIRouter(prefix="/api/v1/keywords", tags=["keywords"])
NOTE = "Search volume, difficulty and CPC are Unavailable: no keyword-data provider is configured, and no values are estimated."


def _save(db, b, rows):
    have = {p for (p,) in db.execute(select(Keyword.phrase).where(Keyword.business_id == b.id))}
    new = []
    for r in rows:
        if r["phrase"] in have:
            continue
        have.add(r["phrase"])
        k = Keyword(business_id=b.id, **r)
        db.add(k)
        new.append(k)
    db.commit()
    return new


@router.post("/research", dependencies=[limiter("ai", "ai_rate_per_min")])
def research(body: KeywordResearchIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    d = biz_dict(b)
    seeds = [body.seed] if body.seed.strip() else []
    services = [body.service] if body.service.strip() else (b.services[:3] if not seeds else [])
    if not (seeds or services or body.niche or b.niche):
        raise AppError(422, "no_seed", "Provide a seed keyword, service or niche")
    items = []
    for s in (seeds or [None]):
        for sv in (services or [""]):
            items += kw.suggest(s or "", body.niche or b.niche, sv, body.audience or b.audience, body.location or b.city)
    ai_used = None
    if body.use_ai:
        res, p = run_ai(db, u, "keywords", lambda pr: workflow.ai_keywords(pr, d, body.seed or (services[0] if services else b.niche)))
        ai_used = p.name
        items += [{"phrase": x, "source": f"ai:{p.name}"} for x in res]
    rows = kw.enrich(items, d, seeds + services)
    new = _save(db, b, rows)
    return {"created": [KeywordOut.model_validate(k).model_dump() for k in new], "skipped_duplicates": len(rows) - len(new),
            "ai_provider": ai_used, "metrics_note": NOTE,
            "source_note": "Suggestions come from template expansion" + (" and an LLM" if ai_used else "") + ", not from search-engine data."}


@router.post("/import", dependencies=[limiter("ai", "ai_rate_per_min")])
def import_csv(body: KeywordImportIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, body.business_id)
    items, errors = kw.parse_csv(body.csv_text)
    new = _save(db, b, kw.enrich(items, biz_dict(b)))
    return {"imported": len(new), "skipped_duplicates": len(items) - len(new), "errors": errors[:50], "metrics_note": NOTE + " Metric columns in CSVs are ignored."}


@router.get("", response_model=list[KeywordOut])
def list_(business_id: int, intent: str | None = None, q: str | None = None, cluster_id: int | None = None,
          u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, business_id)
    st = select(Keyword).where(Keyword.business_id == business_id)
    if intent:
        st = st.where(Keyword.intent == intent)
    if cluster_id:
        st = st.where(Keyword.cluster_id == cluster_id)
    if q:
        st = st.where(Keyword.phrase.contains(q.lower()))
    return db.scalars(st.order_by(Keyword.priority.desc()).limit(1000)).all()


@router.patch("/{kid}", response_model=KeywordOut)
def patch(kid: int, body: KeywordPatch, u: User = Depends(current_user), db: Session = Depends(get_db)):
    k = db.get(Keyword, kid)
    if not k:
        raise AppError(404, "not_found", "Keyword not found")
    get_business(db, u, k.business_id)
    data = body.model_dump(exclude_unset=True)
    if "intent" in data and data["intent"] and data["intent"] != k.intent:
        k.intent_overridden = True
        k.funnel_stage = FUNNEL[data['intent']]
        k.intent_explanation = f"Manually set to {data['intent'].replace('_', ' ')} (was {k.intent.replace('_', ' ')}, heuristic)."
    for f, v in data.items():
        if v is not None:
            setattr(k, f, v)
    db.commit()
    return k
