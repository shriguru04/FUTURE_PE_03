from pydantic import BaseModel, Field


class OutlineSection(BaseModel):
    h2: str = Field(min_length=3, max_length=200)
    h3: list[str] = []
    questions: list[str] = []
    key_concepts: list[str] = []
    evidence_needed: list[str] = []


class OutlineOut(BaseModel):
    seo_title: str
    h1: str
    intro_objective: str
    sections: list[OutlineSection] = Field(min_length=2)
    faq: list[str] = []
    internal_link_ideas: list[str] = []
    cta: str = ""
    conclusion_objective: str = ""


class ArticleOut(BaseModel):
    seo_title: str
    meta_description: str
    slug: str
    body_markdown: str = Field(min_length=200)
    sources_to_verify: list[str] = []
    editorial_notes: list[str] = []


class KeywordSuggestions(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=60)


class LocalOut(BaseModel):
    titles: list[str]
    meta_descriptions: list[str]
    service_page_outline: list[str]
    blog_outline: list[str]
    faqs: list[str]
    content_ideas: list[str]
    ctas: list[str]
