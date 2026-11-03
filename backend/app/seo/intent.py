"""Rule-based search-intent classifier (heuristic, explainable, manually overridable)."""
from .text import tokens

INFORMATIONAL = {"how", "what", "why", "when", "guide", "tutorial", "tips", "ideas", "examples", "learn", "meaning",
                 "checklist", "steps", "explained", "difference", "definition", "benefits", "mistakes", "ways", "work"}
COMMERCIAL = {"best", "top", "vs", "versus", "review", "reviews", "compare", "comparison", "alternative", "alternatives",
              "pros", "cons", "ranked", "recommended"}
TRANSACTIONAL = {"buy", "price", "pricing", "prices", "cost", "quote", "hire", "order", "book", "booking", "discount",
                 "cheap", "affordable", "coupon", "deal", "purchase", "subscribe", "free trial", "estimate"}
NAVIGATIONAL = {"login", "log in", "sign in", "signin", "official", "website", "contact", "download", "portal"}
LOCAL = {"near me", "nearby", "local", "closest", "open now"}

FORMATS = {
    "informational": ("Educational guide / how-to article", "Understand or learn how to do something",
                      "Soft CTA: newsletter, checklist download, or related guide"),
    "commercial_investigation": ("Comparison or 'best of' guide with transparent evaluation criteria",
                                 "Evaluate options before choosing", "Medium CTA: compare plans, request a demo or consultation"),
    "transactional": ("Service/product page with pricing context, proof and clear steps",
                      "Take an action: buy, book or request a quote", "Direct CTA: get a quote, book, call, buy"),
    "navigational": ("Clear brand/destination page (contact, login, product page)", "Reach a specific site or page",
                     "Link directly to the destination"),
    "local": ("Local service page with area-specific details", "Find a provider in a specific area",
              "Direct CTA: call, get directions, book locally"),
}
FUNNEL = {"informational": "TOFU", "commercial_investigation": "MOFU", "transactional": "BOFU", "navigational": "BOFU"}


def _hits(p: str, words: set, vocab):
    return sorted(t for t in vocab if (" " + t + " ") in p or t in words)


def classify(phrase: str, brand: str = "", city: str = "") -> dict:
    p = " " + phrase.lower().strip() + " "
    words = set(p.replace("?", " ").split())
    brand_hit = bool(brand) and brand.lower() in p
    h = {"navigational": _hits(p, words, NAVIGATIONAL), "transactional": _hits(p, words, TRANSACTIONAL),
         "commercial_investigation": _hits(p, words, COMMERCIAL), "informational": _hits(p, words, INFORMATIONAL)}
    is_local = bool(_hits(p, words, LOCAL)) or (bool(city) and city.lower() in p)
    if phrase.strip().endswith("?"):
        h["informational"].append("?")
    if brand_hit:
        h["navigational"].append(f"brand:{brand}")
    intent = "informational"
    if brand_hit and h["navigational"]:
        intent = "navigational"
    elif h["transactional"]:
        intent = "transactional"
    elif h["commercial_investigation"]:
        intent = "commercial_investigation"
    elif h["informational"]:
        intent = "informational"
    elif h["navigational"]:
        intent = "navigational"
    if is_local and intent == "informational" and not h["informational"]:
        intent = "transactional"  # bare "near me"/city modifiers signal a search for a provider
        h["transactional"] = ["local modifier"]
    reasons = h[intent]
    if reasons:
        explanation = f"Classified as {intent.replace('_', ' ')} because the phrase contains: {', '.join(reasons)}."
    else:
        explanation = "No strong intent signal found; defaulted to informational. Review manually."
    if is_local:
        explanation += " Local modifier detected (near me / city name), so local intent is also flagged."
    fmt, goal, cta = FORMATS["local" if (is_local and intent == "transactional") else intent]
    return {"intent": intent, "is_local": is_local, "explanation": explanation, "content_format": fmt,
            "user_goal": goal, "cta": cta, "funnel_stage": FUNNEL[intent], "confidence": "heuristic"}


def relevance(phrase: str, context_terms: list) -> float:
    kt = set(tokens(phrase))
    ct = set()
    for t in context_terms:
        ct.update(tokens(t))
    if not kt or not ct:
        return 0.0
    return round(len(kt & ct) / len(kt), 2)


INTENT_WEIGHT = {"transactional": 30, "commercial_investigation": 25, "informational": 15, "navigational": 5}


def priority_score(intent: str, is_local: bool, rel: float, phrase: str, is_target: bool) -> int:
    """Internal heuristic 0-100. NOT based on search volume or difficulty (unavailable)."""
    s = 50 * rel + INTENT_WEIGHT.get(intent, 10) + (5 if is_local else 0)
    s += 10 if len(phrase.split()) >= 4 else 0
    s += 10 if is_target else 0
    return int(max(0, min(100, round(s))))


def suggested_content_type(intent: str, is_local: bool, phrase: str) -> str:
    if is_local and intent == "transactional":
        return "local_service_page"
    if phrase.lower().startswith("how to"):
        return "how_to"
    if intent == "commercial_investigation":
        return "comparison"
    if intent == "transactional":
        return "service_page"
    if phrase.strip().endswith("?") or phrase.lower().split()[0] in ("what", "why", "when", "can", "does", "is", "how"):
        return "faq"
    return "educational_guide"
