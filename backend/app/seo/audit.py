"""Deterministic on-page SEO checklist engine. The LLM never scores its own output.

Each check: id, label, status (passed|needs_improvement|not_checked|requires_review),
method (verified|heuristic|ai_assisted|manual), explanation. The score is an INTERNAL checklist
ratio, not a Google ranking score and no guarantee of ranking performance.
"""
import re
from collections import Counter
from .text import tokens, flesch_reading_ease, jaccard

DEFAULT_CFG = {"title_min": 30, "title_max": 60, "meta_min": 70, "meta_max": 160, "slug_max": 60,
               "max_paragraph_words": 120, "max_keyword_density": 3.0, "min_internal_links": 2,
               "min_reading_ease": 45.0, "min_words_for_links": 600}
CTA_WORDS = ("contact", "book", "get a quote", "call", "sign up", "request", "schedule", "start", "subscribe",
             "download", "get started", "talk to", "free consultation")
CLAIM_PATTERNS = [r"\b\d+(?:\.\d+)?\s?%", r"\bstud(?:y|ies) (?:show|found|suggest)", r"\baccording to\b",
                  r"\bresearch (?:shows|found|suggests|indicates)", r"\b(?:#1|number one|best in)\b",
                  r"\bguarantee[sd]?\b", r"\bproven\b", r"\bsurvey(?:s|ed)?\b", r"\b\d{1,3}(?:,\d{3})+\b"]
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$", re.M)


def _c(id_, label, status, method, expl, **extra):
    return {"id": id_, "label": label, "status": status, "method": method, "explanation": expl, **extra}


def _strip(md: str) -> str:
    t = re.sub(r"```.*?```", " ", md, flags=re.S)
    t = LINK.sub(r"\1", t)
    t = re.sub(r"^#{1,6}\s+.*$", " ", t, flags=re.M)
    return re.sub(r"[*_>`|-]{1,}", " ", t)


def audit(article: dict, cfg: dict | None = None, site_domain: str = "") -> dict:
    """article keys: seo_title, meta_description, slug, body_markdown, primary_keyword, secondary_keywords,
    intent, cta_text (optional)."""
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    body = article.get("body_markdown") or ""
    title = (article.get("seo_title") or "").strip()
    meta = (article.get("meta_description") or "").strip()
    slug = (article.get("slug") or "").strip()
    pk = (article.get("primary_keyword") or "").strip().lower()
    sks = [s.strip().lower() for s in article.get("secondary_keywords") or [] if s.strip()]
    heads = [(len(m.group(1)), m.group(2).strip()) for m in HEAD.finditer(body)]
    plain = _strip(body)
    words = re.findall(r"[A-Za-z0-9']+", plain)
    wc = len(words)
    lowtext = plain.lower()
    out = []

    # --- title
    if not title:
        out.append(_c("title_present", "SEO title present", "needs_improvement", "verified", "No SEO title set."))
    else:
        ok = cfg["title_min"] <= len(title) <= cfg["title_max"]
        out.append(_c("title_length", "Title length", "passed" if ok else "needs_improvement", "verified",
                      f"Title is {len(title)} characters (guideline {cfg['title_min']}-{cfg['title_max']}, configurable; "
                      "search engines may rewrite titles)."))
    # --- meta
    if not meta:
        out.append(_c("meta_present", "Meta description present", "needs_improvement", "verified", "No meta description set."))
    else:
        ok = cfg["meta_min"] <= len(meta) <= cfg["meta_max"]
        out.append(_c("meta_length", "Meta description length", "passed" if ok else "needs_improvement", "verified",
                      f"{len(meta)} characters (guideline {cfg['meta_min']}-{cfg['meta_max']}; may be rewritten by search engines)."))
    # --- H1 and hierarchy
    h1s = [t for l, t in heads if l == 1]
    if len(h1s) == 1:
        out.append(_c("single_h1", "Exactly one H1", "passed", "verified", f"One H1 found: “{h1s[0]}”."))
    else:
        out.append(_c("single_h1", "Exactly one H1", "needs_improvement", "verified", f"Found {len(h1s)} H1 headings; expected exactly 1."))
    skips = [(a, b) for (a, _), (b, _) in zip(heads, heads[1:]) if b > a + 1]
    first_ok = not heads or heads[0][0] == 1
    if heads and not skips and first_ok:
        out.append(_c("heading_hierarchy", "Heading hierarchy", "passed", "verified", "No skipped heading levels."))
    else:
        out.append(_c("heading_hierarchy", "Heading hierarchy", "needs_improvement", "verified",
                      "Hierarchy problems: " + ("document does not start with an H1; " if not first_ok else "") +
                      ("; ".join(f"H{a} followed by H{b}" for a, b in skips) if skips else "no headings found." if not heads else "")))
    dup = [t for t, n in Counter(t.lower() for _, t in heads).items() if n > 1]
    out.append(_c("duplicate_headings", "No duplicated headings", "needs_improvement" if dup else "passed", "verified",
                  f"Duplicated headings: {', '.join(dup)}" if dup else "All headings are unique."))
    # --- slug
    if not slug:
        out.append(_c("slug_quality", "URL slug quality", "needs_improvement", "verified", "No slug set."))
    else:
        problems = []
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            problems.append("use lowercase letters, numbers and single hyphens only")
        if len(slug) > cfg["slug_max"]:
            problems.append(f"longer than {cfg['slug_max']} characters")
        if pk and not set(tokens(pk)) & set(tokens(slug.replace("-", " "))):
            problems.append("does not reflect the primary keyword")
        out.append(_c("slug_quality", "URL slug quality", "needs_improvement" if problems else "passed", "verified",
                      "; ".join(problems) if problems else "Slug is short, readable and relevant."))
    # --- keywords
    if not pk:
        out.append(_c("primary_keyword", "Primary keyword relevance", "not_checked", "verified", "No primary keyword set."))
    else:
        in_title = pk in title.lower() or set(tokens(pk)) <= set(tokens(title))
        in_h1 = bool(h1s) and set(tokens(pk)) <= set(tokens(h1s[0]))
        in_intro = set(tokens(pk)) <= set(tokens(" ".join(words[:150])))
        miss = [n for n, v in (("title", in_title), ("H1", in_h1), ("first ~150 words", in_intro)) if not v]
        out.append(_c("primary_keyword", "Primary keyword relevance", "needs_improvement" if miss else "passed", "heuristic",
                      ("Primary keyword topic missing from: " + ", ".join(miss) + ". Natural phrasing is fine; exact repetition is not required.")
                      if miss else "Primary keyword topic appears in the title, H1 and introduction."))
        n_kw = lowtext.count(pk)
        density = round(100 * n_kw * max(len(pk.split()), 1) / wc, 2) if wc else 0
        out.append(_c("keyword_repetition", "Excessive repetition", "needs_improvement" if density > cfg["max_keyword_density"] else "passed",
                      "heuristic", f"Exact primary phrase appears {n_kw}× (≈{density}% of words; limit {cfg['max_keyword_density']}%)."))
    if sks:
        cov = [s for s in sks if set(tokens(s)) <= set(tokens(lowtext))]
        r = len(cov) / len(sks)
        out.append(_c("secondary_coverage", "Secondary keyword coverage", "passed" if r >= 0.5 else "needs_improvement", "heuristic",
                      f"{len(cov)}/{len(sks)} secondary keyword topics covered. Missing: {', '.join(set(sks) - set(cov)) or 'none'}."))
    else:
        out.append(_c("secondary_coverage", "Secondary keyword coverage", "not_checked", "verified", "No secondary keywords provided."))
    # --- intent alignment
    intent = article.get("intent")
    cues = {"commercial_investigation": ("compare", "comparison", " vs ", "pros", "cons", "criteria", "alternatives", "best"),
            "transactional": ("price", "pricing", "cost", "quote", "book", "included", "how it works", "contact"),
            "informational": ("what is", "how to", "step", "guide", "why", "example", "tips"),
            "navigational": ("contact", "login", "official")}
    if intent in cues:
        hh = " ".join(t.lower() for _, t in heads) + " " + lowtext[:600]
        hit = [c for c in cues[intent] if c in hh]
        out.append(_c("intent_alignment", "Search intent alignment", "passed" if hit else "needs_improvement", "heuristic",
                      f"Format cues for {intent.replace('_', ' ')} intent found: {', '.join(hit)}." if hit else
                      f"No typical {intent.replace('_', ' ')} format cues in headings/intro. Confirm the page answers the searcher's goal."))
    else:
        out.append(_c("intent_alignment", "Search intent alignment", "not_checked", "verified", "No intent recorded for this article."))
    out.append(_c("intent_judgment", "Does the content satisfy the searcher's actual question?", "requires_review", "manual",
                  "Needs an editor: automated checks cannot tell whether the article is genuinely helpful."))
    # --- readability & paragraphs
    fre = flesch_reading_ease(plain)
    if fre is None:
        out.append(_c("readability", "Readability", "not_checked", "heuristic", "Too little text for a reliable Flesch score."))
    else:
        out.append(_c("readability", "Readability", "passed" if fre >= cfg["min_reading_ease"] else "needs_improvement", "heuristic",
                      f"Flesch reading ease ≈ {fre} (target ≥ {cfg['min_reading_ease']}; English only, approximate syllable counting)."))
    paras = [p for p in re.split(r"\n\s*\n", re.sub(r"^#{1,6}.*$", "", body, flags=re.M)) if len(p.split()) > 0 and not p.strip().startswith(("-", "*", "|", "1."))]
    long_ = [i + 1 for i, p in enumerate(paras) if len(p.split()) > cfg["max_paragraph_words"]]
    out.append(_c("paragraph_length", "Paragraph length", "needs_improvement" if long_ else "passed", "verified",
                  f"Paragraphs over {cfg['max_paragraph_words']} words: #{', #'.join(map(str, long_))}." if long_ else "No overly long paragraphs."))
    sents = [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+", plain) if len(s.split()) > 6]
    repeated = [s for s, n in Counter(sents).items() if n > 1]
    out.append(_c("repeated_sentences", "Repeated sentences", "needs_improvement" if repeated else "passed", "verified",
                  f"{len(repeated)} sentence(s) repeated verbatim." if repeated else "No verbatim repeated sentences."))
    # --- links
    links = LINK.findall(body)
    internal = [u for _, u in links if u.startswith(("/", "#")) or (site_domain and site_domain in u)]
    need = wc >= cfg["min_words_for_links"]
    if not need:
        out.append(_c("internal_links", "Internal-link coverage", "not_checked", "verified", f"Article under {cfg['min_words_for_links']} words; not checked."))
    else:
        out.append(_c("internal_links", "Internal-link coverage", "passed" if len(internal) >= cfg["min_internal_links"] else "needs_improvement",
                      "verified", f"{len(internal)} internal link(s) (recommended ≥ {cfg['min_internal_links']} where relevant targets exist). "
                      "Link targets are not fetched, so link validity is unverified."))
    # --- CTA & FAQ
    cta_text = (article.get("cta_text") or "").strip().lower()
    has_cta = any(w in lowtext[-1200:] for w in CTA_WORDS) or (cta_text and cta_text[:25] in lowtext)
    out.append(_c("cta", "Contextual CTA present", "passed" if has_cta else "needs_improvement", "heuristic",
                  "A call-to-action phrase was found near the end." if has_cta else "No CTA phrase found near the end of the article."))
    faq_idx = next((i for i, (_, t) in enumerate(heads) if re.search(r"faq|frequently asked", t, re.I)), None)
    if faq_idx is None:
        out.append(_c("faq", "FAQ relevance", "not_checked", "verified", "No FAQ section."))
    else:
        qs = [t for l, t in heads[faq_idx + 1:] if l >= 3]
        bad = [q for q in qs if not q.endswith("?") or jaccard(tokens(q), tokens(pk + " " + " ".join(sks))) == 0]
        out.append(_c("faq", "FAQ relevance", "requires_review" if not bad else "needs_improvement", "heuristic",
                      "FAQ questions look topically connected; an editor should confirm they match real user questions." if not bad else
                      "FAQ questions that are not phrased as questions or share no terms with the target keywords: " + "; ".join(bad)))
    # --- claims
    flagged = []
    for s in re.split(r"(?<=[.!?])\s+|\n", body):
        if any(re.search(p, s, re.I) for p in CLAIM_PATTERNS) and not LINK.search(s):
            flagged.append(s.strip()[:200])
    out.append(_c("claims_evidence", "Claims that need evidence", "requires_review" if flagged else "passed", "heuristic",
                  f"{len(flagged)} statement(s) look like statistics, studies or superlatives without a cited source." if flagged
                  else "No unsupported-looking factual patterns detected (pattern-based; not a fact check).", flagged=flagged[:25]))
    out.append(_c("external_sources", "External sources exist and are relevant", "requires_review", "manual",
                  "Source existence is NOT verified by this application. Verify every external reference by hand."))
    scorable = [c for c in out if c["status"] in ("passed", "needs_improvement")]
    score = round(100 * sum(c["status"] == "passed" for c in scorable) / len(scorable)) if scorable else None
    return {"checks": out, "score": score, "word_count": wc,
            "summary": {s: sum(c["status"] == s for c in out) for s in ("passed", "needs_improvement", "not_checked", "requires_review")},
            "disclaimer": "Internal checklist score only. Not a Google ranking score; no guarantee of ranking performance."}
