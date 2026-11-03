# API (all under /api/v1; interactive docs at /api/docs in non-production)
Auth: cookies. All non-GET requests (except login/register) need header `X-CSRF-Token` = `csrf_token` cookie. Errors: `{"error":{"code","message"}}` (validation errors use FastAPI's `detail`).
Other users' resources return **404**, not 403.

| Group | Endpoints |
|---|---|
| auth | POST register, login, refresh, logout; GET me |
| businesses | GET/POST `/businesses`; GET/PATCH/DELETE `/{id}`; GET/POST `/{id}/pages`; POST `/{id}/analyze-website` (one URL, SSRF-guarded) |
| keywords | POST `/research`, POST `/import` (JSON `csv_text`), GET `?business_id=`, PATCH `/{id}` (manual intent) |
| clusters | POST `/generate`, GET `?business_id=`, GET `/{id}` |
| content | POST `/briefs`, `/outlines/generate`, `/articles/generate`; GET `/articles?business_id=`, GET/PATCH/DELETE `/articles/{id}`; POST `/articles/{id}/duplicate`; GET `/articles/{id}/revisions` |
| seo | POST `/seo/audit`, GET `/seo/audits/{id}`, GET `/seo/audits?article_id=` |
| internal-links | POST `/recommend`, GET `?business_id=` |
| local-seo | POST `/generate` (needs ≥80-char context and ≥2 local facts) |
| calendar | GET `?business_id=`, POST, PATCH/DELETE `/{id}` |
| exports | POST (format: md, txt, docx, pdf, csv_keywords, csv_calendar), GET list, GET `/{id}` download |
| dashboard | GET |
| admin (role=admin) | GET users, PATCH users/{id}, GET usage, events, errors, health |
Rate limits: `AUTH_RATE_PER_MINUTE` on login/register; `AI_RATE_PER_MINUTE` on AI, import and fetch routes (in-memory, per process); daily AI quota per user.
