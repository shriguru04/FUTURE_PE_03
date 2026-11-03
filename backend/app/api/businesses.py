from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.db import get_db
from ..core.errors import AppError
from ..models import Business, User, WebsitePage
from ..schemas import BusinessIn, BusinessOut, BusinessPatch, PageIn, PageOut
from ..security.auth import current_user
from ..security.ratelimit import limiter
from ..security.ssrf import fetch_html, parse_page, validate_public_url
from .deps import get_business

router = APIRouter(prefix="/api/v1/businesses", tags=["businesses"])


def _check_url(v):
    if v and not v.lower().startswith(("http://", "https://")):
        raise AppError(422, "invalid_url", "Website URL must start with http:// or https://")


@router.get("", response_model=list[BusinessOut])
def list_(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Business).where(Business.owner_id == u.id).order_by(Business.id.desc())).all()


@router.post("", response_model=BusinessOut, status_code=201)
def create(body: BusinessIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    _check_url(body.website_url)
    b = Business(owner_id=u.id, **body.model_dump())
    db.add(b)
    db.commit()
    return b


@router.get("/{bid}", response_model=BusinessOut)
def get(bid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_business(db, u, bid)


@router.patch("/{bid}", response_model=BusinessOut)
def patch(bid: int, body: BusinessPatch, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, u, bid)
    data = body.model_dump(exclude_unset=True)
    _check_url(data.get("website_url"))
    if "name" in data and data["name"] is None:
        raise AppError(422, "validation", "name cannot be null")
    for k, v in data.items():
        if v is not None or k == "website_url":
            setattr(b, k, v)
    db.commit()
    return b


@router.delete("/{bid}", status_code=204)
def delete(bid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(get_business(db, u, bid))
    db.commit()


@router.get("/{bid}/pages", response_model=list[PageOut])
def pages(bid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, bid)
    return db.scalars(select(WebsitePage).where(WebsitePage.business_id == bid)).all()


@router.post("/{bid}/pages", response_model=PageOut, status_code=201)
def add_page(bid: int, body: PageIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    get_business(db, u, bid)
    if db.scalar(select(WebsitePage).where(WebsitePage.business_id == bid, WebsitePage.url == body.url)):
        raise AppError(409, "duplicate", "This URL is already saved")
    p = WebsitePage(business_id=bid, source="manual", **body.model_dump())
    db.add(p)
    db.commit()
    return p


@router.post("/{bid}/analyze-website", dependencies=[limiter("fetch", "ai_rate_per_min")])
def analyze(bid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Fetches ONE page (the saved website URL). This is not a site crawl."""
    b = get_business(db, u, bid)
    if not b.website_url:
        raise AppError(422, "no_url", "Business has no website URL")
    validate_public_url(b.website_url)
    info = parse_page(fetch_html(b.website_url))
    page = db.scalar(select(WebsitePage).where(WebsitePage.business_id == bid, WebsitePage.url == b.website_url))
    summary = f"{info['meta_description']} | Headings: {'; '.join(info['headings'])}"[:2000]
    if not page:
        page = WebsitePage(business_id=bid, url=b.website_url)
        db.add(page)
    page.title, page.summary, page.source, page.fetched_at = info["title"], summary, "crawled", datetime.now(timezone.utc)
    b.context_source, b.crawled_at = "crawled", datetime.now(timezone.utc)
    db.commit()
    return {"pages_fetched": 1, "title": info["title"], "note": "Only the homepage URL was fetched; this is not a full crawl."}
