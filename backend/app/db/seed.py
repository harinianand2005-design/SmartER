from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal, init_db
from app.models import User, UserRole
from app.services.security import hash_password


def seed_demo_users() -> int:
    settings = get_settings()
    credentials = [
        (settings.demo_admin_email, settings.demo_admin_password, UserRole.ADMIN, "SmartER Administrator"),
        (settings.demo_triage_email, settings.demo_triage_password, UserRole.TRIAGE_NURSE, "Demo Triage Nurse"),
        (settings.demo_health_authority_email, settings.demo_health_authority_password, UserRole.HEALTH_AUTHORITY, "Demo Health Authority"),
    ]
    if any(not password for _, password, _, _ in credentials):
        raise RuntimeError("Set all DEMO_*_PASSWORD values before running the seed command.")

    init_db()
    created = 0
    with SessionLocal() as db:
        for email, password, role, full_name in credentials:
            if db.scalar(select(User).where(User.email == email)):
                continue
            db.add(User(email=email, full_name=full_name, password_hash=hash_password(password), role=role))
            created += 1
        db.commit()
    return created


if __name__ == "__main__":
    print(f"Created {seed_demo_users()} demo users.")