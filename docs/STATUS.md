# Implementation status (honest)

Generated in a sandbox with **no network access** and without FastAPI, SQLAlchemy, Pydantic, pytest or npm packages installed.

## Executed and passing (8 tests, run with a minimal runner)
`backend/tests/test_seo_engines.py`: intent rules, keyword enrichment (no fabricated metrics), CSV import, clustering + cannibalization,
audit statuses, single-H1 rule, link engine (no invented URLs), slugify. Every Python file also passes `py_compile`.

## Written but NOT executed
- FastAPI app, all routers, SQLAlchemy models, auth/CSRF/rate-limit middleware (`tests/test_api.py` covers them; never run).
- `tests/test_ai_validation.py` (needs pydantic).
- Export *endpoints* and the pack builder (DB queries). The DOCX and PDF renderers themselves WERE run in isolation on a sample Markdown string and produced a valid .docx (PK header) and .pdf (%PDF header).
- Frontend (React/Vite): never installed, built or opened in a browser. No frontend tests exist.
- Alembic: configured; **initial migration not generated**.
- Dockerfile / docker-compose.yml: never built.
- Real LLM calls (OpenAI-compatible, Anthropic): never called. Mock provider only is exercised by tests.
- SSRF fetcher: written, tested only by the loopback-rejection test in test_api.py (not run).

Expect first-run fixes. Run `pytest` first; failures there are the authoritative list.

## Implemented (code present)
Auth (scrypt, JWT in HttpOnly cookies, refresh, double-submit CSRF, roles); business CRUD + single-page website fetch; keyword suggestions (templates, optional LLM) and CSV import;
rule-based intent with explanations + manual override; token-overlap clustering, pillar/cluster plan, cannibalization warnings; briefs, outlines, articles, revisions, duplicate;
deterministic SEO audit with passed / needs improvement / not checked / requires review and method labels; internal-link recommendations with issue detection;
local SEO generator with required local facts; calendar; exports (md, txt, docx, pdf, csv); dashboard from DB counts; admin users/usage/errors/events/health; per-user daily AI quota and rate limits.

## Partially implemented
- Provider layer: mock, OpenAI-compatible, Anthropic only.
- Orphan/link analysis: limited to saved articles/pages; labelled "limited" unless the user says the inventory is complete.
- Website analysis fetches one URL (homepage), not a crawl.
- Revision history stored; no diff/restore UI.
- Project roles: owner-only access; no sharing between users (SEO pros manage multiple *businesses*, not shared clients).

## Not implemented
Gemini provider; real keyword-metric provider (interface is just `seo/keywords.py` today; no pluggable class); external source verification / web grounding;
token-level usage accounting for non-mock providers beyond what the API returns; server-side refresh-token revocation; admin-editable AI settings in the UI (env only);
frontend tests; deployment verification; chart visualisations; DOCX/PDF table rendering (tables render as text rows).
