"""Pure-Python engine tests (no web framework needed)."""
from app.seo import audit, clustering, intent, keywords, links
from app.seo.text import slugify

B = {"name": "Acme Plumbing", "niche": "plumbing", "services": ["drain cleaning"], "audience": "homeowners", "city": "Pune", "target_keywords": ["drain cleaning"]}


def test_intent_rules():
    assert intent.classify("how to unclog a drain")["intent"] == "informational"
    assert intent.classify("best crm software for small businesses")["intent"] == "commercial_investigation"
    assert intent.classify("drain cleaning pricing")["intent"] == "transactional"
    assert intent.classify("plumber near me")["is_local"] is True
    assert intent.classify("acme plumbing login", brand="Acme Plumbing")["intent"] == "navigational"
    assert "contains" in intent.classify("best crm")["explanation"]


def test_keyword_rows_never_invent_metrics():
    rows = keywords.enrich(keywords.suggest("drain cleaning", location="Pune"), B)
    assert rows and all("search_volume" not in r and "difficulty" not in r for r in rows)
    assert all(0 <= r["priority"] <= 100 for r in rows)


def test_csv_import_ignores_metrics_and_dedupes():
    items, errs = keywords.parse_csv("keyword,volume\nDrain Cleaning,9999\ndrain  cleaning,1\n,5\n")
    assert [i["phrase"] for i in items] == ["drain cleaning"] and len(errs) == 1


def test_clustering_and_cannibalization():
    k = [{"phrase": p, "intent": "informational", "priority": 50} for p in
         ["drain cleaning cost", "drain cleaning costs", "water heater repair", "water heater repair guide"]]
    cs = clustering.cluster_keywords(k)
    assert len(cs) == 2
    plan = clustering.build_plan(next(c for c in cs if "drain" in c["pillar"]["phrase"]))
    assert plan["cannibalization"], "near-identical phrases with same intent must be flagged"
    assert len(plan["items"]) == 1


def test_audit_flags_and_states():
    body = "# T\n\n#### Skipped\n\nOver 80% of people agree. " + "word " * 5
    r = audit.audit({"seo_title": "x", "meta_description": "", "slug": "Bad Slug", "body_markdown": body, "primary_keyword": "drain cleaning"})
    st = {c["id"]: c["status"] for c in r["checks"]}
    assert st["title_length"] == "needs_improvement" and st["meta_present"] == "needs_improvement"
    assert st["heading_hierarchy"] == "needs_improvement" and st["slug_quality"] == "needs_improvement"
    assert st["claims_evidence"] == "requires_review" and st["external_sources"] == "requires_review"
    assert "not a Google ranking score" in r["disclaimer"].replace("Not a Google ranking score", "not a Google ranking score")


def test_audit_clean_article_h1_rule():
    r = audit.audit({"body_markdown": "# A\n\n# B\n"})
    assert {c["id"]: c["status"] for c in r["checks"]}["single_h1"] == "needs_improvement"


def test_links_never_invent_urls():
    arts = [{"id": 1, "title": "P", "primary_keyword": "drain cleaning", "secondary_keywords": [], "cluster_id": 1, "is_pillar": True,
             "body_markdown": "Read about clogged drain cost.", "status": "draft", "target_url": None, "slug": "p"},
            {"id": 2, "title": "C", "primary_keyword": "clogged drain cost", "secondary_keywords": [], "cluster_id": 1, "is_pillar": False,
             "body_markdown": "See drain cleaning basics.", "status": "draft", "target_url": None, "slug": "c"}]
    r = links.recommend(arts, [])
    assert all(x["target_url"] is None and x["status"] == "proposed_future_page" for x in r["recommendations"])
    assert r["coverage"] == "limited"


def test_slugify():
    assert slugify("Hello, World! 2026") == "hello-world-2026"
