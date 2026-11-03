"""Internal-link recommendation engine (rule based, no invented URLs)."""
import re
from collections import Counter, defaultdict
from .text import tokens, jaccard

HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)


def _section_for(body: str, pos: int) -> str:
    last = ""
    for m in HEAD.finditer(body):
        if m.start() > pos:
            break
        last = m.group(2)
    return last or "Introduction"


def _find_anchor(body: str, target: dict):
    """Look for a natural phrase in the source body that matches the target topic. Returns (anchor, section) or None."""
    cands = [target.get("primary_keyword") or ""] + list(target.get("secondary_keywords") or [])
    for c in cands:
        if not c:
            continue
        m = re.search(re.escape(c), body, re.I)
        if m and not (body[max(0, m.start() - 1):m.start()] == "[" ):
            return m.group(0), _section_for(body, m.start())
    tk = tokens(target.get("primary_keyword") or "")
    if len(tk) >= 2:
        for sent in re.split(r"(?<=[.!?])\s+", body):
            ws = re.findall(r"[A-Za-z']+", sent)
            for n in (3, 2):
                for i in range(len(ws) - n + 1):
                    chunk = ws[i:i + n]
                    if len(set(tokens(" ".join(chunk))) & set(tk)) >= min(2, len(tk)):
                        pos = body.find(" ".join(chunk))
                        if pos >= 0:
                            return " ".join(chunk), _section_for(body, pos)
    return None


def recommend(articles: list, pages: list, sitemap_complete: bool = False) -> dict:
    """articles: dicts id,title,slug,target_url,status,cluster_id,is_pillar,primary_keyword,secondary_keywords,body_markdown.
    pages: dicts id,url,title (existing website pages the user saved/crawled)."""
    recs, by_id = [], {a["id"]: a for a in articles}
    pillars = {a["cluster_id"]: a for a in articles if a.get("is_pillar") and a.get("cluster_id")}

    def target_info(t):
        if t.get("target_url") and t.get("status") == "published":
            return t["target_url"], "existing_page_unverified"
        return (t.get("target_url") or None), "proposed_future_page"

    for src in articles:
        body = src.get("body_markdown") or ""
        targets, rel = [], {}
        for t in articles:
            if t["id"] == src["id"]:
                continue
            same = src.get("cluster_id") and src.get("cluster_id") == t.get("cluster_id")
            if same and t.get("is_pillar"):
                targets.append(t); rel[t["id"]] = "cluster → pillar"
            elif same and src.get("is_pillar"):
                targets.append(t); rel[t["id"]] = "pillar → cluster"
            elif same:
                sim = jaccard(tokens(src["primary_keyword"] or ""), tokens(t["primary_keyword"] or ""))
                if sim >= 0.2:
                    targets.append(t); rel[t["id"]] = "related cluster article"
        recs_for_src = []
        for t in targets:
            found = _find_anchor(body, t) if body else None
            url, status = target_info(t)
            anchor, section = found if found else (None, None)
            recs_for_src.append({
                "source_article_id": src["id"], "target_article_id": t["id"], "target_page_id": None, "target_url": url,
                "anchor_text": anchor or (t.get("primary_keyword") or t["title"]),
                "section": section or "No natural placement found: add manually",
                "placement_found": bool(found), "relation": rel[t["id"]], "status": status,
                "reason": f"{rel[t['id']].capitalize()}: both articles belong to the same topic cluster and help readers move between related topics.",
            })
        recs.extend(recs_for_src)
        for p in pages:
            sim = jaccard(tokens(p.get("title", "")), tokens(src["primary_keyword"] or ""))
            if sim >= 0.34:
                found = _find_anchor(body, {"primary_keyword": p["title"]}) if body else None
                recs.append({"source_article_id": src["id"], "target_article_id": None, "target_page_id": p["id"],
                             "target_url": p["url"], "anchor_text": found[0] if found else p["title"],
                             "section": found[1] if found else "No natural placement found: add manually",
                             "placement_found": bool(found), "relation": "existing website page", "status": "existing_page_unverified",
                             "reason": "Existing page title overlaps with this article's topic.", "irrelevant_risk": False})
    # ----- problems
    issues = []
    incoming = Counter(r["target_article_id"] for r in recs if r["target_article_id"])
    for a in articles:
        if incoming[a["id"]] == 0 and len(articles) > 1:
            issues.append({"type": "no_incoming_links", "article_id": a["id"],
                           "message": f"“{a['title']}” has no recommended incoming internal links within the available dataset."})
        pil = pillars.get(a.get("cluster_id"))
        if pil and pil["id"] != a["id"]:
            if not any(r["source_article_id"] == pil["id"] and r["target_article_id"] == a["id"] for r in recs):
                issues.append({"type": "missing_pillar_to_cluster", "article_id": a["id"], "message": f"Pillar does not link to “{a['title']}”."})
            if not any(r["source_article_id"] == a["id"] and r["target_article_id"] == pil["id"] for r in recs):
                issues.append({"type": "missing_cluster_to_pillar", "article_id": a["id"], "message": f"“{a['title']}” does not link to its pillar."})
    anchors = defaultdict(Counter)
    for r in recs:
        anchors[r["target_article_id"] or r["target_page_id"]][r["anchor_text"].lower()] += 1
    for tgt, c in anchors.items():
        for a, n in c.items():
            if n >= 3:
                issues.append({"type": "repeated_anchor", "target": tgt, "message": f"Anchor “{a}” is used {n} times for the same target; vary anchors naturally."})
    for r in recs:
        if r["target_article_id"]:
            s, t = by_id[r["source_article_id"]], by_id[r["target_article_id"]]
            if jaccard(tokens(s["primary_keyword"] or ""), tokens(t["primary_keyword"] or "")) == 0 and r["relation"] == "related cluster article":
                issues.append({"type": "potentially_irrelevant", "message": f"Link {s['title']} → {t['title']} may be weakly related."})
    cov = "comprehensive" if sitemap_complete else "limited"
    return {"recommendations": recs, "issues": issues, "coverage": cov,
            "coverage_note": ("Orphan detection covers only the articles and pages saved in this application. "
                              "It is not a full-site audit." if cov == "limited" else "User marked the page inventory as complete.")}
