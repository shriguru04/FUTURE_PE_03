"""Keyword suggestion (template expansion) + CSV import. No volume/difficulty/CPC is ever generated."""
import csv
import io
from .intent import classify, relevance, priority_score, suggested_content_type
from .text import tokens

MODS = {
    "primary": ["{s}"],
    "informational": ["what is {s}", "how does {s} work", "{s} guide", "{s} tips", "common {s} mistakes", "{s} checklist"],
    "question": ["how to choose {s}", "how much does {s} cost", "is {s} worth it", "when to use {s}", "why is {s} important"],
    "commercial": ["best {s}", "{s} comparison", "{s} alternatives", "{s} reviews", "top {s} providers"],
    "transactional": ["{s} pricing", "get a {s} quote", "hire {s}", "book {s}", "affordable {s}"],
    "audience": ["{s} for {a}"],
    "local": ["{s} in {c}", "{s} near me", "best {s} in {c}"],
}


def suggest(seed: str, niche: str = "", service: str = "", audience: str = "", location: str = "", limit: int = 80):
    base = [b.strip() for b in (seed, service) if b and b.strip()]
    if not base and niche:
        base = [niche.strip()]
    out, seen = [], set()
    for s in base:
        for group, pats in MODS.items():
            for p in pats:
                if ("{a}" in p and not audience) or ("{c}" in p and not location):
                    continue
                ph = p.format(s=s, a=audience, c=location).lower().strip()
                if ph not in seen:
                    seen.add(ph)
                    out.append({"phrase": ph, "source": "template-expansion", "group": group})
    return out[:limit]


def enrich(items, business: dict, seed_terms=None):
    ctx = [business.get("niche", ""), business.get("audience", ""), *business.get("services", []), *(seed_terms or [])]
    targets = {" ".join(tokens(t)) for t in business.get("target_keywords", [])}
    rows = []
    for it in items:
        ph = " ".join(it["phrase"].lower().split())
        c = classify(ph, business.get("name", ""), business.get("city", ""))
        rel = relevance(ph, ctx)
        rows.append({
            "phrase": ph, "intent": c["intent"], "intent_explanation": c["explanation"], "is_local": c["is_local"],
            "funnel_stage": c["funnel_stage"], "relevance": rel,
            "content_type": suggested_content_type(c["intent"], c["is_local"], ph),
            "priority": priority_score(c["intent"], c["is_local"], rel, ph, " ".join(tokens(ph)) in targets),
            "topic": it.get("topic") or " ".join(tokens(ph)[:2]) or "general",
            "source": it.get("source", "manual"),
        })
    return rows


def parse_csv(text: str, max_rows: int = 2000):
    """Header containing 'keyword'/'phrase' is used; else first column. Metric columns are ignored on purpose."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], ["Empty CSV"]
    header = [h.strip().lower() for h in rows[0]]
    idx, start = 0, 0
    for name in ("keyword", "phrase", "keywords", "query"):
        if name in header:
            idx, start = header.index(name), 1
            break
    errors, out, seen = [], [], set()
    for n, r in enumerate(rows[start:max_rows + start], start=start + 1):
        if len(r) <= idx or not r[idx].strip():
            errors.append(f"Row {n}: empty keyword")
            continue
        ph = " ".join(r[idx].strip().lower().split())
        if len(ph) > 200:
            errors.append(f"Row {n}: too long")
        elif ph not in seen:
            seen.add(ph)
            out.append({"phrase": ph, "source": "csv-import"})
    return out, errors
