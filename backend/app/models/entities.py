from datetime import datetime, timezone
from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.db import Base


def now():
    return datetime.now(timezone.utc)


ROLES = ("business_owner", "seo_professional", "admin")
STATUSES = ("idea", "planned", "outline", "draft", "in_review", "approved", "published", "archived")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="business_owner")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    website_url: Mapped[str | None] = mapped_column(String(500))
    niche: Mapped[str] = mapped_column(String(200), default="")
    services: Mapped[list] = mapped_column(JSON, default=list)
    audience: Mapped[str] = mapped_column(String(300), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    language: Mapped[str] = mapped_column(String(40), default="en")
    brand_voice: Mapped[str] = mapped_column(String(300), default="")
    writing_style: Mapped[str] = mapped_column(String(300), default="")
    objectives: Mapped[str] = mapped_column(Text, default="")
    conversion_goal: Mapped[str] = mapped_column(String(300), default="")
    competitors: Mapped[list] = mapped_column(JSON, default=list)
    target_keywords: Mapped[list] = mapped_column(JSON, default=list)
    context_source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | crawled
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    pages = relationship("WebsitePage", cascade="all, delete-orphan")


class WebsitePage(Base):
    __tablename__ = "website_pages"
    __table_args__ = (UniqueConstraint("business_id", "url"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(600))
    title: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | crawled
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Cluster(Base):
    __tablename__ = "clusters"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    pillar_keyword: Mapped[str] = mapped_column(String(250))
    cannibalization: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("business_id", "phrase"), Index("ix_kw_business_intent", "business_id", "intent"))
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id", ondelete="SET NULL"))
    phrase: Mapped[str] = mapped_column(String(250))
    intent: Mapped[str] = mapped_column(String(40), default="informational")
    intent_explanation: Mapped[str] = mapped_column(Text, default="")
    intent_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    is_local: Mapped[bool] = mapped_column(Boolean, default=False)
    funnel_stage: Mapped[str] = mapped_column(String(10), default="TOFU")
    topic: Mapped[str] = mapped_column(String(120), default="")
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    content_type: Mapped[str] = mapped_column(String(40), default="educational_guide")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(60), default="manual")
    # Metrics are intentionally nullable: never fabricated. Filled only by a real provider integration.
    search_volume: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[float | None] = mapped_column(Float)
    cpc: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id", ondelete="SET NULL"), index=True)
    keyword_id: Mapped[int | None] = mapped_column(ForeignKey("keywords.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300))
    primary_keyword: Mapped[str] = mapped_column(String(250), default="")
    secondary_keywords: Mapped[list] = mapped_column(JSON, default=list)
    intent: Mapped[str] = mapped_column(String(40), default="informational")
    funnel_stage: Mapped[str] = mapped_column(String(10), default="TOFU")
    content_type: Mapped[str] = mapped_column(String(40), default="educational_guide")
    is_pillar: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="idea", index=True)
    slug: Mapped[str] = mapped_column(String(200), default="")
    target_url: Mapped[str | None] = mapped_column(String(600))
    seo_title: Mapped[str] = mapped_column(String(300), default="")
    meta_description: Mapped[str] = mapped_column(String(400), default="")
    brief: Mapped[dict] = mapped_column(JSON, default=dict)
    outline: Mapped[dict] = mapped_column(JSON, default=dict)
    body_markdown: Mapped[str] = mapped_column(Text, default="")
    cta_text: Mapped[str] = mapped_column(String(300), default="")
    editorial_notes: Mapped[list] = mapped_column(JSON, default=list)
    sources_to_verify: Mapped[list] = mapped_column(JSON, default=list)
    generation_meta: Mapped[dict] = mapped_column(JSON, default=dict)  # provider, model, inputs used, mock flag
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    audits = relationship("SeoAudit", cascade="all, delete-orphan")
    revisions = relationship("Revision", cascade="all, delete-orphan")


class Revision(Base):
    __tablename__ = "revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    body_markdown: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SeoAudit(Base):
    __tablename__ = "seo_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    score: Mapped[int | None] = mapped_column(Integer)
    results: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InternalLink(Base):
    __tablename__ = "internal_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    source_article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    target_article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    target_page_id: Mapped[int | None] = mapped_column(ForeignKey("website_pages.id", ondelete="CASCADE"))
    target_url: Mapped[str | None] = mapped_column(String(600))
    anchor_text: Mapped[str] = mapped_column(String(300))
    section: Mapped[str] = mapped_column(String(300), default="")
    relation: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(40), default="proposed_future_page")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CalendarEntry(Base):
    __tablename__ = "calendar_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id", ondelete="SET NULL"))
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id", ondelete="SET NULL"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    topic: Mapped[str] = mapped_column(String(300))
    primary_keyword: Mapped[str] = mapped_column(String(250), default="")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    target_url: Mapped[str | None] = mapped_column(String(600))
    planned_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExportRecord(Base):
    __tablename__ = "exports"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id", ondelete="SET NULL"))
    fmt: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(200))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20))  # ok | error
    error: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
