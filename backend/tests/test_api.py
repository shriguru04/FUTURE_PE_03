"""Integration tests using FastAPI TestClient with the mock AI provider. Requires: pip install -r requirements.txt"""
import pytest

BIZ = {"name": "Acme Plumbing", "niche": "plumbing", "services": ["drain cleaning"], "audience": "homeowners", "city": "Pune",
       "conversion_goal": "Request a quote", "website_url": "https://example.com"}


def mk_business(c):
    r = c.post("/api/v1/businesses", json=BIZ)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_auth_flow_and_csrf(client):
    assert client.get("/api/v1/auth/me").json()["email"] == "a@example.com"
    bad = client.post("/api/v1/businesses", json=BIZ, headers={"X-CSRF-Token": "wrong"})
    assert bad.status_code == 403
    client.post("/api/v1/auth/logout")
    client.cookies.clear()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_register_validation(client):
    r = client.post("/api/v1/auth/register", json={"email": "bad", "password": "short"})
    assert r.status_code == 422


def test_login_wrong_password(client):
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "nope-nope-nope"}).status_code == 401


def test_full_workflow_and_isolation(client, other):
    bid = mk_business(client)
    r = client.post("/api/v1/keywords/research", json={"business_id": bid, "seed": "drain cleaning"})
    assert r.status_code == 200 and r.json()["created"]
    assert "Unavailable" in r.json()["metrics_note"]
    imp = client.post("/api/v1/keywords/import", json={"business_id": bid, "csv_text": "keyword\nsewer line repair\nsewer line repair cost\n"})
    assert imp.json()["imported"] == 2
    cl = client.post("/api/v1/clusters/generate", json={"business_id": bid})
    assert cl.status_code == 200 and cl.json()["clusters"]
    arts = client.get(f"/api/v1/content/articles?business_id={bid}").json()
    aid = arts[0]["id"]
    assert client.post("/api/v1/content/articles/generate", json={"article_id": aid}).status_code == 422  # outline required
    o = client.post("/api/v1/content/outlines/generate", json={"article_id": aid})
    assert o.status_code == 200 and o.json()["outline"]["sections"]
    g = client.post("/api/v1/content/articles/generate", json={"article_id": aid})
    assert g.status_code == 200
    assert g.json()["article"]["generation_meta"]["mock"] is True
    edit = client.patch(f"/api/v1/content/articles/{aid}", json={"body_markdown": g.json()["article"]["body_markdown"] + "\n\nEdited."})
    assert edit.status_code == 200
    assert len(client.get(f"/api/v1/content/articles/{aid}/revisions").json()) >= 2
    au = client.post("/api/v1/seo/audit", json={"article_id": aid})
    assert au.status_code == 201 and au.json()["checks"]
    lk = client.post("/api/v1/internal-links/recommend", json={"business_id": bid})
    assert lk.status_code == 200 and lk.json()["coverage"] == "limited"
    for fmt in ("md", "txt", "docx", "pdf", "csv_keywords", "csv_calendar"):
        x = client.post("/api/v1/exports", json={"business_id": bid, "article_id": aid, "format": fmt})
        assert x.status_code == 201, (fmt, x.text)
        d = client.get(f"/api/v1/exports/{x.json()['id']}")
        assert d.status_code == 200 and len(d.content) > 20
    # isolation: another user gets 404 on everything
    assert other.get(f"/api/v1/businesses/{bid}").status_code == 404
    assert other.get(f"/api/v1/content/articles/{aid}").status_code == 404
    assert other.get(f"/api/v1/keywords?business_id={bid}").status_code == 404
    assert other.post("/api/v1/seo/audit", json={"article_id": aid}).status_code == 404
    assert other.post("/api/v1/exports", json={"business_id": bid, "format": "md"}).status_code == 404
    assert other.delete(f"/api/v1/businesses/{bid}").status_code == 404


def test_keyword_manual_override(client):
    bid = mk_business(client)
    k = client.post("/api/v1/keywords/research", json={"business_id": bid, "seed": "drain cleaning"}).json()["created"][0]
    r = client.patch(f"/api/v1/keywords/{k['id']}", json={"intent": "transactional"})
    assert r.json()["intent_overridden"] is True


def test_local_requires_context(client):
    bid = mk_business(client)
    r = client.post("/api/v1/local-seo/generate", json={"business_id": bid, "service": "drain cleaning", "city": "Pune", "local_context": "short", "local_facts": ["a"]})
    assert r.status_code == 422


def test_ssrf_blocked(client):
    bid = mk_business(client)
    client.patch(f"/api/v1/businesses/{bid}", json={"website_url": "http://127.0.0.1/"})
    r = client.post(f"/api/v1/businesses/{bid}/analyze-website")
    assert r.status_code == 422 and r.json()["error"]["code"] == "blocked_destination"


def test_admin_requires_role(client):
    assert client.get("/api/v1/admin/users").status_code == 403


def test_rate_limit(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("AI_RATE_PER_MINUTE", "2")
    bid = mk_business(client)
    codes = [client.post("/api/v1/keywords/import", json={"business_id": bid, "csv_text": f"k{i}"}).status_code for i in range(4)]
    assert 429 in codes


def test_dashboard_counts_are_real(client):
    assert client.get("/api/v1/dashboard").json()["articles_total"] == 0
