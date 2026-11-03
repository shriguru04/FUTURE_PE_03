# Database
SQLAlchemy models in `backend/app/models/entities.py`: users, businesses, website_pages, clusters, keywords, articles (brief/outline/body JSON+text), revisions, seo_audits, internal_links,
calendar_entries, exports (file bytes stored in DB), generation_jobs (usage + errors), audit_events.
Constraints: unique (business_id, phrase) on keywords, unique (business_id, url) on pages, FKs with ON DELETE CASCADE/SET NULL, indexes on owner/business/status/created_at.
Keyword `search_volume`, `difficulty`, `cpc` are nullable and stay NULL unless a real provider fills them. SQLite enables `PRAGMA foreign_keys=ON`.
PostgreSQL: use `postgresql+psycopg://…`; generate the first Alembic revision (see README).
