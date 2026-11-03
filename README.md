# AI SEO Blog & Content Cluster Generator

Full-stack app (FastAPI + SQLAlchemy + React/Vite) that turns a business profile into keyword suggestions, intent classification,
topic clusters, outlines, articles, deterministic SEO audits, internal-link recommendations, local-SEO assets, a content calendar and exportable SEO Blog Packs.

> **Read `docs/STATUS.md` first.** It states exactly what was executed and verified in the sandbox where this was generated, and what was not.
> Short version: the SEO engines were run and pass their tests; the FastAPI app, frontend build, Alembic migration, Docker and real LLM providers were **not** executed.

## Quick start (development, SQLite, mock AI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # optional; defaults work for dev
uvicorn app.main:app --reload                           # tables are auto-created in development
python -m app.scripts.seed_demo                         # optional DEMO user: demo@example.com / demo-password-123
python -m app.scripts.create_admin you@example.com 'a-long-password'
pytest                                                  # run all tests

cd ../frontend
npm install
npm run dev                                             # http://localhost:5173 (proxies /api to :8000)
```
Dependencies of `pytest`: `fastapi`, `httpx` (TestClient), all in requirements.txt.

## Migrations (PostgreSQL / production)
Alembic is configured, but **no initial revision is checked in** (it could not be generated or tested without the database drivers installed).
Generate and review it once, then commit it:
```bash
cd backend && DATABASE_URL=postgresql+psycopg://user:pass@host/db alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
The backend Docker image runs `alembic upgrade head` on start, so generate the revision before building it.

## AI providers
`AI_PROVIDER=mock` (default): deterministic scaffolds, clearly labelled, no LLM and no key.
`openai`: any OpenAI-compatible `/chat/completions` endpoint (OpenAI, or local Ollama/vLLM/LM Studio via `AI_BASE_URL=http://localhost:11434/v1`).
`anthropic`: Messages API. Gemini is **not implemented**. Set `AI_MODEL` and `AI_API_KEY` in the server environment only.

## Docker
`SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") docker compose up --build` (after generating the migration). Frontend is not containerised; deploy it as a static site behind the same origin as the API.

## Docs
`docs/STATUS.md` (verified vs unverified), `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/API.md`, `docs/SECURITY.md`.
