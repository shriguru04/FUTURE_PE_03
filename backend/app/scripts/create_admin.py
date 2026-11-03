"""Usage: python -m app.scripts.create_admin admin@example.com 'a-long-password'"""
import sys
from sqlalchemy import select
from ..core.db import Base, SessionLocal, engine
from ..models import User
from ..security.auth import hash_password

if __name__ == "__main__":
    email, pw = sys.argv[1].lower(), sys.argv[2]
    if len(pw) < 10:
        sys.exit("password must be at least 10 characters")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == email))
        if u:
            u.role = "admin"
        else:
            db.add(User(email=email, password_hash=hash_password(pw), role="admin"))
        db.commit()
    print("admin ready:", email)
