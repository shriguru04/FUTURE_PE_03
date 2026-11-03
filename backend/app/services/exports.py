"""SEO Blog Pack builder + renderers. Everything is read from the saved DB state."""
import csv
import io
import re
from xml.sax.saxutils import escape
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Article, Business, CalendarEntry, Cluster, InternalLink, Keyword, SeoAudit, WebsitePage

HEAD = re.compile(r"^(#{1,6})\s+(.*)$")


def _latest_audit(db, aid):
    return db.scalars(select(SeoAudit).where(SeoAudit.article_id == aid).order_by(SeoAudit.id.desc())).first()


def build_pack(db: Session, b: Business, article: Article | None) -> str:
    kws = db.scalars(select(Keyword).where(Keyword.business_id == b.id).order_by(Keyword.priority.desc())).all()
    clusters = db.scalars(select(Cluster).where(Cluster.business_id == b.id)).all()
    arts = db.scalars(select(Article).where(Article.business_id == b.id)).all()
    cal = db.scalars(select(CalendarEntry).where(CalendarEntry.business_id == b.id)).all()
    pages = db.scalars(select(WebsitePage).where(WebsitePage.business_id == b.id)).all()
    L = [f"# SEO Blog Pack: {b.name}", "", "_AI-assisted draft material. Metrics marked Unavailable were not provided by any data source; "
         "the checklist score is not a Google ranking score._", "", "## 1. Business Context Summary", ""]
    L += [f"- **Website:** {b.website_url or 'n/a'}", f"- **Niche:** {b.niche}", f"- **Services:** {', '.join(b.services or [])}",
          f"- **Audience:** {b.audience}", f"- **Location:** {', '.join(x for x in (b.city, b.country) if x)}",
          f"- **Language / voice:** {b.language} / {b.brand_voice}", f"- **Conversion goal:** {b.conversion_goal}",
          f"- **Context source:** {'Website pages were fetched (' + str(len(pages)) + ' page records)' if b.context_source == 'crawled' else 'Manually supplied; the website was not crawled'}", ""]
    L += ["## 2. Keyword Research Results", "", "| Keyword | Intent | Funnel | Relevance | Priority | Source | Volume | Difficulty |", "|---|---|---|---|---|---|---|---|"]
    for k in kws[:200]:
        L.append(f"| {k.phrase} | {k.intent.replace('_', ' ')}{' + local' if k.is_local else ''} | {k.funnel_stage} | {k.relevance} | {k.priority} | {k.source} | "
                 f"{k.search_volume if k.search_volume is not None else 'Unavailable'} | {k.difficulty if k.difficulty is not None else 'Unavailable'} |")
    L += ["", "## 3. Search Intent Classifications", ""]
    for k in kws[:60]:
        L.append(f"- **{k.phrase}**: {k.intent_explanation}{' (manually corrected)' if k.intent_overridden else ' (heuristic)'}")
    L += ["", "## 4. Keyword Clusters and 5. Pillar-and-Cluster Content Map", ""]
    for c in clusters:
        L.append(f"### {c.name} (pillar keyword: {c.pillar_keyword})")
        for a in [a for a in arts if a.cluster_id == c.id]:
            L.append(f"- {'**Pillar**' if a.is_pillar else 'Cluster'}: {a.title} · `{a.primary_keyword}` · {a.intent.replace('_', ' ')} · /{a.slug} · {a.status}")
        for w in c.cannibalization or []:
            L.append(f"- ⚠ Possible cannibalization: {' / '.join(w['keywords'])}. {w['explanation']}")
        L.append("")
    L += ["## 6. Recommended Content Calendar", "", "| Date | Topic | Keyword | Status | Priority |", "|---|---|---|---|---|"]
    for e in sorted(cal, key=lambda e: (e.planned_date is None, e.planned_date)):
        L.append(f"| {e.planned_date.date() if e.planned_date else 'Unscheduled'} | {e.topic} | {e.primary_keyword} | {e.status} | {e.priority} |")
    L.append("")
    if article:
        o = article.outline or {}
        L += ["## 7. Selected Blog Outline", "", f"**H1:** {o.get('h1', article.title)}", ""]
        for s in o.get("sections", []):
            L.append(f"- **{s['h2']}**" + ("".join(f"\n  - {h}" for h in s.get("h3", []))))
        L += ["", "## 8. Complete Blog Article", "", article.body_markdown or "_No article body saved yet._", "",
              "## 9. SEO Title, Meta Description and 10. URL Slug", "", f"- **Title:** {article.seo_title}", f"- **Meta description:** {article.meta_description}",
              f"- **Slug:** /{article.slug}", "", "## 11. Internal-Linking Recommendations", ""]
        for l in db.scalars(select(InternalLink).where(InternalLink.source_article_id == article.id)):
            L.append(f"- “{l.anchor_text}” → {l.target_url or 'proposed future page'} ({l.status.replace('_', ' ')}) · section: {l.section} · {l.reason}")
        L += ["", "## 12. Local SEO Adaptations", "", "_Generated separately in the Local SEO workspace; not auto-included._", "", "## 13. SEO Validation Report", ""]
        au = _latest_audit(db, article.id)
        if au:
            L.append(f"Checklist score (internal, not a ranking score): **{au.score}**")
            for c in au.results["checks"]:
                L.append(f"- [{c['status'].replace('_', ' ')} · {c['method']}] **{c['label']}**: {c['explanation']}")
            L += ["", "## 14. Claims and Evidence Review", ""]
            cl = next((c for c in au.results["checks"] if c["id"] == "claims_evidence"), None)
            for f in (cl or {}).get("flagged", []):
                L.append(f"- Needs a verified source: “{f}”")
            for s in article.sources_to_verify or []:
                L.append(f"- Verify manually (not checked by this app): {s}")
        else:
            L.append("_No audit has been run for this article._")
        L += ["", "## 15. Editorial Recommendations", ""]
        L += [f"- {n}" for n in article.editorial_notes or []] or ["- Human editorial review is required before publishing."]
        gm = article.generation_meta or {}
        L += ["", f"_Generation: provider `{gm.get('provider', 'n/a')}`{' (MOCK scaffold, no LLM)' if gm.get('mock') else ''}._"]
    else:
        L += ["_Select an article to include sections 7-15._"]
    return "\n".join(L)


def md_to_text(md: str) -> str:
    t = re.sub(r"^#{1,6}\s+", "", md, flags=re.M)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", t)
    return re.sub(r"[*_`]{1,3}", "", t)


def render_docx(md: str) -> bytes:
    from docx import Document
    d = Document()
    for line in md.splitlines():
        m = HEAD.match(line)
        if m:
            d.add_heading(re.sub(r"[*_`]", "", m.group(2)), level=min(len(m.group(1)), 4) - 0)
        elif line.startswith(("- ", "* ")):
            d.add_paragraph(md_to_text(line[2:]), style="List Bullet")
        elif line.startswith("|"):
            if not re.match(r"^\|[-| ]+\|$", line):
                d.add_paragraph(md_to_text(line.strip("|").replace("|", "  ·  ")))
        elif line.strip():
            d.add_paragraph(md_to_text(line))
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def render_pdf(md: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    ss = getSampleStyleSheet()
    story = []
    for line in md.splitlines():
        m = HEAD.match(line)
        if m:
            story.append(Paragraph(escape(re.sub(r"[*_`]", "", m.group(2))), ss[f"Heading{min(len(m.group(1)), 4)}"]))
        elif line.strip():
            txt = escape(md_to_text(line[2:] if line.startswith(("- ", "* ")) else line))
            story.append(Paragraph(("• " if line.startswith(("- ", "* ")) else "") + txt, ss["BodyText"]))
        else:
            story.append(Spacer(1, 4))
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4).build(story or [Paragraph("(empty)", ss["BodyText"])])
    return buf.getvalue()


def _safe(cell):
    s = "" if cell is None else str(cell)
    return "'" + s if s[:1] in "=+-@" else s  # CSV/Excel formula-injection guard


def csv_keywords(db, b) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["keyword", "intent", "local", "funnel", "topic", "content_type", "relevance", "priority", "source", "volume", "difficulty", "cpc"])
    for k in db.scalars(select(Keyword).where(Keyword.business_id == b.id).order_by(Keyword.priority.desc())):
        w.writerow([_safe(x) for x in (k.phrase, k.intent, k.is_local, k.funnel_stage, k.topic, k.content_type, k.relevance, k.priority, k.source,
                                      *(v if v is not None else "Unavailable" for v in (k.search_volume, k.difficulty, k.cpc)))])
    return out.getvalue().encode()


def csv_calendar(db, b) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["planned_date", "topic", "primary_keyword", "cluster_id", "assignee_id", "priority", "status", "target_url", "published_date"])
    for e in db.scalars(select(CalendarEntry).where(CalendarEntry.business_id == b.id)):
        w.writerow([_safe(x) for x in (e.planned_date, e.topic, e.primary_keyword, e.cluster_id, e.assignee_id, e.priority, e.status, e.target_url, e.published_date)])
    return out.getvalue().encode()
