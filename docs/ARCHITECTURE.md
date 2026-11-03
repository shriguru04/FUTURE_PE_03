# Architecture
- **Frontend** `frontend/`: React 18 + Vite + React Router. Cookie auth (no tokens in JS), CSRF header from the readable `csrf_token` cookie, one fetch wrapper (`services/api.js`) with one refresh retry.
- **Backend** `backend/app`: `api/` (routers, thin) → `seo/` (pure, framework-free engines) and `ai/` (provider interface, prompts, Pydantic-validated outputs) → `models/` (SQLAlchemy 2). `security/` = auth, CSRF, rate limiting, SSRF-safe fetch.
- **AI workflow** (no agents/RAG/web grounding): validate input → build prompt with business context fenced as untrusted data → provider → JSON parse → Pydantic validation (one repair retry) → save → deterministic audit. `mock` provider returns labelled scaffolds.
- **SEO engines** are deterministic and never call an LLM: `intent.py`, `keywords.py`, `clustering.py`, `audit.py`, `links.py`.
- **Config** via env vars only (`core/config.py`). API keys never reach the browser or the database.
