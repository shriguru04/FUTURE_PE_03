from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings

_s = get_settings()
_args = {"check_same_thread": False} if _s.database_url.startswith("sqlite") else {}
engine = create_engine(_s.database_url, connect_args=_args, pool_pre_ping=True)
if _s.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
