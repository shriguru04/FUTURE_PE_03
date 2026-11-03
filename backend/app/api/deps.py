from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..ai.base import ProviderError
from ..ai.providers import get_provider
from ..core.config import get_settings
from ..core.errors import AppError
from ..models import Article, Business, GenerationJob, User


def get_business(db: Session, user: User, bid: int) -> Business:
    b = db.get(Business, bid)
    if not b or b.owner_id != user.id:
        raise AppError(404, "not_found", "Business not found")  # 404 (not 403) so existence is not leaked
    return b


def get_article(db: Session, user: User, aid: int):
    a = db.get(Article, aid)
    if not a:
        raise AppError(404, "not_found", "Article not found")
    return a, get_business(db, user, a.business_id)


def biz_dict(b: Business) -> dict:
    return {c: getattr(b, c) for c in ("name", "website_url", "niche", "services", "audience", "country", "city", "language", "brand_voice",
                                      "writing_style", "objectives", "conversion_goal", "competitors", "target_keywords", "context_source")}


def art_dict(a: Article) -> dict:
    return {c: getattr(a, c) for c in ("id", "title", "primary_keyword", "secondary_keywords", "intent", "brief", "cta_text", "slug",
                                      "seo_title", "meta_description", "body_markdown", "cluster_id", "is_pillar", "status", "target_url")}


def run_ai(db: Session, user: User, kind: str, fn):
    """Quota check -> provider call -> usage record. Maps provider errors to a safe 502."""
    s = get_settings()
    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = db.scalar(select(func.count()).select_from(GenerationJob).where(GenerationJob.user_id == user.id, GenerationJob.created_at >= since))
    if used >= s.ai_daily_limit:
        raise AppError(429, "quota_exceeded", "Daily AI generation limit reached")
    try:
        p = get_provider()
    except ProviderError as e:
        raise AppError(500, "provider_misconfigured", str(e))
    try:
        result, usage = fn(p)
        db.add(GenerationJob(user_id=user.id, kind=kind, provider=p.name, model=p.model, status="ok",
                             input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens")))
        db.commit()
        return result, p
    except ProviderError as e:
        db.add(GenerationJob(user_id=user.id, kind=kind, provider=p.name, model=p.model, status="error", error=str(e)[:500]))
        db.commit()
        raise AppError(502, "ai_provider_error", str(e))
