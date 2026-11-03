"""Token-overlap keyword clustering, content-plan generation and cannibalization detection."""
from collections import Counter
from .text import tokens, jaccard, slugify

THRESH = 0.34
CANNIBAL = 0.7


def cluster_keywords(kws: list) -> list:
    """kws: dicts with phrase, intent, priority. Greedy assignment, highest priority first."""
    clusters = []
    for k in sorted(kws, key=lambda x: (-x.get("priority", 0), len(x["phrase"]))):
        tk = set(tokens(k["phrase"]))
        best, score = None, 0.0
        for c in clusters:
            s = max(jaccard(tk, c["tokens"]), len(tk & c["tokens"]) / max(len(tk), 1) * 0.8)
            if s > score:
                best, score = c, s
        if best is not None and score >= THRESH:
            best["members"].append(k)
            best["tokens"] |= tk
        else:
            clusters.append({"members": [k], "tokens": set(tk)})
    result = []
    for c in clusters:
        freq = Counter(t for m in c["members"] for t in set(tokens(m["phrase"])))

        def cover(m):
            ts = set(tokens(m["phrase"]))
            return sum(freq[t] for t in ts) / max(len(ts), 1) - 0.05 * len(m["phrase"].split())

        pillar = max(c["members"], key=lambda m: (cover(m), m.get("priority", 0)))
        top = [t for t, _ in freq.most_common(2)]
        result.append({"name": " ".join(top).title() or pillar["phrase"].title(), "pillar": pillar, "members": c["members"]})
    return sorted(result, key=lambda r: -len(r["members"]))


def title_for(phrase: str, content_type: str) -> str:
    t = phrase.strip().title()
    return {
        "how_to": f"{t}: Step-by-Step Guide",
        "comparison": f"{t}: How to Compare Your Options",
        "faq": f"{t.rstrip('?')}? Answers to Common Questions",
        "service_page": f"{t}: What's Included and What to Expect",
        "local_service_page": f"{t}: Local Service Guide",
    }.get(content_type, f"{t}: A Practical Guide")


def build_plan(cluster: dict) -> dict:
    pillar = cluster["pillar"]
    items = [{"keyword": pillar, "is_pillar": True, "secondary": []}]
    cannibal, kept = [], [pillar]
    for m in cluster["members"]:
        if m is pillar:
            continue
        dup = next((o for o in kept if m["intent"] == o["intent"]
                    and jaccard(tokens(m["phrase"]), tokens(o["phrase"])) >= CANNIBAL), None)
        if dup:
            cannibal.append({"keywords": [dup["phrase"], m["phrase"]], "intent": m["intent"],
                             "explanation": "Near-identical wording and the same search intent: one page can satisfy both. "
                                            "Use the second phrase as a secondary keyword instead of a new article."})
            next(i for i in items if i["keyword"] is dup)["secondary"].append(m["phrase"])
        else:
            kept.append(m)
            items.append({"keyword": m, "is_pillar": False, "secondary": []})
    return {"items": items, "cannibalization": cannibal}


def slug_unique(base: str, used: set) -> str:
    s = slugify(base) or "post"
    cand, n = s, 2
    while cand in used:
        cand = f"{s}-{n}"
        n += 1
    used.add(cand)
    return cand
