import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["idea", "planned", "outline", "draft", "in_review", "approved", "published", "archived"]
Intent = Literal["informational", "navigational", "commercial_investigation", "transactional"]
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=10, max_length=128)
    role: Literal["business_owner", "seo_professional"] = "business_owner"

    @field_validator("email")
    @classmethod
    def _e(cls, v):
        v = v.strip().lower()
        if not EMAIL.match(v):
            raise ValueError("invalid email")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(ORM):
    id: int
    email: str
    role: str
    is_active: bool


class BusinessIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website_url: str | None = Field(default=None, max_length=500)
    niche: str = ""
    services: list[str] = []
    audience: str = ""
    country: str = ""
    city: str = ""
    language: str = "en"
    brand_voice: str = ""
    writing_style: str = ""
    objectives: str = ""
    conversion_goal: str = ""
    competitors: list[str] = []
    target_keywords: list[str] = []


class BusinessPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    website_url: str | None = None
    niche: str | None = None
    services: list[str] | None = None
    audience: str | None = None
    country: str | None = None
    city: str | None = None
    language: str | None = None
    brand_voice: str | None = None
    writing_style: str | None = None
    objectives: str | None = None
    conversion_goal: str | None = None
    competitors: list[str] | None = None
    target_keywords: list[str] | None = None


class BusinessOut(BusinessIn, ORM):
    id: int
    context_source: str
    crawled_at: datetime | None


class PageIn(BaseModel):
    url: str = Field(max_length=600)
    title: str = Field(default="", max_length=300)
    summary: str = ""


class PageOut(ORM):
    id: int
    url: str
    title: str
    summary: str
    source: str


class KeywordResearchIn(BaseModel):
    business_id: int
    seed: str = Field(default="", max_length=150)
    service: str = ""
    niche: str = ""
    audience: str = ""
    location: str = ""
    use_ai: bool = False


class KeywordImportIn(BaseModel):
    business_id: int
    csv_text: str = Field(max_length=500_000)


class KeywordPatch(BaseModel):
    intent: Intent | None = None
    is_local: bool | None = None
    topic: str | None = None
    content_type: str | None = None
    priority: int | None = Field(default=None, ge=0, le=100)


class KeywordOut(ORM):
    id: int
    business_id: int
    cluster_id: int | None
    phrase: str
    intent: str
    intent_explanation: str
    intent_overridden: bool
    is_local: bool
    funnel_stage: str
    topic: str
    relevance: float
    content_type: str
    priority: int
    source: str
    search_volume: int | None
    difficulty: float | None
    cpc: float | None


class ClusterGenIn(BaseModel):
    business_id: int
    keyword_ids: list[int] | None = None


class ClusterOut(ORM):
    id: int
    business_id: int
    name: str
    pillar_keyword: str
    cannibalization: list


class BriefIn(BaseModel):
    business_id: int
    keyword_id: int | None = None
    primary_keyword: str | None = Field(default=None, max_length=250)
    title: str | None = Field(default=None, max_length=300)
    cluster_id: int | None = None
    cta_text: str = ""


class OutlineGenIn(BaseModel):
    article_id: int


class ArticleGenIn(BaseModel):
    article_id: int
    target_words: int = Field(default=1200, ge=300, le=4000)
    tone: str = "professional, clear"
    reading_level: str = "general adult"
    article_format: str = "educational guide"
    language: str | None = None
    extra_instructions: str = Field(default="", max_length=1000)


class ArticlePatch(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    primary_keyword: str | None = None
    secondary_keywords: list[str] | None = None
    status: Status | None = None
    slug: str | None = Field(default=None, max_length=200)
    target_url: str | None = None
    seo_title: str | None = Field(default=None, max_length=300)
    meta_description: str | None = Field(default=None, max_length=400)
    body_markdown: str | None = Field(default=None, max_length=200_000)
    outline: dict | None = None
    cta_text: str | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    cluster_id: int | None = None


class ArticleOut(ORM):
    id: int
    business_id: int
    cluster_id: int | None
    keyword_id: int | None
    title: str
    primary_keyword: str
    secondary_keywords: list
    intent: str
    funnel_stage: str
    content_type: str
    is_pillar: bool
    priority: int
    status: str
    slug: str
    target_url: str | None
    seo_title: str
    meta_description: str
    brief: dict
    outline: dict
    body_markdown: str
    cta_text: str
    editorial_notes: list
    sources_to_verify: list
    generation_meta: dict
    updated_at: datetime


class AuditIn(BaseModel):
    article_id: int
    config: dict | None = None


class LinkRecIn(BaseModel):
    business_id: int
    sitemap_complete: bool = False


class LocalIn(BaseModel):
    business_id: int
    service: str = Field(min_length=2, max_length=150)
    city: str = Field(min_length=2, max_length=100)
    service_area: str = ""
    local_audience: str = ""
    primary_keyword: str = ""
    local_context: str = Field(min_length=80, max_length=3000)
    local_facts: list[str] = Field(min_length=2, max_length=12)


class CalendarIn(BaseModel):
    business_id: int
    topic: str = Field(min_length=1, max_length=300)
    article_id: int | None = None
    cluster_id: int | None = None
    assignee_id: int | None = None
    primary_keyword: str = ""
    priority: int = Field(default=0, ge=0, le=100)
    status: Status = "planned"
    target_url: str | None = None
    planned_date: datetime | None = None
    published_date: datetime | None = None


class CalendarPatch(BaseModel):
    topic: str | None = None
    assignee_id: int | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    status: Status | None = None
    target_url: str | None = None
    planned_date: datetime | None = None
    published_date: datetime | None = None


class CalendarOut(ORM):
    id: int
    business_id: int
    article_id: int | None
    cluster_id: int | None
    assignee_id: int | None
    topic: str
    primary_keyword: str
    priority: int
    status: str
    target_url: str | None
    planned_date: datetime | None
    published_date: datetime | None


class ExportIn(BaseModel):
    business_id: int
    article_id: int | None = None
    format: Literal["md", "txt", "docx", "pdf", "csv_keywords", "csv_calendar"]
