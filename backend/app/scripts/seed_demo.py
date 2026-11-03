"""DEMO DATA ONLY. Creates demo@example.com with a clearly labelled demo business. Not for production."""
from sqlalchemy import select
from ..core.db import Base, SessionLocal, engine
from ..models import Business, User
from ..security.auth import hash_password

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == "demo@example.com")):
            u = User(email="demo@example.com", password_hash=hash_password("demo-password-123"), role="seo_professional")
            db.add(u)
            db.flush()
            db.add(Business(owner_id=u.id, name="[DEMO] Example Plumbing Co", website_url="https://example.com", niche="plumbing",
                            services=["drain cleaning", "water heater repair"], audience="homeowners", country="India", city="Pune",
                            conversion_goal="Request a quote", target_keywords=["drain cleaning"]))
            db.commit()
    print("demo user: demo@example.com / demo-password-123  (DEMO ONLY)")
