import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import admin, auth, businesses, content, keywords, planning, seo
from .core import errors
from .core.config import get_settings
from .core.db import Base, engine
from .security.auth import csrf_middleware

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_):
    # Dev convenience only. Production must use `alembic upgrade head`.
    if os.getenv("AUTO_CREATE_TABLES", "true" if get_settings().env != "production" else "false").lower() == "true":
        from . import models  # noqa: F401
        Base.metadata.create_all(engine)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="AI SEO Blog & Content Cluster Generator", version="0.1.0", lifespan=lifespan,
                  docs_url="/api/docs" if s.env != "production" else None, openapi_url="/api/openapi.json" if s.env != "production" else None)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])
    app.middleware("http")(csrf_middleware)
    errors.install(app)
    for r in (auth.router, businesses.router, keywords.router, content.clusters, content.content, seo.seo, seo.links, seo.local,
              planning.calendar, planning.exports, planning.dash, admin.router):
        app.include_router(r)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}
    return app


app = create_app()
